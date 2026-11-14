"""
documents/views.py
------------------------------------------------------------------------
Four generic views serve every registered document type:

    panel     the overlay content (options form + preview frame)
    preview   the PDF, shown inline in the preview frame
    download  the same PDF, sent as a file download
    save      the Save button: it issues the document without a PDF

One more view serves the Print button of each page:

    print_page  a greyscale PDF of the headings and the tables of a page,
                or of more pages in one PDF with a cover page

The views take the options from the query string. Thus the preview
frame and the download link share one URL format, and the browser can
cache nothing stale: a new option value gives a new URL. The save view
takes the options from the POST data.
"""

from copy import copy

from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse, QueryDict
from django.shortcuts import render
from django.urls import Resolver404, resolve
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET, require_POST
from .printing import build_report
from .registry import registry
from .renderers import logo_data_uri, render_pdf


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
        return document.get_options_form(request=request).defaults()
    form = document.get_options_form(data=request.GET, request=request)
    if form.is_valid():
        return form.cleaned_data
    return None


@require_GET
def panel(request, module, key):
    """Return the overlay content. The frontend loads it with fetch()."""
    document = _get_document(module, key)
    return render(request, "documents/panel.html", {
        "document": document,
        "form": document.get_options_form(request=request),
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


@require_POST
def save(request, module, key):
    """Issue the document, as a download does, but make no PDF. E.g. an
    invoice gets its number and its journal entry. documents.js sends
    the options form and reads the JSON answer: saved, or the errors."""
    document = _get_document(module, key)
    form = document.get_options_form(data=request.POST, request=request)
    if form.is_valid():
        try:
            document.issue(request, form.cleaned_data)
            return JsonResponse({"saved": True})
        except ValidationError as error:
            form.add_error(None, error)
    errors = [f"{form.fields[name].label}: {message}" if name in form.fields else message
              for name, messages in form.errors.items() for message in messages]
    return JsonResponse({"errors": errors}, status=400)


def _pdf_response(request, module, key, inline):
    document = _get_document(module, key)
    options = _resolve_options(document, request)

    if options is None:
        return HttpResponseBadRequest("One or more options are not valid.")

    if not inline:  # Download and Send use the download view. The preview does not issue.
        try:
            document.issue(request, options)
        except ValidationError as error:    # E.g. an invoice without a customer
            return HttpResponseBadRequest(" ".join(error.messages))

    context     = document.get_context(request, options)
    context["company_logo"] = logo_data_uri(getattr(request, "company", None))
    pdf         = render_pdf(document.template_name, context)
    disposition = "inline" if inline else "attachment"
    filename    = document.get_filename(options)
    response    = HttpResponse(pdf, content_type="application/pdf")

    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    response["Cache-Control"]       = "no-store"
    
    return response


class _NoPrint(Exception):
    """A page that cannot print. The message tells the user why."""


@require_GET
def print_page(request):
    """The Print button of a page (documents.js). The query string gives
    the path of the page: ?url=/accounting/journals/?journal=sales

    The view renders that page again with the same user, company and
    date range (the cookie), thus the report shows what the page shows.
    The page view does its own access checks. The answer is the PDF,
    inline, thus the browser shows it and the user prints it.

    More than one url gives one PDF with a cover page and a part for
    each page, e.g. the Full Financial Statement of the Reports page.
    The title parameter gives the title of the cover page."""
    urls = request.GET.getlist("url")
    if not urls:
        return HttpResponseBadRequest("Give the path of a page.")
    try:
        parts = [_page_report(request, url) for url in urls]
    except _NoPrint as error:
        return HttpResponseBadRequest(str(error))

    company = getattr(request, "company", None)
    context = {"company": company.name if company else "", "printed": timezone.localdate()}
    if len(parts) == 1:
        context.update(parts[0])
        pdf = render_pdf("documents/report_pdf.html", context)
    else:
        context.update(
            title=request.GET.get("title") or "Report",
            period=next((part["period"] for part in parts if part["period"]), ""),
            parts=parts,
            company_logo=logo_data_uri(company),
        )
        pdf = render_pdf("documents/bundle_pdf.html", context)

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{slugify(context["title"]) or "report"}.pdf"'
    response["Cache-Control"]       = "no-store"
    return response


def _page_report(request, url):
    """Render the page at url again for this request. Return its report
    (see printing.build_report). Raise _NoPrint when it cannot print."""
    if not url.startswith("/") or url.startswith("//"):
        raise _NoPrint("Give the path of a page.")
    path, _, query = url.partition("?")
    try:
        match = resolve(path)
    except Resolver404:
        raise Http404("No page has this path.")
    if match.func is print_page:
        raise _NoPrint("This page cannot print itself.")

    page = copy(request)
    page.path = page.path_info = path
    page.META = {**request.META, "PATH_INFO": path, "QUERY_STRING": query}
    page.GET = QueryDict(query)
    page.resolver_match = match

    response = match.func(page, *match.args, **match.kwargs)
    if hasattr(response, "render"):
        response.render()
    if response.status_code != 200 or "text/html" not in response.get("Content-Type", ""):
        raise _NoPrint("This page has nothing to print.")
    return build_report(response.content.decode(response.charset))
