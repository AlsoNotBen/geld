from django.db import models
import uuid

# Generic class for Inventory. Specific types are determined by their relation
class Item(models.Model):

    class ItemType(models.TextChoices):
        ASSET       = "ASSET", "Asset"
        STOCK       = "STOCK", "Stock"
        CONSUMABLE  = "CONSUMABLE", "Consumable"
        COMPONENT   = "COMPONENT", "Component"

    class LifeUnits(models.TextChoices):
        YEARS       = "Y","Years"
        MONTHS      = "M","Months"
        DAYS        = "D","Days"

    sku         = models.CharField(max_length=100,null=True,blank=True)               # user defined labelling structure
    tag         = models.CharField(max_length=32,unique=True,null=True,blank=True)
    serial      = models.CharField(max_length=100,unique=True,null=True,blank=True)
    name        = models.CharField(max_length=255)
    cost        = models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True)
    depreciate  = models.BooleanField(default=False)
    lifespan    = models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True)
    lifeunits   = models.CharField(choices=LifeUnits.choices,null=True,blank=True)
    item_type   = models.CharField(choices=ItemType.choices)    # default should be "STOCK"
    description = models.TextField(null=True,blank=True)
    obsoleted   = models.BooleanField(default=False)
    active      = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if (self.item_type == self.ItemType.ASSET and not self.tag):
            self.tag = uuid.uuid4().hex
        else:
            super().save(*args, **kwargs)


# Need to check for cyclic relationships in the middleware (e.g "A is a component of A")
class ItemRelationship(models.Model):

    class RelationshipType(models.TextChoices):
        CONTAINS    = "CONTAINS", "Contains"
        REPLACES    = "REPLACEMENT", "Replacement"
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

class StockTakeSchedule(models.Model):
    item            = models.OneToOneField(Item,on_delete=models.CASCADE,related_name="stock_take_schedule")
    interval_days   = models.PositiveIntegerField(default=30)
    start_date      = models.DateField()
    next_due        = models.DateField()
    active          = models.BooleanField(default=True)