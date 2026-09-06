from django.db import models

class Entity(models.Model):
    name = models.CharField(max_length=255)
    # address, contact details, etc.


class EntityRole(models.Model):

    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        SUPPLIER = "SUPPLIER", "Supplier"

    Entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name="roles",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["Entity", "role"],
                name="unique_Entity_role",
            )
        ]