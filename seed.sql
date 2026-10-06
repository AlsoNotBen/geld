-- =============================================================================
-- seed_defaults.sql
-- -----------------------------------------------------------------------------
-- Populates the essential and default tables of the Pothos application.
-- Run this script after "python manage.py migrate".
--
--     psql -h <host> -U <user> -d <database> -f seed_defaults.sql
--
-- The script is safe to run again. "ON CONFLICT DO NOTHING" skips rows that
-- are already in the database.
--
-- Assumptions:
--   * South African company, base currency ZAR.
--   * The financial year starts on 1 March and ends on the last day of
--     February (the same as the date range example in date_range.py).
--   * The normal side of an account comes from its type. This is the same
--     rule as NORMAL_SIDE in accounting/views.py.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- shared_currency  (ISO 4217)
-- -----------------------------------------------------------------------------
INSERT INTO shared_currency (alpha_code, numeric_code, minor_unit, name, symbol) VALUES
    ('ZAR', 710, 2, 'South African Rand',    'R'),
    ('USD', 840, 2, 'US Dollar',             '$'),
    ('EUR', 978, 2, 'Euro',                  '€'),
    ('GBP', 826, 2, 'Pound Sterling',        '£'),
    ('JPY', 392, 0, 'Japanese Yen',          '¥'),
    ('CNY', 156, 2, 'Chinese Yuan Renminbi', '¥'),
    ('CHF', 756, 2, 'Swiss Franc',           'CHF'),
    ('AUD',  36, 2, 'Australian Dollar',     'A$'),
    ('CAD', 124, 2, 'Canadian Dollar',       'C$'),
    ('NZD', 554, 2, 'New Zealand Dollar',    'NZ$'),
    ('INR', 356, 2, 'Indian Rupee',          '₹'),
    ('SGD', 702, 2, 'Singapore Dollar',      'S$'),
    ('HKD', 344, 2, 'Hong Kong Dollar',      'HK$'),
    ('AED', 784, 2, 'UAE Dirham',            'AED'),
    ('SEK', 752, 2, 'Swedish Krona',         'kr'),
    ('NOK', 578, 2, 'Norwegian Krone',       'kr'),
    ('DKK', 208, 2, 'Danish Krone',          'kr'),
    ('BRL', 986, 2, 'Brazilian Real',        'R$'),
    ('BWP',  72, 2, 'Botswana Pula',         'P'),
    ('NAD', 516, 2, 'Namibian Dollar',       'N$'),
    ('LSL', 426, 2, 'Lesotho Loti',          'L'),
    ('SZL', 748, 2, 'Swazi Lilangeni',       'E'),
    ('MZN', 943, 2, 'Mozambican Metical',    'MT'),
    ('ZMW', 967, 2, 'Zambian Kwacha',        'ZK'),
    ('KES', 404, 2, 'Kenyan Shilling',       'KSh'),
    ('NGN', 566, 2, 'Nigerian Naira',        '₦'),
    ('MUR', 480, 2, 'Mauritian Rupee',       '₨')
ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- shared_company  (one company)
-- -----------------------------------------------------------------------------
INSERT INTO shared_company (name, slug, tax_number, base_currency_id, is_active, created_at)
VALUES ('Pothos (Pty) Ltd.', 'pothos', '', 'ZAR', TRUE, now())
ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- shared_membership
-- CurrentCompanyMiddleware gets request.company from a membership. Without a
-- membership, a create view (e.g. New Lead) has no company. This statement
-- gives each existing superuser the Owner role. Run "createsuperuser" first,
-- or run the script again after you create the user.
-- -----------------------------------------------------------------------------
INSERT INTO shared_membership (user_id, company_id, role, is_default, created_at)
SELECT u.id, c.id, 'OWN', TRUE, now()
FROM auth_user u
CROSS JOIN shared_company c
WHERE u.is_superuser AND c.slug = 'pothos'
ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- shared_source  (lead sources)
-- -----------------------------------------------------------------------------
INSERT INTO shared_source (name) VALUES
    ('LinkedIn'), ('Facebook'), ('Instagram'), ('X (Twitter)'), ('WhatsApp'),
    ('Website'), ('Google Search'), ('Google Ads'), ('Email Campaign'),
    ('Cold Call'), ('Referral'), ('Existing Customer'), ('Partner'),
    ('Trade Show'), ('Event'), ('Walk-in'), ('Tender'), ('Other')
ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- shared_industry
-- -----------------------------------------------------------------------------
INSERT INTO shared_industry (sector) VALUES
    ('Agriculture'), ('Automotive'), ('Banking and Finance'), ('Construction'),
    ('Consulting'), ('Defence and Military'), ('Education'), ('Energy and Utilities'),
    ('Engineering'), ('Government'), ('Healthcare'), ('Hospitality and Tourism'),
    ('Information Technology'), ('Insurance'), ('Legal'), ('Logistics and Transport'),
    ('Manufacturing'), ('Marketing and Advertising'), ('Media and Entertainment'),
    ('Mining'), ('Non-Profit'), ('Pharmaceuticals'), ('Real Estate'), ('Retail'),
    ('Security'), ('Telecommunications'), ('Wholesale and Distribution'), ('Other')
ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- shared_title  (job titles)
-- -----------------------------------------------------------------------------
INSERT INTO shared_title (job_title) VALUES
    ('Chief Executive Officer'), ('Chief Financial Officer'), ('Chief Operating Officer'),
    ('Chief Technology Officer'), ('Chief Information Officer'), ('Managing Director'),
    ('Director'), ('General Manager'), ('Operations Manager'), ('Finance Manager'),
    ('Financial Controller'), ('Accountant'), ('Bookkeeper'), ('Procurement Manager'),
    ('Buyer'), ('Sales Manager'), ('Sales Representative'), ('Account Manager'),
    ('Marketing Manager'), ('IT Manager'), ('Systems Administrator'), ('Engineer'),
    ('Project Manager'), ('Product Manager'), ('HR Manager'), ('Office Manager'),
    ('Administrator'), ('Personal Assistant'), ('Consultant'), ('Owner'), ('Other')
ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- shared_businessrole  (role of a contact in a sale)
-- -----------------------------------------------------------------------------
INSERT INTO shared_businessrole (role) VALUES
    ('Decision Maker'), ('Economic Buyer'), ('Champion'), ('Influencer'),
    ('Technical Evaluator'), ('Gatekeeper'), ('End User'), ('Non-Decision Maker'),
    ('Blocker'), ('Other')
ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- accounting_fiscalyear  (last year and the current year)
-- -----------------------------------------------------------------------------
INSERT INTO accounting_fiscalyear (company_id, name, start_date, end_date, is_closed)
SELECT c.id, fy.name, fy.start_date, fy.end_date, FALSE
FROM shared_company c
CROSS JOIN (VALUES
    ('FY2025/26', DATE '2025-03-01', DATE '2026-02-28'),
    ('FY2026/27', DATE '2026-03-01', DATE '2027-02-28')
) AS fy(name, start_date, end_date)
WHERE c.slug = 'pothos'
ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- accounting_period  (twelve monthly periods for each fiscal year)
-- -----------------------------------------------------------------------------
INSERT INTO accounting_period (company_id, fiscal_year_id, name, start_date, end_date, is_closed)
SELECT fy.company_id,
       fy.id,
       to_char(m, 'Mon YYYY'),
       m::date,
       (m + INTERVAL '1 month' - INTERVAL '1 day')::date,
       FALSE
