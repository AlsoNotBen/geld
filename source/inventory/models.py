from django.db import models
from shared.models import *
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Case, DecimalField, F, Q, Sum, When
from django.utils import timezone
import uuid

class ItemType(models.TextChoices):
    ASSET      = "ASSET", "Asset"
    STOCK      = "STOCK", "Stock"
    CONSUMABLE = "CONSUMABLE", "Consumable"
    COMPONENT  = "COMPONENT", "Component"


class Manufacturer(CompanyOwned):
    name   = models.CharField(max_length=255)
    url    = models.URLField(max_length=512, blank=True)
    email  = models.EmailField(blank=True)
    phone  = models.CharField(max_length=100, blank=True)
    origin = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    logo   = models.ForeignKey("filestore.StoredFile", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "name"], name="unique_manufacturer_per_company")]

    def __str__(self):
        return self.name


class Category(CompanyOwned):
    name = models.CharField(max_length=255)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "name"], name="unique_category_per_company")]

    def __str__(self):
        return self.name


class Model(CompanyOwned):
    name            = models.CharField(max_length=255)
    number          = models.CharField(max_length=100, blank=True)
    generation      = models.PositiveIntegerField(null=True, blank=True)
    manufacturer    = models.ForeignKey(Manufacturer, on_delete=models.SET_NULL, null=True, blank=True)
    category        = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    cost            = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    alert_amount    = models.PositiveIntegerField(null=True, blank=True)
    lifespan_months = models.PositiveIntegerField(null=True, blank=True)  # set = depreciate
    active          = models.BooleanField(default=True)
    datasheets      = models.ManyToManyField("filestore.StoredFile", blank=True, related_name="+")
    thumbnail       = models.ForeignKey("filestore.StoredFile", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    def __str__(self):
        return self.name


class Item(CompanyOwned):
    model       = models.ForeignKey(Model, on_delete=models.PROTECT, related_name="items")
    item_type   = models.CharField(max_length=10, choices=ItemType.choices, default=ItemType.STOCK)
    sku         = models.CharField(max_length=100, blank=True)
    tag         = models.CharField(max_length=32, unique=True, null=True, blank=True)
    serial      = models.CharField(max_length=100, null=True, blank=True)
    cost        = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)
    active      = models.BooleanField(default=True)
    files       = models.ManyToManyField("filestore.StoredFile", blank=True, related_name="+")

    # Accounting. A tracked item has a value in the ledger: its cost posts to the
    # asset account (Inventory for stock, else a fixed asset account) when the item
    # is added (see inventory.views.post_opening_stock), a bill for the item debits
    # that account, and an invoice for the item credits it and debits Cost of Sales.
    # An untracked item is a record only. It needs no cost and it does not depreciate.
    tracked       = models.BooleanField(default=False)
    account       = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, null=True, blank=True,
                                      related_name="+")       # The asset account. Empty: "Inventory".
    opening_entry = models.ForeignKey("accounting.JournalEntry", on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name="+")       # The entry of the cost when the item was added.

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["company", "serial"], name="unique_item_serial_per_company"),
            # A tracked item needs a cost. The form checks this first (see ItemForm.clean).
            models.CheckConstraint(condition=Q(tracked=False) | Q(cost__isnull=False), name="tracked_item_has_cost"),
        ]

    def __str__(self):
        return self.name

    @property
    def name(self):
        return self.model.name

    @property
    def unit_cost(self):
        return self.cost if self.cost is not None else self.model.cost

    @property
    def is_stocked(self):
        """True for a type with a quantity on hand (stock, consumable, component)."""
        return self.item_type != ItemType.ASSET

    def group(self):
        """The items that the catalog of a document shows as one (see accounting.documents.catalog):
        the same type and the same code, or, without a code, the same type and model. The
        All items table groups the same way (see inventory.views.item_groups)."""
        same = Item.objects.filter(company_id=self.company_id, item_type=self.item_type)
        return same.filter(sku=self.sku) if self.sku else same.filter(sku="", model_id=self.model_id)

    @property
    def current_checkout(self):
        return self.checkouts.filter(checked_in_at__isnull=True).first()

    def save(self, *args, **kwargs):
        if self.item_type == ItemType.ASSET and not self.tag:
            self.tag = uuid.uuid4().hex
        super().save(*args, **kwargs)


