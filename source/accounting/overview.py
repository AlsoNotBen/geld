"""accounting/overview.py: the Overview, the first page of the module.

The page has its own date range (see dashboard_range). The global range of
the module bar does not apply to it. The default range is the last 30 days.

The page shows two kinds of figures:
  - the position at the end of the range (today at the latest): the cash,
    the open invoices and bills, and the short-term debt
  - the activity in the range: the invoices and bills that were paid in
    full, the margin, and the audit trail

The open invoices and bills come from the documents and the payments that
are allocated to them, as on the Receivables and Bills pages (see
document_lines and posting.allocate). The cash position uses the journal:
the posted lines of Accounts Payable give its part of the short-term debt.
When the documents and the journal do not agree, a row of the attention
table asks for a reconciliation (see journal_balance).

The last band shows the address of the company on a map, the public
notes, and the movement against the previous period. The map uses the
OpenStreetMap tiles with a dark filter. Set OVERVIEW_MAP in settings.py
to use other tiles (see MAP).
"""
import json
import math
from datetime import date, timedelta

from django.conf import settings
from django.contrib.contenttypes.prefetch import GenericPrefetch
from django.db.models import Q, Sum
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from accounting.models import (Account, AuditLog, BankAccount, BankTransaction, Document, JournalEntry, JournalLine,
                               Note, Payment)
from shared.models import Supplier
from accounting.date_range import previous_range
from accounting.posting import PAYABLE, RECEIVABLE, SUSPENSE
from accounting.views import ZERO, cash_account_ids, movements, posted_lines, tax_account_ids

RANGES = {
    "7":     "Last 7 days",
    "30":    "Last 30 days",
    "90":    "Last 90 days",
    "month": "This month",
    "ytd":   "Year to date",
    "365":   "Last 12 months",
}
POINTS = 60         # The most points of a card graph. A long range uses a step of more than one day.
RISK_DAYS = 60      # An open invoice more than 60 days after its due date is at risk of default.
SOON_DAYS = 7       # A bill is due soon when its due date is in the next 7 days.
TAX_WORDS = ("vat", "tax", "paye")
RINGS = ((50, 74), (74, 98))    # The radius at the start and at the end of each ring. The chart is 200 units wide.

# The row colour of each level of the attention table (see .attn--* in accounting.css).
LEVELS = {"Critical": "attn--critical", "Warning": "attn--warning", "Action": "attn--action", "Upcoming": ""}
VERBS = {
    AuditLog.Action.CREATE: "created",
    AuditLog.Action.UPDATE: "changed",
    AuditLog.Action.DELETE: "deleted",
    AuditLog.Action.POST:   "posted",
    AuditLog.Action.VOID:   "voided",
}
JOURNAL_TAB_OF = {"G": "general", "S": "sales", "P": "purchases", "CR": "cash", "CP": "cash"}
# The tiles of the map. The standard OpenStreetMap tiles are light, thus
# "invert" gives them the dark filter (see .dash-map in accounting.css).
# A provider of dark tiles needs no filter, e.g. CARTO with a free key:
#   OVERVIEW_MAP = {"tiles": "https://basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png?key=KEY",
#                   "attribution": "&copy; OpenStreetMap contributors &copy; CARTO", "invert": False}
MAP = {
    "tiles": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    "attribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    "invert": True,
}
# The name of each page that can hold a note (the sidebar names).
PAGE_NAMES = {
    "accounting:dashboard":       "Overview",
    "accounting:reports":         "Reports",
    "accounting:journals":        "Journal Entries",
    "accounting:chartaccounts":   "Chart of Accounts",
    "accounting:ledger":          "General Ledger",
    "accounting:balancesheet":    "Balance Sheet",
    "accounting:incomestatement": "Income Statement",
    "accounting:cashflow":        "Cash Flow Statement",
    "accounting:equity":          "Equity and Notes",
    "accounting:bills":           "Bills",
    "accounting:suppliers":       "Suppliers",
}
DOCUMENT_PAGES = {
    Document.DocType.BILL:        "accounting:bills",
    Document.DocType.INVOICE:     "accounting:receivables",
    Document.DocType.QUOTE:       "sales:quotes",
    Document.DocType.CREDIT_NOTE: "sales:credit_notes",
}


