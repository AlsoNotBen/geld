from django.urls import path
from accounting import views

app_name = "accounting"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("invoices/", views.invoices, name = "invoices"),
    path("journals/", views.journals, name = "journals"),
    path("chartaccounts/", views.chartaccounts, name="chartaccounts"),
    path("ledger/",views.ledger,name="ledger"),
    path("balancesheet/",views.balancesheet,name="balancesheet"),
    path("incomestatement/",views.incomestatement,name="incomestatement"),
    path("cashflow/",views.cashflow,name="cashflow"),
    path("equity/",views.equity,name="equity"),
]