# Documents

The `documents` app turns Django templates into PDF files with
WeasyPrint. Each module of the suite can register its own document
types. The app then serves the overlay, the preview and the download
for each type.

## Requirements

```
pip install weasyprint
```

WeasyPrint needs Pango and related system libraries. On Debian or
Ubuntu, install them with:

```
sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
```

## URL paths

The root URLconf includes the app at `/documents/`. Each document type
gets three paths:

| Path | Purpose |
| --- | --- |
| `/documents/<module>/<key>/panel/` | The overlay content: options form and preview frame. |
| `/documents/<module>/<key>/preview.pdf` | The PDF, shown inline in the preview frame. |
| `/documents/<module>/<key>/download.pdf` | The PDF as a file download. |

The preview and the download read the render options from the query
string. Without a query string the initial form values apply.

## Add a document type to your module

Do these four steps. The Accounting module shows a full example
(`accounting/documents.py`).

1. Create a file with the name `documents.py` in your app. The
   documents app imports it at start.
2. Declare an options form. Extend `documents.forms.DocumentOptionsForm`
   and add your fields. Give each field an initial value. The panel
   shows the fields in `customize_field_names` (paper size, accent
   color, company block) in a folded "Customize" section; extend that
   tuple to move more fields there. Two widgets are available for a
   richer form: `SelectWithAddButton` puts an inline "+" button at the
   side of a select (the click dispatches a `doc:action` event, which
   your own script can link to another overlay), and `LineItemsField`
   gives an editor to add, change and remove line items, with a catalog
   select and a free custom line.
3. Declare the document type. Extend `documents.registry.DocumentType`,
   set `module`, `key`, `label` and `template_name`, and decorate the
   class with `@register`. Put your data into the context in
   `get_context`.
4. Create the PDF template. Extend `documents/base_pdf.html` and fill
   the `body` block. Keep all CSS inside the template.

```python
# inventory/documents.py
from documents.registry import DocumentType, register

@register
class StockReportDocument(DocumentType):
    module = "inventory"
    key = "stock-report"
    label = "Stock Report"
    template_name = "inventory/pdf/stock_report.html"
```

## Open the overlay from a page

Give a button the `data-doc-overlay` attribute with the panel URL:

```html
<button class="tool tool--primary" type="button"
        data-doc-overlay="{% url 'documents:panel' 'inventory' 'stock-report' %}">
    Stock Report
</button>
```

The shared script (`documents/static/documents/js/documents.js`)
listens for the click, loads the panel into a `<dialog>`, and blurs
the page behind it. `templates/base.html` loads the script and the
stylesheet for every module.

## Keep the PDF templates self-contained

Put all CSS in the `<style>` block of the template. Do not link
external stylesheets, images or fonts. Then WeasyPrint makes no HTTP
requests back to the server during a render.