def link(name, query=""):
    return reverse(f"accounting:{name}") + query


def day_text(day):
    return f"{day.day} {day:%b %Y}"


def amount_text(value):
    """A full amount, with a no-break space between the groups of three digits."""
    return f"{value:,.2f}".replace(",", "\u00a0")


def compact(value):
    """A short amount for a chart: 950, 12.4K, 3.1M."""
    value = float(value)
    for size, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= size:
            return f"{value / size:.1f}{suffix}"
    return f"{value:.0f}"


# ___________________________________DATES_______________________________________#
def dashboard_range(request):
    """The date range of the Overview as (key, start, end, label). The query
    string holds a preset key (range=30), or range=custom with a start and
    an end date. A bad value gives the default: the last 30 days."""
    today = timezone.localdate()
    key = request.GET.get("range", "30")
    if key == "custom":
        try:
            start, end = date.fromisoformat(request.GET["start"]), date.fromisoformat(request.GET["end"])
            if start <= end:
                return key, start, end, f"{day_text(start)} – {day_text(end)}"
        except (KeyError, ValueError):
            pass
    if key == "month":
        start = today.replace(day=1)
    elif key == "ytd":
        start = today.replace(month=1, day=1)
    elif key in RANGES:
        start = today - timedelta(days=int(key) - 1)
    else:
        key, start = "30", today - timedelta(days=29)
    return key, start, today, RANGES[key]


def sample_days(start, end):
    """The days of the card graphs, from start to end, with the same step.
    The last day is always end."""
    span = (end - start).days
    step = max(1, math.ceil(span / (POINTS - 1)))
    return [start + timedelta(days=n) for n in range(0, span, step)] + [end]


# ___________________________________LEDGER______________________________________#
def daily_balances(company, opening, days):
    """The balance (debits less credits) of each account at the end of each
    day, for the basis of the company. opening holds the balances before the
    first day (see movements)."""
    rows = iter(posted_lines(company)
                .filter(entry__date__range=(days[0], days[-1]))
                .values_list("entry__date", "account_id")
                .annotate(debit=Sum("base_debit"), credit=Sum("base_credit"))
                .order_by("entry__date"))
    balance, result = dict(opening), []
    row = next(rows, None)
    for day in days:
        while row and row[0] <= day:
            balance[row[1]] = balance.get(row[1], ZERO) + row[2] - row[3]
            row = next(rows, None)
        result.append(dict(balance))
    return result


def control_lines(company, name, as_of, sign):
    """The posted lines of a control account up to as_of, oldest first, as
    (entity, date, amount, due). sign 1 makes a debit a charge (Accounts
    Receivable). sign -1 makes a credit a charge (Accounts Payable). The
    lines of the cash basis do not count, as on the statement. The due date
    comes from the document of the entry, else it is the date of the entry."""
    rows = (JournalLine.objects
            .filter(entry__company=company, entry__status=JournalEntry.Status.POSTED,
                    account__company=company, account__name=name, entry__date__lte=as_of)
            .exclude(entry__basis=JournalEntry.Basis.CASH)
            .order_by("entry__date", "entry_id", "id")
            .values_list("entity_id", "entry__date", "base_debit", "base_credit", "entry__document__due"))
    return [(entity, day, sign * (debit - credit), due or day) for entity, day, debit, credit, due in rows]


def document_lines(company, as_of, doc_type):
    """The invoices or the bills up to as_of and their payments, oldest
    first, as (document, date, amount, due) for settle. The key of each line
    is the document, thus a payment pays only the documents that it is
    allocated to (see posting.allocate), as on the Receivables and Bills
    pages. A draft or void document does not count. An entry without a
    document (e.g. a manual journal entry) is not an open invoice."""
    documents = (Document.objects
                 .filter(company=company, doc_type=doc_type, date__lte=as_of)
                 .exclude(status__in=[Document.Status.DRAFT, Document.Status.VOID])
                 .prefetch_related("lines__tax_code", "allocations__payment"))
    lines = []
    for document in documents:
        lines.append((document.pk, document.date, document.gross, document.due or document.date))
        lines += [(document.pk, allocation.payment.date, -allocation.amount, None)
                  for allocation in document.allocations.all() if allocation.payment.date <= as_of]
    return sorted(lines, key=lambda line: line[1])


