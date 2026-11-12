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


def validate(upload, extensions=ALLOWED_EXTENSIONS):
    ext = Path(upload.name).suffix.lower()
    if ext not in extensions:
        raise ValidationError(f"{upload.name}: the file type is not permitted.")
    if upload.size > MAX_SIZE:
        raise ValidationError(f"{upload.name}: the file is larger than {MAX_SIZE // 2**20} MB.")


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def validate_image(upload):
    """An avatar must be an image. SVG is not permitted: it can hold a script."""
    if Path(upload.name).suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValidationError(f"{upload.name}: the avatar must be a PNG, JPG, WEBP or GIF image.")
    validate(upload)


LOGO_EXTENSIONS = {".png", ".svg"}
LOGO_MAX_SIZE   = 2 * 1024 * 1024     # Each PDF holds a copy of the logo.


def validate_logo(upload):
    """A company logo must be a PNG or an SVG image. Only the PDF documents
    show it (see documents.renderers), thus no browser opens the SVG."""
    if Path(upload.name).suffix.lower() not in LOGO_EXTENSIONS:
        raise ValidationError(f"{upload.name}: the logo must be a PNG or SVG image.")
    if upload.size > LOGO_MAX_SIZE:
        raise ValidationError(f"{upload.name}: the logo is larger than {LOGO_MAX_SIZE // 2**20} MB.")


def set_avatar(owner, upload, user=None, company=None):
    """Store the image as the avatar of owner (a model with an "avatar" field
    to StoredFile), save owner, then delete the old image."""
    validate_image(upload)
    old = owner.avatar
    owner.avatar = save_upload(upload, user, company)
    owner.save(update_fields=["avatar"])
    if old:
        old.delete()


def clear_avatar(owner):
    """Remove the avatar of owner, and delete the image."""
    old = owner.avatar
    if old:
        owner.avatar = None
        owner.save(update_fields=["avatar"])
        old.delete()


def update_avatar(owner, upload, clear, user=None, company=None):
    """The avatar field of a form: a new image replaces the old one. Without
    an image, clear (the Remove button, see shared/_file_pick.html) removes it."""
    if upload:
        set_avatar(owner, upload, user, company)
    elif clear:
        clear_avatar(owner)


def save_upload(upload, user=None, company=None, extensions=ALLOWED_EXTENSIONS):
    """Validate and store an UploadedFile or ContentFile. Return the StoredFile.
    Only a member of the company can download the file (see views.download)."""
    validate(upload, extensions)

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
        company=company,
    )
    stored.file.save(name, upload, save=False)
    try:
        stored.save()
    except Exception:
        stored.file.delete(save=False)  # no orphan file if the row fails
        raise
    return stored