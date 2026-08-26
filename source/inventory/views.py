from django.shortcuts import render

def dashboard(request):
    render(request, "inventory/dashboard.html")


def assets(request):
    render(request, "inventory/assets.html")

def stock(request):
    render(request,"inventory/stock.html")