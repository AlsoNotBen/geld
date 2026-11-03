from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from .models import StoredFile


@login_required
def download(request, pk):
    """GET /files/<id>/ downloads. GET /files/<id>/?inline shows it in the browser.
    The file must belong to the current company of the user."""
    if request.company is None:     # company=None would match the files without a company
        raise Http404("No company is selected.")
    stored = get_object_or_404(StoredFile, pk=pk, company=request.company)
    return FileResponse(
        stored.file.open("rb"),
        as_attachment="inline" not in request.GET,
        filename=stored.original_name,
    )