def journal_balance(company, name, as_of, sign):
    """The balance of a control account in the journal at as_of, to check the
    documents. Each entry that is not void counts, also a draft, because a
    document makes its draft entry at once. A manual entry counts too. The
    cash basis does not count. sign 1 gives the debits less the credits."""
    total = (JournalLine.objects
             .filter(entry__company=company, account__company=company, account__name=name, entry__date__lte=as_of)
             .exclude(entry__status=JournalEntry.Status.VOID)
             .exclude(entry__basis=JournalEntry.Basis.CASH)
             .aggregate(debit=Sum("base_debit"), credit=Sum("base_credit")))
    return sign * ((total["debit"] or ZERO) - (total["credit"] or ZERO))


def settle(lines, days):
    """Settle the charges first in, first out, as _statement does: a payment
    or a credit pays the oldest open charges of the same key first. A
    payment that is more than the open charges stays as a credit for the
    next charge.

    lines are (key, date, amount, due), oldest first. The key is the entity
    (see control_lines) or the document (see document_lines). A positive amount
    is a charge (an invoice or a bill). A negative amount pays.
    Returns the charges and, for each day, the totals at the end of that day
    (see aging). A charge is a dict: amount, due, left (the part that is open
    on the last day), date, and paid (the date of the payment in full, or None)."""
    queues, credits, charges, totals = {}, {}, [], []
    lines = iter(lines)
    line = next(lines, None)
    for day in days:
        while line and line[1] <= day:
            entity, when, amount, due = line
            queue = queues.setdefault(entity, [])
            if amount > 0:
                charge = {"date": when, "amount": amount, "due": due, "left": amount, "paid": None}
                charges.append(charge)
                queue.append(charge)
                pay = credits.pop(entity, ZERO)
            else:
                pay = -amount
            while pay and queue:
                charge = queue[0]
                part = min(pay, charge["left"])
                charge["left"] -= part
                pay -= part
                if not charge["left"]:
                    charge["paid"] = when
                    queue.pop(0)
            if pay:
                credits[entity] = credits.get(entity, ZERO) + pay
            line = next(lines, None)
        totals.append(aging([charge for queue in queues.values() for charge in queue], day))
    return charges, totals


def aging(charges, day):
    """The (open, overdue, at risk) totals of the open charges at the end of the day."""
    open_ = overdue = risk = ZERO
    for charge in charges:
        late = (day - charge["due"]).days
        open_ += charge["left"]
        if late > 0:
            overdue += charge["left"]
        if late > RISK_DAYS:
            risk += charge["left"]
    return open_, overdue, risk


def states(charges, start, as_of):
    """The [count, amount] of the charges in each state at as_of:
        due    open, the due date is today or later
        soon   open, the due date is in the next SOON_DAYS days (also in due)
        late   open, 1 to RISK_DAYS days after the due date
        risk   open, more than RISK_DAYS days after the due date
        paid   paid in full in the range (the amount of the charge)"""
    result = {key: [0, ZERO] for key in ("due", "soon", "late", "risk", "paid")}

    def add(key, value):
        result[key][0] += 1
        result[key][1] += value

    for charge in charges:
        days_late = (as_of - charge["due"]).days
        if charge["left"]:
            add("due" if days_late <= 0 else "late" if days_late <= RISK_DAYS else "risk", charge["left"])
            if -SOON_DAYS <= days_late <= 0:
                add("soon", charge["left"])
        elif start <= charge["paid"] <= as_of:
            add("paid", charge["amount"])
    return result


