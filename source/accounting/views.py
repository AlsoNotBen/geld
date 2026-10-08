import json
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import Sum, DecimalField, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from decimal import Decimal
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

#TODO: Sample data, like the card values of overview.html. Replace each list
# with the closing figure of each day of the last 7 days (oldest first).
WEEK_TRENDS = {
    "open":    [44210, 45080, 43900, 46350, 47020, 46480, 48120],
    "overdue": [5200, 5200, 6100, 6100, 6850, 7400, 7400],
    "payable": [14320, 13980, 15110, 14200, 13460, 13050, 12905],
    "cash":    [88140, 89560, 87920, 90310, 91880, 92640, 93517],
    "active":  [31, 32, 32, 33, 33, 34, 34],
    # The cash flow statement has no view yet. These follow its cards.
    "cf_start":     [128940] * 7,
    "cf_operating": [161200, 163850, 166020, 168400, 171230, 173060, 175420],
    "cf_investing": [-62100, -62100, -66800, -66800, -68950, -70440, -70440],
    "cf_financing": [-31200, -31200, -32900, -32900, -34600, -34600, -34600],
    "cf_end":       [196840, 199490, 195260, 197640, 196620, 197900, 199320],
}

BALANCE_KEYS = ["assets_this", "equity_this", "liabilities_this", "working_capital", "current_ratio"]
INCOME_KEYS = ["revenue", "gross_profit", "operating_profit", "tax", "profit_this"]

def change(this, last):
    """The change from last to this, in percent. None if last is zero."""
    if this is None or not last:
        return None
    return (this - last) / abs(last) * 100

