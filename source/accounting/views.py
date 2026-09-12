from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, DecimalField, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from decimal import Decimal
from accounting.models import *
from accounting.date_range import get_range

ZERO = Decimal("0")

def dashboard(request):
    return render(request, "accounting/overview.html")

JOURNAL_TABS = {
    "general_entries":  [JournalEntry.EntryType.GENERAL],
    "sales_entries":    [JournalEntry.EntryType.SALES],
    "purchase_entries": [JournalEntry.EntryType.PURCHASES],
    "cash_entries":     [JournalEntry.EntryType.RECEIPT, JournalEntry.EntryType.PAYMENT],
}

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
        # Data for the New Account form.
        "account_types": Account.AccountType.choices,
        "currencies": Currency.objects.all(),
        "parent_accounts": accounts,
        # The All tab keeps every account.
        "all_accounts": accounts,
        "all_total": sum((a.signed for a in accounts), ZERO),
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


def ledger(request):
    return render(request, "accounting/ledger.html")

def balancesheet(request):
    return render(request,"accounting/balance_sheet.html")

def incomestatement(request):
    return render(request,"accounting/income_statement.html")

def cashflow(request):
    return render(request,"accounting/cash_flow.html")

def equity(request):
    return render(request,"accounting/shareholder_equity.html")