FROM accounting_fiscalyear fy
JOIN shared_company c ON c.id = fy.company_id AND c.slug = 'pothos'
CROSS JOIN LATERAL generate_series(fy.start_date, fy.end_date, INTERVAL '1 month') AS m
ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- accounting_account  (chart of accounts)
--
-- Code ranges:
--   1000-1999  Sales                     5000-5999  Equity
--   2000-2499  Cost of Sales             6000-6999  Non-Current Assets
--   2500-2999  Other Income              7000-7999  Current Assets
--   3000-4499  Expenses                  8000-8499  Non-Current Liabilities
--   4500-4999  Income Tax                8500-8999  Current Liabilities
--                                        9000-9999  Floating Nominal
--
-- Step 1 inserts the accounts. Step 2 sets the parent of each sub-account.
-- -----------------------------------------------------------------------------
CREATE TEMP TABLE seed_account (
    code        varchar(10),
    name        varchar(255),
    type        varchar(10),
    parent_code varchar(10),
    description text
) ON COMMIT DROP;

INSERT INTO seed_account (code, name, type, parent_code, description) VALUES
    -- Sales
    ('1000', 'Sales',                                   'SALES',  NULL,   'Group: income from the main trade.'),
    ('1100', 'Sales - Products',                        'SALES',  '1000', NULL),
    ('1200', 'Sales - Services',                        'SALES',  '1000', NULL),
    ('1900', 'Sales Returns and Allowances',            'SALES',  '1000', 'Contra account: credit notes to customers.'),

    -- Cost of Sales
    ('2000', 'Cost of Sales',                           'COS',    NULL,   'Group: direct costs of the goods and services sold.'),
    ('2100', 'Purchases',                               'COS',    '2000', NULL),
    ('2200', 'Direct Labour',                           'COS',    '2000', NULL),
    ('2300', 'Carriage Inwards',                        'COS',    '2000', NULL),
    ('2400', 'Stock Adjustments',                       'COS',    '2000', NULL),

    -- Other Income
    ('2500', 'Other Income',                            'OTHINC', NULL,   'Group: income that is not from the main trade.'),
    ('2510', 'Interest Received',                       'OTHINC', '2500', NULL),
    ('2520', 'Discount Received',                       'OTHINC', '2500', NULL),
    ('2530', 'Rental Income',                           'OTHINC', '2500', NULL),
    ('2540', 'Profit on Disposal of Assets',            'OTHINC', '2500', NULL),
    ('2550', 'Foreign Exchange Gain',                   'OTHINC', '2500', NULL),

    -- Expenses
    ('3000', 'Expenses',                                'EXP',    NULL,   'Group: operating expenses.'),
    ('3050', 'Accounting Fees',                         'EXP',    '3000', NULL),
    ('3100', 'Advertising and Marketing',               'EXP',    '3000', NULL),
    ('3150', 'Bank Charges',                            'EXP',    '3000', NULL),
    ('3200', 'Computer Expenses',                       'EXP',    '3000', NULL),
    ('3250', 'Consulting Fees',                         'EXP',    '3000', NULL),
    ('3300', 'Depreciation',                            'EXP',    '3000', NULL),
    ('3350', 'Entertainment',                           'EXP',    '3000', NULL),
    ('3400', 'Insurance',                               'EXP',    '3000', NULL),
    ('3450', 'Interest Paid',                           'EXP',    '3000', NULL),
    ('3500', 'Legal Fees',                              'EXP',    '3000', NULL),
    ('3550', 'Motor Vehicle Expenses',                  'EXP',    '3000', NULL),
    ('3600', 'Printing and Stationery',                 'EXP',    '3000', NULL),
    ('3650', 'Rent Paid',                               'EXP',    '3000', NULL),
    ('3700', 'Repairs and Maintenance',                 'EXP',    '3000', NULL),
    ('3750', 'Salaries and Wages',                      'EXP',    '3000', NULL),
    ('3800', 'Employer Contributions (UIF and SDL)',    'EXP',    '3000', NULL),
    ('3850', 'Subscriptions',                           'EXP',    '3000', NULL),
    ('3900', 'Telephone and Internet',                  'EXP',    '3000', NULL),
    ('3950', 'Travel and Accommodation',                'EXP',    '3000', NULL),
    ('4000', 'Water and Electricity',                   'EXP',    '3000', NULL),
    ('4050', 'Training',                                'EXP',    '3000', NULL),
    ('4100', 'Loss on Disposal of Assets',              'EXP',    '3000', NULL),
    ('4150', 'Foreign Exchange Loss',                   'EXP',    '3000', NULL),
    ('4200', 'Bad Debts',                               'EXP',    '3000', NULL),
    ('4250', 'Discount Allowed',                        'EXP',    '3000', NULL),
    ('4300', 'Security',                                'EXP',    '3000', NULL),
    ('4350', 'Courier and Postage',                     'EXP',    '3000', NULL),
    ('4400', 'General Expenses',                        'EXP',    '3000', NULL),

    -- Income Tax
    ('4500', 'Income Tax',                              'TAX',    NULL,   'Group: tax on the profit of the company.'),
    ('4510', 'Income Tax - Current',                    'TAX',    '4500', NULL),
    ('4520', 'Income Tax - Deferred',                   'TAX',    '4500', NULL),

    -- Equity
    ('5000', 'Equity',                                  'EQ',     NULL,   'Group: shareholder equity.'),
    ('5100', 'Share Capital',                           'EQ',     '5000', NULL),
    ('5200', 'Retained Earnings',                       'EQ',     '5000', NULL),
    ('5300', 'Dividends Declared',                      'EQ',     '5000', NULL),
    ('5900', 'Opening Balances',                        'EQ',     '5000', 'Holds the other side of the opening balances at go-live.'),

    -- Non-Current Assets
    ('6000', 'Property, Plant and Equipment',           'NCA',    NULL,   'Group: tangible fixed assets.'),
    ('6100', 'Land and Buildings',                      'NCA',    '6000', 'Group.'),
    ('6110', 'Land and Buildings - Cost',               'NCA',    '6100', NULL),
    ('6120', 'Land and Buildings - Accum. Depreciation','NCA',    '6100', 'Contra account.'),
    ('6200', 'Motor Vehicles',                          'NCA',    '6000', 'Group.'),
    ('6210', 'Motor Vehicles - Cost',                   'NCA',    '6200', NULL),
    ('6220', 'Motor Vehicles - Accum. Depreciation',    'NCA',    '6200', 'Contra account.'),
    ('6300', 'Computer Equipment',                      'NCA',    '6000', 'Group.'),
    ('6310', 'Computer Equipment - Cost',               'NCA',    '6300', NULL),
    ('6320', 'Computer Equipment - Accum. Depreciation','NCA',    '6300', 'Contra account.'),
    ('6400', 'Furniture and Fittings',                  'NCA',    '6000', 'Group.'),
    ('6410', 'Furniture and Fittings - Cost',           'NCA',    '6400', NULL),
    ('6420', 'Furniture and Fittings - Accum. Depr.',   'NCA',    '6400', 'Contra account.'),
    ('6500', 'Plant and Machinery',                     'NCA',    '6000', 'Group.'),
    ('6510', 'Plant and Machinery - Cost',              'NCA',    '6500', NULL),
    ('6520', 'Plant and Machinery - Accum. Depreciation','NCA',   '6500', 'Contra account.'),
    ('6700', 'Intangible Assets',                       'NCA',    NULL,   'Group.'),
    ('6710', 'Goodwill',                                'NCA',    '6700', NULL),
    ('6720', 'Software and Licences',                   'NCA',    '6700', NULL),
    ('6730', 'Intangibles - Accum. Amortisation',       'NCA',    '6700', 'Contra account.'),
    ('6900', 'Long-term Investments',                   'NCA',    NULL,   NULL),

    -- Current Assets
    ('7000', 'Current Assets',                          'CA',     NULL,   'Group.'),
    ('7010', 'Accounts Receivable',                     'CA',     '7000', 'Group.'),
    ('7100', 'Cash and Cash Equivalents',               'CA',     '7000', 'Group.'),
    ('7110', 'Bank - Current Account',                  'CA',     '7100', NULL),
    ('7120', 'Bank - Savings Account',                  'CA',     '7100', NULL),
    ('7130', 'Petty Cash',                              'CA',     '7100', NULL),
    ('7200', 'Trade Receivables',                       'CA',     '7000', 'Group.'),
    ('7210', 'Trade Debtors Control',                   'CA',     '7200', 'Control account for customer balances.'),
    ('7220', 'Allowance for Doubtful Debts',            'CA',     '7200', 'Contra account.'),
    ('7300', 'Inventory',                               'CA',     '7000', 'Group.'),
    ('7310', 'Finished Goods',                          'CA',     '7300', NULL),
    ('7320', 'Raw Materials',                           'CA',     '7300', NULL),
    ('7330', 'Work in Progress',                        'CA',     '7300', NULL),
    ('7400', 'Prepayments and Deposits',                'CA',     '7000', 'Group.'),
    ('7410', 'Prepaid Expenses',                        'CA',     '7400', NULL),
    ('7420', 'Deposits Paid',                           'CA',     '7400', NULL),

    -- Non-Current Liabilities
    ('8000', 'Non-Current Liabilities',                 'NCL',    NULL,   'Group.'),
    ('8010', 'Long-term Loans',                         'NCL',    '8000', NULL),
    ('8020', 'Shareholder Loans',                       'NCL',    '8000', NULL),
    ('8030', 'Lease Liabilities',                       'NCL',    '8000', NULL),
    ('8040', 'Deferred Tax Liability',                  'NCL',    '8000', NULL),

    -- Current Liabilities
    ('8500', 'Current Liabilities',                     'CL',     NULL,   'Group.'),
    ('8510', 'Trade Creditors Control',                 'CL',     '8500', 'Control account for supplier balances.'),
    ('8520', 'Accrued Expenses',                        'CL',     '8500', NULL),
    ('8530', 'Credit Card',                             'CL',     '8500', NULL),
    ('8540', 'Income Received in Advance',              'CL',     '8500', NULL),
    ('8550', 'Current Portion of Long-term Loans',      'CL',     '8500', NULL),
    ('8600', 'Payroll Liabilities',                     'CL',     '8500', 'Group.'),
    ('8610', 'PAYE Payable',                            'CL',     '8600', NULL),
    ('8620', 'UIF Payable',                             'CL',     '8600', NULL),
    ('8630', 'SDL Payable',                             'CL',     '8600', NULL),
    ('8700', 'Income Tax Payable',                      'CL',     '8500', 'Provisional and final income tax due to SARS.'),
    ('8800', 'Dividends Payable',                       'CL',     '8500', NULL),

    -- Floating Nominal (the balance can be on either side)
    ('9500', 'VAT Control',                             'FN',     NULL,   'Input VAT (debit) and output VAT (credit). The net balance is due to or from SARS.'),
    ('9900', 'Suspense',                                'FN',     NULL,   'Temporary account for unallocated amounts.');

