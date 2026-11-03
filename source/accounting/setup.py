"""
accounting/setup.py
------------------------------------------------------------------------
The first-use data of a new company (see seed_company). The lists are
the same as parts 4 to 6 of seed.sql: one financial year with its 12
periods, the standard chart of accounts and the South African VAT codes.

The posting finds some accounts by name: "Accounts Receivable",
"Accounts Payable", "Suspense", "VAT Control", "Sales" and "Opening
Balance Equity". Do not change these names.

The number sequences need no seed: NumberSequence.peek makes each one
on first use.
"""
import calendar
import datetime
from decimal import Decimal

from accounting.models import Account, FiscalYear, Period, TaxCode

T, D, C = Account.AccountType, Account.Side.DEBIT, Account.Side.CREDIT

# (code, name, type, normal side, parent code, description)
ACCOUNTS = [
    ("1000", "Bank",                                          T.CURRENT_ASSETS,          D, None,   "The current account. Payments and receipts go through it."),
    ("1050", "Petty Cash",                                    T.CURRENT_ASSETS,          D, None,   "Cash on hand."),
    ("1100", "Accounts Receivable",                           T.CURRENT_ASSETS,          D, None,   "The open invoices. The posting finds it by name."),
    ("1200", "Inventory",                                     T.CURRENT_ASSETS,          D, None,   "Stock for resale, at cost."),
    ("1300", "Prepaid Expenses",                              T.CURRENT_ASSETS,          D, None,   None),
    ("1500", "Computer Equipment",                            T.NON_CURRENT_ASSETS,      D, None,   None),
    ("1510", "Accumulated Depreciation — Computer Equipment", T.NON_CURRENT_ASSETS,      C, "1500", None),
    ("1520", "Vehicles",                                      T.NON_CURRENT_ASSETS,      D, None,   None),
    ("1530", "Accumulated Depreciation — Vehicles",           T.NON_CURRENT_ASSETS,      C, "1520", None),
    ("1900", "Suspense",                                      T.CURRENT_ASSETS,          D, None,   "Unallocated money (cash basis). The posting finds it by name."),
    ("2000", "Accounts Payable",                              T.CURRENT_LIABILITIES,     C, None,   "The unpaid bills. The posting finds it by name."),
    ("2100", "VAT Control",                                   T.CURRENT_LIABILITIES,     C, None,   "Output VAT less input VAT."),
    ("2200", "PAYE Payable",                                  T.CURRENT_LIABILITIES,     C, None,   "Employees' tax."),
    ("2400", "Accrued Expenses",                              T.CURRENT_LIABILITIES,     C, None,   None),
    ("2500", "Income Tax Payable",                            T.CURRENT_LIABILITIES,     C, None,   None),
    ("3000", "Share Capital",                                 T.SHAREHOLDER_EQUITY,      C, None,   None),
    ("3100", "Retained Earnings",                             T.SHAREHOLDER_EQUITY,      C, None,   None),
    ("3200", "Opening Balance Equity",                        T.SHAREHOLDER_EQUITY,      C, None,   "The other side of each opening balance. The posting finds it by name."),
    ("4000", "Sales",                                         T.SALES,                   C, None,   "The invoices post here."),
    ("4500", "Interest Received",                             T.OTHER_INCOME,            C, None,   None),
    ("5000", "Cost of Sales",                                 T.COST_OF_SALES,           D, None,   "The cost of the stock that was sold."),
    ("6000", "Salaries and Wages",                            T.EXPENSES,                D, None,   None),
    ("6100", "Rent",                                          T.EXPENSES,                D, None,   None),
    ("6200", "Office Supplies",                               T.EXPENSES,                D, None,   None),
    ("6300", "Fuel and Travel",                               T.EXPENSES,                D, None,   None),
    ("6400", "Software and Hosting",                          T.EXPENSES,                D, None,   None),
    ("6500", "Bank Charges",                                  T.EXPENSES,                D, None,   None),
    ("6600", "Depreciation",                                  T.EXPENSES,                D, None,   None),
    ("6700", "Telephone and Internet",                        T.EXPENSES,                D, None,   None),
    ("7000", "Income Tax Expense",                            T.INCOME_TAX,              D, None,   None),
    ("9000", "Clearing Account",                              T.FLOATING_NOMINAL,        D, None,   "A floating account for transfers. It stays at zero."),
]

# South African VAT (VAT Act 89 of 1991): (code, name, kind, rate, valid from, uses VAT Control).
K = TaxCode.Kind
TAX_CODES = [
    ("VAT15", "Standard rated 15%", K.STANDARD, Decimal("15.00"), datetime.date(2018, 4, 1),  True),
    ("ZR",    "Zero rated",         K.ZERO,     Decimal("0.00"),  datetime.date(1991, 9, 30), True),
    ("EX",    "Exempt",             K.EXEMPT,   Decimal("0.00"),  datetime.date(1991, 9, 30), False),
]


def add_months(day, months):
    """The same day, the number of months later. If that month does not
    have the day, the date is the last day of that month."""
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    month += 1
    return datetime.date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def seed_company(company, year_start):
    """Give a new company the data that it must have before first use:
    1. One financial year from year_start, with 12 periods of one month. All are open.
    2. The chart of accounts (see ACCOUNTS). "Bank" has the base currency of the company.
    3. The tax codes (see TAX_CODES).
    The caller runs this in the transaction that makes the company. Thus
    an error makes no company at all."""
    year = FiscalYear.objects.create(company=company, name=f"FY{year_start.year}", start_date=year_start,
                                     end_date=add_months(year_start, 12) - datetime.timedelta(days=1))
    Period.objects.bulk_create(
        Period(company=company, fiscal_year=year, name=f"{add_months(year_start, n):%Y-%m}",
               start_date=add_months(year_start, n),
               end_date=add_months(year_start, n + 1) - datetime.timedelta(days=1))
        for n in range(12))

    accounts = {}
    for code, name, kind, side, parent, description in ACCOUNTS:
        accounts[code] = Account.objects.create(
            company=company, code=code, name=name, type=kind, normal_side=side, parent=accounts.get(parent),
            currency=company.base_currency if code == "1000" else None, description=description)

    vat = accounts["2100"]
    TaxCode.objects.bulk_create(
        TaxCode(company=company, code=code, name=name, kind=kind, rate=rate, valid_from=valid_from,
                input_account=vat if uses_vat else None, output_account=vat if uses_vat else None)
        for code, name, kind, rate, valid_from, uses_vat in TAX_CODES)
