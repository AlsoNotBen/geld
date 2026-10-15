"""
accounting/documents.py
------------------------------------------------------------------------
The document types of the Accounting module. The documents app finds
this file at start and imports it (see documents/apps.py).

The module has no models yet. Thus the customers and the item catalog
below are sample data. Replace them with queries when the models
exist:

    - SAMPLE_CUSTOMERS becomes the customers table. Build the choices
      of the customer field from it, and read the address in
      _customer().
    - CATALOG becomes the products or services table. It fills the
      "Add from the catalog" select of the line item editor.
    - SAMPLE_ACTIVITY is the account of a sample customer in the
      statement. A real customer gets the posted lines of its
      receivable account (see _ledger).
"""

import calendar
import datetime
from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.db import transaction
from documents.forms import (DocumentOptionsForm, LineItemsField, SelectWithAddButton)
from documents.registry import DocumentType, register
from accounting.models import Account, AuditLog, Document, DocumentLine, JournalEntry, JournalLine, NumberSequence, TaxCode
from accounting.posting import RECEIVABLE, post_invoice_entry


CENT = Decimal("0.01")
ZERO = Decimal("0")

#TODO: Intelligently choose the samples used to pre-populate documents to the most likely option (based on recency/frequency or something)
SAMPLE_CUSTOMERS = {
    "aster": {
        "name": "Aster Botanicals (Pty) Ltd",
        "details": "48 Protea Road\n7700 Rondebosch",
        "email": "accounts@aster.example",
        "vat_number": "4870 215 963",
        "registration_number": "2014/087321/07",
    },
    "meridian": {
        "name": "Meridian Freight CC",
        "details": "Unit 9, Harbour Park\n4001 Durban",
        "email": "finance@meridian.example",
        "vat_number": "4310 662 487",
        "registration_number": "2003/041872/23",
    },
    "kloof": {
        "name": "Kloof & Daughters Attorneys",
        "details": "221 Long Street\n8001 Cape Town",
        "email": "billing@kloof.example",
        "vat_number": "4590 118 274",
    },
}

# The account activity of a sample customer, for the statement preview.
# Each row: days ago, reference, description, debit, credit, days to pay.
SAMPLE_ACTIVITY = [
    (100, "INV-00012", "Invoice",          "8500.00", "0",       30),
    (75,  "PAY-00007", "Payment received", "0",       "5000.00", 0),
    (58,  "INV-00019", "Invoice",          "4200.00", "0",       30),
    (20,  "PAY-00011", "Payment received", "0",       "2000.00", 0),
    (15,  "INV-00027", "Invoice",          "6900.00", "0",       30),
    (8,   "CRN-00003", "Credit note",      "0",       "450.00",  0),
    (4,   "INV-00031", "Invoice",          "2300.00", "0",       30),
]

AGEING_LABELS = ["Current", "1–30 days", "31–60 days", "61–90 days", "90+ days"]

CATALOG = [
    {"description": "CRM implementation — discovery workshop",
     "unit": "day", "unit_price": "640.00"},
    {"description": "Data migration from the legacy system",
     "unit": "fixed", "unit_price": "1450.00"},
    {"description": "User training, remote",
     "unit": "session", "unit_price": "380.00"},
    {"description": "Support retainer — first month",
     "unit": "month", "unit_price": "290.00"},
    {"description": "Custom report pack",
     "unit": "fixed", "unit_price": "520.00"},
]

INITIAL_LINES = [
    {**CATALOG[0], "quantity": "2"},
    {**CATALOG[1], "quantity": "1"},
    {**CATALOG[2], "quantity": "3"},
]


def _customers():
    """The entities of the leads. The key of each is its pk."""
    from accounting.models import Entity
    return Entity.objects.filter(leads__isnull=False).distinct()


def _customer_choices():
    samples = [(key, value["name"]) for key, value in SAMPLE_CUSTOMERS.items()]
    return samples + [(str(e.pk), e.name) for e in _customers()]


