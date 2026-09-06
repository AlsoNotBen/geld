from django.db import models
from shared.models import *
from inventory.models import Item

class DataSources(models.Model):
    source      = models.CharField(max_length=255)  # e.g Receipts, Bank Statements, Emails, Handwritten note etc
    filepath    = models.CharField()                # Stores  the filepath of the scanned/OCR'd document
    deteled     = models.BooleanField(default=False)

class VATBehaviour(models.Model):
    name = models.CharField(max_length=255)
    rate = models.DecimalField(max_digits=5,decimal_places=2)

# Billable Item not linked to any Inventory
class Service(models.Model):
    code        = models.CharField(max_length=100,unique=True)
    name        = models.CharField(max_length=255)

class Account(models.Model):

    class AccountType(models.TextChoices):
        SALES                   = 'Sales'
        COST_OF_SALES           = 'Cost of Sales'
        OTHER_INCOME            = 'Other Income'
        EXPENSES                = 'Expenses'
        INCOME_TAX              = 'Income Tax'
        NON_CURRENT_ASSETS      = 'Non-Current Assets'
        CURRENT_ASSETS          = 'Current Assets'
        NON_CURRENT_LIABILITIES = 'Non-Current Liabilities' 
        CURRENT_LIABILITIES     = 'Current Liabilities'
        SHAREHOLDER_EQUITY      = 'Equity'
        MISSING                 = 'Missing Field'

    name            = models.CharField(max_length=255,unique=True)
    type            = models.CharField(choices=AccountType.choices, default=AccountType.MISSING) 
    balance         = models.DecimalField(max_digits=13,decimal_places=2)
    vat_behvaiour   = models.ForeignKey(VATBehaviour,on_delete=models.PROTECT,related_name="vat")

class GeneralJournal(models.Model):

    class TransactionType(models.TextChoices):
        SALES               = 'S','Sales'
        PURCHASES           = 'P','Purchases'
        CASH_RECEIVABLES    = 'CR','Receivables'
        CASH_PAYMENTS       = 'CP', 'Payments'
        GENERAL             = 'G','General'

    date                = models.DateField()
    debit_amount        = models.DecimalField(max_digits=13,decimal_places=2)
    debit_account       = models.ForeignKey(Account,on_delete=models.PROTECT,related_name="debit_entries")
    credit_amount       = models.DecimalField(max_digits=13,decimal_places=2)
    credit_account      = models.ForeignKey(Account,on_delete=models.PROTECT,related_name="credit_entries")
    vat_amount          = models.DecimalField(max_digits=12,decimal_places=2)
    transaction_type    = models.CharField(choices=TransactionType.choices, default=TransactionType.GENERAL)
    reference           = models.CharField(max_length=255)
    source              = models.ForeignKey(DataSources, on_delete=models.CASCADE)

class Quote(models.Model):
    number   = models.CharField(max_length=50, unique=True)
    date     = models.DateField()
    expires  = models.DateField()
    customer = models.ForeignKey(Entity, on_delete=models.PROTECT, related_name="quotes")
    net      = models.DecimalField(max_digits=12, decimal_places=2)
    tax      = models.DecimalField(max_digits=12, decimal_places=2)
    gross    = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    # TODO: verify this with: quote.lines.select_related("product")

class Invoice(models.Model):
    number   = models.CharField(max_length=50, unique=True)
    date     = models.DateField()
    due      = models.DateField()
    customer = models.ForeignKey(Entity, on_delete=models.PROTECT, related_name="invoices")
    quote    = models.ForeignKey(Quote, on_delete=models.SET_NULL, null=True, blank=True,related_name="invoices")
    net      = models.DecimalField(max_digits=12, decimal_places=2)
    tax      = models.DecimalField(max_digits=12, decimal_places=2)
    gross    = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    # TODO: verify this with: invoice.lines.select_related("product")

class LineItem(models.Model):
    item            = models.ForeignKey("inventory.Item",on_delete=models.PROTECT,null=True,blank=True,related_name="+")
    service         = models.ForeignKey("accounting.Service",on_delete=models.PROTECT,null=True,blank=True,related_name="+")
    description     = models.CharField(max_length=255)
    unit_price      = models.DecimalField(max_digits=13,decimal_places=2)
    quantity        = models.DecimalField(max_digits=12,decimal_places=2)   # Fractional quantities are allowed in order to support time tracking billing etc
    total_price     = models.DecimalField(max_digits=12,decimal_places=2)

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(item__isnull=False, service__isnull=True) |
                    models.Q(item__isnull=True, service__isnull=False)
                ),
                name="%(app_label)s_%(class)s_exactly_one_source",
            ),
        ]

class QuoteLine(LineItem):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="lines")

class InvoiceLine(LineItem):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
