"""
documents/registry.py
------------------------------------------------------------------------
The registry connects a (module, key) pair to a document type.

A module declares its document types in a file with the name
"documents.py", in its own package. The documents app imports these
files at start (see apps.py). Example:

    # accounting/documents.py
    from documents.registry import DocumentType, register

    @register
    class InvoiceDocument(DocumentType):
        module = "accounting"
        key = "invoice"
        ...

The generic views then serve the document at these paths:

    /documents/<module>/<key>/panel/          overlay content
    /documents/<module>/<key>/preview.pdf     PDF for the preview frame
    /documents/<module>/<key>/download.pdf    PDF as a download
"""

from .forms import DocumentOptionsForm


class DocumentType:
    """One kind of PDF document that a module can produce.

    A subclass must set module, key, label and template_name. The other
    attributes and methods have safe defaults. Override get_context to
    give data to the template.
    """

    #: The app label of the owner. It is the first part of the URL.
    module = ""

    #: A short slug for this document. It is the second part of the URL.
    key = ""

    #: The name that the overlay shows.
    label = ""

    #: One short sentence about the document. The overlay shows it.
    description = ""

    #: The template that the renderer turns into a PDF.
    template_name = ""

    #: The form with the render options. Subclass DocumentOptionsForm
    #: to add fields for your document.
    options_form_class = DocumentOptionsForm

    def get_options_form(self, data=None):
        """Return the options form. Bind it to data when data is given."""
        return self.options_form_class(data=data)

    def get_context(self, request, options):
        """Return the template context. Override this in a subclass.

        The argument "options" is a dict with the clean form values.
        Always keep it in the context, because the base PDF template
        reads the paper size and the accent color from it.
        """
        return {"options": options}

    def get_filename(self, options):
        """Return the file name for the download."""
        return f"{self.module}-{self.key}.pdf"


class DocumentRegistry:
    """A small container. It maps (module, key) to a DocumentType."""

    def __init__(self):
        self._types = {}

    def register(self, document_class):
        """Add a DocumentType subclass. Use this as a decorator."""
        instance = document_class()
        if not instance.module or not instance.key:
            raise ValueError(
                f"{document_class.__name__} must set 'module' and 'key'."
            )
        self._types[(instance.module, instance.key)] = instance
        return document_class

    def get(self, module, key):
        """Return the document type, or None when it is not known."""
        return self._types.get((module, key))

    def for_module(self, module):
        """Return all document types of one module."""
        return [d for (m, _), d in self._types.items() if m == module]

    def all(self):
        return list(self._types.values())


registry = DocumentRegistry()
register = registry.register
