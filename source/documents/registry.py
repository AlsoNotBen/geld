"""
documents/registry.py
------------------------------------------------------------------------
The registry connects a (module, key) pair to a document type.

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

    module              = ""
    key                 = ""
    label               = ""
    description         = ""
    template_name       = ""
    options_form_class  = DocumentOptionsForm

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
