from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shared", "0009_supplier"),
    ]

    operations = [
        migrations.AlterField(
            model_name="company",
            name="allocate_to_oldest",
            field=models.BooleanField(
                default=True, verbose_name="Allocate unreferenced to oldest invoices"
            ),
        ),
    ]
