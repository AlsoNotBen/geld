from django.urls import path

from . import views

app_name = "filestore"

urlpatterns = [
    path("<uuid:pk>/", views.download, name="download"),
]