from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from shared.models import *
from inventory.models import Item
from django.conf import settings

class FiscalYear(CompanyOwned):
    name        = models.CharField(max_length=50)
    start_date  = models.DateField()
    end_date    = models.DateField()
    is_closed   = models.BooleanField(default=False)

    class Meta:
        unique_together = [("company","name")]

class Period(CompanyOwned):
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT, related_name="periods")
    name        = models.CharField(max_length=50)
    start_date  = models.DateField()
    end_date    = models.DateField()
    is_closed   = models.BooleanField(default=False)

    class Meta:
        unique_together = [("company", "name")]
        ordering = ["start_date"]

class NumberSequence(CompanyOwned):
    name        = models.CharField(max_length=50)
    prefix      = models.CharField(max_length=10, blank=True)
    next_number = models.PositiveIntegerField(default=1)
    padding     = models.PositiveSmallIntegerField(default=5)

    class Meta:
        unique_together = [("company", "name")]

    @classmethod
    def take(cls, company, name):
        with transaction.atomic():
            seq             = cls.objects.select_for_update().get(company=company, name=name)
            number          = seq.next_number
            seq.next_number += 1

            seq.save(update_fields=["next_number"])

        return f"{seq.prefix}{str(number).zfill(seq.padding)}"

class Attachment(CompanyOwned):
    content_type    = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id       = models.PositiveIntegerField()
    content_object  = GenericForeignKey("content_type", "object_id")
    source          = models.CharField(max_length=255)  # e.g Receipts, Bank Statements, Emails, Handwritten note etc
    file            = models.FileField(upload_to="attachments/%Y/%m/")
    filename        = models.CharField(max_length=255)
    uploaded_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["content_type", "object_id"])]

class CostCentre(CompanyOwned):
    code      = models.CharField(max_length=20,null=False)
    name      = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("company", "code")]

class TaxCode(CompanyOwned):

    class Kind(models.TextChoices):
        STANDARD        = "STD", "Standard rated"
        REDUCED         = "RED", "Reduced rated"
        ZERO            = "ZER", "Zero rated"
        EXEMPT          = "EXE", "Exempt"
        REVERSE_CHARGE  = "RCH", "Reverse charge"
        OUT_OF_SCOPE    = "OOS", "Out of scope"

    code            = models.CharField(max_length=20)
    name            = models.CharField(max_length=255)
    kind            = models.CharField(max_length=3, choices=Kind.choices, default=Kind.STANDARD)
    rate            = models.DecimalField(max_digits=5, decimal_places=2)
    valid_from      = models.DateField()
    valid_to        = models.DateField(null=True, blank=True)
    input_account   = models.ForeignKey("Account", on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    output_account  = models.ForeignKey("Account", on_delete=models.PROTECT, null=True, blank=True, related_name="+")

    class Meta:
        unique_together = [("company", "code", "valid_from")]

class Account(CompanyOwned):
    class AccountType(models.TextChoices):
        SALES                   = "SALES", "Sales"
        COST_OF_SALES           = "COS", "Cost of Sales"
        OTHER_INCOME            = "OTHINC", "Other Income"
        EXPENSES                = "EXP", "Expenses"
        INCOME_TAX              = "TAX", "Income Tax"
        NON_CURRENT_ASSETS      = "NCA", "Non-Current Assets"
        CURRENT_ASSETS          = "CA", "Current Assets"
        NON_CURRENT_LIABILITIES = "NCL", "Non-Current Liabilities"
        CURRENT_LIABILITIES     = "CL", "Current Liabilities"
        SHAREHOLDER_EQUITY      = "EQ", "Equity"
        FLOATING_NOMINAL        = "FN", "Floating Nominal"

    class Side(models.TextChoices):
        DEBIT  = "D", "Debit"
        CREDIT = "C", "Credit"

    code        = models.CharField(max_length=10)
    name        = models.CharField(max_length=255)
    type        = models.CharField(max_length=10, choices=AccountType.choices)
    normal_side = models.CharField(max_length=1, choices=Side.choices)
    parent      = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="children")
    currency    = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    is_active   = models.BooleanField(default=True)
    description = models.TextField(max_length=500, null=True, blank=True)

    class Meta:
        unique_together = [("company", "code"), ("company", "name")]
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"

