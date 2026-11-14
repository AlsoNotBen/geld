from django import forms

from accounting.models import Account
from shared.models import Country
from .models import Category, Item, ItemType, Manufacturer, Model

# The account types of the asset account of a tracked item.
ASSET_TYPES = [Account.AccountType.CURRENT_ASSETS, Account.AccountType.NON_CURRENT_ASSETS]

# The most items that one save of the item editor makes.
MAX_COPIES = 500


class ItemForm(forms.ModelForm):
    """Changes an Item and its Model, or makes new items. The three tabs of
    the editor select a manufacturer, a model with its category, and the
    item fields. A new manufacturer, model or category is saved before this
    form (see item_entry in views.py), thus this form only selects them. The
    manufacturer and the category change the model, thus they change every
    item of that model.

    A new item has a quantity. A stocked item (stock, consumable or component)
    without serial numbers is one item: the quantity is its opening stock (see
    cleaned_data["opening_quantity"]). Otherwise the form makes that many
    items of the model, each with a quantity of one. With has_serials, each
    item gets one of the serial numbers in the "serials" fields, in order.

    A tracked item (see Item.tracked) needs a cost and an asset account.
    A blank cost takes the cost of the model. A blank account is Inventory."""

    manufacturer = forms.ModelChoiceField(queryset=Manufacturer.objects.none(), required=False)
    model        = forms.ModelChoiceField(queryset=Model.objects.none(),
                                          error_messages={"required": "Select a model, or add a new one."})
    category     = forms.ModelChoiceField(queryset=Category.objects.none(), required=False)
    quantity     = forms.IntegerField(min_value=1, required=False)     # Copies: not more than MAX_COPIES (see clean)
    has_serials  = forms.BooleanField(required=False)

    class Meta:
        model = Item
        fields = ["sku", "item_type", "tag", "serial", "cost", "description", "active", "tracked", "account"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company = self.instance.company_id
        self.fields["manufacturer"].queryset = Manufacturer.objects.filter(company=company).order_by("name")
        self.fields["model"].queryset = Model.objects.filter(company=company).order_by("name")
        self.fields["category"].queryset = Category.objects.filter(company=company).order_by("name")
        self.fields["account"].queryset = Account.objects.filter(company=company, is_active=True, type__in=ASSET_TYPES)
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
        if data.get("tracked"):
            model = data.get("model")
            if data.get("cost") is None and model and model.cost is not None:
                data["cost"] = model.cost
            if data.get("cost") is None:
                self.add_error("cost", "A tracked item needs a cost.")
        else:
            data["account"] = None
        if self.instance.pk:            # A change to one item.
            data["serials"] = [data.get("serial")]
            return data

        count = data.get("quantity") or 1
        if data.get("item_type") != ItemType.ASSET and not data.get("has_serials"):
            data["serials"], data["opening_quantity"] = [None], count       # One stock item with the full quantity
            return data
        data["opening_quantity"] = 1
        if count > MAX_COPIES:
            self.add_error("quantity", f"One save makes {MAX_COPIES} items or less. "
                                       "A stock item without serial numbers has no limit.")
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
        widgets = {"phone": forms.TelInput}

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