# Need to check for cyclic relationships in the middleware (e.g "A is a component of A")
class ItemRelationship(models.Model):

    class RelationshipType(models.TextChoices):
        CONTAINS    = "CONTAINS", "Contains"
        REPLACES    = "REPLACEMENT", "Replacement"
        ACCESSORY   = "ACCESSORY", "Accessory"
        COMPATIBLE  = "COMPATIBLE", "Compatible"
        DEPENDENCY  = "DEPENDENCY", "Dependency"

    parent              = models.ForeignKey(Item,on_delete=models.PROTECT,related_name="child_relationships")
    child               = models.ForeignKey(Item,on_delete=models.PROTECT,related_name="parent_relationships")
    relationship_type   = models.CharField(max_length=30,choices=RelationshipType.choices)
    quantity            = models.DecimalField(max_digits=13,decimal_places=3,default=1,)

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

class StockMovement(CompanyOwned):
    class Method(models.TextChoices):
        FIFO    = "FIFO", "First in, first out"
        AVERAGE = "AVG", "Weighted average"

    class Direction(models.TextChoices):
        IN         = "IN", "In"
        OUT        = "OUT", "Out"
        ADJUSTMENT = "ADJ", "Adjustment"

    item          = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="movements")
    date          = models.DateField()
    direction     = models.CharField(max_length=3, choices=Direction.choices)
    quantity      = models.DecimalField(max_digits=12, decimal_places=4)
    unit_cost     = models.DecimalField(max_digits=13, decimal_places=4)
    total_cost    = models.DecimalField(max_digits=13, decimal_places=2)
    method        = models.CharField(max_length=4, choices=Method.choices, default=Method.AVERAGE)
    # The bill or the invoice that moved the stock (see accounting.posting.move_stock).
    # Empty: the opening stock of the item, or a manual movement.
    document      = models.ForeignKey("accounting.Document", on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name="stock_movements")

    class Meta:
        indexes = [models.Index(fields=["company", "item", "date"])]

def signed(field):
    """A field of a movement with its sign: an OUT takes stock away."""
    return Case(When(direction=StockMovement.Direction.OUT, then=-F(field)), default=F(field), output_field=DecimalField())


def stock_levels(company, **filters):
    """The quantity on hand and the value of each item, from the stock
    movements of the company. Returns {item_id: (quantity, value)}."""
    rows = (StockMovement.objects.filter(company=company, **filters).values("item_id")
            .annotate(quantity=Sum(signed("quantity")), value=Sum(signed("total_cost"))))
    return {row["item_id"]: (row["quantity"], row["value"]) for row in rows}


class Checkout(CompanyOwned, TimeStamped):
    item          = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="checkouts")
    entity        = models.ForeignKey(Entity, on_delete=models.PROTECT, null=True, blank=True, related_name="checkouts")
    location      = models.ForeignKey(Location, on_delete=models.PROTECT, null=True, blank=True, related_name="checkouts")
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(entity__isnull=False, location__isnull=True) | Q(entity__isnull=True, location__isnull=False),
                name="checkout_entity_xor_location",
            ),
            models.UniqueConstraint(
                fields=["item"],
                condition=Q(checked_in_at__isnull=True),
                name="one_open_checkout_per_item",
            ),
        ]

    def clean(self):
        if self.item.item_type == ItemType.STOCK:
            raise ValidationError("Stock items are not meant to be checked out")

    def check_in(self, user):
        self.checked_in_at = timezone.now()
        self.checked_in_by = user
        self.save(update_fields=["checked_in_at", "checked_in_by", "updated_at"])