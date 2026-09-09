from django.urls import path
from accounting import views

app_name = "accounting"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("invoices/", views.invoices, name = "invoices"),

    # Journals
    path("journals/", views.journals, name = "journals"),
    path("journals/new/", views.journalentry_create, name="journalentry_create"),
    path("journals/entry/<int:pk>/edit/", views.journalentry_update, name="journalentry_update"),
    path("journals/entry/<int:pk>/post/", views.journalentry_post, name="journalentry_post"),
    path("journals/entry/<int:pk>/void/", views.journalentry_void, name="journalentry_void"),
    path("journals/entries/post-all/", views.journalentry_post_all, name="journalentry_post_all"),

    # Accounts
    path("chartaccounts/", views.chartaccounts, name="chartaccounts"),
    path("chartaccounts/new/", views.account_create, name="account_create"),
    path("ledger/",views.ledger,name="ledger"),
    path("balancesheet/",views.balancesheet,name="balancesheet"),
    path("incomestatement/",views.incomestatement,name="incomestatement"),
    path("cashflow/",views.cashflow,name="cashflow"),
    path("equity/",views.equity,name="equity"),
]