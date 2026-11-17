"""accounting/posting.py: the entries of an invoice, a payment and an opening balance,
and the reversal and the recurring copies of an entry.

Tracked inventory (see inventory.models.Item.tracked) posts here too:
    post_opening_stock   a new item: the stock movement of its opening quantity, and for a
                         tracked item a draft entry Dr its asset account / Cr Opening
                         Balance Equity. It waits on the Journal Entries page.
    post_bill            a bill for tracked items: the stock comes in (move_stock).
    post_invoice_entry   an invoice for tracked items: the stock goes out, and the
                         entry gets Dr Cost of Sales / Cr the asset account at cost.
"""
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from accounting.models import (Account, BankAccount, Claim, Document, DocumentLine, JournalEntry, JournalLine,
                               Payment, PaymentAllocation, Period, RecurringEntry, customer_entities, supplier_entities)
from inventory.models import Item, StockMovement, stock_levels

CENT = Decimal("0.01")

# The posting finds these accounts by name in the chart of accounts.
RECEIVABLE = "Accounts Receivable"
PAYABLE    = "Accounts Payable"
SUSPENSE   = "Suspense"
VAT        = "VAT Control"
OPENING    = "Opening Balance Equity"
INVENTORY  = "Inventory"
COST_OF_SALES = "Cost of Sales"
INSURANCE_INCOME = "Insurance Recoveries"
CLAIM_ACCOUNTS = {     # The default control account of each kind of claim (see Claim.control_account)
    Claim.Kind.EXPENSE:   "Employee Claims Payable",
    Claim.Kind.CREDITOR:  "Creditor Claims Payable",
    Claim.Kind.INSURANCE: "Insurance Claims Receivable",
}


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
    Such a payment is not for an invoice, a bill or a claim (e.g. a bank charge or a loan)."""
    return (payment.account_id is not None and payment.account.name not in (RECEIVABLE, PAYABLE)
            and not payment.allocations.exists())


def _claim_of(payment):
    """The claim with the reference of the payment as its number, or None. Tell the user
    when the payment cannot pay the claim."""
    reference = payment.reference.strip()
    document = reference and (Document.objects.filter(company=payment.company, doc_type=Document.DocType.CLAIM,
                                                      number=reference)
                              .select_related("claim", "entity").prefetch_related("lines__tax_code").first())
    if not document:
        return None
    S = Document.Status
    if document.status not in (S.APPROVED, S.PART_PAID):
        raise ValidationError(f"Claim {document.number} is {document.get_status_display().lower()}. "
                              "Only an approved claim with an open amount can take a payment.")
    if payment.entity_id != document.entity_id:
        raise ValidationError(f"Claim {document.number} is for {document.entity.name}. Select {document.entity.name}.")
    if (payment.direction == Payment.Direction.IN) != document.claim.money_in:
        direction = Payment.Direction.IN if document.claim.money_in else Payment.Direction.OUT
        raise ValidationError(f"Claim {document.number} needs the direction {direction.label}.")
    if payment.date < document.date:
        raise ValidationError(f"The payment date cannot be before the date of claim {document.number}.")
    if payment.amount > document.balance:
        raise ValidationError(f"The amount is more than the open amount of claim {document.number}: {document.balance}.")
    return document


def allocate(payment):
    """Allocate the payment to the open documents of its entity. Money out
    pays bills. Money in pays invoices. A draft or void document does not count.

    First the payment pays the document with the reference as its number. The
    match must be exact. Then the rest pays the oldest open documents first:
    always for bills, and for invoices only when the company has the setting
    "Allocate unreferenced to oldest invoices". An amount that is left over
    stays unallocated (see post_cash_entry: it goes to Suspense).
    A direct payment (see is_direct) pays no document.

    A reference that is the number of a claim pays that claim only: all or
    a part of its open amount (see _claim_of). The payment goes to the claim
    account. The claim is Paid or Partially paid when the journal posts the
    entry of the payment (see update_claims).
    Returns the documents that the payment pays.
    """
    claim = _claim_of(payment)
    if claim:
        payment.account = claim.claim.control_account
        payment.save(update_fields=["account"])
        PaymentAllocation.objects.create(payment=payment, document=claim, amount=payment.amount)
        return [claim]
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


def asset_account(item):
    """The asset account of a tracked item: the account on the item, else "Inventory"."""
    return item.account or _account(item.company, INVENTORY)


def tracked_lines(document):
    """The lines of the document that have a tracked item with a quantity on hand (a
    stock, consumable or component item). An asset item is one unit: a bill or an
    invoice does not move its stock."""
    return [line for line in document.lines.select_related("item__model", "item__account")
            if line.item and line.item.tracked and line.item.is_stocked]


def _takes(item, quantity):
    """Split an issue of the quantity over the tracked items of the group of the item (see
    Item.group): the oldest item with stock first. The item takes what stays. Thus the
    stock of one item does not go below zero while another item of the group has stock.
    Returns [(item, quantity)]."""
    group = list(item.group().filter(tracked=True).order_by("pk"))
    levels = stock_levels(item.company, item__in=group)
    takes = []
    for member in group:
        part = min(quantity, max(levels.get(member.pk, (Decimal(0),))[0], Decimal(0)))
        if part > 0:
            takes.append((member, part))
            quantity -= part
    if quantity > 0:
        takes.append((item, quantity))
    return takes


def _move(document, item, direction, quantity, unit_cost):
    total = (quantity * unit_cost).quantize(CENT, ROUND_HALF_UP)
    StockMovement.objects.create(company=document.company, item=item, date=document.date, direction=direction,
                                 quantity=quantity, unit_cost=unit_cost, total_cost=total, document=document)
    return total


def move_stock(document, direction):
    """Write the stock movements of the tracked lines of a bill (IN) or an invoice (OUT).
    The same document again replaces its movements, thus a changed invoice moves the
    stock one time only. A bill moves the stock into the item of the line, at the price
    of the line. An invoice takes it from the items of the group (see _takes), at the
    cost of each item. Returns [(line, total cost)]."""
    StockMovement.objects.filter(document=document).delete()
    moved = []
    for line in tracked_lines(document):
        if direction == StockMovement.Direction.IN:
            total = _move(document, line.item, direction, line.quantity, line.unit_price)
        else:
            total = sum((_move(document, item, direction, quantity, item.unit_cost or Decimal(0))
                         for item, quantity in _takes(line.item, line.quantity)), Decimal(0))
        moved.append((line, total))
    return moved


def post_opening_stock(item, quantity=1):
    """The opening stock of a new item. A stocked item (see Item.is_stocked) gets a stock
    movement IN of the quantity, at its unit cost, because the goods are there. A tracked
    item with a cost also gets a draft entry: Dr its asset account / Cr Opening Balance
    Equity, for the cost of the quantity. The entry waits on the Journal Entries page:
    Accept posts it, Void stops it. Links the entry to the item. Returns the entry, or None."""
    cost = item.unit_cost or Decimal(0)
    today = timezone.localdate()
    entry = None
    with transaction.atomic():
        if item.is_stocked:
            StockMovement.objects.create(company=item.company, item=item, date=today, quantity=quantity,
                                         direction=StockMovement.Direction.IN, unit_cost=cost,
                                         total_cost=(cost * quantity).quantize(CENT, ROUND_HALF_UP))
        if item.tracked and cost:
            reference = (item.sku or item.tag or f"ITEM-{item.pk}")[:255]
            entry = post_opening_balance(item.company, asset_account(item), cost * quantity, today, reference,
                                         f"Opening stock · {item.name}", basis=JournalEntry.Basis.ACCRUAL,
                                         status=JournalEntry.Status.DRAFT)
            item.opening_entry = entry
            item.save(update_fields=["opening_entry"])
    return entry


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

    A line with a tracked stock item sells stock: the stock goes out (see move_stock)
    and the entry gets Dr Cost of Sales / Cr the asset account of the item, at the cost
    of the item. Thus the gross profit of the sale is in the ledger.
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
        # The cost of the stock that the invoice sells. The two sides balance each other.
        cost_parts = []
        for line, cost in move_stock(invoice, StockMovement.Direction.OUT):
            cost_parts += [(_account(company, COST_OF_SALES), cost), (asset_account(line.item), -cost)]
        _add_rolled_up(entry, cost_parts)
    return entry


def post_bill(bill):
    """Approve a draft bill: write its ACCRUAL entry and post it.

    Dr the account of each line (net) and the input tax account (tax),
    Cr Accounts Payable (gross). The payable line keeps the supplier,
    thus the statement of the supplier finds it. On the cash basis the
    bill shows when it is paid (see post_cash_entry).

    A line with a tracked stock item buys stock: the line debits the
    asset account of the item (see inventory.documents, which sets the
    account of the line), and the stock comes in (see move_stock).
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
        move_stock(bill, StockMovement.Direction.IN)
    return entry


