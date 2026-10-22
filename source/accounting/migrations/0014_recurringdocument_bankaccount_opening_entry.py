import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """RecurringInvoice becomes RecurringDocument: one table for each document type
    that recurs. The customer goes, because the template document has the entity.
    A bank account keeps the entry of its opening balance."""

    dependencies = [
        ("accounting", "0013_remove_stale_contenttypes"),
    ]

    operations = [
        migrations.RenameModel(old_name="RecurringInvoice", new_name="RecurringDocument"),
        migrations.RemoveField(model_name="recurringdocument", name="customer"),
        migrations.AddField(
            model_name="bankaccount",
            name="opening_entry",
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="+", to="accounting.journalentry",
            ),
        ),
    ]
