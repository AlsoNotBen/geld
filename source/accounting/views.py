import json
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import Sum, DecimalField, Q
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from accounting.models import *
from accounting.date_range import get_range, previous_range
from accounting.forms import BillForm, NoteForm, PaymentForm, SupplierForm
from accounting.posting import CENT, PAYABLE, VAT, _account, post_bill, post_payment
from datetime import datetime, timedelta
from filestore.services import save_upload, validate

ZERO = Decimal("0")
JOURNAL_TABS = {
    "general_entries":  [JournalEntry.EntryType.GENERAL],
    "sales_entries":    [JournalEntry.EntryType.SALES],
    "purchase_entries": [JournalEntry.EntryType.PURCHASES],
    "cash_entries":     [JournalEntry.EntryType.RECEIPT, JournalEntry.EntryType.PAYMENT],
}

# The Overview (the first page of the module) is in overview.py.

def journal_rows(lines):
    return [{
        "date": line.entry.date,
        "reference": line.entry.reference,
        "journal": line.entry.get_entry_type_display(),
        "account": line.account,
        "amount": line.debit or line.credit,
        "is_debit": line.debit > 0,
    } for line in lines]

def tax_account_ids(company):
    """The tax accounts: VAT Control, and the input and output account of each tax code."""
    ids = set(Account.objects.filter(company=company, name=VAT).values_list("id", flat=True))
    for pair in TaxCode.objects.filter(company=company).values_list("input_account_id", "output_account_id"):
        ids.update(pair)
    return ids

def draft_rows(entries, tax_ids):
    """One row for each draft entry. The row also holds the data of the
    edit form, thus the Edit button can fill the overlay. A line on a tax
    account, other than the debit and the credit of the row, goes into
    debit_taxes or credit_taxes. Thus the row also shows the tax effect.
    The lines stay in the order of their creation: the taxed line comes
    before its tax line (see make_lines)."""
    rows = []
    for entry in entries:
        lines = sorted(entry.lines.all(), key=lambda l: l.id)
        debit = next((l for l in lines if l.debit > 0), None)
        credit = next((l for l in lines if l.credit > 0), None)
        if not (debit and credit):
            continue
        taxes = [l for l in lines if l.account_id in tax_ids and l not in (debit, credit)]
        credit_taxes = [l for l in taxes if l.credit > 0]
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
            "debit_taxes": [l for l in taxes if l.debit > 0],
            "credit_taxes": credit_taxes,
            "amount": credit.credit if credit_taxes else debit.debit,     # The amount before tax
        })
    return rows

def make_lines(entry, post):
    """Make the lines of an entry. The amount is before tax.

    Without a tax code, the debit line and the credit line hold the amount.
    With a tax code, the tax is the amount times the rate of the tax code.
    The taxed line is the income or expense line, else the debit line. The
    tax line goes on the same side, to the output account of the tax code
    for an income account, else to its input account (or VAT Control). The
    other line holds the amount plus the tax. A rate of zero, or a debit or
    credit account that is a tax account, makes no tax line."""
    company = entry.company
    amount = Decimal(post["amount"])
    debit = get_object_or_404(Account, company=company, pk=post["debit_account"])
    credit = get_object_or_404(Account, company=company, pk=post["credit_account"])
    tax_code = TaxCode.objects.filter(company=company, pk=post.get("tax_code") or None).first()
    common = {
        "entry": entry,
        "currency_id": post["currency"],
        "tax_code": tax_code,
        "description": post.get("description", ""),
    }

    def add(account, value):
        """Add one line. A positive value is a debit. A negative value is a credit."""
        side = "debit" if value > 0 else "credit"
        JournalLine.objects.create(account=account, **{side: abs(value), f"base_{side}": abs(value)}, **common)

    if credit.type in PROFIT_TYPES and debit.type not in PROFIT_TYPES:
        taxed, other, sign = credit, debit, -1
    else:
        taxed, other, sign = debit, credit, 1
    tax = ZERO
    if tax_code and not {debit.pk, credit.pk} & tax_account_ids(company):
        tax = (amount * tax_code.rate / 100).quantize(CENT, ROUND_HALF_UP)

    add(taxed, sign * amount)
    if tax:
        tax_account = tax_code.output_account if taxed.type in CATEGORIES["income"] else tax_code.input_account
        add(tax_account or _account(company, VAT), sign * tax)
    add(other, -sign * (amount + tax))

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
        .order_by("date", "id"),
        tax_account_ids(company),
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
    """The Save button of the New Entry overlay. An error (e.g. no tax
    account) saves nothing, and the journals page shows the error."""
    if request.method == "POST":
        try:
            with transaction.atomic():
                entry = JournalEntry.objects.create(
                    company=request.company,                    # Add to every function that creates a CompanyOwned record
                    date=request.POST["date"],
                    period_id=request.POST["period"],
                    entry_type=request.POST["entry_type"],
                    status=JournalEntry.Status.DRAFT,
                    reference=request.POST["reference"],
                    narration=request.POST.get("narration", ""),
                )
                make_lines(entry, request.POST)
                AuditLog.record(request, AuditLog.Action.CREATE, entry)
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
    return redirect("accounting:journals")

