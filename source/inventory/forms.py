from django import forms

from shared.models import Country
from .models import Category, Item, Manufacturer, Model

# The most items that one save of the item editor makes.
MAX_COPIES = 500


class ItemForm(forms.ModelForm):
    """Changes an Item and its Model, or makes new items. The three tabs of
    the editor select a manufacturer, a model with its category, and the
    item fields. A new manufacturer, model or category is saved before this
    form (see item_entry in views.py), thus this form only selects them. The
    manufacturer and the category change the model, thus they change every
    item of that model.

    A new item has a quantity: the form makes that many items of the model.
    With has_serials, each item gets one of the serial numbers in the
    "serials" fields, in order."""

    manufacturer = forms.ModelChoiceField(queryset=Manufacturer.objects.none(), required=False)
    model        = forms.ModelChoiceField(queryset=Model.objects.none(),
                                          error_messages={"required": "Select a model, or add a new one."})
    category     = forms.ModelChoiceField(queryset=Category.objects.none(), required=False)
    quantity     = forms.IntegerField(min_value=1, max_value=MAX_COPIES, required=False)
    has_serials  = forms.BooleanField(required=False)

    class Meta:
        model = Item
        fields = ["sku", "item_type", "tag", "serial", "cost", "description", "active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company = self.instance.company_id
        self.fields["manufacturer"].queryset = Manufacturer.objects.filter(company=company).order_by("name")
        self.fields["model"].queryset = Model.objects.filter(company=company).order_by("name")
        self.fields["category"].queryset = Category.objects.filter(company=company).order_by("name")
        if self.instance.model_id:
            m = self.instance.model
            self.initial.update({"model": m.pk, "manufacturer": m.manufacturer_id, "category": m.category_id})

    def clean_serial(self):
        """A serial number is unique in the company of the item. The model
        constraint has the company, but the form has no company field, thus
        the form does not check the constraint itself."""
        serial = self.cleaned_data["serial"] or None
        if serial and (Item.objects.filter(company_id=self.instance.company_id, serial=serial)
                       .exclude(pk=self.instance.pk).exists()):
            raise forms.ValidationError("An item with this serial number already exists.")
        return serial

    def clean(self):
        data = super().clean()
        if self.instance.pk:            # A change to one item.
            data["serials"] = [data.get("serial")]
            return data

        count = data.get("quantity") or 1
        if count > 1 and data.get("tag"):
            self.add_error("tag", "A tag is unique. Leave it blank to make more than one item.")
        serials = [None] * count
        if data.get("has_serials"):
            given = [s.strip() for s in self.data.getlist("serials")]
            used = (Item.objects.filter(company_id=self.instance.company_id, serial__in=given)
                    .values_list("serial", flat=True))
            if len(given) != count or not all(given):
                self.add_error(None, f"Give a serial number for each of the {count} items.")
            elif len(set(given)) != count:
                self.add_error(None, "Each serial number must be different.")
            elif used:
                self.add_error(None, "These serial numbers already exist: " + ", ".join(used) + ".")
            else:
                serials = given
        data["serials"] = serials
        return data

    def save(self):
        """Save the model, then the item, or the new items. Returns the items."""
        model = self.cleaned_data["model"]
        model.manufacturer, model.category = self.cleaned_data["manufacturer"], self.cleaned_data["category"]
        model.save()
        self.instance.model = model
        if self.instance.pk:
            return [super().save()]
        base = super().save(commit=False)
        values = {f.attname: getattr(base, f.attname) for f in Item._meta.concrete_fields if not f.primary_key}
        return [Item.objects.create(**{**values, "serial": serial}) for serial in self.cleaned_data["serials"]]


class EntryForm(forms.ModelForm):
    """A new record of the company, made with the "+" of the item editor.
    The instance carries the company. The name must be unique in the
    company: the form has no company field, thus the model constraint does
    not check it."""

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if type(self.instance).objects.filter(company_id=self.instance.company_id, name__iexact=name).exists():
            raise forms.ValidationError(f"{name} already exists. Select it in the list.")
        return name


class ManufacturerForm(EntryForm):
    class Meta:
        model = Manufacturer
        fields = ["name", "url", "email", "phone", "origin"]
        labels = {"url": "Website", "origin": "Country of origin"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["origin"].queryset = Country.objects.all()


class CategoryForm(EntryForm):
    class Meta:
        model = Category
        fields = ["name"]


class ModelEntryForm(EntryForm):
    depreciate = forms.BooleanField(required=False)

    class Meta:
        model = Model
        fields = ["name", "number", "generation", "cost", "alert_amount", "lifespan_months", "active",
                  "manufacturer", "category"]
        labels = {"number": "Part number", "generation": "Version number", "alert_amount": "Alert amount",
                  "lifespan_months": "Useful life"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company = self.instance.company_id
        self.fields["manufacturer"].queryset = Manufacturer.objects.filter(company=company)
        self.fields["category"].queryset = Category.objects.filter(company=company)

    def clean(self):
        data = super().clean()
        if not data.get("depreciate"):
            data["lifespan_months"] = None
        elif not data.get("lifespan_months"):
            self.add_error("lifespan_months", "A depreciating model needs a useful life.")
        return data
