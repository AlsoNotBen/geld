"""accounting/posting.py: the entries of an invoice, a payment and an opening balance."""
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from accounting.models import (Account, Document, DocumentLine, JournalEntry, JournalLine, Payment, PaymentAllocation,
                               Period, customer_entities, supplier_entities)

CENT = Decimal("0.01")

# The posting finds these accounts by name in the chart of accounts.
RECEIVABLE = "Accounts Receivable"
PAYABLE    = "Accounts Payable"
SUSPENSE   = "Suspense"
VAT        = "VAT Control"
OPENING    = "Opening Balance Equity"


def _add(entry, account, amount, entity=None, description=""):
    """Add one line. A positive amount is a debit. A negative amount is a credit."""
    amount = Decimal(amount).quantize(CENT, ROUND_HALF_UP)
    if amount == 0:
        return amount
    side = "debit" if amount > 0 else "credit"
    JournalLine.objects.create(entry=entry, account=account, currency=entry.company.base_currency, entity=entity,
                               description=description, **{side: abs(amount), f"base_{side}": abs(amount)})
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
            document = allocation.document
            share = allocation.amount / document.gross
            parts = [(line.account, line.net_amount) for line in document.lines.select_related("account")]
            parts += [((code.output_account if sign > 0 else code.input_account) or _account(payment.company, VAT), tax)
                      for code, tax in document.tax_lines()]
            parts = [(account, (amount * share).quantize(CENT, ROUND_HALF_UP)) for account, amount in parts]
            account, last = parts[-1]       # The last part takes the rounding. Thus the parts make the allocation.
            parts[-1] = (account, last + allocation.amount - sum(amount for _, amount in parts))
            for account, amount in parts:
                total += _add(entry, account, -sign * amount)

        _add(entry, suspense, -total)  # The unallocated part.
        payment.cash_entry = entry
        payment.save(update_fields=["cash_entry"])
    return entry


def _pay(payment, document, amount):
    """Allocate a part of the payment to the document: the amount, but not
    more than the open amount of the document. The document becomes Paid, or
    Partially paid when an amount stays open. Returns the part."""
    open_amount = document.balance
    part = min(amount, open_amount)
    if part <= 0:
        return Decimal(0)
    PaymentAllocation.objects.create(payment=payment, document=document, amount=part)
    document.status = Document.Status.PART_PAID if part < open_amount else Document.Status.PAID
    document.save(update_fields=["status", "updated_at"])
    return part


def allocate(payment):
    """Allocate the payment to the open documents of its entity. Money out
    pays bills. Money in pays invoices. A draft or void document does not count.

    First the payment pays the document with the reference as its number. The
    match must be exact. Then the rest pays the oldest open documents first:
    always for bills, and for invoices only when the company has the setting
    "Allocate unreferenced to oldest invoices". An amount that is left over
    stays unallocated (see post_cash_entry: it goes to Suspense).
    Returns the documents that the payment pays.
    """
    S = Document.Status
    paid_out = payment.direction == Payment.Direction.OUT
    documents = Document.objects.filter(
        company=payment.company, entity=payment.entity,
        direction=Document.Direction.PURCHASE if paid_out else Document.Direction.SALE,
        doc_type=Document.DocType.BILL if paid_out else Document.DocType.INVOICE,
        status__in=[S.SENT, S.APPROVED, S.PART_PAID],
    )
    reference = payment.reference.strip()
    queue = list(documents.filter(number=reference)) if reference else []
    if paid_out or payment.company.allocate_to_oldest:
        queue += [document for document in documents.order_by("date", "id") if document not in queue]

    paid, rest = [], payment.amount
    for document in queue:
        if rest <= 0:
            break
        part = _pay(payment, document, rest)
        if part:
            paid.append(document)
            rest -= part
    return paid


def control_account(payment):
    """The control account of a payment: Accounts Receivable for a customer,
    Accounts Payable for a supplier, in both directions. Thus money in from a
    supplier (e.g. a refund) changes the supplier balance. For an entity that
    is a customer and a supplier, or neither, the direction decides: money
    in is from a customer, money out is to a supplier."""
    company = payment.company
    customer = customer_entities(company).filter(pk=payment.entity_id).exists()
    supplier = supplier_entities(company).filter(pk=payment.entity_id).exists()
    receivable = customer if customer != supplier else payment.direction == Payment.Direction.IN
    return _account(company, RECEIVABLE if receivable else PAYABLE)


def post_payment(payment):
    """Write the two draft entries of a new payment.

    ACCRUAL: money in is Dr Bank / Cr the control account. Money out is
    Dr the control account / Cr Bank (see control_account). The control
    line keeps the entity, thus the balance of the customer or supplier
    and the statement of the customer find it.
    CASH: see post_cash_entry. Without allocations, the amount goes to
    the Suspense account.
    """
    company = payment.company
    period = _open_period(company, payment.date)
    received = payment.direction == Payment.Direction.IN
    control = control_account(payment)
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


