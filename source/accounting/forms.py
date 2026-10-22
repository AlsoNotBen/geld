import datetime
from django import forms
from django.utils import timezone
from accounting.models import (Account, BankAccount, Document, Entity, Note, NumberSequence, OrganizationProfile,
                               Payment, RecurringDocument, in_one_month)
from shared.models import Supplier
from documents.forms import SelectWithSearch


def _opening_fields(min_value=None):
    """The amount and the date of an opening balance. The view uses today when the date is empty."""
    return (forms.DecimalField(label="Opening balance", required=False, min_value=min_value, max_digits=13,
                               decimal_places=2),
            forms.DateField(label="Opening balance date", required=False, initial=datetime.date.today,
                            widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")))


class PaymentForm(forms.ModelForm):
    """The fields of the Record Payment overlay. The view sets the company and the currency."""

    direction = forms.ChoiceField(label="Direction", choices=Payment.Direction.choices, initial=Payment.Direction.IN)

    class Meta:
        model = Payment
        fields = ["number", "date", "direction", "entity", "bank_account", "amount", "reference"]
        labels = {"number": "Payment number", "entity": "Customer or supplier"}
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "entity": SelectWithSearch(search_action="search-entity", search_label="Search the customers and suppliers"),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        banks = BankAccount.objects.filter(company=company, is_active=True)
        first_bank = banks.first()
        self.fields["entity"].queryset = Entity.objects.filter(company=company, is_active=True).order_by("name")
        self.fields["bank_account"].queryset = banks
        self.fields["bank_account"].label_from_instance = lambda bank: bank.name
        if first_bank is None:
            self.fields["bank_account"].empty_label = "No bank account. Add one first."
        self.fields["amount"].widget.attrs["min"] = "0.01"
        self.fields["reference"].widget.attrs["placeholder"] = "Reference - the invoice or bill number. Required to link a payment."
        if not self.is_bound:
            self.initial.update(number=NumberSequence.peek(company, "payment", "PAY-"),date=datetime.date.today(), bank_account=first_bank)
        for field in self.fields.values():
            field.widget.attrs["class"] = "field__control"

    def clean_number(self):
        number = self.cleaned_data["number"]
        if Payment.objects.filter(company=self.company, number=number).exists():
            raise forms.ValidationError("Another payment has this number.")
        return number

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("The amount must be more than zero.")
        return amount


class BillForm(forms.ModelForm):
    """The head fields of the New Bill overlay. The view reads the lines,
    and it sets the company, the type, the status and the currency. A
    recurring bill gets a RecurringDocument with the frequency."""

    recurring = forms.BooleanField(label="Recurring", required=False, help_text="Recurring bill")
    frequency = forms.ChoiceField(label="Frequency", choices=RecurringDocument.Frequency.choices,
                                  initial=RecurringDocument.Frequency.MONTHLY)

    class Meta:
        model = Document
        fields = ["number", "entity", "date", "due", "notes"]
        labels = {"number": "Bill number", "entity": "Supplier", "due": "Due date"}
        widgets = {
            "entity": SelectWithSearch(search_action="search-supplier", search_label="Search the suppliers"),
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "due": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.TextInput(),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        self.fields["entity"].queryset = Entity.objects.filter(company=company, is_active=True).order_by("name")
        if not self.is_bound:
            today = datetime.date.today()
            self.initial.update(number=NumberSequence.peek(company, "bill", "BILL-"), date=today,
                                due=today + datetime.timedelta(days=14))
        for field in self.fields.values():
            field.widget.attrs["class"] = "field__control"

    def clean_number(self):
        number = self.cleaned_data["number"]
        if Document.objects.filter(company=self.company, direction=Document.Direction.PURCHASE,
                                   doc_type=Document.DocType.BILL, number=number).exists():
            raise forms.ValidationError("Another bill has this number.")
        return number

    def clean(self):
        data = super().clean()
        if data.get("date") and data.get("due") and data["due"] < data["date"]:
            self.add_error("due", "The due date must be on or after the bill date.")
        return data


class SupplierForm(forms.ModelForm):
    """The fields of the New Supplier and Edit Supplier pages. save() makes or
    changes the entity and its organization profile from the name, the email,
    the phone and the VAT number. An individual has no VAT number field."""

    name = forms.CharField(label="Name", max_length=255)
    email = forms.EmailField(label="Email", required=False)
    phone = forms.CharField(label="Phone", max_length=50, required=False)
    vat_number = forms.CharField(label="VAT number", max_length=50, required=False)
    opening_balance, opening_date = _opening_fields(min_value=0)    # A new supplier only (see post_opening_document)

    field_order = ["name", "code", "contact", "email", "phone", "vat_number", "terms", "bank_account",
                   "opening_balance", "opening_date"]

    class Meta:
        model = Supplier
        fields = ["code", "contact", "terms", "bank_account"]
        labels = {"contact": "Contact person", "terms": "Payment terms"}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        entity = self.instance.entity if self.instance.entity_id else None
        if entity:
            profile = getattr(entity, "organization_profile", None)
            self.initial.update(name=entity.name, email=entity.email, phone=entity.phone,
                                vat_number=profile.tax_number if profile else "")
            if entity.type == Entity.EntityType.INDIVIDUAL:
                del self.fields["vat_number"]
            del self.fields["opening_balance"], self.fields["opening_date"]
        if not self.instance.pk and not self.is_bound:
            self.initial["code"] = NumberSequence.peek(company, "supplier", "SUP-")
        for field in self.fields.values():
            field.widget.attrs["class"] = "field__control"

    def clean_code(self):
        code = self.cleaned_data["code"]
        if Supplier.objects.filter(company=self.company, code=code).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Another supplier has this code.")
        return code

    def save(self, user):
        """Save the entity, its profile and the supplier details. A new supplier gets a new entity."""
        data = self.cleaned_data
        supplier = super().save(commit=False)
        entity = supplier.entity if supplier.entity_id else Entity(
            company=self.company, created_by=user, type=Entity.EntityType.ORGANIZATION)
        entity.name, entity.email, entity.phone = data["name"], data["email"], data["phone"]
        entity.save()
        if entity.type == Entity.EntityType.ORGANIZATION:
            OrganizationProfile.objects.update_or_create(
                entity=entity, defaults={"legal_name": data["name"], "tax_number": data["vat_number"]})
        supplier.entity = entity
        supplier.company = self.company                     # Add to every function that creates a CompanyOwned record
        supplier.created_by = supplier.created_by or user
        supplier.save()
        return supplier


class BankAccountForm(forms.ModelForm):
    """The fields of the New Bank Account and Edit Bank Account pages. The
    ledger account is a current asset or a floating account of the chart of
    accounts that no other bank account uses. The view sets the company. The
    opening balance comes from the opening entry (see set_bank_opening). A
    negative opening balance is an overdraft."""

    opening_balance, opening_date = _opening_fields()

    class Meta:
        model = BankAccount
        fields = ["bank", "name", "account_number", "sort_code", "iban", "currency", "account", "is_active"]
        labels = {"name": "Account name", "sort_code": "Branch code", "iban": "IBAN", "account": "Ledger account",
                  "is_active": "Status"}
        help_texts = {"is_active": "Active"}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        used = BankAccount.objects.filter(company=company).exclude(pk=self.instance.pk).values("account_id")
        accounts = Account.objects.filter(
            company=company, is_active=True,
            type__in=[Account.AccountType.CURRENT_ASSETS, Account.AccountType.FLOATING_NOMINAL],
        ).exclude(pk__in=used)
        self.fields["account"].queryset = accounts
        self.fields["account"].empty_label = ("Select an account" if accounts.exists()
                                              else "No free account. Add one in the Chart of Accounts.")
        self.fields["currency"].label_from_instance = lambda currency: f"{currency.alpha_code} · {currency.name}"
        if not self.instance.pk:
            self.initial.setdefault("currency", company.base_currency_id)
        entry = self.instance.opening_entry
        if entry:
            line = entry.lines.filter(account_id=self.instance.account_id).first()
            self.initial.update(opening_balance=line and line.debit - line.credit, opening_date=entry.date)
        for field in self.fields.values():
            field.widget.attrs["class"] = "field__control"


class CustomerForm(forms.ModelForm):
    """The fields of the Edit Customer page. A customer is an entity (see
    customer_entities). The VAT number is on the profile of an organization."""

    vat_number = forms.CharField(label="VAT number", max_length=50, required=False)

    field_order = ["name", "email", "phone", "vat_number", "address", "is_active"]

    class Meta:
        model = Entity
        fields = ["name", "email", "phone", "address", "is_active"]
        labels = {"is_active": "Status"}
        help_texts = {"is_active": "Active"}
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.type == Entity.EntityType.ORGANIZATION:
            profile = getattr(self.instance, "organization_profile", None)
            self.initial["vat_number"] = profile.tax_number if profile else ""
        else:
            del self.fields["vat_number"]
        for field in self.fields.values():
            field.widget.attrs["class"] = "field__control"

    def save(self):
        entity = super().save()
        if "vat_number" in self.fields:
            OrganizationProfile.objects.update_or_create(
                entity=entity, defaults={"legal_name": entity.name, "tax_number": self.cleaned_data["vat_number"]})
        return entity


class NoteForm(forms.ModelForm):
    """The fields of the New Note overlay. The page comes from a hidden field.
    The view sets the company, the user and the date range."""

    class Meta:
        model = Note
        fields = ["page", "kind", "visibility", "title", "body", "expires_on", "is_permanent"]
        labels = {"kind": "Type", "body": "Description", "expires_on": "Expires on"}
        widgets = {
            "page": forms.HiddenInput(),
            "visibility": forms.RadioSelect(),
            "body": forms.Textarea(attrs={"rows": 6, "data-note-body": ""}),
            "expires_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "is_permanent": forms.CheckboxInput(attrs={"data-note-permanent": ""}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The Permanent switch disables the date, thus the browser does not send it.
        self.fields["expires_on"].required = False
        self.fields["expires_on"].widget.attrs["min"] = timezone.localdate().isoformat()
        for name in ("kind", "title", "body", "expires_on"):
            self.fields[name].widget.attrs["class"] = "field__control"

    def clean(self):
        data = super().clean()
        data["expires_on"] = data.get("expires_on") or in_one_month()
        if not data.get("is_permanent") and data["expires_on"] < timezone.localdate():
            self.add_error("expires_on", "The expiry date must be today or later.")
        return data
