"""accounting/posting.py: the entries of an invoice, a payment and an opening balance,
and the reversal and the recurring copies of an entry."""
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from accounting.models import (Account, BankAccount, Document, DocumentLine, JournalEntry, JournalLine, Payment,
                               PaymentAllocation, Period, RecurringEntry, customer_entities, supplier_entities)

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


def _add_rolled_up(entry, parts):
    """Add one line for each account: the sum of its (account, amount) parts. Thus an
    invoice with many lines on one account makes one journal line. Returns the total."""
    sums = {}
    for account, amount in parts:
        sums[account] = sums.get(account, Decimal(0)) + amount
    return sum((_add(entry, account, amount) for account, amount in sums.items()), Decimal(0))


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

        rolled = []
        for allocation in payment.allocations.select_related("document"):
            document = allocation.document
            share = allocation.amount / document.gross
            parts = [(line.account, line.net_amount) for line in document.lines.select_related("account")]
            parts += [((code.output_account if sign > 0 else code.input_account) or _account(payment.company, VAT), tax)
                      for code, tax in document.tax_lines()]
            parts = [(account, (amount * share).quantize(CENT, ROUND_HALF_UP)) for account, amount in parts]
            account, last = parts[-1]       # The last part takes the rounding. Thus the parts make the allocation.
            parts[-1] = (account, last + allocation.amount - sum(amount for _, amount in parts))
            rolled += [(account, -sign * amount) for account, amount in parts]
        total += _add_rolled_up(entry, rolled)

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


def is_direct(payment):
    """True when the user selected an account that is not a control account.
    Such a payment is not for an invoice or a bill (e.g. a bank charge or a loan)."""
    return payment.account_id is not None and payment.account.name not in (RECEIVABLE, PAYABLE)


def allocate(payment):
    """Allocate the payment to the open documents of its entity. Money out
    pays bills. Money in pays invoices. A draft or void document does not count.

    First the payment pays the document with the reference as its number. The
    match must be exact. Then the rest pays the oldest open documents first:
    always for bills, and for invoices only when the company has the setting
    "Allocate unreferenced to oldest invoices". An amount that is left over
    stays unallocated (see post_cash_entry: it goes to Suspense).
    A direct payment (see is_direct) pays no document.
    Returns the documents that the payment pays.
    """
    if is_direct(payment):
        return []
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

    The account of the payment, when the user selected one, replaces the
    control account. A direct payment (see is_direct) has no allocations,
    thus its cash entry also goes to that account, not to Suspense.
    """
    company = payment.company
    period = _open_period(company, payment.date)
    received = payment.direction == Payment.Direction.IN
    control = payment.account or control_account(payment)
    suspense = payment.account if is_direct(payment) else _account(company, SUSPENSE)
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


def post_invoice_entry(invoice):
    """Write the draft ACCRUAL entry of a sales invoice from its lines, as post_bill does.

    Dr Accounts Receivable (gross), Cr the accounts of the lines (net) and the output
    tax account of each tax code (tax). Each account gets one journal line only: the
    sum of its invoice lines (see _add_rolled_up). Thus the entry agrees with Document.gross.
    The receivable line keeps the entity, thus the statement of the customer finds it.
    A missing account or open period raises a ValidationError that tells the user.

    An invoice that changed keeps its draft entry: the entry gets the new date and all
    the new lines. The tax is the tax of the invoice only. The default tax code of an
    account (Account.tax_code) adds no tax here.
    """
    company = invoice.company
    head = {"date": invoice.date, "period": _open_period(company, invoice.date), "narration": invoice.entity.name}
    with transaction.atomic():
        entry = invoice.journal_entry
        if entry and entry.status == JournalEntry.Status.DRAFT:
            for name, value in head.items():
                setattr(entry, name, value)
            entry.save()
            entry.lines.all().delete()
        else:
            entry = JournalEntry.objects.create(
                company=company, entry_type=JournalEntry.EntryType.SALES, basis=JournalEntry.Basis.ACCRUAL,
                status=JournalEntry.Status.DRAFT, reference=invoice.number, **head,
            )
        parts = [(line.account, -line.net_amount) for line in invoice.lines.select_related("account")]
        parts += [(code.output_account or _account(company, VAT), -tax) for code, tax in invoice.tax_lines()]
        total = _add_rolled_up(entry, parts)
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
        parts = [(line.account, line.net_amount) for line in bill.lines.select_related("account")]
        parts += [(code.input_account or _account(company, VAT), tax) for code, tax in bill.tax_lines()]
        total = _add_rolled_up(entry, parts)
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
    Dr Opening Balance Equity / Cr Accounts Payable. A negative amount is a credit: the
    business owes the customer, or the supplier owes the business. Its entry has the
    opposite sides, and no payment pays it (see _pay). Returns the document."""
    number = f"OB-{entity.pk}"      # Document.is_opening finds the document with this number.
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


