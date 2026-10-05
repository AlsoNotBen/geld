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
"""

import datetime
from decimal import Decimal, ROUND_HALF_UP
from django import forms
from documents.forms import (DocumentOptionsForm, LineItemsField, SelectWithAddButton)
from documents.registry import DocumentType, register


CENT = Decimal("0.01")

#TODO: Intelligently choose the samples used to pre-populate documents to the most likely option (based on recency/frequency or something)
SAMPLE_CUSTOMERS = {
    "aster": {
        "name": "Aster Botanicals (Pty) Ltd",
        "details": "48 Protea Road\n7700 Rondebosch",
    },
    "meridian": {
        "name": "Meridian Freight CC",
        "details": "Unit 9, Harbour Park\n4001 Durban",
    },
    "kloof": {
        "name": "Kloof & Daughters Attorneys",
        "details": "221 Long Street\n8001 Cape Town",
    },
}

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
    """Return the customer record for the selected choice."""
    key = options["customer"]
    if key.isdigit():
        entity = _customers().filter(pk=key).first()
        if entity:
            return {"name": entity.name, "details": entity.address}
    return SAMPLE_CUSTOMERS.get(key, {"name": key, "details": ""})


def _in_days(days):
    """Return a function that gives today plus the number of days.

    A form evaluates a callable initial value on each render. Thus the
    date stays fresh while the server runs.
    """
    return lambda: datetime.date.today() + datetime.timedelta(days=days)


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
    """Options that the invoice and the quote share."""

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
    number = forms.CharField(label="Invoice number", initial="INV-2026-0042")
    issue_date = _date_field("Issue Date")
    due_date = _date_field("Due Date", days_ahead=30)
    payment_details = forms.CharField(
        label="Payment Details",
        required=False,
        initial="First National Bank\nAccount 620 4471 9902\nBranch 250655\nReference: the invoice number",
        widget=forms.Textarea(attrs={"rows": 4}),
    )


class QuoteOptionsForm(SalesDocumentOptionsForm):
    field_order = [
        "number", "issue_date", "valid_until", "customer", "line_items",
        "currency", "tax_rate", "discount_rate", "notes",
    ]

    number = forms.CharField(label="Quote number", initial="QUO-2026-0017")
    issue_date = _date_field("Issue date")
    valid_until = _date_field("Valid until", days_ahead=14)
    discount_rate = forms.DecimalField(
        label="Discount (%)",
        initial=Decimal("0"),
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        decimal_places=2,
    )


@register
class InvoiceDocument(DocumentType):
    module = "accounting"
    key = "invoice"
    label = "New Invoice"
    description = "A tax invoice with line items, totals and payment details."
    template_name = "accounting/pdf/invoice.html"
    options_form_class = InvoiceOptionsForm

    def get_context(self, request, options):
        money = _build_lines(options["line_items"], options["tax_rate"])
        return {"options": options, "customer": _customer(options), **money}

    def get_filename(self, options):
        return f"{options['number']}.pdf"


@register
class QuoteDocument(DocumentType):
    module = "accounting"
    key = "quote"
    label = "New Quote"
    description = "A sales quote with line items, totals and an acceptance block."
    template_name = "accounting/pdf/quote.html"
    options_form_class = QuoteOptionsForm

    def get_context(self, request, options):
        money = _build_lines(
            options["line_items"], options["tax_rate"], options["discount_rate"],
        )
        return {"options": options, "customer": _customer(options), **money}

    def get_filename(self, options):
        return f"{options['number']}.pdf"