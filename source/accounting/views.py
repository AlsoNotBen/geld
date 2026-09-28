from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum, DecimalField, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from decimal import Decimal
import json
from accounting.models import *
from accounting.date_range import get_range, previous_range
from datetime import datetime, timedelta

ZERO = Decimal("0")
JOURNAL_TABS = {
    "general_entries":  [JournalEntry.EntryType.GENERAL],
    "sales_entries":    [JournalEntry.EntryType.SALES],
    "purchase_entries": [JournalEntry.EntryType.PURCHASES],
    "cash_entries":     [JournalEntry.EntryType.RECEIPT, JournalEntry.EntryType.PAYMENT],
}

def dashboard(request):
    return render(request, "accounting/overview.html")


# ___________________________________LEADS___________________________________________#
RESPONSE_WINDOW = timedelta(days=7)     # The Responsiveness gauge is empty after this time.
TEMPERATURES = Lead.Temperature.values  # From Ice to Hot, thus the index gives the level.
STATUS_TONE = {
    Lead.LeadStatus.NEW:         "busy",
    Lead.LeadStatus.OPEN:        "ok",
    Lead.LeadStatus.QUOTED:      "ok",
    Lead.LeadStatus.IN_PROGRESS: "low",
    Lead.LeadStatus.LOST:        "idle",
    Lead.LeadStatus.WON:         "ok",
}

def card_data(lead, now):
    """Put the data of the card on the lead: the names, the status tone,
    the values of the edit form, and the level (0 to 100) and the text
    of each gauge."""
    entity, owner = lead.entity, lead.entity.owner
    lead.name = entity.display_name or entity.name
    lead.owner_name = (owner.get_full_name() or owner.username) if owner else ""
    lead.form_json = json.dumps({
        "name": entity.name, "type": entity.type, "owner": entity.owner_id,
        "email": entity.email, "phone": entity.phone, "address": entity.address,
        "description": lead.description, "stage": lead.stage, "status": lead.status,
        "size": lead.size, "qualifying_score": lead.qualifying_score,
        "temperature": lead.temperature, "turn": "yours" if lead.turn else "theirs",
        "responsiveness": timezone.localtime(lead.responsiveness).strftime("%Y-%m-%dT%H:%M")
                          if lead.responsiveness else None,
    })
    lead.tone = STATUS_TONE.get(lead.status, "idle")
    if lead.size is not None:
        lead.size_level = min(100, round(lead.size / 10))       # 1 to 1000
    lead.temp_level = TEMPERATURES.index(lead.temperature) * 100 // (len(TEMPERATURES) - 1)
    if lead.responsiveness:
        left = lead.responsiveness + RESPONSE_WINDOW - now
        lead.resp_level = min(100, max(0, round(left / RESPONSE_WINDOW * 100)))
        lead.resp_left = f"{left.days}d {left.seconds // 3600}h" if left > timedelta(0) else "Expired"

def leads(request):
    now = timezone.now()
    rows = list(Lead.objects.select_related("entity__owner").order_by("-id"))
    for lead in rows:
        card_data(lead, now)

    return render(request, "accounting/leads.html", {
        "page_title":   "Leads",
        "columns":      [{"title": label, "leads": [l for l in rows if l.stage == key]}
                         for key, label in Lead.SaleStage.choices if key != Lead.SaleStage.CLOSED],
        "closed_leads": [l for l in rows if l.stage == Lead.SaleStage.CLOSED],
        "stages":       Lead.SaleStage.choices,
        "statuses":     Lead.LeadStatus.choices,
        "temperatures": Lead.Temperature.choices,
        "owners":       get_user_model().objects.filter(is_active=True),
    })

def save_lead(lead, post):
    """Copy the lead form to the lead and its entity, then save both. The
    New Lead overlay and the Edit Lead overlay use the same form."""
    entity = lead.entity
    entity.name = post["name"]
    entity.type = post["type"]
    entity.owner_id = post.get("owner") or None
    entity.email = post.get("email", "")
    entity.phone = post.get("phone", "")
    entity.address = post.get("address", "")

    when = post.get("responsiveness")
    lead.description = post.get("description", "")
    lead.stage = post["stage"]
    lead.status = post["status"]
    if lead.status in (Lead.LeadStatus.LOST, Lead.LeadStatus.WON):
        lead.stage = Lead.SaleStage.CLOSED      # A lost or won lead is closed.
    lead.size = post.get("size") or 1
    lead.qualifying_score = post.get("qualifying_score") or None
    lead.temperature = post["temperature"]
    lead.responsiveness = timezone.make_aware(datetime.fromisoformat(when)) if when else None
    lead.turn = post.get("turn") == "yours"

    with transaction.atomic():
        entity.save()
        lead.save()