def _customer(options):
    """Return the customer record for the selected choice.

    The statement also reads the email, the entity, and the VAT and
    registration numbers. An organization only has these two numbers.
    """
    key = options["customer"]
    if key.isdigit():
        entity = _customers().select_related("organization_profile").filter(pk=key).first()
        if entity:
            org = getattr(entity, "organization_profile", None) if entity.type == entity.EntityType.ORGANIZATION else None
            return {"name": entity.name, "details": entity.address, "email": entity.email, "entity": entity,
                    "vat_number": org and org.tax_number, "registration_number": org and org.registration_number}
    return SAMPLE_CUSTOMERS.get(key, {"name": key, "details": ""})


def _in_days(days):
    """Return a function that gives today plus the number of days.

    A form evaluates a callable initial value on each render. Thus the
    date stays fresh while the server runs.
    """
    return lambda: datetime.date.today() + datetime.timedelta(days=days)


def _month_ago():
    """Return the same day one month ago. A shorter month clips the day."""
    today = datetime.date.today()
    year, month = divmod(today.year * 12 + today.month - 2, 12)
    month += 1
    return datetime.date(year, month, min(today.day, calendar.monthrange(year, month)[1]))


def _date_field(label, days_ahead=0):
    return forms.DateField(label=label,initial=_in_days(days_ahead),widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))


def _build_lines(lines, tax_rate, discount_rate=Decimal("0")):
    """Compute the line totals and the sums.

    The argument "lines" comes from LineItemsField.clean: each row has
    a Decimal quantity and a Decimal unit price.
    """
    computed = []
    subtotal = Decimal("0")

    for line in lines:
        total       = (line["quantity"] * line["unit_price"]).quantize(CENT, ROUND_HALF_UP)
        subtotal    += total
        computed.append({**line, "total": total})

    discount    = (subtotal * discount_rate / 100).quantize(CENT, ROUND_HALF_UP)
    taxable     = subtotal - discount
    tax         = (taxable * tax_rate / 100).quantize(CENT, ROUND_HALF_UP)
    
    return {
        "lines": computed,
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "total": taxable + tax,
    }


