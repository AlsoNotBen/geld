import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import storages
from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone


def filestore_storage():
    # A callable keeps the backend out of migrations.
    # Change STORAGES["filestore"] in settings to move to S3.
    return storages["filestore"]


def upload_to(instance, filename):
    # Never use the user's file name in the path.
    return f"{timezone.now():%Y/%m}/{instance.pk}{Path(filename).suffix.lower()}"


class StoredFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to=upload_to, storage=filestore_storage, max_length=255)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveBigIntegerField()
    checksum = models.CharField(max_length=64, help_text="SHA-256")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_name


@receiver(post_delete, sender=StoredFile)
def remove_file(sender, instance, **kwargs):
    # Remove the file only after the database commit.
    storage, name = instance.file.storage, instance.file.name
    transaction.on_commit(lambda: storage.delete(name))