from django.shortcuts import render


def dashboard(request):
    return render(request, "accounting/overview.html")

def journals(request):

    GENERAL_ENTRIES = [
        {"date": "2026-01-02", "reference": "JE-2026-0001", "account": "Opening balance · Retained earnings",  "amount": "184 300.00", "is_debit": False},
        {"date": "2026-01-05", "reference": "JE-2026-0002", "account": "Depreciation · Office equipment",      "amount": "2 450.00",   "is_debit": True},
        {"date": "2026-01-12", "reference": "JE-2026-0003", "account": "Accrual · Audit fees",                 "amount": "18 000.00",  "is_debit": True},
        {"date": "2026-01-19", "reference": "JE-2026-0004", "account": "Reclass · Prepaid insurance",          "amount": "7 125.50",   "is_debit": False},
        {"date": "2026-01-31", "reference": "JE-2026-0005", "account": "Payroll · Salaries and wages",         "amount": "96 480.00",  "is_debit": True},
        {"date": "2026-02-03", "reference": "JE-2026-0006", "account": "Interest · Term loan",                 "amount": "3 812.40",   "is_debit": True},
        {"date": "2026-02-14", "reference": "JE-2026-0007", "account": "Forex gain · USD account",             "amount": "1 267.85",   "is_debit": False},
    ]
    
    SALES_ENTRIES = [
        {"date": "2026-01-06", "reference": "INV-1041", "account": "Halden Group · Consulting",         "amount": "24 800.00", "is_debit": False},
        {"date": "2026-01-09", "reference": "INV-1042", "account": "Bergman AB · Licence renewal",      "amount": "12 350.00", "is_debit": False},
        {"date": "2026-01-15", "reference": "CN-0114",  "account": "Bergman AB · Credit note",          "amount": "1 150.00",  "is_debit": True},
        {"date": "2026-01-22", "reference": "INV-1043", "account": "Norwind Logistics · Support hours", "amount": "8 940.00",  "is_debit": False},
        {"date": "2026-02-02", "reference": "INV-1044", "account": "Delacroix SARL · Implementation",   "amount": "41 600.00", "is_debit": False},
        {"date": "2026-02-11", "reference": "INV-1045", "account": "Halden Group · Retainer February",  "amount": "9 500.00",  "is_debit": False},
    ]
    
    PURCHASE_ENTRIES = [
        {"date": "2026-01-04", "reference": "BILL-3308", "account": "Kestrel Hosting · Cloud services",  "amount": "4 210.00", "is_debit": True},
        {"date": "2026-01-08", "reference": "BILL-3309", "account": "Vandermeer Office · Stationery",    "amount": "612.75",   "is_debit": True},
        {"date": "2026-01-17", "reference": "BILL-3310", "account": "Lindqvist Legal · Contract review", "amount": "7 800.00", "is_debit": True},
        {"date": "2026-01-25", "reference": "BILL-3311", "account": "Northline Freight · Delivery",      "amount": "1 986.40", "is_debit": True},
        {"date": "2026-02-01", "reference": "DN-0207",   "account": "Kestrel Hosting · Service credit",  "amount": "320.00",   "is_debit": False},
        {"date": "2026-02-09", "reference": "BILL-3312", "account": "Aurora Print · Marketing material", "amount": "3 145.90", "is_debit": True},
    ]
    
    CASH_ENTRIES = [
        {"date": "2026-01-07", "reference": "RCT-0218", "account": "Receipt · Halden Group INV-1041",      "amount": "24 800.00", "is_debit": False},
        {"date": "2026-01-10", "reference": "PMT-0455", "account": "Payment · Kestrel Hosting BILL-3308",  "amount": "4 210.00",  "is_debit": True},
        {"date": "2026-01-16", "reference": "PMT-0456", "account": "Bank charges · Monthly fee",           "amount": "89.00",     "is_debit": True},
        {"date": "2026-01-28", "reference": "RCT-0219", "account": "Receipt · Bergman AB INV-1042",        "amount": "11 200.00", "is_debit": False},
        {"date": "2026-01-31", "reference": "PMT-0457", "account": "Payment · Payroll run January",        "amount": "96 480.00", "is_debit": True},
        {"date": "2026-02-05", "reference": "PMT-0458", "account": "Payment · Lindqvist Legal BILL-3310",  "amount": "7 800.00",  "is_debit": True},
        {"date": "2026-02-12", "reference": "RCT-0220", "account": "Receipt · Norwind Logistics INV-1043", "amount": "8 940.00",  "is_debit": False},
    ]

    context = {
        "page_title": "Journal Entries",
        "period": "FY 2026",
        "general_entries": GENERAL_ENTRIES,
        "sales_entries": SALES_ENTRIES,
        "purchase_entries": PURCHASE_ENTRIES,
        "cash_entries": CASH_ENTRIES,
    }

    return render(request, "accounting/journals.html",context)

def invoices(request):
    return render(request, "accounting/invoices.html")

def chartaccounts(request):
    return render(request, "accounting/chart_of_accounts.html")