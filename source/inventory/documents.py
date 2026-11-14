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
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from accounting.documents import catalog, catalog_record, currency_symbol, standard_rate
from accounting.models import AuditLog, Document, DocumentLine, NumberSequence, TaxCode, supplier_entities
from accounting.posting import COST_OF_SALES, _account, asset_account
from documents.forms import (
    DocumentOptionsForm, LineItemsField, SelectWithAddButton,
)
from documents.registry import DocumentType, register
from inventory.models import ItemType


CENT = Decimal("0.01")
PURCHASED = [ItemType.STOCK, ItemType.CONSUMABLE, ItemType.COMPONENT]


def _suppliers(company):
    return supplier_entities(company).filter(is_active=True)


def _supplier_entity(options, company):
    return _suppliers(company).filter(pk=options["supplier"] or None).first()


def _supplier(options, company):
    """Return the supplier record for the selected choice. No choice gives an empty record."""
    entity = _supplier_entity(options, company)
    return {"name": entity.name, "details": entity.address} if entity else {"name": "", "details": ""}


def _purchase_lines(company, options):
    """The lines of a purchase order as unsaved DocumentLines. A line from the catalog
    keeps its item. A tracked item posts to its asset account (Inventory): the bill
    then puts the stock on the balance sheet. Every other line posts to Cost of Sales.
    The tax rate must have a tax code that is valid on the issue date."""
    day, rate = options["issue_date"], options["tax_rate"]
    tax_code = (TaxCode.usable(company).filter(rate=rate, valid_from__lte=day)
                .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=day)).order_by("-valid_from").first())
    if rate and not tax_code:
        raise ValidationError(f"No tax code has the rate {rate}% on {day:%d %b %Y}. Add it first.")
    expense = _account(company, COST_OF_SALES)
    lines = []
    for index, line in enumerate(options["line_items"]):
        record = catalog_record(company, line.get("ref"))
        item = record.get("item")
        lines.append(DocumentLine(
            account=asset_account(item) if item and item.tracked else expense, tax_code=tax_code,
            description=line["description"], quantity=line["quantity"], unit_price=line["unit_price"],
            sort_order=index, item=item))
    return lines


def _replace_lines(document, lines):
    document.lines.all().delete()
    for line in lines:
        line.pk, line.document = None, document
    DocumentLine.objects.bulk_create(lines)


def record_purchase_order(request, options):
    """Keep an issued purchase order as a Document, and make its draft bill.

    The order is a commitment, not a liability, thus it has no journal entry. The
    draft bill (source_doc = the order) waits in the Review part of the Bills page.
    Approve posts it: Dr the asset or expense account of each line / Cr Accounts
    Payable, and the stock of each tracked item comes in (see posting.post_bill).
    Deny voids it when the supplier does not deliver.

    The same order number again (e.g. Download, then one more line, then Save)
    changes the order and its draft bill. An order with an approved bill cannot
    change. Returns the order."""
    company = request.company
    entity = _supplier_entity(options, company)
    if not entity:
        raise ValidationError("Select a supplier.")
    if not options["line_items"]:
        raise ValidationError("Add one line or more. Each line must have a description.")
    P, B, S = Document.Direction.PURCHASE, Document.DocType, Document.Status
    with transaction.atomic():
        order, created = Document.objects.update_or_create(
            company=company, direction=P, doc_type=B.PURCHASE_ORDER, number=options["number"],
            defaults={"date": options["issue_date"], "due": options["delivery_date"], "entity": entity,
                      "currency": company.base_currency, "notes": options["notes"], "status": S.SENT})
        bill = order.related_docs.filter(doc_type=B.BILL).first()
        if bill and bill.status != S.DRAFT:
            raise ValidationError(f"Purchase order {order.number} has the approved bill {bill.number}, "
                                  "thus it cannot change. Use a new order number.")
        lines = _purchase_lines(company, options)
        _replace_lines(order, lines)
        if not bill:
            NumberSequence.peek(company, "bill", "BILL-")      # Makes the sequence on first use
            bill = Document.objects.create(
                company=company, direction=P, doc_type=B.BILL, number=NumberSequence.take(company, "bill"),
                date=order.date, due=order.due, entity=entity, currency=company.base_currency,
                status=S.DRAFT, source_doc=order, notes=f"From purchase order {order.number}", created_by=request.user)
        else:
            Document.objects.filter(pk=bill.pk).update(date=order.date, due=order.due, entity=entity)
        _replace_lines(bill, lines)
        AuditLog.record(request, AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE, order)
    return order


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
            # Not tax registered: the form ignores a sent rate and uses the initial rate, zero.
            fields["tax_rate"].disabled = not company.is_tax_registered
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

    def issue(self, request, options):
        """Take the number, then keep the order and make its draft bill (see record_purchase_order)."""
        with transaction.atomic():
            super().issue(request, options)
            record_purchase_order(request, options)


@register
class GoodsReceiptDocument(StockDocument):
    key = "goods-receipt"
    prefix = "GRN-"
    label = "New Goods Receipt"
    description = "A record of the goods that came in against a purchase order."
    template_name = "inventory/pdf/goods_receipt.html"
    options_form_class = GoodsReceiptOptionsForm