def post_claim(document):
    """Approve a draft claim (a Document with the Claim type): write its ACCRUAL entry and post it.
        Expense, creditor: Dr the account of each line / Cr the claim account (the total)
        Insurance:         Dr the claim account (the total) / Cr the account of each line
    The claim line keeps the entity of the document (the employee, the creditor or the insurer).
    On the cash basis the claim shows when it is paid (see allocate)."""
    claim = document.claim
    sign = -1 if claim.money_in else 1
    with transaction.atomic():
        entry = JournalEntry.objects.create(
            company=document.company, date=document.date, period=_open_period(document.company, document.date),
            entry_type=JournalEntry.EntryType.GENERAL if claim.money_in else JournalEntry.EntryType.PURCHASES,
            basis=JournalEntry.Basis.ACCRUAL, status=JournalEntry.Status.POSTED, posted_at=timezone.now(),
            reference=document.number, narration=f"{claim.get_kind_display()} · {claim.employee}"[:255],
        )
        total = _add_rolled_up(entry, [(line.account, sign * line.net_amount)
                                       for line in document.lines.select_related("account")])
        _add(entry, claim.control_account, -total, entity=document.entity)
        document.journal_entry = entry
        document.status = Document.Status.APPROVED
        document.save(update_fields=["journal_entry", "status", "updated_at"])
    return entry