-- Step 1: insert the accounts.
INSERT INTO accounting_account (company_id, code, name, type, normal_side, currency_id, is_active, description)
SELECT c.id,
       s.code,
       s.name,
       s.type,
       CASE WHEN s.type IN ('SALES', 'OTHINC', 'NCL', 'CL', 'EQ') THEN 'C' ELSE 'D' END,
       NULL,
       TRUE,
       s.description
FROM seed_account s
CROSS JOIN shared_company c
WHERE c.slug = 'pothos'
ON CONFLICT DO NOTHING;

-- Step 2: set the parent of each sub-account.
UPDATE accounting_account a
SET    parent_id = p.id
FROM   seed_account s
JOIN   shared_company c     ON c.slug = 'pothos'
JOIN   accounting_account p ON p.company_id = c.id AND p.code = s.parent_code
WHERE  a.company_id = c.id
  AND  a.code = s.code
  AND  a.parent_id IS NULL;

-- -----------------------------------------------------------------------------
-- accounting_taxcode  (South African VAT, linked to VAT Control)
-- -----------------------------------------------------------------------------
INSERT INTO accounting_taxcode (company_id, code, name, kind, rate, valid_from, valid_to, input_account_id, output_account_id)
SELECT c.id, t.code, t.name, t.kind, t.rate, DATE '2018-04-01', NULL, vat.id, vat.id
FROM shared_company c
JOIN accounting_account vat ON vat.company_id = c.id AND vat.code = '9500'
CROSS JOIN (VALUES
    ('S', 'Standard rated (15%)', 'STD', 15.00),
    ('Z', 'Zero rated (0%)',      'ZER',  0.00),
    ('E', 'Exempt',               'EXE',  0.00),
    ('N', 'No VAT (out of scope)','OOS',  0.00)
) AS t(code, name, kind, rate)
WHERE c.slug = 'pothos'
ON CONFLICT DO NOTHING;

COMMIT;