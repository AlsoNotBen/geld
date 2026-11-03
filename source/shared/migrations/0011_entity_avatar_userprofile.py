import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("filestore", "0002_storedfile_company"),
        ("shared", "0010_alter_company_allocate_to_oldest"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="entity",
            name="avatar",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="+", to="filestore.storedfile",
            ),
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("avatar", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="+", to="filestore.storedfile",
                )),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE, related_name="profile",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
