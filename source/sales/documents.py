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
from django.core.exceptions import ValidationError
from django.db import transaction
from documents.registry import register
from accounting.documents import (SalesDocument, SalesDocumentOptionsForm,
                                  _build_lines, _customer, _date_field, _sales_record, _terms_label)
from accounting.models import AuditLog, Document


class QuoteOptionsForm(SalesDocumentOptionsForm):
    field_order = [
        "number", "issue_date", "valid_until", "terms", "due_date", "customer", "line_items",
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
        return {"options": options, "customer": _customer(options, request.company), "terms": _terms_label(options), **money}

    def issue(self, request, options):
        """Keep the quote as a Document. The due date is the Valid until date. Save keeps
        a new quote as a draft. Download and Send (a GET, see documents/views.py) make it
        sent. The same number again changes the quote."""
        entity = _customer(options, request.company).get("entity")
        if not entity:
            raise ValidationError("Select a customer.")
        with transaction.atomic():
            super().issue(request, options)
            status = Document.Status.SENT if request.method == "GET" else None
            document, created = _sales_record(request.company, options, entity, Document.DocType.QUOTE,
                                              options["valid_until"], status, discount=options["discount_rate"])
            AuditLog.record(request, AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE, document)
