"""
inventory/views.py
------------------------------------------------------------------------
The pages of the Inventory module. The data comes from three models:

    Item              the items of the company.
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
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from filestore.services import save_upload, validate, validate_image
from .forms import CategoryForm, ItemForm, ManufacturerForm, ModelEntryForm
from shared.models import Country, Entity, Location
from .models import Checkout, Item, ItemRelationship, ItemType, StockTakeSchedule, StockMovement

ZERO = Decimal("0")
T = ItemType
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


def company_items(company):
    """The items of the company with their model. Item.name reads the model."""
    return Item.objects.filter(company=company).select_related("model")


def in_use(item):
    """An active item of an active model."""
    return item.active and item.model.active


def status_of(item):
    """The text and the tone of the status pill of an item."""
    if not item.model.active:
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
                 .select_related("item__model").order_by("-date", "-id")[:limit])
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
    return items.filter(Q(model__name__icontains=q) | Q(sku__icontains=q) | Q(tag__icontains=q) | Q(serial__icontains=q))


# ___________________________________KITS____________________________________________#
def contents(company):
    """The children of each kit of the company: {parent_id: [(child, quantity)]}.
    A kit is an item that contains other items (a Contains relationship)."""
    children = {}
    for relation in (ItemRelationship.objects.filter(parent__company=company, relationship_type=CONTAINS)
                     .select_related("child__model")):
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
    items = with_status(with_stock(company_items(company).order_by("model__name"), levels))
    active = [i for i in items if in_use(i)]
    out = [i for i in active if i.item_type in STOCKED and i.on_hand <= 0]
    due = list(StockTakeSchedule.objects.filter(item__company=company, active=True, next_due__lte=today)
               .select_related("item__model"))
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
        "kit_count": len(contents(company)),
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
                  .values("date", "direction", "quantity", "total_cost", "item__model__name", "item__item_type"))
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
        moved[row["item__model__name"]] = moved.get(row["item__model__name"], ZERO) + abs(quantity)
        if row["direction"] == D.IN:
            by_type[row["item__item_type"]]["received"] += quantity
        elif row["direction"] == D.OUT:
            by_type[row["item__item_type"]]["issued"] += quantity
            if row["item__item_type"] == T.CONSUMABLE:
                used[row["item__model__name"]] = used.get(row["item__model__name"], ZERO) + quantity
    levels = stock_levels(company)
    items = with_stock(company_items(company), levels)
    for row_type, row in by_type.items():
        row["net"] = row["received"] - row["issued"]
        row["value"] = sum((i.value for i in items if i.item_type == row_type), ZERO)

    # The ring: the active items by type.
    circle = Decimal("339.29")              # The length of the circle of the ring: 2 × π × 54
    active = [i for i in items if in_use(i)]
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
    assets = company_items(request.company).filter(item_type=T.ASSET)
    every = list(assets)
    listed = matches(assets, q).order_by("model__name")
    if status in ("active", "inactive"):
        listed = listed.filter(active=status == "active")
    return render(request, "inventory/assets.html", {
        "page_title": "Assets",
        "assets": with_status(list(listed)),
        "total": len(every),
        "active": sum(1 for a in every if a.active),
        "inactive": sum(1 for a in every if not a.active),
        "depreciating": sum(1 for a in every if a.model.lifespan_months),
        "cost": sum((a.unit_cost or ZERO for a in every), ZERO),
        "q": q, "status": status,
    })


def stock(request):
    """The stock items, the quantity on hand of each and the last movements.
    The text filter finds the name, the code, the tag or the serial number."""
    company = request.company
    q = request.GET.get("q", "").strip()
    levels = stock_levels(company)
    stock_items = company_items(company).filter(item_type=T.STOCK)
    every = with_stock(stock_items.filter(active=True), levels)
    listed = with_status(with_stock(matches(stock_items, q).order_by("model__name"), levels))
    last = last_movements(company)
    for item in listed:
        item.last = last.get(item.pk)
    due = StockTakeSchedule.objects.filter(item__company=company, active=True, next_due__lte=timezone.localdate(),
                                           item__item_type=T.STOCK)
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
    items = with_status(with_stock(company_items(company).filter(item_type=T.CONSUMABLE).order_by("model__name"),
                                   levels))
    issues = StockMovement.objects.filter(company=company, direction=D.OUT, date__gte=since,
                                          item__item_type=T.CONSUMABLE)
    used = dict(issues.values_list("item_id").annotate(total=Sum("quantity")))
    for item in items:
        item.used = used.get(item.pk, ZERO)
    active = [i for i in items if in_use(i)]
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
    children = contents(request.company)
    kit_items = with_stock(company_items(request.company).filter(pk__in=children).order_by("model__name"), levels)
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
    children = contents(request.company)
    kit_list = list(company_items(request.company).filter(pk__in=children).order_by("model__name"))
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
        "choices": (company_items(request.company).filter(active=True)
                    .exclude(pk=kit.pk if kit else None).order_by("model__name")),
    })


def codes(request):
    return render(request, "inventory/codes.html", {"page_title": "Codes & Tags", "item_types": T.choices})


def items(request):
    """The item editor. The list at the left finds the items (?q, ?item_type).
    A click selects an item (?item=pk): the form then changes that item, and
    the right column shows its relationships. Without a selection, the form
    makes a new item."""
    items = company_items(request.company)
    item_id = request.GET.get("item", "")
    selected = items.filter(pk=item_id).first() if item_id.isdigit() else None
    form = ItemForm(request.POST or None, instance=selected or Item(company=request.company))

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
                saved = form.save()
                stored = [save_upload(u, request.user, request.company) for u in uploads]
                for item in saved:
                    item.files.add(*stored)
            count = len(saved)
            messages.success(request, f"Saved {count} items of {saved[0].name}." if count > 1 else f"Saved {saved[0].name}.")
            return redirect(f"{request.path}?item={saved[0].pk}")  # Post/Redirect/Get

    q, item_type = request.GET.get("q", "").strip(), request.GET.get("item_type", "")
    listed = matches(items, q).order_by("model__name")
    if item_type in T.values:
        listed = listed.filter(item_type=item_type)
    listed = listed.annotate(relation_count=Count("child_relationships", distinct=True)
                             + Count("parent_relationships", distinct=True))
    relationships = []
    if selected:
        relationships = (
            [{"item": r.child, "type": r.get_relationship_type_display(), "role": "Parent of", "quantity": r.quantity}
             for r in selected.child_relationships.select_related("child__model")]
            + [{"item": r.parent, "type": r.get_relationship_type_display(), "role": "Child of", "quantity": r.quantity}
               for r in selected.parent_relationships.select_related("parent__model")])
    # The open checkout of each item, for the Checkout and Check In buttons.
    open_checkouts = {c.item_id: c for c in Checkout.objects.filter(company=request.company, checked_in_at__isnull=True)
                      .select_related("entity", "location")}
    listed = with_status(with_stock(listed.select_related("model__thumbnail"), stock_levels(request.company)))
    for item in listed:
        item.open_checkout = open_checkouts.get(item.pk)
    # ?new=1 opens an empty editor. ?new=item also opens the Item tab fields.
    new = request.GET.get("new", "")
    return render(request, "inventory/items.html", {
        "page_title": "Items",
        "form": form,
        "selected": selected,
        "show_editor": bool(selected or form.is_bound or new),
        "item_open": bool(selected or form.is_bound or new == "item"),
        "items": listed,
        "posted_serials": request.POST.getlist("serials"),
        "countries": Country.objects.order_by("name"),
        "entities": Entity.objects.filter(company=request.company).order_by("name"),
        "locations": Location.objects.filter(company=request.company).order_by("address"),
        "stock_type": T.STOCK,
        "all_items": items.order_by("model__name"),
        "item_count": items.count(),
        "relationships": relationships,
        "relationship_types": ItemRelationship.RelationshipType.choices,
        "related_choices": items.exclude(pk=selected.pk if selected else None).order_by("model__name"),
        "q": q, "item_type": item_type,
    })


# The "+" entries of the item editor: the form, the image field and the
# files field of the record.
ENTRIES = {
    "manufacturer": (ManufacturerForm, "logo", None),
    "model": (ModelEntryForm, "thumbnail", "datasheets"),
    "category": (CategoryForm, None, None),
}


@require_POST
def item_entry(request, kind):
    """Saves a new manufacturer, model or category of the item editor. The
    Next and Previous buttons send the fields of the open "+" entry here.
    The fields have the prefix new_<kind>. Returns JSON: the new record, or
    an error."""
    if kind not in ENTRIES:
        raise Http404
    form_class, image_field, files_field = ENTRIES[kind]
    prefix = f"new_{kind}"
    form = form_class(request.POST, prefix=prefix, instance=form_class._meta.model(company=request.company))
    image = request.FILES.get(f"{prefix}-{image_field}") if image_field else None
    files = request.FILES.getlist(f"{prefix}-{files_field}") if files_field else []
    if form.is_valid():
        try:
            if image:
                validate_image(image)
            for upload in files:
                validate(upload)
        except ValidationError as error:
            form.add_error(None, error)
    if form.errors:
        errors = [f"{form[f].label}: {e}" if f != "__all__" else e for f, es in form.errors.items() for e in es]
        return JsonResponse({"error": " ".join(errors)}, status=400)

    with transaction.atomic():
        if image:
            setattr(form.instance, image_field, save_upload(image, request.user, request.company))
        entry = form.save()
        if files:
            getattr(entry, files_field).add(*(save_upload(u, request.user, request.company) for u in files))
    number = getattr(entry, "number", "")
    return JsonResponse({
        "pk": entry.pk,
        "label": f"{entry.name} · {number}" if number else entry.name,
        "manufacturer": getattr(entry, "manufacturer_id", None) or "",
        "category": getattr(entry, "category_id", None) or "",
    })


def item_view(request, pk):
    """The content of the View overlay of an item (see items.html)."""
    item = get_object_or_404(company_items(request.company).select_related(
        "model__manufacturer__logo", "model__manufacturer__origin", "model__category", "model__thumbnail"), pk=pk)
    return render(request, "inventory/_item_view.html", {
        "item": item,
        "checkout": item.current_checkout,
    })


@require_POST
def item_checkout(request, pk):
    """Check an item out to a person, an organization or a location. The
    target is "e:<pk>" for an entity or "l:<pk>" for a location."""
    item = get_object_or_404(company_items(request.company), pk=pk)
    kind, _, target = request.POST.get("target", "").partition(":")
    checkout = Checkout(company=request.company, item=item, created_by=request.user)
    if target.isdigit():
        if kind == "e":
            checkout.entity = Entity.objects.filter(company=request.company, pk=target).first()
        elif kind == "l":
            checkout.location = Location.objects.filter(company=request.company, pk=target).first()
    if not (checkout.entity or checkout.location):
        messages.error(request, f"{item.name} was not checked out. Select a person, organization or location.")
        return redirect("inventory:items")
    try:
        checkout.full_clean()
    except ValidationError as error:
        messages.error(request, f"{item.name} was not checked out. " + " ".join(error.messages))
    else:
        checkout.save()
        messages.success(request, f"Checked out {item.name} to {checkout.entity or checkout.location.address}.")
    return redirect("inventory:items")


@require_POST
def item_checkin(request, pk):
    """Check in the open checkout of an item."""
    checkout = get_object_or_404(Checkout, company=request.company, item_id=pk, checked_in_at__isnull=True)
    checkout.check_in(request.user)
    messages.success(request, f"Checked in {checkout.item.name}.")
    return redirect("inventory:items")