def lead_create(request):
    """The Save button of the New Lead overlay. It makes the entity and its lead."""
    if request.method == "POST":
        entity = Entity(company=request.company, created_by=request.user)   # Add to every function that creates a CompanyOwned record
        save_lead(Lead(company=request.company, entity=entity), request.POST)
    return redirect("accounting:leads")

def lead_update(request, pk):
    """The Save button of the Edit Lead overlay."""
    if request.method == "POST":
        save_lead(get_object_or_404(Lead.objects.select_related("entity"), pk=pk), request.POST)
    return redirect("accounting:leads")

def sales_dashboard(request):
    return render(request, "accounting/sales_dashboard.html")

def sales_quotes(request):
    return render(request, "accounting/sales_quotes.html")

def credit_notes(request):
    return render(request, "accounting/sales_crnotes.html")

def sales_invoices(request):
    return render(request, "accounting/sales_invoices.html")

def sales_partners(request):
    return render(request, "accounting/sales_partners.html")

def journal_rows(lines):
    return [{
        "date": line.entry.date,
        "reference": line.entry.reference,
        "journal": line.entry.get_entry_type_display(),
        "account": line.account,
        "amount": line.debit or line.credit,
        "is_debit": line.debit > 0,
    } for line in lines]

def draft_rows(entries):
    """One row for each draft entry. The row also holds the data of the
    edit form, thus the Edit button can fill the overlay."""
    rows = []
    for entry in entries:
        lines = list(entry.lines.all())
        debit = next((l for l in lines if l.debit > 0), None)
        credit = next((l for l in lines if l.credit > 0), None)
        if not (debit and credit):
            continue
        rows.append({
            "id": entry.id,
            "date": entry.date,
            "reference": entry.reference,
            "journal": entry.get_entry_type_display(),
            "entry_type": entry.entry_type,
            "period_id": entry.period_id,
            "narration": entry.narration,
            "debit_account": debit.account,
            "credit_account": credit.account,
            "debit_amount": debit.debit,
            "credit_amount": credit.credit,
            "debit_id": debit.account_id,
            "credit_id": credit.account_id,
            "currency_id": debit.currency_id,
            "tax_id": debit.tax_code_id or "",
            "description": debit.description,
        })
    return rows

def make_lines(entry, post):
    """Make the debit line and the credit line of an entry."""
    amount = Decimal(post["amount"])
    common = {
        "entry": entry,
        "currency_id": post["currency"],
        "tax_code_id": post.get("tax_code") or None,
        "description": post.get("description", ""),
    }
    JournalLine.objects.create(
        account_id=post["debit_account"], debit=amount, base_debit=amount, **common,
    )
    JournalLine.objects.create(
        account_id=post["credit_account"], credit=amount, base_credit=amount, **common,
    )

def journals(request):
    # The global date range keeps only the entries of the selected period.
    key, start, end = get_range(request)

    lines = (JournalLine.objects
             .filter(entry__date__range=(start, end))
             .select_related("entry", "account")
             .order_by("entry__date", "entry_id", "id"))

    posted = list(lines.filter(entry__status=JournalEntry.Status.POSTED))
    drafts = draft_rows(
        JournalEntry.objects
        .filter(status=JournalEntry.Status.DRAFT, date__range=(start, end))
        .prefetch_related("lines__account")
        .order_by("date", "id")
    )

    context = {
        "draft_entries": drafts,
        "pending_count": len(drafts),
        "entry_types": JournalEntry.EntryType.choices,
        "periods": Period.objects.filter(is_closed=False),
        "accounts": Account.objects.filter(is_active=True),
        "currencies": Currency.objects.all(),
        "tax_codes": TaxCode.objects.all(),
    }
    for key, types in JOURNAL_TABS.items():
        context[key] = journal_rows([l for l in posted if l.entry.entry_type in types])

    return render(request, "accounting/journals.html", context)

