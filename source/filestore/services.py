"""Public API of the filestore. Other apps use only these functions."""
import hashlib
import mimetypes
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError

from .models import StoredFile

MAX_SIZE = getattr(settings, "FILESTORE_MAX_SIZE", 20 * 1024 * 1024)
ALLOWED_EXTENSIONS = getattr(settings, "FILESTORE_ALLOWED_EXTENSIONS", {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif",
    ".txt", ".csv", ".docx", ".xlsx",
})


def validate(upload):
    ext = Path(upload.name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"{upload.name}: the file type is not permitted.")
    if upload.size > MAX_SIZE:
        raise ValidationError(f"{upload.name}: the file is larger than {MAX_SIZE // 2**20} MB.")


def save_upload(upload, user=None):
    """Validate and store an UploadedFile or ContentFile. Return the StoredFile."""
    validate(upload)

    digest = hashlib.sha256()
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)

    name = Path(upload.name).name
    stored = StoredFile(
        original_name=name[:255],
        content_type=mimetypes.guess_type(name)[0] or "application/octet-stream",
        size=upload.size,
        checksum=digest.hexdigest(),
        uploaded_by=user if user and user.is_authenticated else None,
    )
    stored.file.save(name, upload, save=False)
    try:
        stored.save()
    except Exception:
        stored.file.delete(save=False)  # no orphan file if the row fails
        raise
    return stored