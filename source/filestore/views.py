from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404

from .models import StoredFile


@login_required
def download(request, pk):
    """GET /files/<id>/ downloads. GET /files/<id>/?inline shows it in the browser."""
    stored = get_object_or_404(StoredFile, pk=pk)
    return FileResponse(
        stored.file.open("rb"),
        as_attachment="inline" not in request.GET,
        filename=stored.original_name,
    )