def copy_entry(source, date, reverse=False, **fields):
    """Write a draft copy of the entry on the date, with the same lines. reverse moves each
    amount to the other side. fields replace fields of the entry. Returns the copy."""
    with transaction.atomic():
        entry = JournalEntry.objects.create(**{
            "company": source.company, "date": date, "period": _open_period(source.company, date),
            "entry_type": source.entry_type, "basis": source.basis, "status": JournalEntry.Status.DRAFT,
            "reference": source.reference, "narration": source.narration, **fields,
        })
        JournalLine.objects.bulk_create(
            JournalLine(entry=entry, account_id=line.account_id, description=line.description,
                        currency_id=line.currency_id, exchange_rate=line.exchange_rate,
                        debit=line.credit if reverse else line.debit, credit=line.debit if reverse else line.credit,
                        base_debit=line.base_credit if reverse else line.base_debit,
                        base_credit=line.base_debit if reverse else line.base_credit,
                        tax_code_id=line.tax_code_id, entity_id=line.entity_id, project_id=line.project_id)
            for line in source.lines.order_by("id"))
    return entry


def linked_entry_ids(company):
    """The entries that a document, a payment or a bank account made. Such an entry is not
    reversed in the journal, because the record (e.g. the open invoice) must change with it."""
    ids = set(Document.objects.filter(company=company).values_list("journal_entry_id", flat=True))
    for pair in Payment.objects.filter(company=company).values_list("journal_entry_id", "cash_entry_id"):
        ids.update(pair)
    ids.update(BankAccount.objects.filter(company=company).values_list("opening_entry_id", flat=True))
    return ids


def reverse_entry(entry, date):
    """Write the draft entry that reverses a posted entry: the same lines on the other side,
    on the date. The entry itself does not change, thus the ledger keeps its history. The
    reversal links to the entry (JournalEntry.reverses). An entry has one reversal only,
    but a void reversal does not count. Returns the reversal."""
    if entry.status != JournalEntry.Status.POSTED:
        raise ValidationError("Only a posted entry can be reversed. Mark a draft entry as void.")
    if entry.pk in linked_entry_ids(entry.company):
        raise ValidationError(f"{entry.reference} is the entry of a document, a payment or a bank account. "
                              "It cannot be reversed in the journal.")
    if entry.reversed_by.exclude(status=JournalEntry.Status.VOID).exists():
        raise ValidationError(f"{entry.reference} already has a reversal.")
    if date < entry.date:
        raise ValidationError("The date of the reversal cannot be before the date of the entry.")
    return copy_entry(entry, date, reverse=True, reverses=entry, reference=f"REV-{entry.reference}"[:255],
                      narration=f"Reversal of {entry.reference} of {entry.date:%d %b %Y}")


def run_recurring(company):
    """Write the draft entries of the recurring entries that are due: one copy of the template
    for each date up to today (see RecurringEntry). A date without an open period makes no
    entry: the series waits for the period. Returns the problems as text, for the user."""
    today = timezone.localdate()
    problems = []
    with transaction.atomic():
        due = RecurringEntry.objects.select_for_update().filter(company=company, is_active=True, next_run__lte=today)
        for recurring in due:
            template = recurring.template
            try:
                while recurring.is_active and recurring.next_run <= today:
                    copy_entry(template, recurring.next_run, recurring=recurring)
                    recurring.advance()
            except ValidationError as error:
                problems.append(f"The recurring entry {template.reference} waits. {' '.join(error.messages)}")
    return problems
