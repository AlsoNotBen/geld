"""accounting/posting.py: the entries of an invoice and of a payment."""
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
from accounting.models import Account, JournalEntry, JournalLine, Payment, Period

CENT = Decimal("0.01")


def _add(entry, account, amount):
    """Add one line. A positive amount is a debit. A negative amount is a credit."""
    amount = Decimal(amount).quantize(CENT, ROUND_HALF_UP)
    if amount == 0:
        return amount
    side = "debit" if amount > 0 else "credit"
    JournalLine.objects.create(entry=entry, account=account, currency=entry.company.base_currency,
                               **{side: abs(amount), f"base_{side}": abs(amount)})
    return amount


def post_cash_entry(payment, period, suspense):
    """Write the CASH entry of a payment. Call again each time the allocations change."""
    sign = 1 if payment.direction == Payment.Direction.IN else -1
    with transaction.atomic():
        if payment.cash_entry_id:
            JournalEntry.objects.filter(pk=payment.cash_entry_id).update(status=JournalEntry.Status.VOID)

        entry = JournalEntry.objects.create(
            company=payment.company, date=payment.date, period=period,
            entry_type=JournalEntry.EntryType.RECEIPT if sign > 0 else JournalEntry.EntryType.PAYMENT,
            basis=JournalEntry.Basis.CASH, status=JournalEntry.Status.POSTED,
            posted_at=timezone.now(), reference=payment.number,
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


def post_invoice_entry(company, number, date, total, tax, narration=""):
    """Write the draft ACCRUAL entry of a sales invoice. Do nothing when the invoice has an entry."""
    entries = JournalEntry.objects.filter(company=company, entry_type=JournalEntry.EntryType.SALES, reference=number)
    if entries.exclude(status=JournalEntry.Status.VOID).exists():
        return None

    def account(name):
        return Account.objects.get(company=company, name=name)

    with transaction.atomic():
        entry = JournalEntry.objects.create(
            company=company, date=date,
            period=Period.objects.get(company=company, start_date__lte=date, end_date__gte=date),
            entry_type=JournalEntry.EntryType.SALES, basis=JournalEntry.Basis.ACCRUAL,
            status=JournalEntry.Status.DRAFT, reference=number, narration=narration,
        )
        _add(entry, account("Accounts Receivable"), total)
        _add(entry, account("Sales"), -(total - tax))
        _add(entry, account("VAT Control"), -tax)
    return entry
