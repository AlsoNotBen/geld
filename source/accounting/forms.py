import datetime
from decimal import Decimal, InvalidOperation
from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from accounting.models import (Account, BankAccount, Claim, Document, Entity, Note, NumberSequence, OrganizationProfile,
                               Payment, RecurringDocument, Service, in_one_month)
from accounting.posting import CLAIM_ACCOUNTS
from shared.models import Supplier
from shared.forms import AvatarField
from filestore.services import update_avatar
from documents.forms import SelectWithSearch


def _opening_fields():
    """The amount and the date of an opening balance. The amount can be negative (see
    post_opening_document and set_bank_opening). The view uses today when the date is empty."""
    return (forms.DecimalField(label="Opening balance", required=False, max_digits=13, decimal_places=2),
            forms.DateField(label="Opening balance date", required=False, initial=datetime.date.today,
                            widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")))


class PaymentForm(forms.ModelForm):
    """The fields of the Record Payment overlay. The view sets the company and the currency."""

    direction = forms.ChoiceField(label="Direction", choices=Payment.Direction.choices, initial=Payment.Direction.IN)

    class Meta:
        model = Payment
        fields = ["number", "date", "direction", "entity", "bank_account", "account", "amount", "reference"]
        labels = {"number": "Payment number", "entity": "Customer or supplier", "account": "Account"}
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
        # Empty: the control account pays the open invoices or bills (see posting.post_payment).
        self.fields["account"].queryset = Account.objects.filter(company=company, is_active=True).order_by("code")
        self.fields["account"].empty_label = "Default: Accounts Receivable / Payable"
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


class ClaimForm(forms.ModelForm):
    """The New Claim overlay: the claim (a Document with the Claim type, and its Claim) and its
    lines. The tabs of the overlay set the kind. The user must be a member of the company. The
    view sets the company, the employee of the user, and for an expense claim, the entity (the
    employee).

    Each line row sends line_key, line_reason, line_account and line_amount, and its files as
    line_files_<key>. clean() puts the lines in self.lines: [(reason, account, amount, uploads)]."""

    kind            = forms.ChoiceField(choices=Claim.Kind.choices, widget=forms.HiddenInput())
    user            = forms.ModelChoiceField(label="Employee", queryset=get_user_model().objects.none())
    control_account = forms.ModelChoiceField(label="Claim account", queryset=Account.objects.none(), empty_label="Select")

    class Meta:
        model = Document
        fields = ["kind", "number", "user", "date", "control_account", "entity"]
        labels = {"number": "Claim number", "entity": "Creditor"}
        widgets = {"date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, company=None, user=None, defaults=None, **kwargs):
        """defaults: the default claim account of each kind (see ClaimForm.defaults)."""
        kwargs.setdefault("auto_id", "claim_%s")      # The Record Payment overlay of the page has id_number etc.
        super().__init__(*args, **kwargs)
        self.company = company
        self.lines = []
        users = get_user_model().objects.filter(memberships__company=company).order_by("first_name", "username")
        self.fields["user"].queryset = users
        self.fields["user"].label_from_instance = lambda u: u.get_full_name() or u.get_username()
        self.fields["control_account"].queryset = Account.objects.filter(company=company, is_active=True).order_by("code")
        self.fields["entity"].required = False
        self.fields["entity"].queryset = Entity.objects.filter(company=company).order_by("name")
        self.fields["entity"].empty_label = "Select"
        if not self.is_bound:
            self.initial.update(number=NumberSequence.peek(company, "claim", "CLM-"), date=datetime.date.today(),
                                user=user, kind=Claim.Kind.EXPENSE,
                                control_account=(defaults or {}).get(Claim.Kind.EXPENSE))
        for field in self.fields.values():
            field.widget.attrs["class"] = "field__control"

    def clean_number(self):
        number = self.cleaned_data["number"]
        if Document.objects.filter(company=self.company, doc_type=Document.DocType.CLAIM, number=number).exists():
            raise forms.ValidationError("Another claim has this number.")
        return number

    def clean(self):
        data = super().clean()
        kind = data.get("kind")
        if kind == Claim.Kind.EXPENSE:
            data["entity"] = None
        elif not data.get("entity"):
            self.add_error("entity", "Select the insurer." if kind == Claim.Kind.INSURANCE else "Select the creditor.")
        self.clean_lines(data.get("control_account"))
        return data

    def clean_lines(self, control):
        """Read the line rows into self.lines. A row without a reason, an amount and files is ignored."""
        accounts = {str(a.pk): a for a in self.fields["control_account"].queryset}
        rows = zip(*(self.data.getlist(f"line_{name}") for name in ("key", "reason", "account", "amount")))
        for n, (key, reason, account, amount) in enumerate(rows, 1):
            reason, uploads = reason.strip(), self.files.getlist(f"line_files_{key}") if self.files else []
            if not (reason or amount.strip() or uploads):
                continue
            try:
                amount = Decimal(amount)
            except InvalidOperation:
                amount = None
            if not reason:
                self.add_error(None, f"Line {n}: give the reason.")
            elif account not in accounts:
                self.add_error(None, f"Line {n}: select the account.")
            elif amount is None or not amount.is_finite() or amount <= 0:
                self.add_error(None, f"Line {n}: the amount must be more than zero.")
            elif accounts[account] == control:
                self.add_error(None, f"Line {n}: select an account that is not the claim account.")
            else:
                self.lines.append((reason[:255], accounts[account], amount.quantize(Decimal("0.01")), uploads))
        if not self.lines and not self.errors:
            self.add_error(None, "Add a line with a reason, an account and an amount.")

    @staticmethod
    def defaults(company):
        """The default claim account of each kind of claim: {kind: account id} (see CLAIM_ACCOUNTS)."""
        ids = dict(Account.objects.filter(company=company, name__in=CLAIM_ACCOUNTS.values()).values_list("name", "id"))
        return {kind: ids.get(name) for kind, name in CLAIM_ACCOUNTS.items()}


class SupplierForm(forms.ModelForm):
    """The fields of the New Supplier and Edit Supplier pages. save() makes or
    changes the entity and its organization profile from the name, the email,
    the phone and the VAT number. An individual has no VAT number field."""

    name = forms.CharField(label="Name", max_length=255)
    email = forms.EmailField(label="Email", required=False)
    phone = forms.CharField(label="Phone", max_length=50, required=False, widget=forms.TelInput)
    vat_number = forms.CharField(label="VAT number", max_length=50, required=False)
    avatar = AvatarField()
    opening_balance, opening_date = _opening_fields()    # A new supplier only (see post_opening_document)

    field_order = ["avatar", "name", "code", "contact", "email", "phone", "vat_number", "terms", "bank_account",
                   "opening_balance", "opening_date"]

    class Meta:
        model = Supplier
        fields = ["code", "contact", "terms", "bank_account"]
        labels = {"contact": "Contact person", "terms": "Payment terms"}
        widgets = {"bank_account": forms.Textarea(attrs={"rows": 4, "maxlength": 255})}

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
        self.fields["avatar"].widget.attrs["class"] = "file-input"

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
        update_avatar(entity, data["avatar"], self.data.get("avatar_clear"), user, self.company)
        if entity.type == Entity.EntityType.ORGANIZATION:
            OrganizationProfile.objects.update_or_create(
                entity=entity, defaults={"legal_name": data["name"], "tax_number": data["vat_number"]})
        supplier.entity = entity
        supplier.company = self.company                     # Add to every function that creates a CompanyOwned record
        supplier.created_by = supplier.created_by or user
        supplier.save()
        return supplier


class BankAccountForm(forms.ModelForm):
    """The fields of the New Bank Account and Edit Bank Account pages. A new
    bank account gets a new ledger account below the parent account (see
    child_account). The parent account is a current asset or a floating
    account of the chart of accounts. The ledger account does not change
    after that, thus the Edit page only shows it. The view sets the company.
    The opening balance comes from the opening entry (see set_bank_opening).
    A negative opening balance is an overdraft."""

    parent = forms.ModelChoiceField(label="Parent account", queryset=Account.objects.none())
    opening_balance, opening_date = _opening_fields()

    field_order = ["bank", "name", "account_number", "sort_code", "iban", "currency", "parent", "account", "is_active"]

    class Meta:
        model = BankAccount
        fields = ["bank", "name", "account_number", "sort_code", "iban", "currency", "account", "is_active"]
        labels = {"name": "Account name", "sort_code": "Branch code", "iban": "IBAN", "account": "Ledger account",
                  "is_active": "Status"}
        help_texts = {"is_active": "Active"}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            del self.fields["parent"]
            self.fields["account"].queryset = Account.objects.filter(pk=self.instance.account_id)
            self.fields["account"].empty_label = None
            self.fields["account"].disabled = True
        else:
            del self.fields["account"]
            parents = Account.objects.filter(
                company=company, is_active=True,
                type__in=[Account.AccountType.CURRENT_ASSETS, Account.AccountType.FLOATING_NOMINAL],
            )
            self.fields["parent"].queryset = parents
            self.fields["parent"].empty_label = ("Select a parent account" if parents.exists()
                                                 else "No parent account. Add one in the Chart of Accounts.")
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
    avatar = AvatarField()

    field_order = ["avatar", "name", "email", "phone", "vat_number", "address", "is_active"]

    class Meta:
        model = Entity
        fields = ["name", "email", "phone", "address", "is_active"]
        labels = {"is_active": "Status"}
        help_texts = {"is_active": "Active"}
        widgets = {"address": forms.Textarea(attrs={"rows": 3}), "phone": forms.TelInput}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.type == Entity.EntityType.ORGANIZATION:
            profile = getattr(self.instance, "organization_profile", None)
            self.initial["vat_number"] = profile.tax_number if profile else ""
        else:
            del self.fields["vat_number"]
        for field in self.fields.values():
            field.widget.attrs["class"] = "field__control"
        self.fields["avatar"].widget.attrs["class"] = "file-input"

    def save(self, user=None):
        entity = super().save()
        update_avatar(entity, self.cleaned_data["avatar"], self.data.get("avatar_clear"), user, entity.company)
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


class ServiceForm(forms.ModelForm):
    """The fields of the New Service and Edit Service pages. The account is an
    income account: the invoice line of the service posts there. Empty: Sales.
    The view sets the company. The code must be unique in the company: the
    form has no company field, thus the model constraint does not check it."""

    class Meta:
        model = Service
        fields = ["code", "name", "description", "unit_price", "account", "active"]
        labels = {"unit_price": "Unit price", "account": "Income account", "active": "Status"}
        help_texts = {"unit_price": "The default price on an invoice or a quote. Empty: type it on the document.",
                      "active": "Active"}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        self.fields["account"].queryset = Account.objects.filter(
            company=company, is_active=True, type__in=[Account.AccountType.SALES, Account.AccountType.OTHER_INCOME])
        self.fields["account"].empty_label = "Sales (default)"
        if not self.is_bound and not self.instance.pk:
            self.initial["code"] = NumberSequence.peek(company, "service", "SVC-")
        for field in self.fields.values():
            field.widget.attrs["class"] = "field__control"

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if Service.objects.filter(company=self.company, code=code).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A service with this code already exists.")
        return code
