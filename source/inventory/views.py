
from django.shortcuts import render
 
 
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
    return _page(request, "inventory/items.html", "Items")
