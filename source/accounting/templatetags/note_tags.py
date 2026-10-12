"""The notes of a page: the Notes pill, the note cards and the New Note
overlay. A page with a Note button uses the two tags:

    {% load note_tags %}
    <h1 class="page__title">Balance Sheet{% notes_pill %}</h1>
    ...
    {% notes_section %}

The page of a note is the view name of its URL, e.g. "accounting:balancesheet".
Thus a note shows only on the page where the user wrote it.
"""

from html import escape
from html.parser import HTMLParser

from django import template
from django.utils.safestring import mark_safe

from accounting.forms import NoteForm
from accounting.models import Note

register = template.Library()


@register.inclusion_tag("accounting/_notes_pill.html", takes_context=True)
def notes_pill(context):
    request = context["request"]
    return {"count": Note.active(request.company, request.resolver_match.view_name).count()}


@register.inclusion_tag("accounting/_notes.html", takes_context=True)
def notes_section(context):
    request = context["request"]
    page = request.resolver_match.view_name
    notes = list(Note.active(request.company, page).select_related("created_by").prefetch_related("files"))
    return {
        "csrf_token": context.get("csrf_token"),
        "notes": notes,
        "groups": [
            {"key": "comments", "title": "Commentary", "open": False,
             "notes": [n for n in notes if n.kind == Note.Kind.COMMENT]},
            {"key": "footnotes", "title": "Footnotes", "open": True,
             "notes": [n for n in notes if n.kind == Note.Kind.FOOTNOTE]},
        ],
        "form": NoteForm(initial={"page": page}, auto_id="note-%s"),
        "range_start": context.get("range_start"),
        "range_end": context.get("range_end"),
    }


class RichText(HTMLParser):
    """Keep only the tags of the note editor. A tag loses its attributes,
    except the href of a link to a web or mail address. The text is escaped
    again, thus no script can get into the page."""

    TAGS = {"p", "br", "strong", "em", "u", "ol", "ul", "li", "a"}
    LINKS = ("http://", "https://", "mailto:")

    def __init__(self):
        super().__init__()
        self.out, self.open = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in self.TAGS:
            return
        if tag == "br":
            self.out.append("<br>")
            return
        href = dict(attrs).get("href") or ""
        if tag == "a" and href.startswith(self.LINKS):
            self.out.append(f'<a href="{escape(href)}" target="_blank" rel="noopener noreferrer">')
        else:
            self.out.append(f"<{tag}>")
        self.open.append(tag)

    def handle_endtag(self, tag):
        if tag not in self.open:
            return                          # an end tag without a start tag goes away
        while True:                         # close the inner tags first
            last = self.open.pop()
            self.out.append(f"</{last}>")
            if last == tag:
                return

    def handle_data(self, data):
        self.out.append(escape(data))


@register.filter
def rich_text(html):
    """The description of a note, clean and safe for the page."""
    parser = RichText()
    parser.feed(html or "")
    parser.close()
    parser.out += [f"</{tag}>" for tag in reversed(parser.open)]
    return mark_safe("".join(parser.out))