def journalentry_create(request):
    if request.method == "POST":
        entry = JournalEntry.objects.create(
            company=request.company,                            # Add to every function that creates a CompanyOwned record
            date=request.POST["date"],
            period_id=request.POST["period"],
            entry_type=request.POST["entry_type"],
            status=JournalEntry.Status.DRAFT,
            reference=request.POST["reference"],
            narration=request.POST.get("narration", ""),
        )
        make_lines(entry, request.POST)
    return redirect("accounting:journals")

def journalentry_update(request, pk):
    """The Edit button sends the overlay here. The form holds one debit and
    one credit, thus the view makes the lines again."""
    if request.method == "POST":
        entry = get_object_or_404(JournalEntry, pk=pk, status=JournalEntry.Status.DRAFT)
        entry.date = request.POST["date"]
        entry.period_id = request.POST["period"]
        entry.entry_type = request.POST["entry_type"]
        entry.reference = request.POST["reference"]
        entry.narration = request.POST.get("narration", "")
        entry.save()
        entry.lines.all().delete()
        make_lines(entry, request.POST)
    return redirect("accounting:journals")

def journalentry_post(request, pk):
    """The Accept button. It moves one draft entry to the Posted status."""
    if request.method == "POST":
        JournalEntry.objects.filter(pk=pk, status=JournalEntry.Status.DRAFT).update(
            status=JournalEntry.Status.POSTED, posted_at=timezone.now(),
        )
    return redirect("accounting:journals")

def journalentry_post_all(request):
    """The Accept All button. It moves each draft entry to the Posted status."""
    if request.method == "POST":
        JournalEntry.objects.filter(status=JournalEntry.Status.DRAFT).update(
            status=JournalEntry.Status.POSTED, posted_at=timezone.now(),
        )
    return redirect("accounting:journals")

def journalentry_void(request, pk):
    """The Void button of the entry overlay. It stops a draft entry."""
    if request.method == "POST":
        JournalEntry.objects.filter(pk=pk, status=JournalEntry.Status.DRAFT).update(
            status=JournalEntry.Status.VOID,
        )
    return redirect("accounting:journals")

def invoices(request):
    return render(request, "accounting/invoices.html")

# ___________________________________CHART OF ACCOUNTS___________________________________________#
# The account types of each tab. FLOATING_NOMINAL is not in this map,
# because its category comes from the balance (see category_of).
CATEGORIES = {
    "asset":     [Account.AccountType.CURRENT_ASSETS, Account.AccountType.NON_CURRENT_ASSETS],
    "liability": [Account.AccountType.CURRENT_LIABILITIES, Account.AccountType.NON_CURRENT_LIABILITIES],
    "equity":    [Account.AccountType.SHAREHOLDER_EQUITY],
    "income":    [Account.AccountType.SALES, Account.AccountType.OTHER_INCOME],
    "expense":   [Account.AccountType.COST_OF_SALES, Account.AccountType.EXPENSES, Account.AccountType.INCOME_TAX],
}
 
# The service layer owns the normal side. It comes from the account type,
# thus the user does not choose it. A floating nominal account starts on
# the debit side, but its balance can move to either side.
NORMAL_SIDE = {
    Account.AccountType.SALES:                   Account.Side.CREDIT,
    Account.AccountType.OTHER_INCOME:            Account.Side.CREDIT,
    Account.AccountType.COST_OF_SALES:           Account.Side.DEBIT,
    Account.AccountType.EXPENSES:                Account.Side.DEBIT,
    Account.AccountType.INCOME_TAX:              Account.Side.DEBIT,
    Account.AccountType.NON_CURRENT_ASSETS:      Account.Side.DEBIT,
    Account.AccountType.CURRENT_ASSETS:          Account.Side.DEBIT,
    Account.AccountType.NON_CURRENT_LIABILITIES: Account.Side.CREDIT,
    Account.AccountType.CURRENT_LIABILITIES:     Account.Side.CREDIT,
    Account.AccountType.SHAREHOLDER_EQUITY:      Account.Side.CREDIT,
    Account.AccountType.FLOATING_NOMINAL:        Account.Side.DEBIT,
}
 