def dashboard(request):
    """The overview. The Balance and Income parts show the figures of the
    statements at the last day of the range (today at the latest), with
    the 7 days to that day."""
    ctx = statement_context(request)
    company = ctx["company"]
    accounts = list(Account.objects.filter(company=company))
    as_of = min(ctx["end"], timezone.localdate())
    days = [as_of - timedelta(days=n) for n in range(6, -1, -1)]

    balance = [balance_data(accounts, movements(company, end=day), {}) for day in days]
    income = [income_data(accounts, movements(company, ctx["start"], day), {}) for day in days]
    trends = dict(WEEK_TRENDS)
    for key in BALANCE_KEYS:
        trends[key] = [figures[key] for figures in balance]
    for key in INCOME_KEYS:
        trends[key] = [figures[key] for figures in income]

    # The comparison table: this period against the last period.
    full = income_data(accounts, movements(company, ctx["start"], ctx["end"]),
                       movements(company, ctx["prev_start"], ctx["prev_end"]))
    comparison = [
        ("Revenue", full["revenue"], full["revenue_last"], "is-credit"),
        ("Cost of sales", full["cost_of_sales"], full["cost_of_sales_last"], "is-debit"),
        ("Operating expenses", full["expenses"], full["expenses_last"], "is-debit"),
        ("Profit for the period", full["profit_this"], full["profit_last"], "is-credit"),
    ]
    ctx.update({
        "as_of": as_of,
        "balance": balance[-1],
        "income": income[-1],
        "trends": trends,
        "comparison": [{"name": n, "this": t, "last": l, "tone": c, "change": change(t, l)}
                       for n, t, l, c in comparison],
        "margin_this": full["margin_this"],
        "margin_last": full["margin_last"],
        "margin_change": (full["margin_this"] - full["margin_last"]
                          if full["margin_this"] is not None and full["margin_last"] is not None else None),
    })
    return render(request, "accounting/overview.html", ctx)


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

    company = request.company
    lines = (JournalLine.objects
             .filter(entry__company=company, entry__date__range=(start, end),
                     entry__basis__in=JournalEntry.bases_of(company))
             .select_related("entry", "account")
             .order_by("entry__date", "entry_id", "id"))

    posted = list(lines.filter(entry__status=JournalEntry.Status.POSTED))
    drafts = draft_rows(
        JournalEntry.objects
        .filter(company=company, status=JournalEntry.Status.DRAFT, date__range=(start, end))
        .prefetch_related("lines__account")
        .order_by("date", "id")
    )

    context = {
        "draft_entries": drafts,
        "pending_count": len(drafts),
        "entry_types": JournalEntry.EntryType.choices,
        "periods": Period.objects.filter(company=company, is_closed=False),
        "accounts": Account.objects.filter(company=company, is_active=True),
        "currencies": Currency.objects.all(),
        "tax_codes": TaxCode.objects.filter(company=company),
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
    """The View button sends the overlay here. The user can change the line
    description only, thus the view ignores the other fields."""
    if request.method == "POST":
        entry = get_object_or_404(JournalEntry, pk=pk, company=request.company, status=JournalEntry.Status.DRAFT)
        entry.lines.update(description=request.POST.get("description", ""))
    return redirect("accounting:journals")

def journalentry_post(request, pk):
    """The Accept button. It moves one draft entry to the Posted status."""
    if request.method == "POST":
        JournalEntry.objects.filter(pk=pk, company=request.company, status=JournalEntry.Status.DRAFT).update(
            status=JournalEntry.Status.POSTED, posted_at=timezone.now(),
        )
    return redirect("accounting:journals")

def journalentry_post_all(request):
    """The Accept All button. It moves each draft entry to the Posted status."""
    if request.method == "POST":
        JournalEntry.objects.filter(company=request.company, status=JournalEntry.Status.DRAFT).update(
            status=JournalEntry.Status.POSTED, posted_at=timezone.now(),
        )
    return redirect("accounting:journals")

def journalentry_void(request, pk):
    """The Void button of the entry overlay. It stops a draft entry."""
    if request.method == "POST":
        JournalEntry.objects.filter(pk=pk, company=request.company, status=JournalEntry.Status.DRAFT).update(
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
    company = request.company
    in_range = Q(lines__entry__date__range=(start, end),
                 lines__entry__status=JournalEntry.Status.POSTED,
                 lines__entry__basis__in=JournalEntry.bases_of(company))

    accounts = list(Account.objects.filter(company=company).annotate(
        debits=Coalesce(Sum("lines__base_debit", filter=in_range), ZERO, output_field=DecimalField()),
        credits=Coalesce(Sum("lines__base_credit", filter=in_range), ZERO, output_field=DecimalField()),
    ).order_by("code"))
 
    parent_ids = set(Account.objects.filter(company=company).exclude(parent=None).values_list("parent_id", flat=True))
 
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

def posted_lines(company):
    """The posted lines of the company, for the basis of the company."""
    return JournalLine.objects.filter(entry__company=company,
                                      entry__status=JournalEntry.Status.POSTED,
                                      entry__basis__in=JournalEntry.bases_of(company))

def movements(company, start=None, end=None):
    """The signed movement (debits less credits) of each account, from the
    posted entries in the date range. Returns {account_id: Decimal}."""
    lines = posted_lines(company)
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
    company = request.company
    return {
        "start": start, "end": end, "prev_start": prev_start, "prev_end": prev_end,
        "company": company,
        "currency": company.base_currency_id,
        "basis": company.get_accounting_basis_display().lower(),
    }

def ledger(request):
    ctx = statement_context(request)
    company = ctx["company"]
    opening = movements(company, end=ctx["start"] - timedelta(days=1))
    lines = (posted_lines(company)
             .filter(entry__date__range=(ctx["start"], ctx["end"]))
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

def balance_data(accounts, this, last):
    """The figures of the balance sheet. this and last are the balances
    (see movements) at the end of this period and of the last period."""
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
    return {
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
    }

def balancesheet(request):
    ctx = statement_context(request)
    company = ctx["company"]
    accounts = list(Account.objects.filter(company=company))
    ctx.update(balance_data(accounts, movements(company, end=ctx["end"]), movements(company, end=ctx["prev_end"])))
    return render(request, "accounting/balance_sheet.html", ctx)

def income_data(accounts, this, last):
    """The figures of the income statement. this and last are the
    movements (see movements) of this period and of the last period."""
    groups = by_type(accounts)
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

    return {
        "rows": (revenue + cost + [sum_row("Gross profit", gross_this, gross_last)]
                 + other + expenses + [sum_row("Operating profit", operating_this, operating_last)]
                 + tax),
        "revenue": rev_this,
        "revenue_last": rev_last,
        "cost_of_sales": cost_this,
        "cost_of_sales_last": cost_last,
        "expenses": exp_this,
        "expenses_last": exp_last,
        "gross_profit": gross_this,
        "operating_profit": operating_this,
        "tax": tax_this,
        "profit_this": profit_this,
        "profit_last": profit_last,
        "margin_this": gross_this / rev_this * 100 if rev_this else None,
        "margin_last": gross_last / rev_last * 100 if rev_last else None,
    }

def incomestatement(request):
    ctx = statement_context(request)
    company = ctx["company"]
    accounts = list(Account.objects.filter(company=company))
    ctx.update(income_data(accounts, movements(company, ctx["start"], ctx["end"]),
                           movements(company, ctx["prev_start"], ctx["prev_end"])))
    return render(request, "accounting/income_statement.html", ctx)

def cashflow(request):
    return render(request, "accounting/cash_flow.html")

def equity(request):
    ctx = statement_context(request)
    company = ctx["company"]
    accounts = list(Account.objects.filter(company=company))
    columns = [a for a in accounts if a.type == Account.AccountType.SHAREHOLDER_EQUITY]
    column_ids = [a.id for a in columns]
    size = len(columns) + 1

    def row(name, values, row_class, reference="", prior=False):
        return {"name": name, "reference": reference, "values": values,
                "total": sum(values, ZERO),
                "row_class": row_class + (" is-prior" if prior else "")}

    def balance_row(end, prior):
        bal = movements(company, end=end)
        values = [-bal.get(a.id, ZERO) for a in columns] + [profit_of(bal, accounts)]
        return row(f"Balance at {end:%d %b %Y}", values, "is-sum", prior=prior)

    def period_rows(start, end, prior):
        """The group row of one period, its profit, and one row for each
        posted entry that touched an equity account."""
        mv = movements(company, start, end)
        rows = [{"group": True, "start": start, "end": end,
                 "row_class": "is-group" + (" is-prior" if prior else "")}]
        rows.append(row("Profit for the period", [ZERO] * (size - 1) + [profit_of(mv, accounts)], "is-nest", prior=prior))
        entries = (JournalEntry.objects
                   .filter(company=company, status=JournalEntry.Status.POSTED, date__range=(start, end),
                           basis__in=JournalEntry.bases_of(company), lines__account__in=columns)
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

# ___________________________________UI SHELLS_______________________________________#
# These pages show dummy data from the template only.


def reports(request):
    return render(request, "accounting/reports.html")

def bill_list(request, *statuses, **filters):
    """The bills of the company with one of the statuses, the next due first."""
    return list(Document.objects
                .filter(company=request.company, direction=Document.Direction.PURCHASE,
                        doc_type=Document.DocType.BILL, status__in=statuses, **filters)
                .select_related("entity").prefetch_related("lines__tax_code")
                .order_by("due", "date"))

def bills(request):
    """Review: the draft bills. Unpaid: the approved bills that are not
    paid in full. Paid: the paid bills of the date range."""
    _, start, end = get_range(request)
    S = Document.Status
    review = bill_list(request, S.DRAFT)
    unpaid = bill_list(request, S.SENT, S.APPROVED, S.PART_PAID)
    paid = bill_list(request, S.PAID, date__range=(start, end))
    return render(request, "accounting/bills.html", {
        "review_bills": review,
        "unpaid_bills": unpaid,
        "paid_bills": paid,
        "unpaid_total": sum((b.gross for b in unpaid), ZERO),
        "paid_total": sum((b.gross for b in paid), ZERO),
        "today": timezone.localdate(),
    })

def bill_review(request, pk, status):
    """The Approve and Deny buttons. They change a draft bill only."""
    if request.method == "POST":
        Document.objects.filter(pk=pk, company=request.company, doc_type=Document.DocType.BILL,
                                status=Document.Status.DRAFT).update(status=status)
    return redirect("accounting:bills")

def bill_approve(request, pk):
    return bill_review(request, pk, Document.Status.APPROVED)

def bill_deny(request, pk):
    return bill_review(request, pk, Document.Status.VOID)

def suppliers(request):
    return render(request, "accounting/suppliers.html")

def claims(request):
    return render(request, "accounting/claims.html")

def accounting_settings(request):
    return render(request, "accounting/accounting_settings.html")

def module_settings(request):
    company = request.company
    membership = request.user.memberships.filter(company=company).first()
    can_post = bool(membership and membership.can_post)
    if request.method == "POST":
        # The viewing mode goes into a cookie. The basis goes onto the company.
        basis = request.POST.get("accounting_basis")
        if can_post and basis in Company.Basis.values:
            company.accounting_basis = basis
            company.save(update_fields=["accounting_basis"])
        mode = "easy" if request.POST.get("easy_view") else "standard"
        response = redirect("accounting:module_settings")
        response.set_cookie("view_mode", mode, max_age=365 * 24 * 3600, samesite="Lax")
        return response
    return render(request, "accounting/module_settings.html", {
        "bases": Company.Basis.choices, "can_set_basis": can_post,
    })

# Customers
def customers(request):
    return render(request, "accounting/customers.html")

def customer_new(request):
    return render(request, "accounting/customer_new.html")

def receivables(request):
    return render(request, "accounting/receivables.html")

def aging_receivables(request):
    return render(request, "accounting/aging_receivables.html")

def customer_dashboard(request):
    return render(request, "accounting/customer_dashboard.html")

# Suppliers
def supplier_new(request):
    return render(request, "accounting/supplier_new.html")

def payables(request):
    return render(request, "accounting/payables.html")

def aging_payables(request):
    return render(request, "accounting/aging_payables.html")

def supplier_dashboard(request):
    return render(request, "accounting/supplier_dashboard.html")

# Banking
def bank_accounts(request):
    return render(request, "accounting/bank_accounts.html")

def bank_account_new(request):
    return render(request, "accounting/bank_account_new.html")

def cards(request):
    return render(request, "accounting/cards.html")

def import_statement(request):
    return render(request, "accounting/import_statement.html")

def reconcile(request):
    return render(request, "accounting/reconcile.html")

def payment_runs(request):
    return render(request, "accounting/payment_runs.html")

# Taxes
def income_tax(request):
    return render(request, "accounting/income_tax.html")

def provisional_tax(request):
    return render(request, "accounting/provisional_tax.html")

def vat(request):
    return render(request, "accounting/vat.html")

def paye(request):
    return render(request, "accounting/paye.html")

def tax_dashboard(request):
    return render(request, "accounting/tax_dashboard.html")
