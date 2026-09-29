from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from filestore.services import save_upload, validate
from .forms import ItemForm


def _page(request, template, title):
    """Render one page of the module."""
    return render(request, template, {"page_title": title})


def overview(request):
    return _page(request, "inventory/overview.html", "Overview")


def analytics(request):
    return _page(request, "inventory/analytics.html", "Analytics")


def reports(request):
    return _page(request, "inventory/reports.html", "Reports")


def assets(request):
    return _page(request, "inventory/assets.html", "Assets")


def stock(request):
    return _page(request, "inventory/stock.html", "Stock")


def consumables(request):
    return _page(request, "inventory/consumables.html", "Consumables")


def kits(request):
    return _page(request, "inventory/kits.html", "Kit & Components")


def bom(request):
    return _page(request, "inventory/bom.html", "Bill of Materials")


def codes(request):
    return _page(request, "inventory/codes.html", "Codes & Tags")


def items(request):
    form = ItemForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        uploads = request.FILES.getlist("files")
        try:
            # Validate every file first, so a bad file stores nothing.
            for upload in uploads:
                validate(upload)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            with transaction.atomic():
                item = form.save()
                item.files.add(*(save_upload(u, request.user) for u in uploads))
            messages.success(request, f"Saved {item.name}.")
            return redirect(request.path)  # Post/Redirect/Get

    return render(request, "inventory/items.html", {"page_title": "Items", "form": form})