class JournalEntry(CompanyOwned, TimeStamped):
    class Status(models.TextChoices):
        DRAFT  = "D", "Draft"
        POSTED = "P", "Posted"
        VOID   = "V", "Void"

    class EntryType(models.TextChoices):
        SALES     = "S", "Sales"
        PURCHASES = "P", "Purchases"
        RECEIPT   = "CR", "Receipts"
        PAYMENT   = "CP", "Payments"
        GENERAL   = "G", "General"

    date       = models.DateField()
    period     = models.ForeignKey(Period, on_delete=models.PROTECT, related_name="entries")
    entry_type = models.CharField(max_length=2, choices=EntryType.choices, default=EntryType.GENERAL)
    status     = models.CharField(max_length=1, choices=Status.choices, default=Status.DRAFT)
    reference  = models.CharField(max_length=255)
    narration  = models.TextField(blank=True)
    source     = models.ForeignKey(Attachment, on_delete=models.PROTECT, null=True, blank=True, related_name="entries")
    reverses   = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="reversed_by")
    posted_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "journal entries"
        indexes = [
            models.Index(fields=["company", "date"]),
            models.Index(fields=["company", "status", "date"]),
        ]

    @property
    def is_balanced(self):
        totals = self.lines.aggregate(d=models.Sum("base_debit"), c=models.Sum("base_credit"))
        return (totals["d"] or 0) == (totals["c"] or 0)

class JournalLine(models.Model):
    entry       = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account     = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="lines")
    description = models.CharField(max_length=255, blank=True)

    currency      = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="+")
    exchange_rate = models.DecimalField(max_digits=18, decimal_places=8, default=1)
    debit         = models.DecimalField(max_digits=13, decimal_places=2, default=0)
    credit        = models.DecimalField(max_digits=13, decimal_places=2, default=0)
    base_debit    = models.DecimalField(max_digits=13, decimal_places=2, default=0)
    base_credit   = models.DecimalField(max_digits=13, decimal_places=2, default=0)

    tax_code    = models.ForeignKey(TaxCode, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    entity      = models.ForeignKey(Entity, on_delete=models.PROTECT, null=True, blank=True, related_name="journal_lines")
    cost_centre = models.ForeignKey(CostCentre, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    project     = models.ForeignKey(Project, on_delete=models.PROTECT, null=True, blank=True, related_name="+")

    class Meta:
        indexes = [models.Index(fields=["account", "entry"])]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(debit__gt=0, credit=0) |
                    models.Q(credit__gt=0, debit=0)
                ),
                name="journalline_one_side_only",
            ),
        ]

# Billable item not based on any physical goods (e.g consulting, installation etc)
class Service(CompanyOwned):
    code    = models.CharField(max_length=100)
    name    = models.CharField(max_length=255)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True, related_name="+")

    class Meta:
        unique_together = [("company", "code")]

class Document(CompanyOwned, TimeStamped):
    """
    Unified model for quotes, invoices, bills, and credit notes.
    Direction indicates sale or purchase.
    DocType differentiates the exact document type.
    """

    class Direction(models.TextChoices):
        SALE     = "S", "Sale"
        PURCHASE = "P", "Purchase"

    class DocType(models.TextChoices):
        QUOTE       = "Q", "Quote"
        INVOICE     = "I", "Invoice"
        BILL        = "B", "Bill"
        CREDIT_NOTE = "C", "Credit note"

    class Status(models.TextChoices):
        DRAFT     = "D", "Draft"
        SENT      = "S", "Sent"
        APPROVED  = "A", "Approved"  
        PART_PAID = "PP", "Partially paid"
        PAID      = "P", "Paid"
        VOID      = "V", "Void"

    direction       = models.CharField(max_length=1, choices=Direction.choices)
    doc_type        = models.CharField(max_length=1, choices=DocType.choices)
    number          = models.CharField(max_length=50)
    date            = models.DateField()
    due             = models.DateField(null=True, blank=True)
    entity          = models.ForeignKey(Entity, on_delete=models.PROTECT, related_name="documents")
    status          = models.CharField(max_length=2, choices=Status.choices, default=Status.DRAFT)
    currency        = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="+")
    exchange_rate   = models.DecimalField(max_digits=18, decimal_places=8, default=1)
    notes           = models.TextField(blank=True)
    source_doc      = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="related_docs")
    journal_entry   = models.OneToOneField(JournalEntry, on_delete=models.PROTECT, null=True, blank=True, related_name="document")

    class Meta:
        unique_together = [("company", "direction", "doc_type", "number")]
        indexes = [
            models.Index(fields=["company", "direction", "doc_type", "status"]),
            models.Index(fields=["company", "entity", "status"]),
        ]

    # Derived properties – no stored totals.
    @property
    def net(self):
        return sum(line.net_amount for line in self.lines.all())

    @property
    def tax(self):
        return sum(line.tax_amount for line in self.lines.all())

    @property
    def gross(self):
        return self.net + self.tax

    @property
    def is_sale(self):
        return self.direction == self.Direction.SALE

    @property
    def is_purchase(self):
        return self.direction == self.Direction.PURCHASE