def category_of(account):
    if account.type == Account.AccountType.FLOATING_NOMINAL:
        return "asset" if account.is_debit else "liability"
    for key, types in CATEGORIES.items():
        if account.type in types:
            return key
    return None
 
def chartaccounts(request):
    # The balance of an account uses only the lines of the date range.
    key, start, end = get_range(request)
    in_range = Q(lines__entry__date__range=(start, end))

    accounts = list(Account.objects.annotate(
        debits=Coalesce(Sum("lines__base_debit", filter=in_range), ZERO, output_field=DecimalField()),
        credits=Coalesce(Sum("lines__base_credit", filter=in_range), ZERO, output_field=DecimalField()),
    ).order_by("code"))
 
    parent_ids = set(Account.objects.exclude(parent=None).values_list("parent_id", flat=True))
 
    for account in accounts:
        account.signed = account.debits - account.credits
        account.is_debit = account.signed >= 0
        account.is_credit = not account.is_debit
        account.balance = abs(account.signed)
        account.is_group = account.pk in parent_ids
 
    context = {
        "account_types"     : Account.AccountType.choices,
        "currencies"        : Currency.objects.all(),
        "parent_accounts"   : accounts,
        "all_accounts"      : accounts,
        "all_total"         : sum((a.signed for a in accounts), ZERO),
    }
    for key in CATEGORIES:
        rows = [a for a in accounts if category_of(a) == key]
        context[f"{key}_accounts"] = rows
        context[f"{key}_total"] = abs(sum((a.signed for a in rows), ZERO))
 
    return render(request, "accounting/chart_of_accounts.html", context)
 
def account_create(request):
    if request.method == "POST":
        Account.objects.create(
            company=request.company,                            # Add to every function that creates a CompanyOwned record
            code=request.POST["code"],
            name=request.POST["name"],
            type=request.POST["type"],
            normal_side=NORMAL_SIDE[request.POST["type"]],
            parent_id=request.POST.get("parent") or None,
            currency_id=request.POST.get("currency") or None,
            is_active=bool(request.POST.get("is_active")),
            description=request.POST.get("description", ""),
        )
    return redirect("accounting:chartaccounts")

PROFIT_TYPES = [
    Account.AccountType.SALES, Account.AccountType.COST_OF_SALES, Account.AccountType.OTHER_INCOME,
    Account.AccountType.EXPENSES, Account.AccountType.INCOME_TAX,
]

def movements(start=None, end=None):
    """The signed movement (debits less credits) of each account, from the
    posted entries in the date range. Returns {account_id: Decimal}."""
    lines = JournalLine.objects.filter(entry__status=JournalEntry.Status.POSTED)
    if start:
        lines = lines.filter(entry__date__gte=start)
    if end:
        lines = lines.filter(entry__date__lte=end)
    rows = lines.values("account_id").annotate(d=Sum("base_debit"), c=Sum("base_credit"))
    return {row["account_id"]: row["d"] - row["c"] for row in rows}

def profit_of(balances, accounts):
    """The profit in a set of balances: credits less debits of the
    profit or loss accounts."""
    return -sum((balances.get(a.id, ZERO) for a in accounts if a.type in PROFIT_TYPES), ZERO)

def items_of(accounts, this, last, sign):
    """One (name, code, this, last) for each account. sign is 1 for a
    debit balance shown as positive, -1 for a credit balance."""
    return [(a.name, a.code, sign * this.get(a.id, ZERO), sign * last.get(a.id, ZERO)) for a in accounts]

def block(title, items, total_label):
    """The rows of one group of a statement: a group row, a nested row for
    each item with a figure, and a sum row. Returns (rows, this, last)."""
    rows = [{"name": title, "row_class": "is-group", "group": True}]
    this = last = ZERO
    for name, code, v1, v2 in items:
        if v1 == 0 and v2 == 0:
            continue
        rows.append({"name": name, "code": code, "row_class": "is-nest", "this": v1, "last": v2})
        this += v1
        last += v2
    rows.append({"name": total_label, "row_class": "is-sum", "this": this, "last": last})
    return rows, this, last

def sum_row(name, this, last):
    return {"name": name, "row_class": "is-sum", "this": this, "last": last}

def by_type(accounts):
    groups = {}
    for account in accounts:
        groups.setdefault(account.type, []).append(account)
    return groups

