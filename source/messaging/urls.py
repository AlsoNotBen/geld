from django.urls import path
from messaging import views

app_name = "messaging"

urlpatterns = [
    path('compose/', views.compose, name='compose'),
]
