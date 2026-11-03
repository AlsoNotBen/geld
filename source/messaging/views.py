"""
messaging/views.py
------------------------------------------------------------------------
One view serves the message overlay (see messaging.js):

    GET     the empty form
    POST    send the message, with each file of "attachment"

The view always returns an HTML fragment: the form (with the errors and,
after a failed send, the failure banner), or the confirmation.
"""

from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .forms import MessageForm
from .services import Message, send


@require_http_methods(["GET", "POST"])
def compose(request):
    form = MessageForm(request.POST or None)
    failure = None

    if form.is_valid():
        files = request.FILES.getlist("attachment")
        message = Message(
            **form.cleaned_data,
            attachments=[(f.name, f.read(), f.content_type) for f in files],
        )
        try:
            send(message)
        except Exception as error:      # SMTP, network and configuration errors
            failure = str(error) or error.__class__.__name__
        else:
            return render(request, "messaging/sent.html", {"message": message})

    return render(request, "messaging/compose.html", {"form": form, "failure": failure})
