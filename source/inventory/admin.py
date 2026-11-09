from django.contrib import admin
from inventory.models import (
    Category, Checkout, Item, ItemRelationship, Manufacturer, Model, StockMovement,
)

admin.site.register(Manufacturer)
admin.site.register(Category)
admin.site.register(Model)
admin.site.register(Item)
admin.site.register(ItemRelationship)
admin.site.register(StockMovement)
admin.site.register(Checkout)
