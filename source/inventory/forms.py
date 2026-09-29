from django import forms

from .models import Item


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            "sku", "name", "item_type", "serial", "description",
            "active", "depreciate", "lifespan", "lifeunits",
        ]