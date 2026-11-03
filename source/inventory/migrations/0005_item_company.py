import django.db.models.deletion
from django.db import migrations, models


def set_company(apps, schema_editor):
    """Give each existing item a company: the company of its first stock
    movement, else the first company. Before this migration each company
    saw all the items, thus the first company is only a best guess."""
    Item = apps.get_model("inventory", "Item")
    Company = apps.get_model("shared", "Company")
    StockMovement = apps.get_model("inventory", "StockMovement")
    items = Item.objects.filter(company__isnull=True)
    if not items.exists():
        return
    first = Company.objects.order_by("pk").first()
    if first is None:
        raise RuntimeError("Items exist, but no company exists. Add a company first, then migrate again.")
    for item in items:
        movement = StockMovement.objects.filter(item=item).order_by("date", "pk").first()
        item.company_id = movement.company_id if movement else first.pk
        item.save(update_fields=["company"])


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0004_stockmovement"),
        ("shared", "0010_alter_company_allocate_to_oldest"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="company",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name="%(class)ss", to="shared.company"),
        ),
        migrations.RunPython(set_company, migrations.RunPython.noop),
    ]
