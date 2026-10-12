import datetime
from django import forms
from django.utils import timezone
from accounting.models import BankAccount, Document, Entity, Note, NumberSequence, Payment, in_one_month


class PaymentForm(forms.ModelForm):
    """The fields of the Record Payment overlay. The view sets the company and the currency."""

    direction = forms.ChoiceField(label="Direction", choices=Payment.Direction.choices, initial=Payment.Direction.IN)

    class Meta:
        model = Payment
        fields = ["number", "date", "direction", "entity", "bank_account", "amount", "reference"]
        labels = {"number": "Payment number", "entity": "Customer or supplier"}
        widgets = {"date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

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
        self.fields["reference"].widget.attrs["placeholder"] = "Bank reference"
        if not self.is_bound:
            self.initial.update(number=NumberSequence.peek(company, "payment", "PAY-"),
                                date=datetime.date.today(), bank_account=first_bank)
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
    and it sets the company, the type, the status and the currency."""

    class Meta:
        model = Document
        fields = ["number", "entity", "date", "due", "notes"]
        labels = {"number": "Bill number", "entity": "Supplier", "due": "Due date"}
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "due": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.TextInput(),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        self.fields["entity"].queryset = Entity.objects.filter(company=company, is_active=True).order_by("name")
        if not self.is_bound:
            self.initial.update(number=NumberSequence.peek(company, "bill", "BILL-"), date=datetime.date.today())
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


class NoteForm(forms.ModelForm):
    """The fields of the New Note overlay. The page comes from a hidden field.
    The view sets the company, the user and the date range."""

    class Meta:
        model = Note
        fields = ["page", "kind", "title", "body", "expires_on", "is_permanent"]
        labels = {"kind": "Type", "body": "Description", "expires_on": "Expires on"}
        widgets = {
            "page": forms.HiddenInput(),
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
