"""
messaging/forms.py
------------------------------------------------------------------------
The form of the message overlay. The field names agree with the fields
of services.Message, thus Message(**form.cleaned_data) is possible.
"""

from django import forms
from django.core.validators import validate_email


class AddressListField(forms.Field):
    """Email addresses with a comma between them. Clean gives a list."""

    widget = forms.EmailInput(attrs={"multiple": True})

    def to_python(self, value):
        return [part.strip() for part in (value or "").split(",") if part.strip()]

    def validate(self, value):
        super().validate(value)
        for address in value:
            validate_email(address)


class MessageForm(forms.Form):
    to = AddressListField(label="To", help_text="Put a comma between two addresses.")
    cc = AddressListField(label="Cc", required=False)
    subject = forms.CharField(label="Subject", max_length=200)
    body = forms.CharField(
        label="Message",
        required=False,
        widget=forms.Textarea(attrs={"rows": 8}),
    )
