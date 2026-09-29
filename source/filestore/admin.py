from django.contrib import admin

from .models import StoredFile


@admin.register(StoredFile)
class StoredFileAdmin(admin.ModelAdmin):
    list_display = ("original_name", "content_type", "size", "uploaded_by", "created_at")
    search_fields = ("original_name", "checksum")
    readonly_fields = ("file", "content_type", "size", "checksum", "uploaded_by", "created_at")