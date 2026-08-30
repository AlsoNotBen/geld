"""
documents/forms.py
------------------------------------------------------------------------
The base form with the render options, and two reusable widgets:

    SelectWithAddButton   a select with a small "+" button at its side
    LineItemsField        an editor for line items (add, remove, edit)

A module extends DocumentOptionsForm for each of its document types.
"""

import json
from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.html import format_html, format_html_join


PAPER_SIZES = [
    ("A4", "A4"),
    ("letter", "US Letter"),
]

hex_color = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Give the color as #RRGGBB.",
)


class SelectWithAddButton(forms.Select):
    """A select with an inline "+" button.

    The button carries a data-doc-action attribute. documents.js turns
    a click into one "doc:action" event on the document and does no
    more. Listen for the event to open your own overlay:

        document.addEventListener("doc:action", function (e) {
            if (e.detail.action === "new-customer") { ... }
        });
    """

    def __init__(self, attrs=None, choices=(), action="", button_label="Add"):
        super().__init__(attrs, choices)
        self.action = action
        self.button_label = button_label

    def render(self, name, value, attrs=None, renderer=None):
        select = super().render(name, value, attrs, renderer)
        return format_html(
            '<span class="doc-inline">{}'
            '<button type="button" class="doc-inline__add" data-doc-action="{}"'
            ' title="{}" aria-label="{}">+</button></span>',
            select, self.action, self.button_label, self.button_label,
        )


def _line_row(row):
    """Return the HTML of one line item row.

    documents.js builds the same structure for a new row. Keep the two
    in step. The row inputs have no name attribute, thus only the JSON
    of the hidden input travels in the query string.
    """
    return format_html(
        '<div class="doc-lines__row" data-doc-line>'
        '<input type="text" data-line-field="description" value="{}"'
        ' placeholder="Description" aria-label="Description">'
        '<input type="hidden" data-line-field="unit" value="{}">'
        '<input type="number" data-line-field="quantity" value="{}"'
        ' min="0" step="any" aria-label="Quantity">'
        '<input type="number" data-line-field="unit_price" value="{}"'
        ' min="0" step="0.01" aria-label="Unit price">'
        '<button type="button" class="doc-lines__remove" data-line-remove'
        ' aria-label="Remove the line">&times;</button>'
        '</div>',
        row.get("description", ""), row.get("unit", ""),
        row.get("quantity", ""), row.get("unit_price", ""),
    )


class LineItemsWidget(forms.Widget):
    """The editor for line items.

    The widget shows one row per item, a catalog select that adds a
    predefined item, and a button that adds a free custom line. Each
    part of a row stays editable: description, quantity and unit price.
    documents.js keeps a hidden JSON input in step with the rows.
    """

    catalog = []

    def render(self, name, value, attrs=None, renderer=None):
        rows = value or []
        if isinstance(rows, str):
            try:
                rows = json.loads(rows)
            except ValueError:
                rows = []

        rows_html = format_html_join("", "{}", ((_line_row(row),) for row in rows))
        catalog_html = format_html_join(
            "",
            '<option value="{}" data-description="{}" data-unit="{}" data-price="{}">{}</option>',
            (
                (str(index), item["description"], item.get("unit", ""),
                 item.get("unit_price", ""), item["description"])
                for index, item in enumerate(self.catalog)
            ),
        )

        return format_html(
            '<div class="doc-lines" data-doc-lines>'
            '<input type="hidden" name="{}" value="{}">'
            '<div class="doc-lines__rows" data-doc-lines-rows>{}</div>'
            '<div class="doc-lines__add">'
            '<select data-line-catalog aria-label="Catalog item">'
            '<option value="">Add from the catalog&hellip;</option>{}</select>'
            '<button type="button" class="doc-inline__add" data-line-add-catalog'
            ' title="Add the catalog item" aria-label="Add the catalog item">+</button>'
            '</div>'
            '<button type="button" class="doc-lines__custom" data-line-add-custom>'
            '+ Add a custom line</button>'
            '</div>',
            name, json.dumps(rows, default=str), rows_html, catalog_html,
        )


class LineItemsField(forms.JSONField):
    """Line items as one JSON value.

    The clean method returns a list of dicts with these keys:
    description (str), unit (str), quantity (Decimal) and unit_price
    (Decimal). A row without a description does not count.
    """

    widget = LineItemsWidget

    def __init__(self, *, catalog=None, **kwargs):
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)
        self.widget.catalog = list(catalog or [])

    def clean(self, value):
        rows = super().clean(value) or []
        if not isinstance(rows, list):
            raise ValidationError("The line items must be a list.")
        lines = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValidationError("Each line item must be an object.")
            description = str(row.get("description", "")).strip()
            if not description:
                continue
            try:
                quantity = Decimal(str(row.get("quantity") or "0"))
                unit_price = Decimal(str(row.get("unit_price") or "0"))
            except InvalidOperation:
                raise ValidationError("A quantity or a unit price is not a number.")
            if not (quantity.is_finite() and unit_price.is_finite()):
                raise ValidationError("A quantity or a unit price is not a number.")
            if quantity < 0 or unit_price < 0:
                raise ValidationError("A quantity or a unit price is below zero.")
            lines.append({
                "description": description[:200],
                "unit": str(row.get("unit", ""))[:24],
                "quantity": quantity,
                "unit_price": unit_price,
            })
        return lines


class DocumentOptionsForm(forms.Form):
    """Options that apply to every PDF document.

    The fields in customize_field_names go into the folded "Customize"
    section of the panel. All other fields stay in the main section.
    Extend the tuple in a subclass when more fields belong there.

    The panel view reads the initial values for the first preview.
    Thus give each field an initial value, also in a subclass.
    """

    customize_field_names = (
        "paper_size", "accent_color", "company_name", "company_details",
    )

    paper_size = forms.ChoiceField(
        label="Paper size",
        choices=PAPER_SIZES,
        initial="A4",
    )
    accent_color = forms.CharField(
        label="Accent color",
        initial="#F0BE72",
        validators=[hex_color],
        widget=forms.TextInput(attrs={"type": "color"}),
    )
    company_name = forms.CharField(
        label="Company name",
        initial="Pothos ERM Suite",
        max_length=80,
    )
    company_details = forms.CharField(
        label="Company details",
        required=False,
        initial="12 Fynbos Lane\n8001 Cape Town\nVAT 4550 123 456",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def main_fields(self):
        """Return the bound fields of the main section, in form order."""
        return [f for f in self if f.name not in self.customize_field_names]

    def customize_fields(self):
        """Return the bound fields of the Customize section."""
        return [self[name] for name in self.customize_field_names
                if name in self.fields]

    def defaults(self):
        """Return the clean initial value of each field.

        The method evaluates a callable initial value, and runs the
        clean method of each field. Thus the first preview gets values
        of the same types as a bound form gives.
        """
        data = {}
        for name, field in self.fields.items():
            value = field.initial() if callable(field.initial) else field.initial
            data[name] = field.clean(value)
        return data
