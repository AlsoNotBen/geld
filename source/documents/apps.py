from django.apps import AppConfig
from django.utils.module_loading import autodiscover_modules


class DocumentsConfig(AppConfig):
    name = 'documents'
    verbose_name = 'Documents'

    def ready(self):
        # Find a file with the name "documents.py" in each installed app.
        # Import each file that exists. The import runs the register calls
        # of the module. Thus each module declares its own document types,
        # and this app does not know the modules.
        autodiscover_modules('documents')
