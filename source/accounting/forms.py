import datetime
from django import forms
from accounting.models import BankAccount, Entity, NumberSequence, Payment


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
