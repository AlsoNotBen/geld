"""URLs of the Inventory module.

The names follow the Accounting module: one word, no underscore. The first
page has the name "dashboard", as in Accounting, but its template is
overview.html and its title is Overview.

core/urls.py must hold this line:

    path("inventory/", include("inventory.urls")),
"""

from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.overview, name="dashboard"),
    path("analytics/", views.analytics, name="analytics"),
    path("reports/", views.reports, name="reports"),
    path("assets/", views.assets, name="assets"),
    path("stock/", views.stock, name="stock"),
    path("consumables/", views.consumables, name="consumables"),
    path("kits/", views.kits, name="kits"),
    path("bom/", views.bom, name="bom"),
    path("codes/", views.codes, name="codes"),
    path("items/", views.items, name="items"),
    path("items/new/<str:kind>/", views.item_entry, name="itementry"),
    path("items/<int:pk>/", views.item_view, name="itemview"),
    path("items/<int:pk>/checkout/", views.item_checkout, name="itemcheckout"),
    path("items/<int:pk>/checkin/", views.item_checkin, name="itemcheckin"),
]