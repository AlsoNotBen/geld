from django.contrib import admin
from inventory.models import Item, ItemRelationship, StockMovement

# Register your models here.
admin.site.register(Item)
admin.site.register(ItemRelationship)
admin.site.register(StockMovement)