# ___________________________________CHARTS______________________________________#
def node(label, tone, href, value=ZERO, children=(), note=""):
    """One part of a sunburst. A part with children gets the sum of their
    values. tone is the name of a fill (see .tone-* in accounting.css).
    The tooltip shows the note after the label."""
    children = list(children)
    if children:
        value = sum((child["value"] for child in children), ZERO)
    return {"label": label, "tone": tone, "href": href, "value": value, "children": children, "note": note}


def arc(r0, r1, a0, a1):
    """The SVG path of a ring part from angle a0 to angle a1 (degrees,
    clockwise from the top), between the radii r0 and r1."""
    if a1 - a0 >= 359.99:   # A full ring: two circles, the inner one in the other direction.
        return (f"M100 {100 - r1}A{r1} {r1} 0 1 1 100 {100 + r1}A{r1} {r1} 0 1 1 100 {100 - r1}Z"
                f"M100 {100 - r0}A{r0} {r0} 0 1 0 100 {100 + r0}A{r0} {r0} 0 1 0 100 {100 - r0}Z")

    def point(r, angle):
        angle = math.radians(angle)
        return f"{100 + r * math.sin(angle):.2f} {100 - r * math.cos(angle):.2f}"

    large = 1 if a1 - a0 > 180 else 0
    return (f"M{point(r1, a0)}A{r1} {r1} 0 {large} 1 {point(r1, a1)}"
            f"L{point(r0, a1)}A{r0} {r0} 0 {large} 0 {point(r0, a0)}Z")


def sunburst(nodes, unit=""):
    """The segments and the legend of a sunburst chart. The inner ring holds
    the nodes, the outer ring holds their children. The angle of a part is
    in proportion to its value. unit is the currency of an amount; a count
    has no unit. The legend has one group for each node: the node, and its
    children when the node has a value."""
    total = sum((n["value"] for n in nodes), ZERO)
    segments, legend, angle = [], [], 0.0
    for i, parent in enumerate(nodes):
        items = [(parent, 0, str(i))]
        if parent["value"]:
            items += [(child, 1, f"{i}-{j}") for j, child in enumerate(parent["children"])]
        child_angle = angle
        legend.append([])
        for item, depth, key in items:
            sweep = 360 * float(item["value"] / total) if total else 0
            text = f"{amount_text(item['value'])} {unit}" if unit else str(item["value"])
            row = {"key": key, "depth": depth, "label": item["label"], "tone": item["tone"], "href": item["href"],
                   "tip": f"{item['label']} · {item['note']}" if item["note"] else item["label"],
                   "short": compact(item["value"]) if unit else item["value"], "zero": not item["value"],
                   "text": f"{text} · {item['value'] / total:.0%}" if total else text}
            legend[-1].append(row)
            if sweep:
                start = angle if depth == 0 else child_angle
                segments.append({**row, "path": arc(*RINGS[depth], start, start + sweep)})
            if depth:
                child_angle += sweep
        angle += 360 * float(parent["value"] / total) if total else 0
    return {"segments": segments, "legend": legend}


# ___________________________________ACTIVITY____________________________________#
def page_of(name):
    try:
        return reverse(name)
    except NoReverseMatch:
        return ""


def subject(obj):
    """The words, the other party and the page of a record of the audit trail."""
    if isinstance(obj, JournalEntry):
        return f"journal entry {obj.reference}", "", link("journals", f"?journal={JOURNAL_TAB_OF[obj.entry_type]}")
    if isinstance(obj, Document):
        return (f"{obj.get_doc_type_display().lower()} {obj.number}", obj.entity.name,
                page_of(DOCUMENT_PAGES[obj.doc_type]))
    if isinstance(obj, Payment):
        return f"payment {obj.number}", obj.entity.name, link("journals", "?journal=cash")
    if isinstance(obj, Note):
        return f"note “{obj.title}”", "", page_of(obj.page)
    if isinstance(obj, Supplier):
        return f"supplier {obj.code}", obj.entity.name, link("suppliers")
    if isinstance(obj, Account):
        return f"account {obj}", "", link("chartaccounts")
    if isinstance(obj, BankAccount):
        return f"bank account {obj.name}", obj.bank, link("bank_accounts")
    return ("a record that no longer exists", "", "") if obj is None else (str(obj), "", "")


