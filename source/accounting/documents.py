"""
accounting/documents.py
------------------------------------------------------------------------
The document types of the Accounting module. The documents app finds
this file at start and imports it (see documents/apps.py).

The data of the company fills the options of each document:

    - the active customers (customer_entities) give the choices of the
      customer field. _customer() reads the address and the numbers.
    - the services and the active stock items give the "Add from the
      catalog" select of the line item editor (see catalog).
    - the base currency and the standard tax code give the currency and
      the tax rate. The active bank accounts give the choices of the bank
      account field. The first one is the default (see get_options_form).
    - the posted lines of the receivable account of the customer give the
      account in the statement (see _ledger).
"""

import calendar
import datetime
from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from documents.forms import (DocumentOptionsForm, LineItemsField, SelectWithAddButton, SelectWithDetails)
from documents.registry import DocumentType, register
from accounting.models import *
from accounting.posting import RECEIVABLE, _account, invoice_posted, post_invoice_entry


CENT = Decimal("0.01")
ZERO = Decimal("0")

AGEING_LABELS = ["Current", "1–30 days", "31–60 days", "61–90 days", "90+ days"]


def age_bucket(days):
    """The index in AGEING_LABELS of an amount that is the number of days after its due date."""
    return 0 if days <= 0 else min((days - 1) // 30 + 1, 4)


def _customers(company):
    """The active customers of the company. The key of each is its pk."""
    return customer_entities(company).filter(is_active=True)


def _customer_choices(company):
    """The customers, after an empty choice. The first preview has no customer."""
    return [("", "Select a customer")] + [(str(e.pk), e.name) for e in _customers(company)]


def _customer(options, company):
    """Return the customer record for the selected choice. No choice gives
    an empty record.

    The statement also reads the email, the entity, and the VAT and
    registration numbers. An organization only has these two numbers.
    """
    entity = (_customers(company).select_related("organization_profile")
              .filter(pk=options["customer"] or None).first())
    if not entity:
        return {"name": "", "details": ""}
    org = getattr(entity, "organization_profile", None) if entity.type == entity.EntityType.ORGANIZATION else None
    return {"name": entity.name, "details": entity.address, "email": entity.email, "entity": entity,
            "vat_number": org and org.tax_number, "registration_number": org and org.registration_number}


def catalog(company, item_types, purchase=False):
    """The rows of the "Add from the catalog" select. A sale lists the
    services of the company, then the active items of the types, with no
    price: the data has no sale price, thus the user types it. A purchase
    lists the items only, with the cost of each item as its price."""
    services = [] if purchase else Service.objects.filter(company=company).order_by("name")
    rows = [{"description": s.name, "unit": "", "unit_price": ""} for s in services]
    for item in Item.objects.filter(item_type__in=item_types, active=True, obsoleted=False).order_by("name"):
        price = item.cost if purchase and item.cost is not None else ""
        rows.append({"description": item.name, "unit": "", "unit_price": str(price)})
    return rows


def currency_symbol(company):
    """The symbol of the base currency of the company, else its code."""
    return company.base_currency.symbol or company.base_currency_id


def standard_rate(company):
    """The rate of the standard tax code of the company that applies today, else zero."""
    today = datetime.date.today()
    code = (TaxCode.objects.filter(company=company, kind=TaxCode.Kind.STANDARD, valid_from__lte=today)
            .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today)).order_by("-valid_from").first())
    return code.rate if code else ZERO


def _bank_field():
    """The bank account of a payment. The field shows all the details of the selected account."""
    return forms.ChoiceField(label="Bank account", required=False, widget=SelectWithDetails)


def _bank_details(bank, reference):
    """The details of a bank account, for a payment."""
    return "\n".join(filter(None, [
        bank.bank or bank.name,
        bank.account_number and f"Account {bank.account_number}",
        bank.sort_code and f"Branch {bank.sort_code}",
        bank.iban and f"IBAN {bank.iban}",
        f"Reference: {reference}",
    ]))


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


def _due(options):
    """The due date of an invoice: its issue date with its payment terms, or the custom due date."""
    return PaymentTerms(options["terms"]).due(options["issue_date"], options["due_date"])


