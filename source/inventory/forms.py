from django import forms

from .models import Item


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            "sku", "name", "item_type", "serial", "description",
            "active", "depreciate", "lifespan", "lifeunits",
        ]

    def clean_serial(self):
        """A serial number is unique in the company of the item. The model
        constraint has the company, but the form has no company field, thus
        the form does not check the constraint itself."""
        serial = self.cleaned_data["serial"]
        if serial and (Item.objects.filter(company_id=self.instance.company_id, serial=serial)
                       .exclude(pk=self.instance.pk).exists()):
            raise forms.ValidationError("An item with this serial number already exists.")
        return serial
