"""
sales/documents.py
------------------------------------------------------------------------
The document types of the Sales module. The documents app finds this
file at start and imports it (see documents/apps.py).

The quote uses the shared parts of the sales documents in
accounting/documents.py.
"""

from decimal import Decimal
from django import forms
from documents.registry import register
from accounting.documents import (SalesDocument, SalesDocumentOptionsForm,
                                  _build_lines, _customer, _date_field)


class QuoteOptionsForm(SalesDocumentOptionsForm):
    field_order = [
        "number", "issue_date", "valid_until", "customer", "line_items",
        "currency", "tax_rate", "discount_rate", "notes",
    ]

    number = forms.CharField(label="Quote number")
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
class QuoteDocument(SalesDocument):
    module = "sales"
    key = "quote"
    prefix = "QUO-"
    label = "New Quote"
    description = "A sales quote with line items, totals and an acceptance block."
    template_name = "sales/pdf/quote.html"
    options_form_class = QuoteOptionsForm

    def get_context(self, request, options):
        money = _build_lines(
            options["line_items"], options["tax_rate"], options["discount_rate"],
        )
        return {"options": options, "customer": _customer(options), **money}
