"""
documents/printing.py
------------------------------------------------------------------------
The Print button of a page. The print view (see views.print_page)
renders the page again on the server. This module takes the headings
and the tables from that HTML. The template documents/report_pdf.html
then makes a greyscale PDF of them.

The rules:
  - Only the content of <main id="main"> counts.
  - A heading (h2 to h4) gives its text. The first h1 is the title.
    An element with the attribute data-print-heading gives the text of
    its children as one h3. A heading without a table below it goes.
  - A table keeps its rows and its cells. Buttons with the class "tool"
    or "row-icon", forms, inputs and icons go. Other buttons and links
    become plain text. A column without a header text goes.
  - Each tab panel (.tabset__panel) becomes one section. The template
    starts each section on a new page. A hidden panel prints too.
  - The action bar, the tab buttons, the new entries for review, the
    notes and the overlays do not print.
"""

import re
from datetime import date
from xml.etree import ElementTree as ET

from weasyprint import HTML

HEADINGS        = {"h1", "h2", "h3", "h4"}
SKIP_TAGS       = {"script", "style", "noscript", "template", "dialog", "svg", "canvas",
                   "form", "input", "select", "textarea"}
SKIP_CLASSES    = {"actionbar", "tabset__list", "review", "page-notes", "notes-pill",
                   "visually-hidden", "tool", "row-icon", "journal-group__count"}
TABLE_TAGS      = {"table", "thead", "tbody", "tfoot", "tr", "th", "td", "br", "b", "strong"}
MONEY           = re.compile(r"^\(?-?[\d  ]+\.\d{2}\)?(\s+(Dr|Cr))?$")
PLAIN_MONEY     = re.compile(r"^-?\d+\.\d{2}$")
DEPTH           = re.compile(r"--depth:\s*(\d+)")
CONTENT         = 9     # The level of a table in _walk. A heading has the level 1 to 4.


def build_report(page_html):
    """Return a dict for the report template:
        title     the text of the first h1
        period    the date range of the page, or ""
        sections  a list of HTML strings. Each one starts on a new page.
    """
    root = HTML(string=page_html).etree_element
    main = next((el for el in root.iter() if el.get("id") == "main"), root)

    h1 = next(main.iter("h1"), None)
    title = _text(h1) if h1 is not None else ""

    sections = [[]]
    _walk(main, sections)
    sections = [_drop_empty_headings(items) for items in sections]
    return {
        "title":    title or "Report",
        "period":   _period(root),
        "sections": ["".join(items) for items in sections if items],
    }


def _drop_empty_headings(items):
    """Remove each heading that has no table below it, e.g. the title of
    a chart. An item is (level, html). A table has the level CONTENT."""
    kept, next_level = [], 0
    for level, html in reversed(items):
        if level < CONTENT and next_level <= level:
            continue
        kept.append(html)
        next_level = level
    return kept[::-1]


def _period(root):
    """The date range of the module bar, e.g. "1 Mar 2026 – 28 Feb 2027".
    A page without the date range button gives an empty text."""
    picker = next((el for el in root.iter() if el.get("data-daterange") is not None), None)
    if picker is None:
        return ""
    try:
        start = date.fromisoformat(picker.get("data-start", ""))
        end   = date.fromisoformat(picker.get("data-end", ""))
    except ValueError:
        return ""
    return f"{start.day} {start:%b %Y} – {end.day} {end:%b %Y}"


def _skip(el):
    if not isinstance(el.tag, str) or el.tag in SKIP_TAGS:
        return True
    if el.get("aria-hidden") == "true":
        return True
    classes = set(el.get("class", "").split())
    if classes & SKIP_CLASSES:
        return True
    return el.get("hidden") is not None and "tabset__panel" not in classes


