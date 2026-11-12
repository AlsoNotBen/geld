"""
documents/renderers.py
------------------------------------------------------------------------
One function turns a Django template into PDF bytes with WeasyPrint.

Keep the PDF templates self-contained: put the CSS in a <style> block,
and do not link external files. Then WeasyPrint does not fetch other
resources over HTTP while the server handles the request.
"""

import base64

from django.template.loader import render_to_string
from weasyprint import HTML
from weasyprint.urls import URLFetcher


def logo_data_uri(company):
    """Return the logo of the company as a data: URI, or "". The PDF then
    holds the image, and WeasyPrint does not fetch it over HTTP."""
    if not company or not company.logo:
        return ""
    with company.logo.file.open("rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return f"data:{company.logo.content_type};base64,{data}"


# Fetch only data: URIs. An SVG logo can refer to other URLs (file:, http:);
# this stops WeasyPrint from fetching them.
_data_only = URLFetcher(allowed_protocols={"data"})


def render_pdf(template_name, context=None):
    """Render the template with the context. Return the PDF as bytes.
    The template must be self-contained: only data: URIs load."""
    html = render_to_string(template_name, context or {})
    return HTML(string=html, url_fetcher=_data_only).write_pdf()
