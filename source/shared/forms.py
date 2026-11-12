import datetime

from django import forms
from django.utils import timezone
from django.utils.text import slugify

from filestore.services import validate_image, validate_logo

from .models import Company, Currency


class AvatarField(forms.FileField):
    """An optional image. The form stores it with filestore.services.set_avatar."""

    def __init__(self, **kwargs):
        kwargs.setdefault("label", "Avatar")
        kwargs.setdefault("required", False)
        kwargs.setdefault("widget", forms.FileInput(attrs={"accept": ".png,.jpg,.jpeg,.webp,.gif", "class": "file-input"}))
        super().__init__(**kwargs)

    def clean(self, data, initial=None):
        upload = super().clean(data, initial)
        if upload:
            validate_image(upload)
        return upload


class LogoField(forms.FileField):
    """An optional company logo: a PNG or an SVG image."""

    def __init__(self, **kwargs):
        kwargs.setdefault("label", "Logo")
        kwargs.setdefault("required", False)
        kwargs.setdefault("help_text", "A PNG or SVG image. It shows on the documents (invoices, quotes, statements).")
        kwargs.setdefault("widget", forms.FileInput(attrs={"accept": ".png,.svg,image/png,image/svg+xml", "class": "file-input"}))
        super().__init__(**kwargs)

    def clean(self, data, initial=None):
        upload = super().clean(data, initial)
        if upload:
            validate_logo(upload)
        return upload


def current_year_start():
    """1 March of the financial year that includes today, as in seed.sql."""
    today = timezone.localdate()
    return datetime.date(today.year if today.month >= 3 else today.year - 1, 3, 1)


class CompanyForm(forms.ModelForm):
    """The fields of the Add New Company overlay. The slug comes from the name
    (see save). The view gives the financial year start to seed_company."""

    fiscal_year_start = forms.DateField(
        label="Financial year starting date",
        initial=current_year_start,
        help_text="The financial year runs for one year from this date, in 12 periods of one month.",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    logo = LogoField()  # The view stores the file (see shared.views.company_create).

    class Meta:
        model = Company
        fields = ["name", "tax_number", "base_currency", "accounting_basis", "fiscal_year_start", "address"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["base_currency"].queryset = Currency.objects.order_by("alpha_code")
        self.fields["base_currency"].label_from_instance = lambda c: f"{c.alpha_code} · {c.name}"
        self.fields["address"].help_text = ""

    def save(self, commit=True):
        """Give the company a unique slug. A second "Acme" gets "acme-2"."""
        company = super().save(commit=False)
        base = slugify(company.name)[:40] or "company"
        slug, number = base, 1
        while Company.objects.filter(slug=slug).exists():
            number += 1
            slug = f"{base}-{number}"
        company.slug = slug
        if commit:
            company.save()
        return company