def _terms_label(options):
    """The text of the payment terms. A statement without terms keeps the terms of each invoice."""
    if not options.get("terms"):
        return "As invoiced"
    if options["terms"] == PaymentTerms.CUSTOM:
        return f"Custom, due {options['due_date']:%d %b %Y}"
    return PaymentTerms(options["terms"]).label


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
        "number", "issue_date", "valid_until",
        "currency", "tax_rate", "bank_account",
    )

    # SalesDocument.get_options_form gives the customers, the catalog, the
    # currency, the tax rate and the payment details of the company.
    customer = forms.ChoiceField(
        label="Customer",
        required=False,             # The first preview has no customer. An invoice needs one (see InvoiceDocument.issue).
        widget=SelectWithAddButton(
            action="new-customer", button_label="Add a new customer",
            search_action="search-customer", search_label="Search the customers",
        ),
    )
    line_items = LineItemsField(
        label="Line items",
        initial=[],
    )
    terms = forms.ChoiceField(
        label="Payment terms",
        choices=PaymentTerms.choices,
        initial=PaymentTerms.DAYS_30,
    )
    due_date = forms.DateField(
        label="Custom due date",
        required=False,
        initial=_in_days(30),
        help_text="Used only when the payment terms are Custom.",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    currency = forms.CharField(
        label="Currency symbol",
        required=False,
        max_length=4,
    )
    tax_rate = forms.DecimalField(
        label="Tax rate (%)",
        initial=ZERO,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        decimal_places=2,
    )
    notes = forms.CharField(
        label="Notes",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean(self):
        data = super().clean()
        if data.get("terms") == PaymentTerms.CUSTOM:
            if not data.get("due_date"):
                self.add_error("due_date", "Give the due date of the Custom payment terms.")
            elif data.get("issue_date") and data["due_date"] < data["issue_date"]:
                self.add_error("due_date", "The due date must be on or after the issue date.")
        return data


class InvoiceOptionsForm(SalesDocumentOptionsForm):
    field_order = [
        "pro_forma", "recurring", "frequency", "number", "issue_date", "terms", "due_date", "customer", "line_items",
        "currency", "tax_rate", "bank_account", "notes",
    ]

    pro_forma = forms.BooleanField(label="Pro-Forma", required=False, initial=False)
    recurring = forms.BooleanField(label="Recurring Invoice", required=False, initial=False)
    frequency = forms.ChoiceField(label="Frequency", choices=RecurringDocument.Frequency.choices,
                                  initial=RecurringDocument.Frequency.MONTHLY,
                                  help_text="Used only for a recurring invoice.")
    number = forms.CharField(label="Invoice number")
    issue_date = _date_field("Issue Date")     # The payment terms give the due date (see _due).
    bank_account = _bank_field()


class StatementOptionsForm(SalesDocumentOptionsForm):
    """The statement keeps the customer, currency and notes fields of the parent form."""

    line_items = None   # A None value removes the field of the parent form.
    tax_rate = None
    muted_field_names = ("number", "currency", "bank_account")
    field_order = [
        "number", "start_date", "end_date", "customer", "brought_forward",
        "terms", "due_date", "interest_rate", "currency", "bank_account", "notes",
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
    terms = forms.ChoiceField(
        label="Payment terms",
        choices=[("", "As invoiced")] + PaymentTerms.choices,
        initial="",
        required=False,
        help_text="As invoiced keeps the due date of each invoice. Other terms give each charge a due date from its date. "
                  "Custom gives each charge the custom due date, but not a date before the charge.",
    )
    interest_rate = forms.DecimalField(
        label="Interest on arrears (% per year)",
        initial=Decimal("0"),
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        decimal_places=2,
        help_text="Simple interest per day on each overdue amount. 0 gives no interest.",
    )
    bank_account = _bank_field()

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
            company, fields = request.company, form.fields
            fields["number"].initial = NumberSequence.peek(company, self.key, self.prefix)
            fields["customer"].choices = _customer_choices(company)
            fields["currency"].initial = currency_symbol(company)
            if "line_items" in fields:
                fields["line_items"].widget.catalog = catalog(company, [Item.ItemType.STOCK])
            if "tax_rate" in fields:
                fields["tax_rate"].initial = standard_rate(company)
            if "bank_account" in fields:
                banks = list(BankAccount.objects.filter(company=company, is_active=True).order_by("id"))
                fields["bank_account"].choices = [("", "No bank details")] + [
                    (str(bank.pk), " · ".join(filter(None, [bank.bank, bank.name]))) for bank in banks]
                fields["bank_account"].initial = str(banks[0].pk) if banks else ""
                fields["bank_account"].widget.details = {
                    str(bank.pk): _bank_details(bank, f"the {self.key} number") for bank in banks}
        return form

    def bank_details(self, request, options):
        """The details of the selected bank account, for the PDF."""
        bank = BankAccount.objects.filter(company=request.company, pk=options["bank_account"] or None).first()
        return _bank_details(bank, f"the {self.key} number") if bank else ""

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
        return {"options": options, "customer": _customer(options, request.company), "due": _due(options),
                "terms": _terms_label(options), "bank_details": self.bank_details(request, options), **money}

    def issue(self, request, options):
        """Keep the invoice as a Document, then post its entry from the Document (see
        post_invoice_entry). An invoice that has an entry does not change."""
        if options["pro_forma"]:
            return
        entity = _customer(options, request.company).get("entity")
        if not entity:
            raise ValidationError("Select a customer.")
        with transaction.atomic():
            super().issue(request, options)
            if invoice_posted(request.company, options["number"]):
                return
            document, _ = _sales_record(request.company, options, entity, Document.DocType.INVOICE, _due(options),
                                        Document.Status.SENT)
            document.journal_entry = post_invoice_entry(document)
            document.save(update_fields=["journal_entry"])
            AuditLog.record(request, AuditLog.Action.CREATE, document)
            if options["recurring"]:
                RecurringDocument.start(document, options["frequency"], request.user)


def _sales_record(company, options, entity, doc_type, due, status=None, discount=ZERO):
    """Keep an issued sales document (an invoice or a quote) as a Document with its lines.
    The same number again changes the document and replaces its lines. A status of None
    keeps the status (a new document is a draft). The statement reads the due date.
    A tax rate must have a tax code that is valid on the issue date. Returns (document, created)."""
    sales = _account(company, "Sales")
    day, rate = options["issue_date"], options["tax_rate"]
    tax_code = (TaxCode.objects.filter(company=company, rate=rate, valid_from__lte=day)
                .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=day)).order_by("-valid_from").first())
    if rate and not tax_code:
        raise ValidationError(f"No tax code has the rate {rate}% on {day:%d %b %Y}. Add it first.")
    fields = {"date": day, "due": due, "terms": options["terms"], "entity": entity,
              "currency": company.base_currency, "notes": options["notes"]}
    if status:
        fields["status"] = status
    document, created = Document.objects.update_or_create(
        company=company, direction=Document.Direction.SALE, doc_type=doc_type, number=options["number"],
        defaults=fields,
    )
    document.lines.all().delete()
    DocumentLine.objects.bulk_create(
        DocumentLine(document=document, account=sales, tax_code=tax_code, description=line["description"],
                     quantity=line["quantity"], unit_price=line["unit_price"], discount=discount, sort_order=index)
        for index, line in enumerate(options["line_items"])
    )
    return document, created


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
        if document:    # The line description of an opening balance stays (see post_opening_document).
            row.update(reference=document.number, description=line.description or document.get_doc_type_display(),
                       due=document.due or entry.date)
        elif payment:   # Money out to a customer is e.g. a refund.
            kind = "Payment received" if payment.direction == Payment.Direction.IN else "Payment made"
            row.update(reference=payment.number, description=" — ".join(filter(None, [kind, payment.reference])))
        elif entry.entry_type == JournalEntry.EntryType.SALES:
            row["description"] = "Invoice"
        rows.append(row)
    return rows


def _statement(ledger, options):
    """Compute the figures of the statement from the account rows.

    The payments and the credits settle the oldest charges first. Thus
    the newest charges make the closing balance. The ageing and the
    interest use the due date of each of these charges, at the end date.
    Payment terms on the statement replace the due date of each charge.
    """
    start, end, rate = options["start_date"], options["end_date"], options["interest_rate"]
    ledger = [row for row in ledger if row["date"] <= end]
    if options.get("terms"):
        terms = PaymentTerms(options["terms"])     # max(): a charge is not due before its date.
        ledger = [{**row, "due": max(row["date"], terms.due(row["date"], options["due_date"]))} for row in ledger]
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
        ageing[age_bucket(days)] += part
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
        customer = _customer(options, request.company)
        ledger = _ledger(request.company, customer["entity"]) if customer.get("entity") else []
        return {"options": options, "customer": customer, "terms": _terms_label(options),
                "bank_details": self.bank_details(request, options), **_statement(ledger, options)}
