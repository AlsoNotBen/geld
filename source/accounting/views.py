from django.shortcuts import render


def dashboard(request):
    return render(request, "accounting/overview.html")


def invoices(request):
    return render(request, "accounting/invoices.html")