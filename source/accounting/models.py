from django.db import models


class DataSources(models.Model):
    source      = models.CharField(max_length=255)  # e.g Receipts, Bank Statements, Emails, Handwritten note etc
    filepath    = models.CharField()                # Stores  the filepath of the scanned/OCR'd document
    deteled     = models.BooleanField(default=False)

class GeneralJournal(models.Model):

    class TransactionType(models.TextChoices):
        SALES               = 'S','Sales'
        PURCHASES           = 'P','Purchases'
        CASH_RECEIVABLES    = 'CR','Receivables'
        CASH_PAYMENTS       = 'CP', 'Payments'
        GENERAL             = 'G','General'

    date                = models.DateField()
    debit_amount        = models.DecimalField(max_digits=13,decimal_places=2)
    credit_amount       = models.DecimalField(max_digits=13,decimal_places=2)
    vat_amount          = models.DecimalField(max_digits=12,decimal_places=2)
    transaction_type    = models.CharField(choices=TransactionType.choices, default=TransactionType.GENERAL)
    reference           = models.CharField(max_length=255)
    source              = models.ForeignKey(DataSources, on_delete=models.CASCADE)
    # TODO: finish this

class SalesJournal(models.Model):
    date                = models.DateField()
    debit_amount        = models.DecimalField(max_digits=13,decimal_places=2)
    credit_amount       = models.DecimalField(max_digits=13,decimal_places=2)
    reference           = models.CharField(max_length=255)
    # etc

class PurchasesJournal(models.Model):
    date                = models.DateField()
    debit_amount        = models.DecimalField(max_digits=13,decimal_places=2)
    credit_amount       = models.DecimalField(max_digits=13,decimal_places=2)
    reference           = models.CharField(max_length=255)
    # etc

class CashJournal(models.Model):
    date                = models.DateField()
    debit_amount        = models.DecimalField(max_digits=13,decimal_places=2)
    credit_amount       = models.DecimalField(max_digits=13,decimal_places=2)
    reference           = models.CharField(max_length=255)
    # etc

class Customer(models.Model):
    first_name = models.CharField(max_length=50)
    last_name  = models.CharField(max_length=50)
    # TODO: finish this

class Quote(models.Model):
    number   = models.CharField(max_length=50, unique=True)
    date     = models.DateField()
    expires  = models.DateField()
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="quotes")
    net      = models.DecimalField(max_digits=12, decimal_places=2)
    tax      = models.DecimalField(max_digits=12, decimal_places=2)
    gross    = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    # TODO: verify this with: quote.lines.select_related("product")

class Invoice(models.Model):
    number   = models.CharField(max_length=50, unique=True)
    date     = models.DateField()
    due      = models.DateField()
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="invoices")
    quote    = models.ForeignKey(Quote, on_delete=models.SET_NULL, null=True, blank=True,related_name="invoices")
    net      = models.DecimalField(max_digits=12, decimal_places=2)
    tax      = models.DecimalField(max_digits=12, decimal_places=2)
    gross    = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    # TODO: verify this with: invoice.lines.select_related("product")

class LineItem(models.Model):
    product         = models.CharField()                                    # TODO: use Product as a foreign key
    unit_price      = models.DecimalField(max_digits=13,decimal_places=2)
    quantity        = models.DecimalField(max_digits=12,decimal_places=2)   # Fractional quantities are allowed in order to support time tracking billing etc
    total_price     = models.DecimalField(max_digits=12,decimal_places=2)

    class Meta:
        abstract = True

class QuoteLine(LineItem):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="lines")

class InvoiceLine(LineItem):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")