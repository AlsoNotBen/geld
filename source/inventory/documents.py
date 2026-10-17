"""
inventory/documents.py
------------------------------------------------------------------------
The document types of the Inventory module. The documents app finds
this file at start and imports it (see documents/apps.py).

The data of the company fills the options of each document: the active
suppliers (supplier_entities) give the choices of the supplier field,
and the active stock items, consumables and components give the catalog,
with the cost of each item as its unit price. The number of a document
comes from a NumberSequence with the name of its key.
"""

import datetime
from decimal import Decimal, ROUND_HALF_UP

from django import forms

from accounting.documents import catalog, currency_symbol, standard_rate
from accounting.models import NumberSequence, supplier_entities
from documents.forms import (
    DocumentOptionsForm, LineItemsField, SelectWithAddButton,
)
from documents.registry import DocumentType, register
from inventory.models import Item


CENT = Decimal("0.01")
PURCHASED = [Item.ItemType.STOCK, Item.ItemType.CONSUMABLE, Item.ItemType.COMPONENT]


def _suppliers(company):
    return supplier_entities(company).filter(is_active=True)


def _supplier(options, company):
    """Return the supplier record for the selected choice. No choice gives an empty record."""
    entity = _suppliers(company).filter(pk=options["supplier"] or None).first()
    return {"name": entity.name, "details": entity.address} if entity else {"name": "", "details": ""}


def _in_days(days):
    """Return a function that gives today plus the number of days."""
    return lambda: datetime.date.today() + datetime.timedelta(days=days)


def _date_field(label, days_ahead=0):
    return forms.DateField(
        label=label,
        initial=_in_days(days_ahead),
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )


def _build_lines(lines, tax_rate):
    """Compute the line totals and the sums."""
    computed = []
    subtotal = Decimal("0")
    for line in lines:
        total = (line["quantity"] * line["unit_price"]).quantize(CENT, ROUND_HALF_UP)
        subtotal += total
        computed.append({**line, "total": total})
    tax = (subtotal * tax_rate / 100).quantize(CENT, ROUND_HALF_UP)
    return {
        "lines": computed,
        "subtotal": subtotal,
        "tax": tax,
        "total": subtotal + tax,
    }


class StockDocumentOptionsForm(DocumentOptionsForm):
    """Options that the purchase order and the goods receipt share.
    StockDocument.get_options_form gives the suppliers, the catalog, the
    currency and the tax rate of the company."""

    supplier = forms.ChoiceField(
        label="Supplier",
        required=False,     # The first preview has no supplier.
        widget=SelectWithAddButton(
            action="new-supplier", button_label="Add a new supplier",
        ),
    )
    line_items = LineItemsField(
        label="Line items",
        initial=[],
    )
    currency = forms.CharField(
        label="Currency symbol",
        required=False,
        max_length=4,
    )
    tax_rate = forms.DecimalField(
        label="Tax rate (%)",
        initial=Decimal("0"),
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        decimal_places=2,
    )
    notes = forms.CharField(
        label="Notes",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class PurchaseOrderOptionsForm(StockDocumentOptionsForm):
    field_order = [
        "number", "issue_date", "delivery_date", "supplier", "deliver_to",
        "line_items", "currency", "tax_rate", "terms", "notes",
    ]

    number = forms.CharField(label="Order number")
    issue_date = _date_field("Issue date")
    delivery_date = _date_field("Delivery date", days_ahead=7)
    deliver_to = forms.CharField(
        label="Deliver to",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    terms = forms.CharField(
        label="Terms",
        required=False,
        initial="Quote the order number on the delivery note and on the invoice.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class GoodsReceiptOptionsForm(StockDocumentOptionsForm):
    field_order = [
        "number", "received_date", "order_number", "delivery_note",
        "supplier", "received_at", "line_items", "currency", "tax_rate",
        "notes",
    ]

    number = forms.CharField(label="Receipt number")
    received_date = _date_field("Received date")
    order_number = forms.CharField(label="Order number", required=False)
    delivery_note = forms.CharField(
        label="Delivery note",
        required=False,
    )
    received_at = forms.CharField(
        label="Received at",
    )


class StockDocument(DocumentType):
    """The purchase order and the goods receipt. The number comes from a
    NumberSequence with the name of the key. The company gives the place
    of the delivery."""
    module = "inventory"
    prefix = ""

    def get_options_form(self, data=None, request=None):
        form = super().get_options_form(data, request)
        if request:
            company, fields = request.company, form.fields
            fields["number"].initial = NumberSequence.peek(company, self.key, self.prefix)
            fields["supplier"].choices = [("", "Select a supplier")] + [
                (str(e.pk), e.name) for e in _suppliers(company)]
            fields["line_items"].widget.catalog = catalog(company, PURCHASED, purchase=True)
            fields["currency"].initial = currency_symbol(company)
            fields["tax_rate"].initial = standard_rate(company)
            if "deliver_to" in fields:
                fields["deliver_to"].initial = "\n".join(filter(None, [company.name, company.address]))
            if "received_at" in fields:
                fields["received_at"].initial = company.name
        return form

    def issue(self, request, options):
        # Take the number only when the document uses the next number. Thus a second download takes no number.
        if options["number"] == NumberSequence.peek(request.company, self.key, self.prefix):
            NumberSequence.take(request.company, self.key)

    def get_context(self, request, options):
        money = _build_lines(options["line_items"], options["tax_rate"])
        return {"options": options, "supplier": _supplier(options, request.company), **money}

    def get_filename(self, options):
        return f"{options['number']}.pdf"


@register
class PurchaseOrderDocument(StockDocument):
    key = "purchase-order"
    prefix = "PO-"
    label = "New Purchase Order"
    description = "An order to a supplier with line items, totals and delivery details."
    template_name = "inventory/pdf/purchase_order.html"
    options_form_class = PurchaseOrderOptionsForm


@register
class GoodsReceiptDocument(StockDocument):
    key = "goods-receipt"
    prefix = "GRN-"
    label = "New Goods Receipt"
    description = "A record of the goods that came in against a purchase order."
    template_name = "inventory/pdf/goods_receipt.html"
    options_form_class = GoodsReceiptOptionsForm
