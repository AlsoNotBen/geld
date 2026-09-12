"""
inventory/documents.py
------------------------------------------------------------------------
The document types of the Inventory module. The documents app finds
this file at start and imports it (see documents/apps.py).

The module has no supplier or item models yet. Thus the suppliers and
the item catalog below are sample data. Replace them with queries when
the models exist:

    - SAMPLE_SUPPLIERS becomes the suppliers table.
    - CATALOG becomes the stock items table.
"""

import datetime
from decimal import Decimal, ROUND_HALF_UP

from django import forms

from documents.forms import (
    DocumentOptionsForm, LineItemsField, SelectWithAddButton,
)
from documents.registry import DocumentType, register


CENT = Decimal("0.01")

SAMPLE_SUPPLIERS = {
    "cape-fasteners": {
        "name": "Cape Fasteners (Pty) Ltd",
        "details": "14 Bofors Circle\n7405 Epping",
    },
    "atlas-electrical": {
        "name": "Atlas Electrical Wholesale",
        "details": "3 Cobalt Road\n7460 Montague Gardens",
    },
    "southern-packaging": {
        "name": "Southern Packaging CC",
        "details": "Unit 12, Gateway Park\n7100 Somerset West",
    },
}

# Sample stock items. All values are strings, because the line items
# travel as JSON. The clean method of LineItemsField turns the numbers
# into Decimal values.
CATALOG = [
    {"description": "M8 x 40 hex bolt, zinc plated (box of 100)",
     "unit": "box", "unit_price": "185.00"},
    {"description": "2.5 mm² twin and earth cable (100 m roll)",
     "unit": "roll", "unit_price": "1240.00"},
    {"description": "Corrugated carton 400 x 300 x 300 mm",
     "unit": "each", "unit_price": "9.60"},
    {"description": "Nitrile gloves, size L (box of 100)",
     "unit": "box", "unit_price": "142.00"},
    {"description": "Pallet wrap 500 mm x 300 m",
     "unit": "roll", "unit_price": "78.50"},
]

INITIAL_LINES = [
    {**CATALOG[0], "quantity": "4"},
    {**CATALOG[1], "quantity": "2"},
    {**CATALOG[2], "quantity": "150"},
]


def _supplier_choices():
    return [(key, value["name"]) for key, value in SAMPLE_SUPPLIERS.items()]


def _supplier(options):
    """Return the supplier record for the selected choice."""
    return SAMPLE_SUPPLIERS.get(
        options["supplier"], {"name": options["supplier"], "details": ""},
    )


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
    """Options that the purchase order and the goods receipt share."""

    supplier = forms.ChoiceField(
        label="Supplier",
        choices=_supplier_choices,
        initial="cape-fasteners",
        widget=SelectWithAddButton(
            action="new-supplier", button_label="Add a new supplier",
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


class PurchaseOrderOptionsForm(StockDocumentOptionsForm):
    field_order = [
        "number", "issue_date", "delivery_date", "supplier", "deliver_to",
        "line_items", "currency", "tax_rate", "terms", "notes",
    ]

    number = forms.CharField(label="Order number", initial="PO-2026-0108")
    issue_date = _date_field("Issue date")
    delivery_date = _date_field("Delivery date", days_ahead=7)
    deliver_to = forms.CharField(
        label="Deliver to",
        initial="Main Warehouse\n12 Fynbos Lane\n8001 Cape Town",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    terms = forms.CharField(
        label="Terms",
        required=False,
        initial="Payment 30 days from the date of the invoice.\nQuote the order number on the delivery note and on the invoice.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class GoodsReceiptOptionsForm(StockDocumentOptionsForm):
    field_order = [
        "number", "received_date", "order_number", "delivery_note",
        "supplier", "received_at", "line_items", "currency", "tax_rate",
        "notes",
    ]

    number = forms.CharField(label="Receipt number", initial="GRN-2026-0073")
    received_date = _date_field("Received date")
    order_number = forms.CharField(label="Order number", initial="PO-2026-0108")
    delivery_note = forms.CharField(
        label="Delivery note",
        required=False,
        initial="DN-55821",
    )
    received_at = forms.CharField(
        label="Received at",
        initial="Main Warehouse, Bay 3",
    )


@register
class PurchaseOrderDocument(DocumentType):
    module = "inventory"
    key = "purchase-order"
    label = "New Purchase Order"
    description = "An order to a supplier with line items, totals and delivery details."
    template_name = "inventory/pdf/purchase_order.html"
    options_form_class = PurchaseOrderOptionsForm

    def get_context(self, request, options):
        money = _build_lines(options["line_items"], options["tax_rate"])
        return {"options": options, "supplier": _supplier(options), **money}

    def get_filename(self, options):
        return f"{options['number']}.pdf"


@register
class GoodsReceiptDocument(DocumentType):
    module = "inventory"
    key = "goods-receipt"
    label = "New Goods Receipt"
    description = "A record of the goods that came in against a purchase order."
    template_name = "inventory/pdf/goods_receipt.html"
    options_form_class = GoodsReceiptOptionsForm

    def get_context(self, request, options):
        money = _build_lines(options["line_items"], options["tax_rate"])
        return {"options": options, "supplier": _supplier(options), **money}

    def get_filename(self, options):
        return f"{options['number']}.pdf"