def journalentry_update(request, pk):
    """The View button sends the overlay here. The user can change the line
    description only, thus the view ignores the other fields."""
    if request.method == "POST":
        entry = get_object_or_404(JournalEntry, pk=pk, company=request.company, status=JournalEntry.Status.DRAFT)
        entry.lines.update(description=request.POST.get("description", ""))
        AuditLog.record(request, AuditLog.Action.UPDATE, entry)
    return redirect("accounting:journals")

def journalentry_post(request, pk):
    """The Accept button. It moves one draft entry to the Posted status."""
    if request.method == "POST":
        if JournalEntry.objects.filter(pk=pk, company=request.company, status=JournalEntry.Status.DRAFT).update(
            status=JournalEntry.Status.POSTED, posted_at=timezone.now(),
        ):
            AuditLog.record(request, AuditLog.Action.POST, JournalEntry(pk=pk))
    return redirect("accounting:journals")

def journalentry_post_all(request):
    """The Accept All button. It moves each draft entry to the Posted status."""
    if request.method == "POST":
        ids = list(JournalEntry.objects.filter(company=request.company, status=JournalEntry.Status.DRAFT)
                   .values_list("pk", flat=True))
        JournalEntry.objects.filter(pk__in=ids, status=JournalEntry.Status.DRAFT).update(
            status=JournalEntry.Status.POSTED, posted_at=timezone.now(),
        )
        AuditLog.record(request, AuditLog.Action.POST, *(JournalEntry(pk=pk) for pk in ids))
    return redirect("accounting:journals")

def journalentry_void(request, pk):
    """The Void button of the entry overlay. It stops a draft entry."""
    if request.method == "POST":
        if JournalEntry.objects.filter(pk=pk, company=request.company, status=JournalEntry.Status.DRAFT).update(
            status=JournalEntry.Status.VOID,
        ):
            AuditLog.record(request, AuditLog.Action.VOID, JournalEntry(pk=pk))
    return redirect("accounting:journals")

def payment_create(request):
    """The Save button of the Record Payment overlay. payment_form.js sends
    the form with fetch() and reads the JSON answer: the errors, or the
    page to go to. The draft entries of the payment wait on that page."""
    if request.method != "POST":
        return redirect("accounting:journals")
    form = PaymentForm(request.POST, company=request.company)
    uploads = request.FILES.getlist("files")
    if form.is_valid():
        try:
            for upload in uploads:          # Validate every file first, so a bad file stores nothing.
                validate(upload)
            with transaction.atomic():
                payment = form.save(commit=False)
                payment.company = request.company       # Add to every function that creates a CompanyOwned record
                payment.currency = payment.bank_account.currency
                payment.created_by = request.user
                payment.save()
                post_payment(payment)
                payment.files.add(*(save_upload(u, request.user) for u in uploads))
                AuditLog.record(request, AuditLog.Action.CREATE, payment)
                if payment.number == NumberSequence.peek(request.company, "payment", "PAY-"):
                    NumberSequence.take(request.company, "payment")
            return JsonResponse({"redirect": reverse("accounting:journals")})
        except ValidationError as error:
            form.add_error(None, error)
    return form_errors(form)

def form_errors(form):
    """The errors of a form as JSON, for the overlays that send with fetch()."""
    errors = [f"{form[name].label}: {message}" if name in form.fields else message
              for name, field_errors in form.errors.items() for message in field_errors]
    return JsonResponse({"errors": errors}, status=400)

