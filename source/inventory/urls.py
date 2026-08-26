from django.urls import path
from inventory import views

app_name = "inventory"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("stock", views.stock, name = "stock"),
    path("assets", views.assets, name = "assets")
]