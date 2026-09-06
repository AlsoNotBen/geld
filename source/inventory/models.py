from django.db import models

# Generic class for Inventory. Specific types are determined by their relation
class Item(models.Model):

    class ItemType(models.TextChoices):
        ASSET       = "ASSET", "Asset"
        STOCK       = "STOCK", "Stock"
        CONSUMABLE  = "CONSUMABLE", "Consumable"
        COMPONENT   = "COMPONENT", "Component"

    code        = models.CharField(max_length=100, unique=True)
    name        = models.CharField(max_length=255)
    item_type   = models.CharField(choices=ItemType.choices)
    description = models.TextField(blank=True)
    active      = models.BooleanField(default=True)

# Need to check for cyclic relationships in the middleware (e.g "A is a component of A")
class ItemRelationship(models.Model):

    class RelationshipType(models.TextChoices):
        CONTAINS    = "CONTAINS", "Contains"
        REPLACEMENT = "REPLACEMENT", "Replacement"
        ACCESSORY   = "ACCESSORY", "Accessory"
        COMPATIBLE  = "COMPATIBLE", "Compatible"
        DEPENDENCY  = "DEPENDENCY", "Dependency"

    parent = models.ForeignKey(Item,on_delete=models.PROTECT,related_name="child_relationships")
    child = models.ForeignKey(Item,on_delete=models.PROTECT,related_name="parent_relationships")
    relationship_type = models.CharField(max_length=30,choices=RelationshipType.choices)
    quantity = models.DecimalField(max_digits=13,decimal_places=3,default=1,)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "parent",
                    "child",
                    "relationship_type",
                ],
                name="unique_item_relationship",
            ),
        ]