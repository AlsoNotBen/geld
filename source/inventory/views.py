"""
inventory/views.py
------------------------------------------------------------------------
The pages of the Inventory module. The data comes from three models:

    Item              the items. An item has no company yet, thus each
                      company sees all the items.
    ItemRelationship  a parent, a child, a type and a quantity. A kit is
                      an item that contains other items (see contents).
    StockMovement     a movement of the stock of the company. The quantity on hand and the
                      value of an item come from its movements (see
                      stock_levels).

The module has no model for a location, a minimum level, a holder or a
code format yet. Thus the pages show no figures for them.
"""
import datetime
from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, Count, DecimalField, F, Q, Sum, When
from django.shortcuts import redirect, render
from django.utils import timezone
from filestore.services import save_upload, validate
from .forms import ItemForm
from .models import Item, ItemRelationship, StockTakeSchedule, StockMovement

ZERO = Decimal("0")
T = Item.ItemType
D = StockMovement.Direction
STOCKED = [T.STOCK, T.CONSUMABLE, T.COMPONENT]     # The types that have a quantity on hand
CONTAINS = ItemRelationship.RelationshipType.CONTAINS
MOVED = {D.IN: "Received", D.OUT: "Issued", D.ADJUSTMENT: "Adjusted"}


# ___________________________________STOCK___________________________________________#
def signed(field):
    """A field of a movement with its sign: an OUT takes stock away."""
    return Case(When(direction=D.OUT, then=-F(field)), default=F(field), output_field=DecimalField())


def stock_levels(company):
    """The quantity on hand and the value of each item, from the stock
    movements of the company. Returns {item_id: (quantity, value)}."""
    rows = (StockMovement.objects.filter(company=company).values("item_id")
            .annotate(quantity=Sum(signed("quantity")), value=Sum(signed("total_cost"))))
    return {row["item_id"]: (row["quantity"], row["value"]) for row in rows}


def with_stock(items, levels):
    """Put the quantity on hand and the value on each item. Returns the items as a list."""
    items = list(items)
    for item in items:
        item.on_hand, item.value = levels.get(item.pk, (ZERO, ZERO))
    return items


def status_of(item):
    """The text and the tone of the status pill of an item."""
    if item.obsoleted:
        return "Obsolete", "idle"
    if not item.active:
        return "Inactive", "idle"
    if item.item_type in STOCKED:
        return ("In stock", "ok") if item.on_hand > 0 else ("Out of stock", "out")
    return "Active", "ok"


def with_status(items):
    for item in items:
        item.status, item.tone = status_of(item)
    return items


def movement_rows(company, limit=None, **filters):
    """The last stock movements, the newest first: the date, the text and
    the change with its sign. A movement has no reference."""
    movements = (StockMovement.objects.filter(company=company, **filters)
                 .select_related("item").order_by("-date", "-id")[:limit])
    return [{"date": m.date, "reference": "",
             "text": f"{MOVED[m.direction]} · {m.item.name}",
             "change": -m.quantity if m.direction == D.OUT else m.quantity} for m in movements]


def last_movements(company):
    """The date and the signed quantity of the last movement of each item. Returns {item_id: (date, change)}."""
    last = {}
    for m in StockMovement.objects.filter(company=company).order_by("date", "id"):
        last[m.item_id] = (m.date, -m.quantity if m.direction == D.OUT else m.quantity)
    return last


def matches(items, q):
    """The items with the text in the name, the code, the tag or the serial number."""
    if not q:
        return items
    return items.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(tag__icontains=q) | Q(serial__icontains=q))


# ___________________________________KITS____________________________________________#
def contents():
    """The children of each kit: {parent_id: [(child, quantity)]}. A kit is
    an item that contains other items (a Contains relationship)."""
    children = {}
    for relation in ItemRelationship.objects.filter(relationship_type=CONTAINS).select_related("child"):
        children.setdefault(relation.parent_id, []).append((relation.child, relation.quantity))
    return children