def when_text(moment, today):
    moment = timezone.localtime(moment)
    if moment.date() == today:
        return f"Today {moment:%H:%M}"
    if moment.date() == today - timedelta(days=1):
        return f"Yesterday {moment:%H:%M}"
    return f"{moment.day} {moment:%b, %H:%M}"


def activity(company, start, end):
    """The audit trail of the range, newest first: who did what, and when."""
    logs = (AuditLog.objects.filter(company=company, timestamp__date__range=(start, end))
            .select_related("user")
            .prefetch_related(GenericPrefetch("content_object", [
                Document.objects.select_related("entity"),
                Payment.objects.select_related("entity"),
                Supplier.objects.select_related("entity"),
            ]))[:50])
    today = timezone.localdate()
    rows = []
    for log in logs:
        what, party, href = subject(log.content_object)
        who = (log.user.get_full_name() or log.user.get_username()) if log.user else "System"
        rows.append({"who": who, "initials": "".join(word[0] for word in who.split()[:2]).upper(),
                     "verb": VERBS[log.action], "what": what, "party": party, "href": href,
                     "when": log.timestamp, "when_text": when_text(log.timestamp, today)})
    return rows


# ___________________________________THE LAST BAND_______________________________#
def public_notes(company):
    """The public notes of each page that did not expire, newest first. A
    note links to its page, and the page opens the note (see notes.js)."""
    notes = (Note.objects.filter(company=company, visibility=Note.Visibility.PUBLIC)
             .filter(Q(is_permanent=True) | Q(expires_on__gte=timezone.localdate()))
             .select_related("created_by").order_by("-created_at")[:24])
    rows = []
    for note in notes:
        page = page_of(note.page)
        rows.append({"title": note.title, "kind": note.kind, "kind_name": note.get_kind_display(),
                     "page": PAGE_NAMES.get(note.page, note.page.rsplit(":", 1)[-1].title()),
                     "href": f"{page}#note-{note.pk}" if page else "",
                     "by": note.created_by.get_full_name() or note.created_by.get_username() if note.created_by else "",
                     "when": note.created_at})
    return rows


def change(this, last, good):
    """The change from the previous period, as (text, tone). good is True
    when a rise is good news, False when it is bad news, None for neither."""
    if not last:
        return ("New", "") if this else ("—", "")
    rise = (this - last) / abs(last) * 100
    if not rise:
        return "0%", ""
    tone = "" if good is None else "is-credit" if (rise > 0) == good else "is-debit"
    return f"{'▲' if rise > 0 else '▼'} {abs(rise):.0f}%", tone


def movement(company, accounts, invoices, bills, start, end):
    """The rows of the movement table: this period and the previous period
    of the same length (see previous_range)."""
    T = Account.AccountType
    before = previous_range(start, end)

    def figures(first, last):
        def count(charges, key):
            return sum(1 for charge in charges if charge[key] and first <= charge[key] <= last)

        moved = movements(company, first, last)
        income = -sum((moved.get(a.id, ZERO) for a in accounts if a.type in (T.SALES, T.OTHER_INCOME)), ZERO)
        expenses = sum((moved.get(a.id, ZERO) for a in accounts if a.type in (T.COST_OF_SALES, T.EXPENSES)), ZERO)
        return [
            count(invoices, "date"), count(invoices, "paid"), count(bills, "date"), count(bills, "paid"),
            JournalEntry.objects.filter(company=company, status=JournalEntry.Status.POSTED, date__range=(first, last),
                                        basis__in=JournalEntry.bases_of(company)).count(),
            income, expenses, income - expenses,
        ]

    # Each row: the name, True when a rise is good news (see change), and True for an amount.
    names = [("Invoices issued", True, False), ("Invoices paid", True, False), ("Bills received", None, False),
             ("Bills paid", None, False), ("Entries posted", None, False), ("Income", True, True),
             ("Expenses", False, True), ("Margin", True, True)]

    def text(value, money):
        """An amount shows whole units, thus the table stays narrow."""
        return f"{value:,.0f}".replace(",", "\u00a0") if money else str(value)

    rows = []
    for (name, good, money), this, last in zip(names, figures(start, end), figures(*before)):
        rise, tone = change(this, last, good)
        rows.append({"name": name, "this": text(this, money), "last": text(last, money), "change": rise, "tone": tone})
    return before, rows


