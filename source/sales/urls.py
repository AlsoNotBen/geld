from django.urls import path
from sales import views

app_name = "sales"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("leads/", views.leads, name="leads"),
    path("leads/new/", views.lead_create, name="lead_create"),
    path("leads/<int:pk>/edit/", views.lead_update, name="lead_update"),
    path("quotes/", views.quotes, name="quotes"),
    path("invoices/", views.invoices, name="invoices"),
    path("crnotes/", views.credit_notes, name="credit_notes"),
    path("partners/", views.partners, name="partners"),
]
