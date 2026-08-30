"""
documents/views.py
------------------------------------------------------------------------
Three generic views serve every registered document type:

    panel     the overlay content (options form + preview frame)
    preview   the PDF, shown inline in the preview frame
    download  the same PDF, sent as a file download

The views take the options from the query string. Thus the preview
frame and the download link share one URL format, and the browser can
cache nothing stale: a new option value gives a new URL.
"""

from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET

from .registry import registry
from .renderers import render_pdf


def _get_document(module, key):
    document = registry.get(module, key)
    if document is None:
        raise Http404(f"No document type '{module}/{key}' is registered.")
    return document


def _resolve_options(document, request):
    """Return the clean options dict, or None when the input is bad.

    Without a query string the initial form values apply. That gives
    the first preview, before the user changes an option.
    """
    if not request.GET:
        return document.get_options_form().defaults()
    form = document.get_options_form(data=request.GET)
    if form.is_valid():
        return form.cleaned_data
    return None


@require_GET
def panel(request, module, key):
    """Return the overlay content. The frontend loads it with fetch()."""
    document = _get_document(module, key)
    return render(request, "documents/panel.html", {
        "document": document,
        "form": document.get_options_form(),
    })


@require_GET
@xframe_options_sameorigin
def preview(request, module, key):
    """Return the PDF for the preview frame.

    The decorator permits the frame on the same origin. Without it the
    clickjacking middleware blocks the PDF inside the <iframe>.
    """
    return _pdf_response(request, module, key, inline=True)


@require_GET
def download(request, module, key):
    """Return the PDF as a file download."""
    return _pdf_response(request, module, key, inline=False)


def _pdf_response(request, module, key, inline):
    document = _get_document(module, key)
    options = _resolve_options(document, request)
    if options is None:
        return HttpResponseBadRequest("One or more options are not valid.")
    context = document.get_context(request, options)
    pdf = render_pdf(document.template_name, context)
    disposition = "inline" if inline else "attachment"
    filename = document.get_filename(options)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    response["Cache-Control"] = "no-store"
    return response
