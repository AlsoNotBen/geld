import django.db.models.deletion
from django.db import migrations, models


# A separate migration: PostgreSQL does not alter a table in the same
# transaction as the data update of 0005 ("pending trigger events").
class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0005_item_company"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="company",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                    related_name="%(class)ss", to="shared.company"),
        ),
        migrations.AlterField(
            model_name="item",
            name="serial",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddConstraint(
            model_name="item",
            constraint=models.UniqueConstraint(fields=("company", "serial"), name="unique_item_serial_per_company"),
        ),
    ]
