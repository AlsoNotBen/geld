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

    # Analysis
    path("reports/", views.reports, name="reports"),

    # Cost Centre
    path("bills/", views.bills, name="bills"),
    path("bills/<int:pk>/approve/", views.bill_approve, name="bill_approve"),
    path("bills/<int:pk>/deny/", views.bill_deny, name="bill_deny"),
    path("claims/", views.claims, name="claims"),

    # General
    path("settings/accounting/", views.accounting_settings, name="accounting_settings"),
    path("settings/module/", views.module_settings, name="module_settings"),

    # Customers
    path("customers/", views.customers, name="customers"),
    path("customers/new/", views.customer_new, name="customer_new"),
    path("customers/receivables/", views.receivables, name="receivables"),
    path("customers/aging/", views.aging_receivables, name="aging_receivables"),
    path("customers/dashboard/", views.customer_dashboard, name="customer_dashboard"),

    # Suppliers
    path("suppliers/", views.suppliers, name="suppliers"),
    path("suppliers/new/", views.supplier_new, name="supplier_new"),
    path("suppliers/payables/", views.payables, name="payables"),
    path("suppliers/aging/", views.aging_payables, name="aging_payables"),
    path("suppliers/dashboard/", views.supplier_dashboard, name="supplier_dashboard"),

    # Banking
    path("banking/", views.bank_accounts, name="bank_accounts"),
    path("banking/new/", views.bank_account_new, name="bank_account_new"),
    path("banking/cards/", views.cards, name="cards"),
    path("banking/import/", views.import_statement, name="import_statement"),
    path("banking/reconcile/", views.reconcile, name="reconcile"),
    path("banking/payments/", views.payment_runs, name="payment_runs"),

    # Taxes
    path("taxes/income/", views.income_tax, name="income_tax"),
    path("taxes/provisional/", views.provisional_tax, name="provisional_tax"),
    path("taxes/vat/", views.vat, name="vat"),
    path("taxes/paye/", views.paye, name="paye"),
    path("taxes/dashboard/", views.tax_dashboard, name="tax_dashboard"),
]