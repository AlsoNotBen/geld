"""
messaging/services.py
------------------------------------------------------------------------
The public API of the messaging app. Other apps use only this module:

    from messaging.services import Message, send

    send(Message(
        to=["jane@example.com"],
        subject="Invoice INV-2026-0042",
        body="The invoice is attached.",
        attachments=[("INV-2026-0042.pdf", pdf_bytes, "application/pdf")],
    ))

A channel is a function that sends one Message through one medium.
CHANNELS maps a name to each channel. To add a medium (e.g. Matrix),
write a send_matrix(message) function and add it to CHANNELS. Then
call send(message, channel="matrix"). The Message stays the same.
"""
import logging
from dataclasses import dataclass, field
from django.core.mail import EmailMessage, make_msgid
from email.utils import parseaddr
from django.conf import settings

@dataclass
class Message:
    """One message. The fields do not depend on the medium."""
    to: list
    subject: str
    body: str = ""
    cc: list = field(default_factory=list)
    attachments: list = field(default_factory=list)  # (filename, content, mimetype)


def send_email(message):
    """Send the message through the "default" entry of settings.MAILERS.

    The sender is settings.DEFAULT_FROM_EMAIL. An SMTP error or a
    network error raises an OSError.
    """
    domain = parseaddr(settings.DEFAULT_FROM_EMAIL)[1].rpartition("@")[2]

    try:
        EmailMessage(
            subject=message.subject,
            body=message.body,
            to=message.to,
            cc=message.cc,
            attachments=message.attachments,
            headers={"Message-ID": make_msgid(domain=domain)}
        ).send()

    except Exception as e:
        logging.error(f"Error while attempting to send mail: {e}")


CHANNELS = {
    "email": send_email,
}


def send(message, channel="email"):
    """Send the message through the channel."""
    CHANNELS[channel](message)