def statement_context(request):
    """The dates that each statement shows."""
    key, start, end = get_range(request)
    prev_start, prev_end = previous_range(start, end)
    company = getattr(request, "company", None)
    return {
        "start": start, "end": end, "prev_start": prev_start, "prev_end": prev_end,
        "currency": company.base_currency_id if company else "",
    }

def ledger(request):
    ctx = statement_context(request)
    opening = movements(end=ctx["start"] - timedelta(days=1))
    lines = (JournalLine.objects
             .filter(entry__status=JournalEntry.Status.POSTED,
                     entry__date__range=(ctx["start"], ctx["end"]))
             .select_related("entry", "account")
             .order_by("account__code", "entry__date", "entry_id", "id"))

    # One block for each account with a movement in the period.
    blocks = {}
    for line in lines:
        acct = blocks.get(line.account_id)
        if acct is None:
            balance = opening.get(line.account_id, ZERO)
            acct = {"account": line.account, "opening": balance, "closing": balance,
                    "debit_total": ZERO, "credit_total": ZERO, "lines": []}
            blocks[line.account_id] = acct
        acct["closing"] += line.base_debit - line.base_credit
        acct["debit_total"] += line.base_debit
        acct["credit_total"] += line.base_credit
        acct["lines"].append({
            "date": line.entry.date,
            "reference": line.entry.reference,
            "details": line.description or line.entry.narration,
            "debit": line.base_debit,
            "credit": line.base_credit,
            "balance": acct["closing"],
        })

    # The balance column shows the side of the closing balance.
    for acct in blocks.values():
        acct["account"].is_debit = acct["closing"] >= 0
        acct["side"] = "Dr" if acct["account"].is_debit else "Cr"
        if not acct["account"].is_debit:
            acct["opening"] = -acct["opening"]
            acct["closing"] = -acct["closing"]
            for row in acct["lines"]:
                row["balance"] = -row["balance"]

    for key in CATEGORIES:
        ctx[f"{key}_accounts"] = [a for a in blocks.values() if category_of(a["account"]) == key]
    return render(request, "accounting/ledger.html", ctx)

def balancesheet(request):
    ctx = statement_context(request)
    accounts = list(Account.objects.all())
    this = movements(end=ctx["end"])
    last = movements(end=ctx["prev_end"])
    groups = by_type(accounts)
    T = Account.AccountType

    # A floating nominal account goes to the side of its balance today.
    floating = groups.get(T.FLOATING_NOMINAL, [])
    floating_debit = [a for a in floating if this.get(a.id, ZERO) >= 0]
    floating_credit = [a for a in floating if this.get(a.id, ZERO) < 0]

    nca, nca_this, nca_last = block("Non-current assets", items_of(groups.get(T.NON_CURRENT_ASSETS, []), this, last, 1), "Total non-current assets")
    ca, ca_this, ca_last = block("Current assets", items_of(groups.get(T.CURRENT_ASSETS, []) + floating_debit, this, last, 1), "Total current assets")

    # The profit that is not yet closed to an equity account stays in the
    # profit or loss accounts. The statement shows it as one equity line.
    equity_items = items_of(groups.get(T.SHAREHOLDER_EQUITY, []), this, last, -1)
    equity_items.append(("Profit or loss to date", "", profit_of(this, accounts), profit_of(last, accounts)))
    eq, eq_this, eq_last = block("Equity", equity_items, "Total equity")
    ncl, ncl_this, ncl_last = block("Non-current liabilities", items_of(groups.get(T.NON_CURRENT_LIABILITIES, []), this, last, -1), "Total non-current liabilities")
    cl, cl_this, cl_last = block("Current liabilities", items_of(groups.get(T.CURRENT_LIABILITIES, []) + floating_credit, this, last, -1), "Total current liabilities")

    assets_this, assets_last = nca_this + ca_this, nca_last + ca_last
    liabilities_this, liabilities_last = ncl_this + cl_this, ncl_last + cl_last
    ctx.update({
        "asset_rows": nca + ca,
        "equity_rows": eq + ncl + cl,
        "assets_this": assets_this, "assets_last": assets_last,
        "equity_this": eq_this,
        "liabilities_this": liabilities_this,
        "equity_liabilities_this": eq_this + liabilities_this,
        "equity_liabilities_last": eq_last + liabilities_last,
        "working_capital": ca_this - cl_this,
        "current_ratio": ca_this / cl_this if cl_this else None,
        "is_balanced": assets_this == eq_this + liabilities_this,
    })
    return render(request, "accounting/balance_sheet.html", ctx)