class DocumentLine(models.Model):
    """
    A line on any document. Points at an inventory item, a service, or neither.
    Company is inherited from the parent Document.
    """

    document   = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="lines")
    item       = models.ForeignKey(Item, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    service    = models.ForeignKey(Service, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    account    = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="+")
    tax_code   = models.ForeignKey(TaxCode, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    cost_centre = models.ForeignKey(CostCentre, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    project    = models.ForeignKey(Project, on_delete=models.PROTECT, null=True, blank=True, related_name="+")

    description = models.CharField(max_length=255)
    quantity    = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price  = models.DecimalField(max_digits=13, decimal_places=2)
    discount    = models.DecimalField(max_digits=5, decimal_places=2, default=0)   # percent
    sort_order  = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(item__isnull=False, service__isnull=False),
                name="documentline_not_item_and_service",
            ),
        ]

    # Derived fields – no stored totals.
    @property
    def line_total_before_discount(self):
        return self.quantity * self.unit_price

    @property
    def discount_amount(self):
        return self.line_total_before_discount * (self.discount / 100)

    @property
    def net_amount(self):
        return self.line_total_before_discount - self.discount_amount

    @property
    def tax_amount(self):
        if self.tax_code:
            # Obtain the effective tax rate for the document date (simplified: use latest rate)
            # In practice, service layer would determine exact rate.
            return self.net_amount * (self.tax_code.rate / 100)
        return 0

    @property
    def total_price(self):
        return self.net_amount + self.tax_amount

class BankAccount(CompanyOwned):
    name           = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50, blank=True)
    sort_code      = models.CharField(max_length=20, blank=True)
    iban           = models.CharField(max_length=34, blank=True)
    currency       = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="+")
    account        = models.OneToOneField(Account, on_delete=models.PROTECT, related_name="bank_account")
    is_active      = models.BooleanField(default=True)

class Payment(CompanyOwned, TimeStamped):
    class Direction(models.TextChoices):
        IN  = "IN", "Received"
        OUT = "OUT", "Paid"

    number        = models.CharField(max_length=50)
    date          = models.DateField()
    direction     = models.CharField(max_length=3, choices=Direction.choices)
    entity        = models.ForeignKey(Entity, on_delete=models.PROTECT, related_name="payments")
    bank_account  = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name="payments")
    currency      = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="+")
    exchange_rate = models.DecimalField(max_digits=18, decimal_places=8, default=1)
    amount        = models.DecimalField(max_digits=13, decimal_places=2)
    reference     = models.CharField(max_length=255, blank=True)
    journal_entry = models.OneToOneField(JournalEntry, on_delete=models.PROTECT, null=True, blank=True, related_name="payment")

    class Meta:
        unique_together = [("company", "number")]

class PaymentAllocation(models.Model):
    payment  = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="allocations")
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="allocations")
    amount   = models.DecimalField(max_digits=13, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(document__isnull=False),
                name="paymentallocation_document_required",
            ),
        ]


class BankTransaction(CompanyOwned):
    bank_account  = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name="transactions")
    date          = models.DateField()
    description   = models.CharField(max_length=255)
    amount        = models.DecimalField(max_digits=13, decimal_places=2)
    external_id   = models.CharField(max_length=100, blank=True)
    reconciled    = models.BooleanField(default=False)
    payment       = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name="bank_lines")
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="bank_lines")
    source        = models.ForeignKey(Attachment, on_delete=models.PROTECT, null=True, blank=True, related_name="bank_lines")

    class Meta:
        unique_together = [("bank_account", "external_id")]
        indexes = [models.Index(fields=["bank_account", "date"])]

