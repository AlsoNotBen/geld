import django.db.models.deletion
from django.db import migrations, models

# The models that link to a file, as (app, model). Each has a company and a "files" field.
OWNERS = [("accounting", "Document"), ("accounting", "Payment"), ("accounting", "Note"), ("inventory", "Item")]


def set_company(apps, schema_editor):
    """Give each existing file the company of the record that links to it.
    A file without a link keeps no company, thus nobody can download it."""
    StoredFile = apps.get_model("filestore", "StoredFile")
    for app, name in OWNERS:
        Owner = apps.get_model(app, name)
        for record in Owner.objects.prefetch_related("files"):
            ids = [f.pk for f in record.files.all()]
            StoredFile.objects.filter(pk__in=ids, company__isnull=True).update(company_id=record.company_id)


class Migration(migrations.Migration):

    dependencies = [
        ("filestore", "0001_initial"),
        ("shared", "0010_alter_company_allocate_to_oldest"),
        ("accounting", "0014_recurringdocument_bankaccount_opening_entry"),
        ("inventory", "0006_item_company_required"),
    ]

    operations = [
        migrations.AddField(
            model_name="storedfile",
            name="company",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name="+", to="shared.company"),
        ),
        migrations.RunPython(set_company, migrations.RunPython.noop),
    ]
