from django.urls import path
from accounting import views

app_name = "accounting"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("invoices/", views.invoices, name = "invoices"),
    path("journals/", views.journals, name = "journals")
]