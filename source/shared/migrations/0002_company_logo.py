import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("filestore", "0001_initial"),
        ("shared", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="logo",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name="+", to="filestore.storedfile"),
        ),
    ]