def _walk(el, sections):
    """Add the headings and the tables below el, in page order."""
    for child in el:
        if _skip(child):
            continue
        if "tabset__panel" in child.get("class", "").split():
            sections.append([])
            _walk(child, sections)
            if not any(level == CONTENT for level, _ in sections[-1]):
                sections[-1].append((CONTENT, '<p class="empty">There is nothing to show.</p>'))
            sections.append([])
        elif child.tag == "h1":
            continue    # The head of the report shows the title.
        elif child.tag == "table":
            sections[-1].append((CONTENT, _table(child)))
        elif child.tag in HEADINGS:
            _heading(sections[-1], child.tag, _text(child))
        elif child.get("data-print-heading") is not None:
            # E.g. the head of a ledger account: code · name · type · balance
            parts = [_text(part) for part in child if not _skip(part)]
            _heading(sections[-1], "h3", " · ".join(filter(None, parts)))
        else:
            _walk(child, sections)


def _heading(items, tag, text):
    if text:
        el = ET.Element(tag)
        el.text = text
        items.append((int(tag[1]), ET.tostring(el, encoding="unicode", method="html")))


def _text(el):
    """The visible text of el, on one line."""
    _prune(el)
    return " ".join("".join(el.itertext()).split())


def _prune(el):
    """Remove the children that do not print. Keep the tail text of each one."""
    for child in list(el):
        if _skip(child):
            tail = child.tail or ""
            index = list(el).index(child)
            if index:
                prev = el[index - 1]
                prev.tail = (prev.tail or "") + tail
            else:
                el.text = (el.text or "") + tail
            el.remove(child)
        else:
            _prune(child)


def _cells(row):
    """Yield (first column, cell) for each cell of the row."""
    column = 0
    for cell in row:
        if cell.tag in ("td", "th"):
            yield column, cell
            column += _span(cell)


def _span(cell):
    try:
        return max(1, int(cell.get("colspan", 1)))
    except ValueError:
        return 1


def _table(table):
    """Return the clean HTML of one table."""
    _prune(table)
    rows = [row for row in table.iter("tr")]
    head = [row for part in table.findall("thead") for row in part.findall("tr")]
    body = [row for row in rows if row not in head]

    # A column without a header text, e.g. the buttons of each row, goes.
    empty = set()
    if head:
        empty = {column for column, cell in _cells(head[-1])
                 if _span(cell) == 1 and not "".join(cell.itertext()).strip()}

    # A column with an amount in a body row aligns at the right.
    numeric = {column for row in body for column, cell in _cells(row)
               if _span(cell) == 1 and MONEY.match("".join(cell.itertext()).strip())}

    for row in rows:
        for column, cell in list(_cells(row)):
            covered = len(empty & set(range(column, column + _span(cell))))
            if covered == _span(cell):
                row.remove(cell)
                continue
            if covered:
                cell.set("colspan", str(_span(cell) - covered))
            if column + _span(cell) - 1 in numeric:
                cell.set("data-num", "")
            if len(cell) == 0 and PLAIN_MONEY.match((cell.text or "").strip()):
                cell.text = _group(cell.text.strip())

    for el in table.iter():
        _clean_attributes(el)
    table.set("class", "report-table")
    return ET.tostring(table, encoding="unicode", method="html")


def _group(text):
    """Put a no-break space between each group of three digits, as base.js does."""
    whole, cents = text.split(".")
    return re.sub(r"\B(?=(\d{3})+(?!\d))", " ", whole) + "." + cents


def _clean_attributes(el):
    """Keep only what the report CSS reads. A tag that is not part of a
    table becomes a <span>, thus a link or a button is plain text."""
    keep = {}
    for name in ("colspan", "rowspan", "data-num"):
        if el.get(name) is not None:
            keep[name] = el.get(name)
    if el.tag in ("tr", "tbody"):
        keep["class"] = el.get("class", "")
    depth = DEPTH.search(el.get("style", ""))
    if depth:   # The indent of a child account in the Chart of Accounts
        keep["style"] = f"padding-left: {2.5 + 4 * int(depth.group(1))}mm"
    el.attrib.clear()
    el.attrib.update(keep)
    if el.tag not in TABLE_TAGS:
        el.tag = "span"