class SalesDocumentOptionsForm(DocumentOptionsForm):
    """Options that the invoice and the quote share. The quote is in sales/documents.py."""

    muted_field_names = (
        "number", "issue_date", "due_date", "valid_until",
        "currency", "tax_rate", "payment_details",
    )

    customer = forms.ChoiceField(
        label="Customer",
        choices=_customer_choices,
        initial="aster",
        widget=SelectWithAddButton(
            action="new-customer", button_label="Add a new customer",
            search_action="search-customer", search_label="Search the customers",
        ),
    )
    line_items = LineItemsField(
        label="Line items",
        catalog=CATALOG,
        initial=INITIAL_LINES,
    )
    currency = forms.CharField(
        label="Currency symbol",
        initial="R",
        max_length=4,
    )
    tax_rate = forms.DecimalField(
        label="Tax rate (%)",
        initial=Decimal("15"),
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        decimal_places=2,
    )
    notes = forms.CharField(
        label="Notes",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class InvoiceOptionsForm(SalesDocumentOptionsForm):
    field_order = [
        "pro_forma", "recurring", "number", "issue_date", "due_date", "customer", "line_items",
        "currency", "tax_rate", "payment_details", "notes",
    ]

    pro_forma = forms.BooleanField(label="Pro-Forma", required=False, initial=False)
    recurring = forms.BooleanField(label="Recurring Invoice", required=False, initial=False)
    number = forms.CharField(label="Invoice number")
    issue_date = _date_field("Issue Date")
    due_date = _date_field("Due Date", days_ahead=30)
    payment_details = forms.CharField(
        label="Payment Details",
        required=False,
        initial="First National Bank\nAccount 620 4471 9902\nBranch 250655\nReference: the invoice number",
        widget=forms.Textarea(attrs={"rows": 4}),
    )


class StatementOptionsForm(SalesDocumentOptionsForm):
    """The statement keeps the customer, currency and notes fields of the parent form."""

    line_items = None   # A None value removes the field of the parent form.
    tax_rate = None
    muted_field_names = ("number", "currency", "bank_details")
    field_order = [
        "number", "start_date", "end_date", "customer", "brought_forward",
        "interest_rate", "currency", "bank_details", "notes",
    ]

    number = forms.CharField(label="Statement number")
    start_date = forms.DateField(label="Period from", initial=_month_ago,
                                 widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    end_date = _date_field("Period to")
    brought_forward = forms.DecimalField(
        label="Balance brought forward",
        required=False,
        max_digits=13,
        decimal_places=2,
        help_text="Leave blank to calculate it from the records. A typed balance is overdue from the period start.",
        widget=forms.NumberInput(attrs={"placeholder": "Calculated", "step": "0.01"}),
    )
    interest_rate = forms.DecimalField(
        label="Interest on arrears (% per year)",
        initial=Decimal("0"),
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        decimal_places=2,
        help_text="Simple interest per day on each overdue amount. 0 gives no interest.",
    )
    bank_details = forms.CharField(
        label="Bank details",
        required=False,
        initial="First National Bank\nAccount 620 4471 9902\nBranch 250655\nReference: the statement number",
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    def clean(self):
        data = super().clean()
        if data.get("start_date") and data.get("end_date") and data["start_date"] > data["end_date"]:
            raise forms.ValidationError("The period must start on or before its end.")
        return data


class SalesDocument(DocumentType):
    """The invoice, the quote and the statement. The number comes from a NumberSequence with the name of the key."""
    module = "accounting"
    prefix = ""

    def get_options_form(self, data=None, request=None):
        form = super().get_options_form(data, request)
        if request:
            form.fields["number"].initial = NumberSequence.peek(request.company, self.key, self.prefix)
        return form

    def issue(self, request, options):
        # Take the number only when the document uses the next number. Thus a second download takes no number.
        if options["number"] == NumberSequence.peek(request.company, self.key, self.prefix):
            NumberSequence.take(request.company, self.key)

    def get_filename(self, options):
        return f"{options['number']}.pdf"


@register
class InvoiceDocument(SalesDocument):
    key = "invoice"
    prefix = "INV-"
    label = "New Invoice"
    description = "A tax invoice with line items, totals and payment details."
    template_name = "accounting/pdf/invoice.html"
    options_form_class = InvoiceOptionsForm

    def get_context(self, request, options):
        money = _build_lines(options["line_items"], options["tax_rate"])
        return {"options": options, "customer": _customer(options), **money}

    def issue(self, request, options):
        if options["pro_forma"]:
            return
        money = _build_lines(options["line_items"], options["tax_rate"])
        customer = _customer(options)
        entity = customer.get("entity")
        with transaction.atomic():
            super().issue(request, options)
            entry = post_invoice_entry(request.company, options["number"], options["issue_date"],
                                       money["total"], money["tax"], narration=customer["name"], entity=entity)
            if entry:
                document = _invoice_record(request.company, options, entity, entry) if entity else None
                AuditLog.record(request, AuditLog.Action.CREATE, document or entry)


def _invoice_record(company, options, entity, entry):
    """Keep an issued invoice as a Document, linked to its entry. The statement reads its due date.
    Returns the document."""
    sales = Account.objects.get(company=company, name="Sales")
    tax_code = (TaxCode.objects.filter(company=company, rate=options["tax_rate"], valid_from__lte=options["issue_date"])
                .order_by("-valid_from").first())
    document = Document.objects.create(
        company=company, direction=Document.Direction.SALE, doc_type=Document.DocType.INVOICE,
        number=options["number"], date=options["issue_date"], due=options["due_date"], entity=entity,
        status=Document.Status.SENT, currency=company.base_currency, notes=options["notes"], journal_entry=entry,
    )
    DocumentLine.objects.bulk_create(
        DocumentLine(document=document, account=sales, tax_code=tax_code, description=line["description"],
                     quantity=line["quantity"], unit_price=line["unit_price"], sort_order=index)
        for index, line in enumerate(options["line_items"])
    )
    return document


def _ledger(company, entity):
    """Return the rows of the customer account, oldest first.

    The rows are the posted lines of the Accounts Receivable account for
    the customer. Thus the statement agrees with the general ledger. A
    linked document or payment gives the description, and a document
    gives the due date. Without a document, the entry date is the due date.
    """
    lines = (JournalLine.objects
             .filter(entry__company=company, entry__status=JournalEntry.Status.POSTED,
                     account__company=company, account__name=RECEIVABLE, entity=entity)
             .exclude(entry__basis=JournalEntry.Basis.CASH)
             .select_related("entry__document", "entry__payment")
             .order_by("entry__date", "entry_id", "id"))
    rows = []
    for line in lines:
        entry = line.entry
        document = getattr(entry, "document", None)     # None when no record links to the entry
        payment = getattr(entry, "payment", None)
        row = {"date": entry.date, "due": entry.date, "reference": entry.reference,
               "description": line.description or entry.get_entry_type_display(),
               "debit": line.base_debit, "credit": line.base_credit}
        if document:
            row.update(reference=document.number, description=document.get_doc_type_display(),
                       due=document.due or entry.date)
        elif payment:
            row.update(reference=payment.number,
                       description=" — ".join(filter(None, ["Payment received", payment.reference])))
        elif entry.entry_type == JournalEntry.EntryType.SALES:
            row["description"] = "Invoice"
        rows.append(row)
    return rows


def _sample_ledger():
    """Return the rows of a sample customer. The dates move with today."""
    today = datetime.date.today()
    rows = []
    for days, reference, description, debit, credit, terms in SAMPLE_ACTIVITY:
        date = today - datetime.timedelta(days=days)
        rows.append({"date": date, "due": date + datetime.timedelta(days=terms), "reference": reference,
                     "description": description, "debit": Decimal(debit), "credit": Decimal(credit)})
    return rows


def _statement(ledger, options):
    """Compute the figures of the statement from the account rows.

    The payments and the credits settle the oldest charges first. Thus
    the newest charges make the closing balance. The ageing and the
    interest use the due date of each of these charges, at the end date.
    """
    start, end, rate = options["start_date"], options["end_date"], options["interest_rate"]
    ledger = [row for row in ledger if row["date"] <= end]
    rows = [row for row in ledger if row["date"] >= start]
    brought_forward = options["brought_forward"]

    if brought_forward is None:
        before = [row for row in ledger if row["date"] < start]
        brought_forward = sum((row["debit"] - row["credit"] for row in before), ZERO)
        charges = [row for row in before if row["debit"]]
    else:   # A typed balance replaces the charges before the period.
        day_before = start - datetime.timedelta(days=1)
        charges = [{"date": day_before, "due": day_before, "reference": "B/F",
                    "debit": brought_forward}] if brought_forward > 0 else []

    balance = brought_forward
    for row in rows:
        balance += row["debit"] - row["credit"]
        row["balance"] = balance

    ageing = [ZERO] * len(AGEING_LABELS)
    arrears = []
    remaining = balance
    for charge in reversed(charges + [row for row in rows if row["debit"]]):
        if remaining <= 0:
            break
        part = min(charge["debit"], remaining)
        remaining -= part
        days = (end - charge["due"]).days
        ageing[0 if days <= 0 else min((days - 1) // 30 + 1, 4)] += part
        if days > 0:
            arrears.insert(0, {**charge, "outstanding": part, "days": days,
                               "interest": (part * rate * days / 36500).quantize(CENT, ROUND_HALF_UP)})
    ageing[0] += remaining  # A credit balance shows as current.

    interest = sum((item["interest"] for item in arrears), ZERO)
    return {
        "brought_forward": brought_forward,
        "rows": rows,
        "total_debit": sum((row["debit"] for row in rows), ZERO),
        "total_credit": sum((row["credit"] for row in rows), ZERO),
        "closing": balance,
        "ageing": [{"label": label, "amount": amount} for label, amount in zip(AGEING_LABELS, ageing)],
        "arrears": arrears,
        "interest": interest,
        "total_due": balance + interest,
    }


@register
class StatementDocument(SalesDocument):
    key = "statement"
    prefix = "STM-"
    label = "Account Statement"
    description = "A statement of the customer account, with the ageing of the balance and the interest on arrears."
    template_name = "accounting/pdf/statement.html"
    options_form_class = StatementOptionsForm

    def get_context(self, request, options):
        customer = _customer(options)
        if customer.get("entity"):
            ledger = _ledger(request.company, customer["entity"])
        else:
            ledger = _sample_ledger() if options["customer"] in SAMPLE_CUSTOMERS else []
        return {"options": options, "customer": customer, **_statement(ledger, options)}