def note_create(request):
    """The Save button of the New Note overlay. notes.js sends the form with
    fetch() and reads the JSON answer. The note gets the date range of the
    page, the user and the time automatically. The page comes from the form."""
    if request.method != "POST":
        return redirect("accounting:dashboard")
    form = NoteForm(request.POST)
    uploads = request.FILES.getlist("note_files")
    if form.is_valid():
        try:
            for upload in uploads:          # Validate every file first, so a bad file stores nothing.
                validate(upload)
            _, start, end = get_range(request)
            with transaction.atomic():
                note = form.save(commit=False)
                note.company = request.company          # Add to every function that creates a CompanyOwned record
                note.created_by = request.user
                note.range_start, note.range_end = start, end
                note.save()
                note.files.add(*(save_upload(u, request.user) for u in uploads))
                AuditLog.record(request, AuditLog.Action.CREATE, note)
            return JsonResponse({"saved": True})
        except ValidationError as error:
            form.add_error(None, error)
    return form_errors(form)

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

def tree_order(accounts):
    """The accounts as (account, depth) pairs, each child below its parent.
    The depth is the number of parents above the account in the list, thus
    the table can indent the child. An account with its parent outside the
    list starts a new tree. The order in each level stays the order of the list."""
    ids = {a.pk for a in accounts}
    children = {}
    for account in accounts:
        children.setdefault(account.parent_id if account.parent_id in ids else None, []).append(account)
    rows = []
    def add(parent_id, depth):
        for account in children.get(parent_id, []):
            rows.append((account, depth))
            add(account.pk, depth + 1)
    add(None, 0)
    seen = {a.pk for a, _ in rows}
    return rows + [(a, 0) for a in accounts if a.pk not in seen]     # A loop of parents has no top account.

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
        "all_accounts"      : tree_order(accounts),
        "all_total"         : sum((a.signed for a in accounts), ZERO),
    }
    for key in CATEGORIES:
        rows = [a for a in accounts if category_of(a) == key]
        context[f"{key}_accounts"] = tree_order(rows)
        context[f"{key}_total"] = abs(sum((a.signed for a in rows), ZERO))
 
    return render(request, "accounting/chart_of_accounts.html", context)
 
def account_create(request):
    if request.method == "POST":
        account = Account.objects.create(
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
        AuditLog.record(request, AuditLog.Action.CREATE, account)
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

DEPRECIATION_WORDS = ("depreciation", "amortisation", "amortization")

def cash_account_ids(company, accounts):
    """The cash accounts: the account of each bank account, and each
    current asset with "cash" or "bank" in its name."""
    ids = set(BankAccount.objects.filter(company=company).values_list("account_id", flat=True))
    return ids | {a.id for a in accounts if a.type == Account.AccountType.CURRENT_ASSETS
                  and ("cash" in a.name.lower() or "bank" in a.name.lower())}

def depreciation_account_ids(company, accounts):
    """The accumulated depreciation accounts: the account of each fixed
    asset, and each non-current asset with "depreciation" or
    "amortisation" in its name."""
    ids = set(FixedAsset.objects.filter(company=company).values_list("accumulated_account_id", flat=True))
    return ids | {a.id for a in accounts if a.type == Account.AccountType.NON_CURRENT_ASSETS
                  and any(word in a.name.lower() for word in DEPRECIATION_WORDS)}

def cash_flow_data(accounts, cash_ids, dep_ids, this, last, open_this, open_last):
    """The figures of the cash flow statement (the indirect method).
    this and last are the movements (see movements) of this period and of
    the last period. open_this and open_last are the cash at the start.

    The cash flow of an account is its movement with the opposite sign: a
    credit movement brings cash in. The entries balance, thus the sum of
    the three groups is the movement of the cash accounts."""
    T = Account.AccountType
    other = [a for a in accounts if a.id not in cash_ids]

    def flow(accts, mv):
        return -sum((mv.get(a.id, ZERO) for a in accts), ZERO)

    def total(name, accts):
        return (name, "", flow(accts, this), flow(accts, last))

    def each(accts, prefix=""):
        return [(prefix + a.name, a.code, flow([a], this), flow([a], last)) for a in accts]

    profit = [a for a in other if a.type in PROFIT_TYPES and a.type != T.INCOME_TAX]
    depreciation = [a for a in other if a.id in dep_ids]
    working = [a for a in other if a.type in (T.CURRENT_ASSETS, T.CURRENT_LIABILITIES, T.FLOATING_NOMINAL)]
    tax = [a for a in other if a.type == T.INCOME_TAX]
    investing = [a for a in other if a.type == T.NON_CURRENT_ASSETS and a.id not in dep_ids]
    financing = [a for a in other if a.type in (T.NON_CURRENT_LIABILITIES, T.SHAREHOLDER_EQUITY)]

    op, op_this, op_last = block("Cash from operating activities",
                                 [total("Profit before tax", profit),
                                  total("Depreciation and amortisation", depreciation)]
                                 + each(working, "Movement in ")
                                 + [total("Income tax", tax)],
                                 "Net cash from operating activities")
    inv, inv_this, inv_last = block("Cash from investing activities", each(investing),
                                    "Net cash from investing activities")
    fin, fin_this, fin_last = block("Cash from financing activities", each(financing),
                                    "Net cash from financing activities")

    change_this, change_last = op_this + inv_this + fin_this, op_last + inv_last + fin_last
    cash = [a for a in accounts if a.id in cash_ids]
    end_this, end_last = open_this - flow(cash, this), open_last - flow(cash, last)
    return {
        "rows": op + inv + fin + [sum_row("Change of cash in the period", change_this, change_last)],
        "operating_this": op_this, "investing_this": inv_this, "financing_this": fin_this,
        "change_this": change_this, "change_last": change_last,
        "start_this": open_this, "start_last": open_last,
        "end_this": end_this, "end_last": end_last,
        "is_balanced": open_this + change_this == end_this,
    }

def cash_flow_of(company, accounts, start, end, prev_start, prev_end):
    cash_ids = cash_account_ids(company, accounts)
    dep_ids = depreciation_account_ids(company, accounts)

    def cash_at(day):
        balances = movements(company, end=day)
        return sum((balances.get(i, ZERO) for i in cash_ids), ZERO)

    day = timedelta(days=1)
    return cash_flow_data(accounts, cash_ids, dep_ids,
                          movements(company, start, end), movements(company, prev_start, prev_end),
                          cash_at(start - day), cash_at(prev_start - day))

def cashflow(request):
    ctx = statement_context(request)
    company = ctx["company"]
    accounts = list(Account.objects.filter(company=company))
    ctx.update(cash_flow_of(company, accounts, ctx["start"], ctx["end"], ctx["prev_start"], ctx["prev_end"]))
    return render(request, "accounting/cash_flow.html", ctx)

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
                .select_related("entity").prefetch_related("lines__tax_code", "files")
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
        "bill_form": BillForm(company=request.company),
        "accounts": Account.objects.filter(company=request.company, is_active=True),
        "tax_codes": TaxCode.objects.filter(company=request.company),
    })