def incomestatement(request):
    ctx = statement_context(request)
    groups = by_type(Account.objects.all())
    this = movements(ctx["start"], ctx["end"])
    last = movements(ctx["prev_start"], ctx["prev_end"])
    T = Account.AccountType

    def part(title, account_type, total_label):
        return block(title, items_of(groups.get(account_type, []), this, last, -1), total_label)

    revenue, rev_this, rev_last = part("Revenue", T.SALES, "Total revenue")
    cost, cost_this, cost_last = part("Cost of sales", T.COST_OF_SALES, "Total cost of sales")
    other, other_this, other_last = part("Other income", T.OTHER_INCOME, "Total other income")
    expenses, exp_this, exp_last = part("Operating expenses", T.EXPENSES, "Total operating expenses")
    tax, tax_this, tax_last = part("Income tax", T.INCOME_TAX, "Total income tax")

    gross_this, gross_last = rev_this + cost_this, rev_last + cost_last
    operating_this = gross_this + other_this + exp_this
    operating_last = gross_last + other_last + exp_last
    profit_this, profit_last = operating_this + tax_this, operating_last + tax_last

    ctx.update({
        "rows": (revenue + cost + [sum_row("Gross profit", gross_this, gross_last)]
                 + other + expenses + [sum_row("Operating profit", operating_this, operating_last)]
                 + tax),
        "revenue": rev_this,
        "gross_profit": gross_this,
        "operating_profit": operating_this,
        "tax": tax_this,
        "profit_this": profit_this,
        "profit_last": profit_last,
        "margin_this": gross_this / rev_this * 100 if rev_this else None,
        "margin_last": gross_last / rev_last * 100 if rev_last else None,
    })
    return render(request, "accounting/income_statement.html", ctx)

def cashflow(request):
    return render(request, "accounting/cash_flow.html")

def equity(request):
    ctx = statement_context(request)
    accounts = list(Account.objects.all())
    columns = [a for a in accounts if a.type == Account.AccountType.SHAREHOLDER_EQUITY]
    column_ids = [a.id for a in columns]
    size = len(columns) + 1

    def row(name, values, row_class, reference="", prior=False):
        return {"name": name, "reference": reference, "values": values,
                "total": sum(values, ZERO),
                "row_class": row_class + (" is-prior" if prior else "")}

    def balance_row(end, prior):
        bal = movements(end=end)
        values = [-bal.get(a.id, ZERO) for a in columns] + [profit_of(bal, accounts)]
        return row(f"Balance at {end:%d %b %Y}", values, "is-sum", prior=prior)

    def period_rows(start, end, prior):
        """The group row of one period, its profit, and one row for each
        posted entry that touched an equity account."""
        mv = movements(start, end)
        rows = [{"group": True, "start": start, "end": end,
                 "row_class": "is-group" + (" is-prior" if prior else "")}]
        rows.append(row("Profit for the period", [ZERO] * (size - 1) + [profit_of(mv, accounts)], "is-nest", prior=prior))
        entries = (JournalEntry.objects
                   .filter(status=JournalEntry.Status.POSTED, date__range=(start, end),
                           lines__account__in=columns)
                   .distinct().prefetch_related("lines").order_by("date", "id"))
        for entry in entries:
            values = [ZERO] * size
            for line in entry.lines.all():
                if line.account_id in column_ids:
                    values[column_ids.index(line.account_id)] += line.base_credit - line.base_debit
            rows.append(row(entry.narration or entry.reference, values, "is-nest", entry.reference, prior))
        return rows

    ctx.update({
        "columns": columns,
        "rows": ([balance_row(ctx["prev_start"] - timedelta(days=1), True)]
                 + period_rows(ctx["prev_start"], ctx["prev_end"], True)
                 + [balance_row(ctx["prev_end"], True)]
                 + period_rows(ctx["start"], ctx["end"], False)),
        "closing": balance_row(ctx["end"], False),
    })
    return render(request, "accounting/shareholder_equity.html", ctx)