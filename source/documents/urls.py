from django.urls import path
from documents import views

app_name = "documents"

urlpatterns = [
    path("<slug:module>/<slug:key>/panel/", views.panel, name="panel"),
    path("<slug:module>/<slug:key>/preview.pdf", views.preview, name="preview"),
    path("<slug:module>/<slug:key>/download.pdf", views.download, name="download"),
]
