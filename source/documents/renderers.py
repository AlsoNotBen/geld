"""
documents/renderers.py
------------------------------------------------------------------------
One function turns a Django template into PDF bytes with WeasyPrint.

Keep the PDF templates self-contained: put the CSS in a <style> block,
and do not link external files. Then WeasyPrint does not fetch other
resources over HTTP while the server handles the request.
"""

from django.template.loader import render_to_string
from weasyprint import HTML


def render_pdf(template_name, context=None, base_url=None):
    """Render the template with the context. Return the PDF as bytes.

    Set base_url when the template refers to images or stylesheets with
    a relative URL. A self-contained template does not need it.
    """
    html = render_to_string(template_name, context or {})
    return HTML(string=html, base_url=base_url).write_pdf()