def invoice_posted(company, number):
    """True when the sales invoice with the number has an entry that is not void."""
    return (JournalEntry.objects.filter(company=company, entry_type=JournalEntry.EntryType.SALES, reference=number)
            .exclude(status=JournalEntry.Status.VOID).exists())


def post_invoice_entry(invoice):
    """Write the draft ACCRUAL entry of a sales invoice from its lines, as post_bill does.

    Dr Accounts Receivable (gross), Cr the account of each line (net) and the output
    tax account of each tax code (tax). Thus the entry agrees with Document.gross.
    The receivable line keeps the entity, thus the statement of the customer finds it.
    A missing account or open period raises a ValidationError that tells the user.
    """
    company = invoice.company
    with transaction.atomic():
        entry = JournalEntry.objects.create(
            company=company, date=invoice.date, period=_open_period(company, invoice.date),
            entry_type=JournalEntry.EntryType.SALES, basis=JournalEntry.Basis.ACCRUAL,
            status=JournalEntry.Status.DRAFT, reference=invoice.number, narration=invoice.entity.name,
        )
        total = Decimal(0)
        for line in invoice.lines.select_related("account"):
            total += _add(entry, line.account, -line.net_amount)
        for code, tax in invoice.tax_lines():
            total += _add(entry, code.output_account or _account(company, VAT), -tax)
        _add(entry, _account(company, RECEIVABLE), -total, entity=invoice.entity)
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
        for line in bill.lines.select_related("account"):
            total += _add(entry, line.account, line.net_amount)
        for code, tax in bill.tax_lines():
            total += _add(entry, code.input_account or _account(company, VAT), tax)
        _add(entry, payable, -total, entity=bill.entity)
        bill.journal_entry = entry
        bill.status = Document.Status.APPROVED
        bill.save(update_fields=["journal_entry", "status"])
    return entry


def post_opening_balance(company, account, amount, date, reference, narration, entity=None,
                         basis=JournalEntry.Basis.BOTH):
    """Write the posted entry of an opening balance. A positive amount is a debit on the
    account. The other side goes to Opening Balance Equity. Returns the entry."""
    opening = _account(company, OPENING)
    period = _open_period(company, date)
    with transaction.atomic():
        entry = JournalEntry.objects.create(
            company=company, date=date, period=period, entry_type=JournalEntry.EntryType.GENERAL, basis=basis,
            status=JournalEntry.Status.POSTED, posted_at=timezone.now(), reference=reference, narration=narration,
        )
        _add(entry, account, amount, entity=entity, description="Opening balance")
        _add(entry, opening, -amount)
    return entry


def post_opening_document(company, entity, amount, date, sale):
    """Keep the opening balance of a customer (sale) or a supplier as an open invoice or
    bill. Thus a payment can pay it (see allocate), and the open documents agree with
    the journal. The entry is Dr Accounts Receivable / Cr Opening Balance Equity, or
    Dr Opening Balance Equity / Cr Accounts Payable. Returns the document."""
    number = f"OB-{entity.pk}"
    control = _account(company, RECEIVABLE if sale else PAYABLE)
    with transaction.atomic():
        entry = post_opening_balance(company, control, amount if sale else -amount, date, number, entity.name,
                                     entity=entity, basis=JournalEntry.Basis.ACCRUAL)
        document = Document.objects.create(
            company=company, direction=Document.Direction.SALE if sale else Document.Direction.PURCHASE,
            doc_type=Document.DocType.INVOICE if sale else Document.DocType.BILL, number=number,
            date=date, due=date, entity=entity, currency=company.base_currency, notes="Opening balance",
            status=Document.Status.SENT if sale else Document.Status.APPROVED, journal_entry=entry,
        )
        DocumentLine.objects.create(document=document, account=_account(company, OPENING),
                                    description="Opening balance", quantity=1, unit_price=amount)
    return document


def set_bank_opening(bank, amount, date):
    """Replace the opening balance of a bank account: void the old entry, then post the
    amount on the ledger account of the bank. A negative amount is an overdraft. No
    amount posts no entry."""
    old = bank.opening_entry
    if old and old.period.is_closed:
        raise ValidationError("The period of the opening balance is closed. You cannot change it.")
    with transaction.atomic():
        if old:
            old.status = JournalEntry.Status.VOID
            old.save(update_fields=["status", "updated_at"])
        bank.opening_entry = post_opening_balance(bank.company, bank.account, amount, date, f"OB-{bank.account.code}",
                                                  bank.name) if amount else None
        bank.save(update_fields=["opening_entry"])