def update_claims(company):
    """Run after the journal posts or voids entries. When the ACCRUAL entry of a claim payment
    is void, the payment pays nothing: its CASH entry becomes void too, and its allocation goes.
    Then the posted payments set the status of the claim: Paid (all the claim), Partially paid,
    or Approved (no posted payment)."""
    S = JournalEntry.Status
    claims = (Document.objects
              .filter(company=company, doc_type=Document.DocType.CLAIM,
                      status__in=[Document.Status.APPROVED, Document.Status.PART_PAID])
              .prefetch_related("lines__tax_code", "allocations__payment__journal_entry"))
    for document in claims:
        posted = Decimal(0)
        for allocation in document.allocations.all():
            payment = allocation.payment
            if payment.journal_entry.status == S.VOID:
                JournalEntry.objects.filter(pk=payment.cash_entry_id, status=S.DRAFT).update(status=S.VOID)
                allocation.delete()
            elif payment.journal_entry.status == S.POSTED:
                posted += allocation.amount
        status = (Document.Status.PAID if posted >= document.gross
                  else Document.Status.PART_PAID if posted else Document.Status.APPROVED)
        if status != document.status:
            Document.objects.filter(pk=document.pk).update(status=status)


def post_opening_balance(company, account, amount, date, reference, narration, entity=None,
                         basis=JournalEntry.Basis.BOTH, status=JournalEntry.Status.POSTED):
    """Write the entry of an opening balance: posted, or a draft with status DRAFT. A
    positive amount is a debit on the account. The other side goes to Opening Balance
    Equity. Returns the entry."""
    opening = _account(company, OPENING)
    period = _open_period(company, date)
    posted = status == JournalEntry.Status.POSTED
    with transaction.atomic():
        entry = JournalEntry.objects.create(
            company=company, date=date, period=period, entry_type=JournalEntry.EntryType.GENERAL, basis=basis,
            status=status, posted_at=timezone.now() if posted else None, reference=reference, narration=narration,
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
    ids.update(Item.objects.filter(company=company).values_list("opening_entry_id", flat=True))
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
