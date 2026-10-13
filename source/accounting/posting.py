"""accounting/posting.py: the entries of an invoice and of a payment."""
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from accounting.models import Account, Document, JournalEntry, JournalLine, Payment, Period

CENT = Decimal("0.01")

# The posting finds these accounts by name in the chart of accounts.
RECEIVABLE = "Accounts Receivable"
PAYABLE    = "Accounts Payable"
SUSPENSE   = "Suspense"
VAT        = "VAT Control"


def _add(entry, account, amount, entity=None):
    """Add one line. A positive amount is a debit. A negative amount is a credit."""
    amount = Decimal(amount).quantize(CENT, ROUND_HALF_UP)
    if amount == 0:
        return amount
    side = "debit" if amount > 0 else "credit"
    JournalLine.objects.create(entry=entry, account=account, currency=entry.company.base_currency, entity=entity,
                               **{side: abs(amount), f"base_{side}": abs(amount)})
    return amount


def _account(company, name):
    """Return the account with the name. Tell the user when it does not exist."""
    account = Account.objects.filter(company=company, name=name).first()
    if account is None:
        raise ValidationError(f'The chart of accounts has no account "{name}". Add it first.')
    return account


def _open_period(company, date):
    """Return the open period that includes the date. Tell the user when there is none."""
    period = Period.objects.filter(company=company, start_date__lte=date,
                                   end_date__gte=date, is_closed=False).first()
    if period is None:
        raise ValidationError(f"No open period includes the date {date:%d %b %Y}.")
    return period


def post_cash_entry(payment, period, suspense):
    """Write the draft CASH entry of a payment. Call again each time the allocations change."""
    sign = 1 if payment.direction == Payment.Direction.IN else -1
    with transaction.atomic():
        if payment.cash_entry_id:
            JournalEntry.objects.filter(pk=payment.cash_entry_id).update(status=JournalEntry.Status.VOID)

        entry = JournalEntry.objects.create(
            company=payment.company, date=payment.date, period=period,
            entry_type=JournalEntry.EntryType.RECEIPT if sign > 0 else JournalEntry.EntryType.PAYMENT,
            basis=JournalEntry.Basis.CASH, status=JournalEntry.Status.DRAFT,
            reference=payment.number, narration=f"{payment.entity.name} (cash basis)",
        )
        total = _add(entry, payment.bank_account.account, sign * payment.amount)

        for allocation in payment.allocations.select_related("document"):
            share = allocation.amount / allocation.document.gross
            for line in allocation.document.lines.select_related("tax_code"):
                total += _add(entry, line.account, -sign * line.net_amount * share)
                if line.tax_code:
                    tax = line.tax_code.output_account if sign > 0 else line.tax_code.input_account
                    total += _add(entry, tax, -sign * line.tax_amount * share)

        _add(entry, suspense, -total)  # Unallocated part and rounding.
        payment.cash_entry = entry
        payment.save(update_fields=["cash_entry"])
    return entry


def post_payment(payment):
    """Write the two draft entries of a new payment.

    ACCRUAL: money in is Dr Bank / Cr Accounts Receivable. Money out is
    Dr Accounts Payable / Cr Bank. The control line keeps the entity,
    thus the statement of the customer finds it.
    CASH: see post_cash_entry. Without allocations, the amount goes to
    the Suspense account.
    """
    company = payment.company
    period = _open_period(company, payment.date)
    received = payment.direction == Payment.Direction.IN
    control = _account(company, RECEIVABLE if received else PAYABLE)
    suspense = _account(company, SUSPENSE)
    sign = 1 if received else -1

    with transaction.atomic():
        entry = JournalEntry.objects.create(
            company=company, date=payment.date, period=period,
            entry_type=JournalEntry.EntryType.RECEIPT if received else JournalEntry.EntryType.PAYMENT,
            basis=JournalEntry.Basis.ACCRUAL, status=JournalEntry.Status.DRAFT,
            reference=payment.number, narration=payment.entity.name,
        )
        _add(entry, payment.bank_account.account, sign * payment.amount)
        _add(entry, control, -sign * payment.amount, entity=payment.entity)
        payment.journal_entry = entry
        payment.save(update_fields=["journal_entry"])
        post_cash_entry(payment, period, suspense)


def post_invoice_entry(company, number, date, total, tax, narration="", entity=None):
    """Write the draft ACCRUAL entry of a sales invoice. Do nothing when the invoice has an entry.

    The receivable line keeps the entity, thus the statement of the customer finds it.
    A missing account or open period raises a ValidationError that tells the user.
    """
    entries = JournalEntry.objects.filter(company=company, entry_type=JournalEntry.EntryType.SALES, reference=number)
    if entries.exclude(status=JournalEntry.Status.VOID).exists():
        return None

    with transaction.atomic():
        entry = JournalEntry.objects.create(
            company=company, date=date, period=_open_period(company, date),
            entry_type=JournalEntry.EntryType.SALES, basis=JournalEntry.Basis.ACCRUAL,
            status=JournalEntry.Status.DRAFT, reference=number, narration=narration,
        )
        _add(entry, _account(company, RECEIVABLE), total, entity=entity)
        _add(entry, _account(company, "Sales"), -(total - tax))
        _add(entry, _account(company, VAT), -tax)
    return entry


def post_bill(bill):
    """Approve a draft bill: write its ACCRUAL entry and post it.

    Dr the account of each line (net) and the input tax account (tax),
    Cr Accounts Payable (gross). The payable line keeps the supplier,
    thus the statement of the supplier finds it. On the cash basis the
    bill shows when it is paid (see post_cash_entry).
    """
    company = bill.company
    period = _open_period(company, bill.date)
    payable = _account(company, PAYABLE)

    with transaction.atomic():
        entry = JournalEntry.objects.create(
            company=company, date=bill.date, period=period,
            entry_type=JournalEntry.EntryType.PURCHASES, basis=JournalEntry.Basis.ACCRUAL,
            status=JournalEntry.Status.POSTED, posted_at=timezone.now(),
            reference=bill.number, narration=bill.entity.name,
        )
        total = Decimal(0)
        for line in bill.lines.select_related("account", "tax_code__input_account"):
            total += _add(entry, line.account, line.net_amount)
            if line.tax_amount:
                total += _add(entry, line.tax_code.input_account or _account(company, VAT), line.tax_amount)
        _add(entry, payable, -total, entity=bill.entity)
        bill.journal_entry = entry
        bill.status = Document.Status.APPROVED
        bill.save(update_fields=["journal_entry", "status"])
    return entry