def buildable(kit_id, children, levels):
    """The number of kits that the stock on hand of the direct children can
    build, and the ids of the children that set that number."""
    ratios = {child.pk: int(max(levels.get(child.pk, (ZERO, ZERO))[0], ZERO) // quantity)
              for child, quantity in children.get(kit_id, []) if quantity > 0}
    if not ratios:
        return 0, set()
    count = min(ratios.values())
    return count, {pk for pk, ratio in ratios.items() if ratio == count}


# ___________________________________PAGES___________________________________________#
def overview(request):
    """The position of the inventory today, the items that need an action,
    the items that came in last and the last stock movements."""
    company = request.company
    today = timezone.localdate()
    levels = stock_levels(company)
    items = with_status(with_stock(Item.objects.order_by("name"), levels))
    active = [i for i in items if i.active and not i.obsoleted]
    out = [i for i in active if i.item_type in STOCKED and i.on_hand <= 0]
    due = list(StockTakeSchedule.objects.filter(active=True, next_due__lte=today).select_related("item"))
    for schedule in due:
        schedule.item.on_hand = levels.get(schedule.item_id, (ZERO, ZERO))[0]
    week = StockMovement.objects.filter(company=company, date__gt=today - datetime.timedelta(days=7))
    count = {t: sum(1 for i in active if i.item_type == t) for t in T.values}
    return render(request, "inventory/overview.html", {
        "page_title": "Overview",
        "today": today,
        "inventory_value": sum((value for _, value in levels.values()), ZERO),
        "asset_count": count[T.ASSET],
        "stock_count": count[T.STOCK],
        "consumable_count": count[T.CONSUMABLE],
        "component_count": count[T.COMPONENT],
        "kit_count": len(contents()),
        "inactive_count": len(items) - len(active),
        "out": out,
        "due": due,
        "movement_count": week.count(),
        "recent_items": sorted(items, key=lambda i: i.pk, reverse=True)[:6],
        "movements": movement_rows(company, 7),
        "week_change": week.aggregate(total=Sum(signed("quantity")))["total"] or ZERO,
    })


def month_starts(today, count=12):
    """The first day of each of the last months, the oldest first."""
    months = []
    for back in range(count - 1, -1, -1):
        year, month = divmod(today.year * 12 + today.month - 1 - back, 12)
        months.append(datetime.date(year, month + 1, 1))
    return months


def line_points(values, left=10, right=590, top=30, bottom=150):
    """The points of the line of a chart with a viewBox of 600 by 160."""
    low, high = min(values), max(values)
    step = (right - left) / (len(values) - 1)
    return " ".join(f"{left + i * step:.0f},{bottom - float((v - low) / ((high - low) or 1)) * (bottom - top):.0f}"
                    for i, v in enumerate(values))


def ranked(totals, limit=6):
    """The largest totals as rows of a rank chart: the name, the total and
    the width of the bar in percent of the largest."""
    rows = sorted(((name, total) for name, total in totals.items() if total), key=lambda r: r[1], reverse=True)[:limit]
    top = rows[0][1] if rows else 1
    return [{"name": name, "total": total, "width": round(total / top * 100)} for name, total in rows]


def analytics(request):
    """The charts of the stock movements of the last 12 months, and the
    figures of the last 30 days."""
    company = request.company
    today = timezone.localdate()
    months = month_starts(today)
    since = today - datetime.timedelta(days=29)
    moves = StockMovement.objects.filter(company=company)
    window = list(moves.filter(date__gte=months[0], date__lte=today)
                  .values("date", "direction", "quantity", "total_cost", "item__name", "item__item_type"))
    opening = moves.filter(date__lt=months[0]).aggregate(total=Sum(signed("total_cost")))["total"] or ZERO

    # Chart 1 and 2: the units received and issued, and the value at the end, of each month.
    received, issued, change = ({m: ZERO for m in months} for _ in range(3))
    for row in window:
        month = row["date"].replace(day=1)
        if row["direction"] == D.IN:
            received[month] += row["quantity"]
        elif row["direction"] == D.OUT:
            issued[month] += row["quantity"]
        change[month] += -row["total_cost"] if row["direction"] == D.OUT else row["total_cost"]
    top = max([*received.values(), *issued.values()]) or 1
    values, value = [], opening
    for month in months:
        value += change[month]
        values.append(value)
    points = line_points(values)

    # Chart 3, 4 and the table: the last 30 days.
    recent = [row for row in window if row["date"] >= since]
    moved, used = {}, {}
    by_type = {t: {"label": label, "received": ZERO, "issued": ZERO} for t, label in T.choices}
    for row in recent:
        quantity = row["quantity"]
        moved[row["item__name"]] = moved.get(row["item__name"], ZERO) + abs(quantity)
        if row["direction"] == D.IN:
            by_type[row["item__item_type"]]["received"] += quantity
        elif row["direction"] == D.OUT:
            by_type[row["item__item_type"]]["issued"] += quantity
            if row["item__item_type"] == T.CONSUMABLE:
                used[row["item__name"]] = used.get(row["item__name"], ZERO) + quantity
    levels = stock_levels(company)
    items = with_stock(Item.objects.all(), levels)
    for row_type, row in by_type.items():
        row["net"] = row["received"] - row["issued"]
        row["value"] = sum((i.value for i in items if i.item_type == row_type), ZERO)

    # The ring: the active items by type.
    circle = Decimal("339.29")              # The length of the circle of the ring: 2 × π × 54
    active = [i for i in items if i.active and not i.obsoleted]
    parts, start = [], ZERO
    for n, (item_type, label) in enumerate(T.choices, 1):
        count = sum(1 for i in active if i.item_type == item_type)
        length = circle * count / len(active) if active else ZERO
        parts.append({"label": label, "count": count, "color": f"chart-c{n}", "length": f"{length:.2f}",
                      "offset": f"{-start:.2f}"})
        start += length

    rows = list(by_type.values())
    total_in, total_out = sum((r["received"] for r in rows), ZERO), sum((r["issued"] for r in rows), ZERO)
    return render(request, "inventory/analytics.html", {
        "page_title": "Analytics",
        "inventory_value": sum((i.value for i in items), ZERO),
        "received": total_in,
        "issued": total_out,
        "net": total_in - total_out,
        "columns": [{"label": f"{m:%b}", "received": received[m], "issued": issued[m],
                     "in": round(received[m] / top * 100), "out": round(issued[m] / top * 100)} for m in months],
        "points": points,
        "first": {"label": f"{months[0]:%b %Y}", "value": values[0]},
        "last": {"label": f"{months[-1]:%b %Y}", "value": values[-1]},
        "top_moved": ranked(moved),
        "top_used": ranked(used),
        "parts": parts,
        "item_count": len(active),
        "by_type": rows,
        "circle": circle,
    })


def reports(request):
    return render(request, "inventory/reports.html", {"page_title": "Reports"})


def assets(request):
    """The asset register. The text filter finds the name, the code, the tag
    or the serial number. The status filter is active or inactive."""
    q, status = request.GET.get("q", "").strip(), request.GET.get("status", "")
    every = list(Item.objects.filter(item_type=T.ASSET))
    listed = matches(Item.objects.filter(item_type=T.ASSET), q).order_by("name")
    if status in ("active", "inactive"):
        listed = listed.filter(active=status == "active")
    return render(request, "inventory/assets.html", {
        "page_title": "Assets",
        "assets": with_status(list(listed)),
        "total": len(every),
        "active": sum(1 for a in every if a.active),
        "inactive": sum(1 for a in every if not a.active),
        "depreciating": sum(1 for a in every if a.depreciate),
        "cost": sum((a.cost or ZERO for a in every), ZERO),
        "q": q, "status": status,
    })


def stock(request):
    """The stock items, the quantity on hand of each and the last movements.
    The text filter finds the name, the code, the tag or the serial number."""
    company = request.company
    q = request.GET.get("q", "").strip()
    levels = stock_levels(company)
    every = with_stock(Item.objects.filter(item_type=T.STOCK, active=True), levels)
    listed = with_status(with_stock(matches(Item.objects.filter(item_type=T.STOCK), q).order_by("name"), levels))
    last = last_movements(company)
    for item in listed:
        item.last = last.get(item.pk)
    due = StockTakeSchedule.objects.filter(active=True, next_due__lte=timezone.localdate(), item__item_type=T.STOCK)
    return render(request, "inventory/stock.html", {
        "page_title": "Stock",
        "items": listed,
        "item_count": len(every),
        "units": sum((i.on_hand for i in every), ZERO),
        "value": sum((i.value for i in every), ZERO),
        "out_count": sum(1 for i in every if i.on_hand <= 0),
        "due_count": due.count(),
        "listed_units": sum((i.on_hand for i in listed), ZERO),
        "movements": movement_rows(company, 6, item__item_type=T.STOCK),
        "q": q,
    })


def consumables(request):
    """The consumables, the quantity on hand of each and the quantity that the last 30 days used."""
    company = request.company
    since = timezone.localdate() - datetime.timedelta(days=29)
    levels = stock_levels(company)
    items = with_status(with_stock(Item.objects.filter(item_type=T.CONSUMABLE).order_by("name"), levels))
    issues = StockMovement.objects.filter(company=company, direction=D.OUT, date__gte=since,
                                          item__item_type=T.CONSUMABLE)
    used = dict(issues.values_list("item_id").annotate(total=Sum("quantity")))
    for item in items:
        item.used = used.get(item.pk, ZERO)
    active = [i for i in items if i.active and not i.obsoleted]
    return render(request, "inventory/consumables.html", {
        "page_title": "Consumables",
        "items": items,
        "line_count": len(active),
        "value": sum((i.value for i in active), ZERO),
        "used_value": issues.aggregate(total=Sum("total_cost"))["total"] or ZERO,
        "out_count": sum(1 for i in active if i.on_hand <= 0),
        "on_hand": sum((i.on_hand for i in items), ZERO),
        "used": sum((i.used for i in items), ZERO),
    })


def kits(request):
    """The kits, then the components that the kits contain. A kit shows the
    number that the stock of its components can build (see buildable)."""
    levels = stock_levels(request.company)
    children = contents()
    kit_items = with_stock(Item.objects.filter(pk__in=children).order_by("name"), levels)
    for kit in kit_items:
        kit.parts = children[kit.pk]
        kit.can_build = buildable(kit.pk, children, levels)[0]
    components = {child.pk: child for parts in children.values() for child, _ in parts}
    component_items = with_status(with_stock(sorted(components.values(), key=lambda i: i.name), levels))
    return render(request, "inventory/kits.html", {
        "page_title": "Kit & Components",
        "kits": kit_items,
        "components": component_items,
        "on_hand": sum((kit.on_hand for kit in kit_items), ZERO),
        "short_count": sum(1 for kit in kit_items if not kit.can_build),
    })


def bom(request):
    """The bill of materials of one kit (?kit=pk, else the first kit): the
    kits with the number that each can build, the assembly map of the kit
    and its direct components."""
    levels = stock_levels(request.company)
    children = contents()
    kit_list = list(Item.objects.filter(pk__in=children).order_by("name"))
    for kit in kit_list:
        kit.can_build = buildable(kit.pk, children, levels)[0]
        kit.part_count = len(children[kit.pk])
    kit = next((k for k in kit_list if str(k.pk) == request.GET.get("kit")), kit_list[0] if kit_list else None)

    graph, parts, limits = {"direction": "LR", "nodes": [], "edges": []}, [], set()
    if kit:
        kit.can_build, limits = buildable(kit.pk, children, levels)
        seen = set()

        def visit(item, depth):
            """Add the item and its children to the map. An item shows one time only."""
            if item.pk in seen:
                return
            seen.add(item.pk)
            on_hand = levels.get(item.pk, (ZERO, ZERO))[0]
            if depth == 0:
                kind, status, count = "kit", "build" if kit.can_build else "idle", f"{kit.can_build} buildable"
            else:
                kind = "sub" if item.pk in children else "part"
                status, count = "ok" if on_hand > 0 else "out", f"{on_hand.normalize():f}"
            graph["nodes"].append({"id": str(item.pk), "name": item.name, "code": item.sku or "", "kind": kind,
                                   "status": status, "count": count})
            for child, quantity in children.get(item.pk, []):
                graph["edges"].append({"from": str(item.pk), "to": str(child.pk),
                                       "qty": f"× {quantity.normalize():f}", "limit": depth == 0 and child.pk in limits})
                visit(child, depth + 1)

        visit(kit, 0)
        for child, quantity in children[kit.pk]:
            on_hand = levels.get(child.pk, (ZERO, ZERO))[0]
            parts.append({"item": child, "quantity": quantity, "on_hand": on_hand,
                          "tone": "ok" if on_hand >= quantity else "low" if on_hand > 0 else "out"})
        parts.sort(key=lambda p: p["on_hand"], reverse=True)

    return render(request, "inventory/bom.html", {
        "page_title": "Bill of Materials",
        "kits": kit_list,
        "kit": kit,
        "graph": graph,
        "parts": parts,
        "limit": next((p["item"] for p in parts if p["item"].pk in limits), None),
        "short_count": sum(1 for k in kit_list if not k.can_build),
        "choices": Item.objects.filter(active=True).exclude(pk=kit.pk if kit else None).order_by("name"),
    })


def codes(request):
    return render(request, "inventory/codes.html", {"page_title": "Codes & Tags", "item_types": T.choices})


def items(request):
    """The item editor. The list at the left finds the items (?q, ?item_type).
    A click selects an item (?item=pk): the form then changes that item, and
    the right column shows its relationships. Without a selection, the form
    makes a new item."""
    selected = Item.objects.filter(pk=request.GET.get("item") or None).first()
    form = ItemForm(request.POST or None, instance=selected)

    if request.method == "POST" and form.is_valid():
        uploads = request.FILES.getlist("files")
        try:
            # Validate every file first, so a bad file stores nothing.
            for upload in uploads:
                validate(upload)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            with transaction.atomic():
                item = form.save()
                item.files.add(*(save_upload(u, request.user) for u in uploads))
            messages.success(request, f"Saved {item.name}.")
            return redirect(f"{request.path}?item={item.pk}")  # Post/Redirect/Get

    q, item_type = request.GET.get("q", "").strip(), request.GET.get("item_type", "")
    listed = matches(Item.objects.all(), q).order_by("name")
    if item_type in T.values:
        listed = listed.filter(item_type=item_type)
    listed = listed.annotate(relation_count=Count("child_relationships", distinct=True)
                             + Count("parent_relationships", distinct=True))
    relationships = []
    if selected:
        relationships = (
            [{"item": r.child, "type": r.get_relationship_type_display(), "role": "Parent of", "quantity": r.quantity}
             for r in selected.child_relationships.select_related("child")]
            + [{"item": r.parent, "type": r.get_relationship_type_display(), "role": "Child of", "quantity": r.quantity}
               for r in selected.parent_relationships.select_related("parent")])
    return render(request, "inventory/items.html", {
        "page_title": "Items",
        "form": form,
        "selected": selected,
        "items": with_status(with_stock(listed, stock_levels(request.company))),
        "item_count": Item.objects.count(),
        "relationships": relationships,
        "relationship_types": ItemRelationship.RelationshipType.choices,
        "related_choices": Item.objects.exclude(pk=selected.pk if selected else None).order_by("name"),
        "q": q, "item_type": item_type,
    })