def bill_lines(post, company):
    """The lines of the New Bill overlay, as unsaved DocumentLine objects.
    An empty row is ignored."""
    accounts = {str(a.id): a for a in Account.objects.filter(company=company, is_active=True)}
    taxes = {str(t.id): t for t in TaxCode.objects.filter(company=company)}
    rows = zip(post.getlist("line_description"), post.getlist("line_account"), post.getlist("line_quantity"),
               post.getlist("line_price"), post.getlist("line_tax"))
    lines = []
    for number, (description, account, quantity, price, tax) in enumerate(rows, 1):
        if not (description.strip() or account or price):
            continue
        try:
            quantity, price = Decimal(quantity or "1"), Decimal(price)
        except InvalidOperation:
            raise ValidationError(f"Line {number}: the quantity and the price must be numbers.")
        if account not in accounts:
            raise ValidationError(f"Line {number}: select an account.")
        if quantity <= 0 or price <= 0:
            raise ValidationError(f"Line {number}: the quantity and the price must be more than zero.")
        lines.append(DocumentLine(
            description=(description.strip() or accounts[account].name)[:255], account=accounts[account],
            quantity=quantity, unit_price=price, tax_code=taxes.get(tax), sort_order=number,
        ))
    if not lines:
        raise ValidationError("Add one line or more.")
    return lines

def bill_create(request):
    """The Save button of the New Bill overlay. bills.js sends the form with
    fetch() and reads the JSON answer: the errors, or the page to go to.
    The bill is a draft. It waits in the Review part of the Bills page."""
    if request.method != "POST":
        return redirect("accounting:bills")
    form = BillForm(request.POST, company=request.company)
    uploads = request.FILES.getlist("attachments")
    if form.is_valid():
        try:
            lines = bill_lines(request.POST, request.company)
            for upload in uploads:          # Validate every file first, so a bad file stores nothing.
                validate(upload)
            with transaction.atomic():
                bill = form.save(commit=False)
                bill.company = request.company          # Add to every function that creates a CompanyOwned record
                bill.direction = Document.Direction.PURCHASE
                bill.doc_type = Document.DocType.BILL
                bill.status = Document.Status.DRAFT
                bill.currency = request.company.base_currency
                bill.created_by = request.user
                bill.save()
                for line in lines:
                    line.document = bill
                DocumentLine.objects.bulk_create(lines)
                bill.files.add(*(save_upload(u, request.user) for u in uploads))
                AuditLog.record(request, AuditLog.Action.CREATE, bill)
                if bill.number == NumberSequence.peek(request.company, "bill", "BILL-"):
                    NumberSequence.take(request.company, "bill")
            return JsonResponse({"redirect": reverse("accounting:bills")})
        except ValidationError as error:
            form.add_error(None, error)
    return form_errors(form)