# ___________________________________THE PAGE____________________________________#
def dashboard(request):
    company     = request.company
    T           = Account.AccountType

    key, start, end, label = dashboard_range(request)

    as_of   = min(end, timezone.localdate())
    start   = min(start, as_of)
    days    = sample_days(start, as_of)

    # The ledger at the end of each day, the open invoices and bills (the
    # documents), and the Accounts Payable of the journal (for the cash position).
    accounts    = list(Account.objects.filter(company=company))
    opening     = movements(company, end=start - timedelta(days=1))
    balances    = daily_balances(company, opening, days)
    invoices, receivable = settle(document_lines(company, as_of, Document.DocType.INVOICE), days)
    bills, unpaid = settle(document_lines(company, as_of, Document.DocType.BILL), days)
    _, payable = settle(control_lines(company, PAYABLE, as_of, -1), days)
    sold, bought = states(invoices, start, as_of), states(bills, start, as_of)
    review = list(Document.objects.filter(company=company, direction=Document.Direction.PURCHASE,
                                          doc_type=Document.DocType.BILL, status=Document.Status.DRAFT)
                  .prefetch_related("lines__tax_code"))

    # The cash, and the short-term debt in four parts. A part is a current
    # liability: Accounts Payable, the credit cards (an account with "card"
    # in its name), the tax, and the others. A bank overdraft and a
    # floating account with a credit balance are in the others too. A
    # current liability is never cash, also when a bank account uses it.
    tax_ids = tax_account_ids(company)
    part_of = {a.id: "cards" if "card" in a.name.lower()
               else "tax" if a.id in tax_ids or any(word in a.name.lower() for word in TAX_WORDS) else "other"
               for a in accounts if a.type == T.CURRENT_LIABILITIES and a.name != PAYABLE}
    cash_ids = cash_account_ids(company, accounts) - set(part_of)
    credit_ids = cash_ids | {a.id for a in accounts if a.type == T.FLOATING_NOMINAL}

    def position(balance, accounts_payable):
        parts = {"payable": accounts_payable, "tax": ZERO, "cards": ZERO, "other": ZERO}
        for account_id, part in part_of.items():
            parts[part] -= balance.get(account_id, ZERO)
        parts["other"] += sum((max(-balance.get(i, ZERO), ZERO) for i in credit_ids), ZERO)
        cash = sum((max(balance.get(i, ZERO), ZERO) for i in cash_ids), ZERO)
        return cash, {part: max(value, ZERO) for part, value in parts.items()}

    positions = [position(balance, totals[0]) for balance, totals in zip(balances, payable)]
    cash, parts = positions[-1]
    owed = sum(parts.values(), ZERO)
    committed = min(cash, owed)

    # The margin from the start of the range to each day: income less expenses.
    def moved(balance, types):
        return sum((balance.get(a.id, ZERO) - opening.get(a.id, ZERO) for a in accounts if a.type in types), ZERO)

    incomes = [-moved(balance, (T.SALES, T.OTHER_INCOME)) for balance in balances]
    margins = [income - moved(balance, (T.COST_OF_SALES, T.EXPENSES)) for income, balance in zip(incomes, balances)]

    unit = company.base_currency_id
    bills_page = link("bills")
    since = f"Open at {as_of.day} {as_of:%b} · paid from {start.day} {start:%b}"
    charts = [
        {"title": "CASH POSITION", "href": link("cashflow"), "hint": f"{unit} · at {day_text(as_of)}",
         "center": {"label": "Net cash" if cash >= owed else "Shortfall", "value": compact(abs(cash - owed)),
                    "tone": "is-credit" if cash >= owed else "is-debit", "href": link("cashflow")},
         **sunburst([
             node("Cash on Hand", "aqua", link("bank_accounts"), note="the bank and cash accounts readily available", children=[
                 node("Available", "aqua", link("cashflow"), cash - committed,
                      note="the cash after honoring the short-term debt"),
                 node("Committed", "blue", link("payment_runs"), committed,
                      note="the cash that pays the short-term debt"),
             ]),
             node("Short-term debt", "orange", link("balancesheet"), note="the current liabilities", children=[
                 node("Accounts Payable", "orange", link("payables"), parts["payable"],
                      note="the Accounts Payable balance in the journal"),
                 node("Tax", "violet", link("tax_dashboard"), parts["tax"], note="VAT, PAYE and other tax"),
                 node("Credit Cards", "magenta", link("cards"), parts["cards"]),
                 node("Other", "gray", link("balancesheet"), parts["other"],
                      note="other current liabilities and bank overdrafts"),
             ]),
         ], unit)},
        {"title": "INVOICES", "href": link("receivables"), "hint": since,
         "center": {"label": "Invoices", "value": sum(sold[s][0] for s in ("due", "late", "risk", "paid")),
                    "href": link("receivables")},
         **sunburst([
             node("Open", "blue", link("receivables"), note="not paid in full", children=[
                 node("Not Yet Due", "blue", link("receivables"), sold["due"][0]),
                 node("Overdue", "yellow", link("aging_receivables"), sold["late"][0],
                      note=f"1 to {RISK_DAYS} days after the due date"),
                 node("Default Risk", "red", link("aging_receivables"), sold["risk"][0],
                      note=f"more than {RISK_DAYS} days after the due date"),
             ]),
             node("Paid", "aqua", link("receivables", "?invoices=paid"), sold["paid"][0],
                  note="paid in full in the date range"),
         ])},
        {"title": "BILLS & CLAIMS", "href": bills_page, "hint": since,
         "center": {"label": "Total",
                    "value": len(review) + sum(bought[s][0] for s in ("due", "late", "risk", "paid")),
                    "href": bills_page},
         **sunburst([
             node("Bills", "orange", bills_page, children=[
                 node("For Review", "violet", bills_page + "#review-title", len(review), note="draft bills"),
                 node("Overdue", "yellow", bills_page + "?bills=unpaid", bought["late"][0] + bought["risk"][0],
                      note="after the due date"),
                 node("Unpaid", "blue", bills_page + "?bills=unpaid", bought["due"][0], note="not yet due"),
                 node("Paid", "aqua", bills_page + "?bills=paid", bought["paid"][0],
                      note="paid in full in the date range"),
             ]),
             # TODO: Claims have no model yet. Add the states of the claims as
             # the children of this node when the model exists.
             node("Claims", "violet", link("claims"), note="no claims are recorded yet"),
         ])},
    ]

    # The items that need an action. A row with no count and no amount does not show.
    drafts = JournalEntry.objects.filter(company=company, status=JournalEntry.Status.DRAFT)
    suspense = next((a.id for a in accounts if a.name == SUSPENSE), None)

    def ledger_of(name, tab):
        """The block of a control account in the General Ledger (see _ledger_panel.html)."""
        return link("ledger", f"?type={tab}#acct-{next((a.code for a in accounts if a.name == name), '')}")

    # The difference between the open documents and the journal (see journal_balance).
    receivable_gap = abs(receivable[-1][0] - journal_balance(company, RECEIVABLE, as_of, 1))
    payable_gap = abs(unpaid[-1][0] - journal_balance(company, PAYABLE, as_of, -1))
    rows = [
        ("Critical", "Invoices at risk of default", f"More than {RISK_DAYS} days after the due date",
         *sold["risk"], "is-overdue", link("aging_receivables")),
        ("Critical", "Cash shortfall", "The short-term debt is more than the cash on hand",
         None, max(owed - cash, ZERO), "is-debit", link("cashflow")),
        ("Warning", "Overdue invoices", f"1 to {RISK_DAYS} days after the due date",
         *sold["late"], "is-overdue", link("aging_receivables")),
        ("Warning", "Overdue bills", "Pay these bills now",
         bought["late"][0] + bought["risk"][0], bought["late"][1] + bought["risk"][1], "is-debit",
         bills_page + "?bills=unpaid"),
        ("Warning", "Receivables need reconciliation",
         "The open invoices do not match Accounts Receivable in the journal. Please review.",
         None, receivable_gap, "", ledger_of(RECEIVABLE, "assets")),
        ("Warning", "Payables need reconciliation",
         "The open bills do not match Accounts Payable in the journal. Please review.",
         None, payable_gap, "", ledger_of(PAYABLE, "liabilities")),
        ("Action", "Bills to review", "Approve or deny each draft bill",
         len(review), sum((bill.gross for bill in review), ZERO), "is-debit", bills_page + "#review-title"),
        ("Action", "Journal entries to accept", "Draft entries are not in the reports",
         drafts.count(), JournalLine.objects.filter(entry__in=drafts).aggregate(total=Sum("base_debit"))["total"],
         "", link("journals")),
        ("Action", "Unreconciled bank lines", "Match each line to a payment or an entry",
         BankTransaction.objects.filter(company=company, reconciled=False).count(), None, "", link("reconcile")),
        ("Action", "Money in Suspense", "Allocate each payment to its invoices or bills",
         None, abs(balances[-1].get(suspense, ZERO)), "", link("ledger")),
        ("Upcoming", f"Bills due in the next {SOON_DAYS} days", "Plan the payment run",
         *bought["soon"], "is-debit", link("payment_runs")),
    ]
    attention = [{"level": level, "row_class": LEVELS[level], "title": title, "note": note, "count": count,
                  "amount": amount, "tone": tone, "href": href}
                 for level, title, note, count, amount, tone, href in rows if count or amount]

    def card(label, series, tone, href, hint=""):
        return {"label": label, "value": series[-1], "series": series, "tone": tone, "href": href, "hint": hint,
                "points": json.dumps([[day.isoformat(), float(value)] for day, value in zip(days, series)])}

    margin, income = margins[-1], incomes[-1]
    cards = [
        card("Open Invoices", [t[0] for t in receivable], "is-credit", link("receivables")),
        card("Invoices Overdue", [t[1] for t in receivable], "is-overdue", link("aging_receivables")),
        card("Default Risk Amount", [t[2] for t in receivable], "is-debit", link("aging_receivables")),
        card("Unpaid Bills", [t[0] for t in unpaid], "is-debit", bills_page + "?bills=unpaid"),
        card("Paid Bills", [sum((b["amount"] for b in bills if b["paid"] and start <= b["paid"] <= day), ZERO)
                            for day in days], "is-debit", bills_page + "?bills=paid"),
        # TODO: Claims have no model yet. Use the unpaid claims of each day when the model exists.
        card("Unpaid Claims", [ZERO] * len(days), "is-debit", link("claims")),
        card("Immediate/Short Term Debt", [sum(p.values(), ZERO) for _, p in positions], "is-debit",
             link("balancesheet")),
        card("Expenses/Income Margin", margins, "is-credit" if margin >= 0 else "is-debit", link("incomestatement"),
             f"{margin / income:.1%} of income" if income else "No income in the range"),
    ]

    (prev_start, prev_end), moves = movement(company, accounts, invoices, bills, start, as_of)
    return render(request, "accounting/overview.html", {
        "dash_key": key, "dash_label": label, "dash_ranges": RANGES.items(),
        "start": start, "end": end, "as_of": as_of, "currency": unit,
        "charts": charts, "attention": attention, "activity": activity(company, start, end), "cards": cards,
        "company": company, "map": {**MAP, **getattr(settings, "OVERVIEW_MAP", {})},
        "notes": public_notes(company), "moves": moves, "prev_start": prev_start, "prev_end": prev_end,
    })