class FixedAsset(CompanyOwned, TimeStamped):
    class Method(models.TextChoices):
        STRAIGHT_LINE = "SL", "Straight line"
        REDUCING      = "RB", "Reducing balance"

    code                = models.CharField(max_length=50)
    name                = models.CharField(max_length=255)
    purchase_date       = models.DateField()
    cost                = models.DecimalField(max_digits=13, decimal_places=2)
    residual_value      = models.DecimalField(max_digits=13, decimal_places=2, default=0)
    useful_life_months  = models.PositiveSmallIntegerField()
    method              = models.CharField(max_length=2, choices=Method.choices, default=Method.STRAIGHT_LINE)
    asset_account       = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="+")
    accumulated_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="+")
    expense_account     = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="+")
    disposal_date       = models.DateField(null=True, blank=True)
    disposal_amount     = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = [("company", "code")]


class DepreciationSchedule(models.Model):
    asset         = models.ForeignKey(FixedAsset, on_delete=models.CASCADE, related_name="schedule")
    period        = models.ForeignKey(Period, on_delete=models.PROTECT, related_name="+")
    amount        = models.DecimalField(max_digits=13, decimal_places=2)
    posted        = models.BooleanField(default=False)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        unique_together = [("asset", "period")]


class StockMovement(CompanyOwned):
    class Method(models.TextChoices):
        FIFO    = "FIFO", "First in, first out"
        AVERAGE = "AVG", "Weighted average"

    class Direction(models.TextChoices):
        IN         = "IN", "In"
        OUT        = "OUT", "Out"
        ADJUSTMENT = "ADJ", "Adjustment"

    item          = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="movements")
    date          = models.DateField()
    direction     = models.CharField(max_length=3, choices=Direction.choices)
    quantity      = models.DecimalField(max_digits=12, decimal_places=4)
    unit_cost     = models.DecimalField(max_digits=13, decimal_places=4)
    total_cost    = models.DecimalField(max_digits=13, decimal_places=2)
    method        = models.CharField(max_length=4, choices=Method.choices, default=Method.AVERAGE)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        indexes = [models.Index(fields=["company", "item", "date"])]


class Budget(CompanyOwned):
    name        = models.CharField(max_length=255)
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name="budgets")
    is_active   = models.BooleanField(default=True)

    class Meta:
        unique_together = [("company", "name", "fiscal_year")]


class BudgetLine(models.Model):
    budget      = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name="lines")
    account     = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="+")
    period      = models.ForeignKey(Period, on_delete=models.PROTECT, related_name="+")
    cost_centre = models.ForeignKey(CostCentre, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    amount      = models.DecimalField(max_digits=13, decimal_places=2)

    class Meta:
        unique_together = [("budget", "account", "period", "cost_centre")]


class RecurringInvoice(CompanyOwned, TimeStamped):
    class Frequency(models.TextChoices):
        WEEKLY    = "W", "Weekly"
        MONTHLY   = "M", "Monthly"
        QUARTERLY = "Q", "Quarterly"
        YEARLY    = "Y", "Yearly"

    name      = models.CharField(max_length=255)
    customer  = models.ForeignKey(Entity, on_delete=models.PROTECT, related_name="recurring_invoices")
    template  = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="+")  # must be an invoice
    frequency = models.CharField(max_length=1, choices=Frequency.choices)
    next_run  = models.DateField()
    end_date  = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)


class AuditLog(CompanyOwned):
    class Action(models.TextChoices):
        CREATE = "C", "Create"
        UPDATE = "U", "Update"
        DELETE = "D", "Delete"
        POST   = "P", "Post"
        VOID   = "V", "Void"

    content_type   = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id      = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    action    = models.CharField(max_length=1, choices=Action.choices)
    user      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    timestamp = models.DateTimeField(auto_now_add=True)
    changes   = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=["content_type", "object_id", "-timestamp"])]
        ordering = ["-timestamp"]