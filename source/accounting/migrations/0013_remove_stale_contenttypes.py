from django.db import migrations

# The models that 0012 removed from accounting. Their content types stay in the
# database, and the audit log rows that point to them break the Overview page.
# Deleting the content types also deletes those audit log rows (CASCADE).
REMOVED = ["lead", "supplier", "stockmovement", "budget", "budgetline", "costcentre", "attachment"]


def remove_stale(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="accounting", model__in=REMOVED).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0012_remove_attachment_accounting__content_f9470e_idx_and_more"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(remove_stale, migrations.RunPython.noop),
    ]