def bill_approve(request, pk):
    """The Approve button. It posts the entry of a draft bill to the ledger."""
    if request.method == "POST":
        bill = get_object_or_404(Document, pk=pk, company=request.company, doc_type=Document.DocType.BILL,
                                 status=Document.Status.DRAFT)
        try:
            post_bill(bill)
            AuditLog.record(request, AuditLog.Action.POST, bill)
        except ValidationError as error:
            messages.error(request, f"{bill.number} is not approved. {' '.join(error.messages)}")
    return redirect("accounting:bills")

def bill_deny(request, pk):
    """The Deny button. It voids a draft bill."""
    if request.method == "POST":
        if Document.objects.filter(pk=pk, company=request.company, doc_type=Document.DocType.BILL,
                                   status=Document.Status.DRAFT).update(status=Document.Status.VOID):
            AuditLog.record(request, AuditLog.Action.VOID, Document(pk=pk))
    return redirect("accounting:bills")

def suppliers(request):
    """Each entity with supplier details or with a bill. The balance is the
    money that the business owes: the posted Accounts Payable lines of the
    supplier (see post_bill and post_payment). The balance is overdue when
    an unpaid bill is after its due date."""
    company = request.company
    S = Document.Status
    entities = (Entity.objects.filter(company=company)
                .filter(Q(supplier__isnull=False) | Q(documents__doc_type=Document.DocType.BILL))
                .distinct().select_related("supplier").order_by("name"))
    balances = dict(JournalLine.objects
                    .filter(entry__company=company, entry__status=JournalEntry.Status.POSTED, account__name=PAYABLE)
                    .exclude(entry__basis=JournalEntry.Basis.CASH)
                    .values_list("entity")
                    .annotate(balance=Sum("base_credit") - Sum("base_debit")))
    late = set(Document.objects
               .filter(company=company, doc_type=Document.DocType.BILL, status__in=[S.SENT, S.APPROVED, S.PART_PAID],
                       due__lt=timezone.localdate())
               .values_list("entity_id", flat=True))
    rows = []
    for entity in entities:
        details = getattr(entity, "supplier", None)
        balance = balances.get(entity.id, ZERO)
        rows.append({
            "code": details and details.code,
            "name": entity.name,
            "contact": details and details.contact,
            "terms": details and details.get_terms_display(),
            "is_active": entity.is_active,
            "balance": balance,
            "is_overdue": balance > 0 and entity.id in late,
        })
    return render(request, "accounting/suppliers.html", {"suppliers": rows})

def claims(request):
    return render(request, "accounting/claims.html")

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
    """The New Supplier page. Save makes the entity (an organization), its
    profile and the supplier details. The browser then goes to the Suppliers page."""
    form = SupplierForm(request.POST or None, company=request.company)
    if form.is_valid():
        data = form.cleaned_data
        with transaction.atomic():
            entity = Entity.objects.create(
                company=request.company,                        # Add to every function that creates a CompanyOwned record
                created_by=request.user, name=data["name"], type=Entity.EntityType.ORGANIZATION,
                email=data["email"], phone=data["phone"],
            )
            OrganizationProfile.objects.create(entity=entity, legal_name=data["name"], tax_number=data["vat_number"])
            supplier = form.save(commit=False)
            supplier.company = request.company                  # Add to every function that creates a CompanyOwned record
            supplier.entity = entity
            supplier.created_by = request.user
            supplier.save()
            if supplier.code == NumberSequence.peek(request.company, "supplier", "SUP-"):
                NumberSequence.take(request.company, "supplier")
            AuditLog.record(request, AuditLog.Action.CREATE, supplier)
        return redirect("accounting:suppliers")
    return render(request, "accounting/supplier_new.html", {"form": form})

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
