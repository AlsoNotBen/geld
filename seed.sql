-- ============================================================================
-- seed.sql — first-use data for the shared and accounting apps (PostgreSQL)
-- ----------------------------------------------------------------------------
-- The file needs only the schema of the migrations.
--
--     python manage.py migrate
--     psql "$DATABASE_URL" -f seed.sql      (or: python manage.py dbshell < seed.sql)
--
-- WARNING: The file REPLACES ALL DATA of the shared and accounting apps and of
-- the users. Do not run it on a database that has real data.
-- The file runs in one transaction. If an error occurs, nothing changes.
--
-- The file adds only the data that the apps must have before first use:
--   1. The ISO 4217 currencies.
--   2. The GICS sectors (the industry list).
--   3. One user, one company and the membership of the user.
--   4. The financial years and their periods.
--   5. A standard chart of accounts.
--   6. The South African VAT codes.
--   7. The number sequences.
--
-- Log in as admin / admin. Change the password immediately.
-- Then change the company name, tax number and address in the admin.
-- ============================================================================

BEGIN;

-- Django uses TIME_ZONE = 'UTC'. Thus "today" of the seed is the same day as in the app.
SET LOCAL TIME ZONE 'UTC';

TRUNCATE TABLE
    accounting_account,
    accounting_auditlog,
    accounting_bankaccount,
    accounting_banktransaction,
    accounting_depreciationschedule,
    accounting_document,
    accounting_document_files,
    accounting_documentline,
    accounting_fiscalyear,
    accounting_fixedasset,
    accounting_journalentry,
    accounting_journalline,
    accounting_note,
    accounting_note_files,
    accounting_numbersequence,
    accounting_payment,
    accounting_payment_files,
    accounting_paymentallocation,
    accounting_period,
    accounting_recurringdocument,
    accounting_service,
    accounting_taxcode,
    auth_user,
    django_admin_log,
    django_session,
    shared_businessrole,
    shared_company,
    shared_currency,
    shared_entity,
    shared_exchangerate,
    shared_individualprofile,
    shared_industry,
    shared_membership,
    shared_organizationprofile,
    shared_project,
    shared_source,
    shared_supplier,
    shared_title
RESTART IDENTITY CASCADE;

-- ____________________________________________________________________________
-- 1. Currencies: the active currencies of ISO 4217 (List One).
-- Fund codes, precious metals and test codes are not in the list.
-- The symbols come from the Unicode CLDR. A blank symbol means that CLDR has no short local symbol.

INSERT INTO shared_currency (alpha_code, numeric_code, minor_unit, name, symbol) VALUES
    ('AED', 784, 2, 'UAE Dirham', ''),
    ('AFN', 971, 2, 'Afghani', ''),
    ('ALL',   8, 2, 'Lek', 'Lekë'),
    ('AMD',  51, 2, 'Armenian Dram', '֏'),
    ('AOA', 973, 2, 'Kwanza', 'Kz'),
    ('ARS',  32, 2, 'Argentine Peso', '$'),
    ('AUD',  36, 2, 'Australian Dollar', '$'),
    ('AWG', 533, 2, 'Aruban Florin', 'Afl.'),
    ('AZN', 944, 2, 'Azerbaijan Manat', '₼'),
    ('BAM', 977, 2, 'Convertible Mark', 'КМ'),
    ('BBD',  52, 2, 'Barbados Dollar', '$'),
    ('BDT',  50, 2, 'Taka', '৳'),
    ('BHD',  48, 3, 'Bahraini Dinar', 'د.ب.‏'),
    ('BIF', 108, 0, 'Burundi Franc', 'FBu'),
    ('BMD',  60, 2, 'Bermudian Dollar', '$'),
    ('BND',  96, 2, 'Brunei Dollar', '$'),
    ('BOB',  68, 2, 'Boliviano', 'Bs'),
    ('BRL', 986, 2, 'Brazilian Real', 'R$'),
    ('BSD',  44, 2, 'Bahamian Dollar', '$'),
    ('BTN',  64, 2, 'Ngultrum', 'Nu.'),
    ('BWP',  72, 2, 'Pula', 'P'),
    ('BYN', 933, 2, 'Belarusian Ruble', 'Br'),
    ('BZD',  84, 2, 'Belize Dollar', '$'),
    ('CAD', 124, 2, 'Canadian Dollar', '$'),
    ('CDF', 976, 2, 'Congolese Franc', 'FC'),
    ('CHF', 756, 2, 'Swiss Franc', ''),
    ('CLP', 152, 0, 'Chilean Peso', ''),
    ('CNY', 156, 2, 'Yuan Renminbi', '¥'),
    ('COP', 170, 2, 'Colombian Peso', '$'),
    ('CRC', 188, 2, 'Costa Rican Colon', '₡'),
    ('CUP', 192, 2, 'Cuban Peso', '$'),
    ('CVE', 132, 2, 'Cabo Verde Escudo', '​'),
    ('CZK', 203, 2, 'Czech Koruna', ''),
    ('DJF', 262, 0, 'Djibouti Franc', 'Fdj'),
    ('DKK', 208, 2, 'Danish Krone', 'kr.'),
    ('DOP', 214, 2, 'Dominican Peso', 'RD$'),
    ('DZD',  12, 2, 'Algerian Dinar', 'د.ج.‏'),
    ('EGP', 818, 2, 'Egyptian Pound', 'ج.م.‏'),
    ('ERN', 232, 2, 'Nakfa', 'Nfk'),
    ('ETB', 230, 2, 'Ethiopian Birr', 'Br'),
    ('EUR', 978, 2, 'Euro', '€'),
    ('FJD', 242, 2, 'Fiji Dollar', '$'),
    ('FKP', 238, 2, 'Falkland Islands Pound', '£'),
    ('GBP', 826, 2, 'Pound Sterling', '£'),
    ('GEL', 981, 2, 'Lari', ''),
    ('GHS', 936, 2, 'Ghana Cedi', 'GH₵'),
    ('GIP', 292, 2, 'Gibraltar Pound', '£'),
    ('GMD', 270, 2, 'Dalasi', 'D'),
    ('GNF', 324, 0, 'Guinean Franc', 'FG'),
    ('GTQ', 320, 2, 'Quetzal', 'Q'),
    ('GYD', 328, 2, 'Guyana Dollar', '$'),
    ('HKD', 344, 2, 'Hong Kong Dollar', 'HK$'),
    ('HNL', 340, 2, 'Lempira', 'L'),
    ('HTG', 332, 2, 'Gourde', 'G'),
    ('HUF', 348, 2, 'Forint', ''),
    ('IDR', 360, 2, 'Rupiah', 'Rp'),
    ('ILS', 376, 2, 'New Israeli Sheqel', '₪'),
    ('INR', 356, 2, 'Indian Rupee', '₹'),
    ('IQD', 368, 3, 'Iraqi Dinar', 'د.ع.‏'),
    ('IRR', 364, 2, 'Iranian Rial', ''),
    ('ISK', 352, 0, 'Iceland Krona', 'kr.'),
    ('JMD', 388, 2, 'Jamaican Dollar', '$'),
    ('JOD', 400, 3, 'Jordanian Dinar', 'د.أ.‏'),
    ('JPY', 392, 0, 'Yen', '¥'),
    ('KES', 404, 2, 'Kenyan Shilling', 'Ksh'),
    ('KGS', 417, 2, 'Som', 'сом'),
    ('KHR', 116, 2, 'Riel', '៛'),
    ('KMF', 174, 0, 'Comorian Franc ', 'CF'),
    ('KPW', 408, 2, 'North Korean Won', ''),
    ('KRW', 410, 0, 'Won', '₩'),
    ('KWD', 414, 3, 'Kuwaiti Dinar', 'د.ك.‏'),
    ('KYD', 136, 2, 'Cayman Islands Dollar', '$'),
    ('KZT', 398, 2, 'Tenge', '₸'),
    ('LAK', 418, 2, 'Lao Kip', '₭'),
    ('LBP', 422, 2, 'Lebanese Pound', 'ل.ل.‏'),
    ('LKR', 144, 2, 'Sri Lanka Rupee', 'රු.'),
    ('LRD', 430, 2, 'Liberian Dollar', '$'),
    ('LSL', 426, 2, 'Loti', ''),
    ('LYD', 434, 3, 'Libyan Dinar', 'د.ل.‏'),
    ('MAD', 504, 2, 'Moroccan Dirham', 'د.م.‏'),
    ('MDL', 498, 2, 'Moldovan Leu', 'L'),
    ('MGA', 969, 2, 'Malagasy Ariary', 'Ar'),
    ('MKD', 807, 2, 'Denar', 'ден.'),
    ('MMK', 104, 2, 'Kyat', 'K'),
    ('MNT', 496, 2, 'Tugrik', '₮'),
    ('MOP', 446, 2, 'Pataca', 'MOP$'),
    ('MRU', 929, 2, 'Ouguiya', 'أ.م.'),
    ('MUR', 480, 2, 'Mauritius Rupee', 'Rs'),
    ('MVR', 462, 2, 'Rufiyaa', 'Rf'),
    ('MWK', 454, 2, 'Malawi Kwacha', 'MK'),
    ('MXN', 484, 2, 'Mexican Peso', '$'),
    ('MYR', 458, 2, 'Malaysian Ringgit', 'RM'),
    ('MZN', 943, 2, 'Mozambique Metical', 'MTn'),
    ('NAD', 516, 2, 'Namibia Dollar', '$'),
    ('NGN', 566, 2, 'Naira', '₦'),
    ('NIO', 558, 2, 'Cordoba Oro', 'C$'),
    ('NOK', 578, 2, 'Norwegian Krone', 'kr'),
    ('NPR', 524, 2, 'Nepalese Rupee', 'नेरू'),
    ('NZD', 554, 2, 'New Zealand Dollar', '$'),
    ('OMR', 512, 3, 'Rial Omani', 'ر.ع.‏'),
    ('PAB', 590, 2, 'Balboa', 'B/.'),
    ('PEN', 604, 2, 'Sol', 'S/'),
    ('PGK', 598, 2, 'Kina', 'K'),
    ('PHP', 608, 2, 'Philippine Peso', '₱'),
    ('PKR', 586, 2, 'Pakistan Rupee', 'Rs'),
    ('PLN', 985, 2, 'Zloty', ''),
    ('PYG', 600, 0, 'Guarani', 'Gs.'),
    ('QAR', 634, 2, 'Qatari Rial', 'ر.ق.‏'),
    ('RON', 946, 2, 'Romanian Leu', ''),
    ('RSD', 941, 2, 'Serbian Dinar', ''),
    ('RUB', 643, 2, 'Russian Ruble', ''),
    ('RWF', 646, 0, 'Rwanda Franc', 'RF'),
    ('SAR', 682, 2, 'Saudi Riyal', 'ر.س.‏'),
    ('SBD',  90, 2, 'Solomon Islands Dollar', '$'),
    ('SCR', 690, 2, 'Seychelles Rupee', 'SR'),
    ('SDG', 938, 2, 'Sudanese Pound', ''),
    ('SEK', 752, 2, 'Swedish Krona', 'kr'),
    ('SGD', 702, 2, 'Singapore Dollar', '$'),
    ('SHP', 654, 2, 'Saint Helena Pound', '£'),
    ('SLE', 925, 2, 'Leone', 'Le'),
    ('SOS', 706, 2, 'Somali Shilling', 'S'),
    ('SRD', 968, 2, 'Surinam Dollar', '$'),
    ('SSP', 728, 2, 'South Sudanese Pound', '£'),
    ('STN', 930, 2, 'Dobra', 'Db'),
    ('SVC', 222, 2, 'El Salvador Colon', ''),
    ('SYP', 760, 2, 'Syrian Pound', ''),
    ('SZL', 748, 2, 'Lilangeni', 'E'),
    ('THB', 764, 2, 'Baht', ''),
    ('TJS', 972, 2, 'Somoni', ''),
    ('TMT', 934, 2, 'Turkmenistan New Manat', ''),
    ('TND', 788, 3, 'Tunisian Dinar', 'د.ت.‏'),
    ('TOP', 776, 2, 'Pa’anga', 'T$'),
    ('TRY', 949, 2, 'Turkish Lira', ''),
    ('TTD', 780, 2, 'Trinidad and Tobago Dollar', '$'),
    ('TWD', 901, 2, 'New Taiwan Dollar', 'NT$'),
    ('TZS', 834, 2, 'Tanzanian Shilling', 'TSh'),
    ('UAH', 980, 2, 'Hryvnia', '₴'),
    ('UGX', 800, 0, 'Uganda Shilling', 'USh'),
    ('USD', 840, 2, 'US Dollar', '$'),
    ('UYU', 858, 2, 'Peso Uruguayo', '$'),
    ('UZS', 860, 2, 'Uzbekistan Sum', ''),
    ('VED', 926, 2, 'Bolívar Soberano', ''),
    ('VES', 928, 2, 'Bolívar Soberano', 'Bs.S'),
    ('VND', 704, 0, 'Dong', '₫'),
    ('VUV', 548, 0, 'Vatu', 'VT'),
    ('WST', 882, 2, 'Tala', 'WS$'),
    ('XAD', 396, 2, 'Arab Accounting Dinar', ''),
    ('XAF', 950, 0, 'CFA Franc BEAC', 'FCFA'),
    ('XCD', 951, 2, 'East Caribbean Dollar', '$'),
    ('XCG', 532, 2, 'Caribbean Guilder', 'Cg.'),
    ('XOF', 952, 0, 'CFA Franc BCEAO', 'F CFA'),
    ('XPF', 953, 0, 'CFP Franc', 'FCFP'),
    ('YER', 886, 2, 'Yemeni Rial', 'ر.ي.‏'),
    ('ZAR', 710, 2, 'Rand', 'R'),
    ('ZMW', 967, 2, 'Zambian Kwacha', 'K'),
    ('ZWG', 924, 2, 'Zimbabwe Gold', '');

-- ____________________________________________________________________________
-- 2. Industries: the 11 sectors of the Global Industry Classification Standard (GICS).
-- Source, Title and BusinessRole stay empty. Each company has its own values.

INSERT INTO shared_industry (sector) VALUES
    ('Energy'),
    ('Materials'),
    ('Industrials'),
    ('Consumer Discretionary'),
    ('Consumer Staples'),
    ('Health Care'),
    ('Financials'),
    ('Information Technology'),
    ('Communication Services'),
    ('Utilities'),
    ('Real Estate');

-- ____________________________________________________________________________
-- 3. The first user, the company and the membership.

-- admin / password admin. Change it immediately.
INSERT INTO auth_user (password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) VALUES
    ('pbkdf2_sha256$1500000$GRj5fXhr4X2EQonVF5StfA$TeMQCgByi5gx7bsvLKmQZp9J6mToP4sAQ97lWGdmJbU=', NULL, TRUE, 'admin', '', '', '', TRUE, TRUE, now());

-- Change the name, the tax number and the address before you use the company.
INSERT INTO shared_company (name, slug, tax_number, base_currency_id, accounting_basis, allocate_to_oldest, address, is_active, created_at) VALUES
    ('My Company', 'my-company', '', 'ZAR', 'A', TRUE, '', TRUE, now());

INSERT INTO shared_membership (user_id, company_id, role, is_default, created_at)
SELECT u.id, c.id, 'OWN', TRUE, now()
FROM auth_user AS u, shared_company AS c
WHERE u.username = 'admin' AND c.slug = 'my-company';

-- ____________________________________________________________________________
-- 4. Financial years (March to February): the current year and the next year.
-- Each year has 12 periods (calendar months). All are open.

INSERT INTO accounting_fiscalyear (company_id, name, start_date, end_date, is_closed)
SELECT c.id, 'FY' || extract(year from y.start)::int, y.start::date,
       (y.start + interval '1 year' - interval '1 day')::date, FALSE
FROM shared_company AS c,
     (SELECT make_date(extract(year from CURRENT_DATE - interval '2 month')::int, 3, 1) + make_interval(years => n) AS start
      FROM generate_series(0, 1) AS n) AS y;

INSERT INTO accounting_period (company_id, fiscal_year_id, name, start_date, end_date, is_closed)
SELECT fy.company_id, fy.id, to_char(month, 'YYYY-MM'), month::date,
       (month + interval '1 month' - interval '1 day')::date, FALSE
FROM accounting_fiscalyear AS fy, generate_series(fy.start_date, fy.end_date, interval '1 month') AS month
ORDER BY month;

-- ____________________________________________________________________________
-- 5. Chart of accounts. The posting finds these accounts by name: "Accounts Receivable",
-- "Accounts Payable", "Suspense", "VAT Control", "Sales" and "Opening Balance Equity".
-- Do not change these names.
-- Add a bank account in the app. Its ledger account is "Bank". Give its opening balance there.

INSERT INTO accounting_account (company_id, code, name, type, normal_side, currency_id, is_active, description)
SELECT c.id, a.code, a.name, a.type, a.side, a.currency, TRUE, a.description
FROM shared_company AS c, (VALUES
    ('1000', 'Bank',                                          'CA',     'D', 'ZAR', 'The current account. Payments and receipts go through it.'),
    ('1050', 'Petty Cash',                                    'CA',     'D', NULL,  'Cash on hand.'),
    ('1100', 'Accounts Receivable',                           'CA',     'D', NULL,  'The open invoices. The posting finds it by name.'),
    ('1200', 'Inventory',                                     'CA',     'D', NULL,  'Stock for resale, at cost.'),
    ('1300', 'Prepaid Expenses',                              'CA',     'D', NULL,  NULL),
    ('1500', 'Computer Equipment',                            'NCA',    'D', NULL,  NULL),
    ('1510', 'Accumulated Depreciation — Computer Equipment', 'NCA',    'C', NULL,  NULL),
    ('1520', 'Vehicles',                                      'NCA',    'D', NULL,  NULL),
    ('1530', 'Accumulated Depreciation — Vehicles',           'NCA',    'C', NULL,  NULL),
    ('1900', 'Suspense',                                      'CA',     'D', NULL,  'Unallocated money (cash basis). The posting finds it by name.'),
    ('2000', 'Accounts Payable',                              'CL',     'C', NULL,  'The unpaid bills. The posting finds it by name.'),
    ('2100', 'VAT Control',                                   'CL',     'C', NULL,  'Output VAT less input VAT.'),
    ('2200', 'PAYE Payable',                                  'CL',     'C', NULL,  'Employees'' tax.'),
    ('2400', 'Accrued Expenses',                              'CL',     'C', NULL,  NULL),
    ('2500', 'Income Tax Payable',                            'CL',     'C', NULL,  NULL),
    ('3000', 'Share Capital',                                 'EQ',     'C', NULL,  NULL),
    ('3100', 'Retained Earnings',                             'EQ',     'C', NULL,  NULL),
    ('3200', 'Opening Balance Equity',                        'EQ',     'C', NULL,  'The other side of each opening balance. The posting finds it by name.'),
    ('4000', 'Sales',                                         'SALES',  'C', NULL,  'The invoices post here.'),
    ('4500', 'Interest Received',                             'OTHINC', 'C', NULL,  NULL),
    ('5000', 'Cost of Sales',                                 'COS',    'D', NULL,  'The cost of the stock that was sold.'),
    ('6000', 'Salaries and Wages',                            'EXP',    'D', NULL,  NULL),
    ('6100', 'Rent',                                          'EXP',    'D', NULL,  NULL),
    ('6200', 'Office Supplies',                               'EXP',    'D', NULL,  NULL),
    ('6300', 'Fuel and Travel',                               'EXP',    'D', NULL,  NULL),
    ('6400', 'Software and Hosting',                          'EXP',    'D', NULL,  NULL),
    ('6500', 'Bank Charges',                                  'EXP',    'D', NULL,  NULL),
    ('6600', 'Depreciation',                                  'EXP',    'D', NULL,  NULL),
    ('6700', 'Telephone and Internet',                        'EXP',    'D', NULL,  NULL),
    ('7000', 'Income Tax Expense',                            'TAX',    'D', NULL,  NULL),
    ('9000', 'Clearing Account',                              'FN',     'D', NULL,  'A floating account for transfers. It stays at zero.')
) AS a (code, name, type, side, currency, description);

-- Each accumulated depreciation account is a child of its asset account.
UPDATE accounting_account AS child
SET parent_id = parent.id
FROM accounting_account AS parent
WHERE parent.company_id = child.company_id
  AND (child.code, parent.code) IN (('1510', '1500'), ('1530', '1520'));

-- ____________________________________________________________________________
-- 6. Tax codes: South African VAT (VAT Act 89 of 1991).
-- The standard rate is 15% from 1 April 2018. If the company is not in South Africa, replace these codes.

INSERT INTO accounting_taxcode (company_id, code, name, kind, rate, valid_from, valid_to, input_account_id, output_account_id)
SELECT c.id, t.code, t.name, t.kind, t.rate, t.valid_from, NULL,
       CASE WHEN t.has_account THEN vat.id END, CASE WHEN t.has_account THEN vat.id END
FROM shared_company AS c
JOIN accounting_account AS vat ON vat.company_id = c.id AND vat.code = '2100',
(VALUES
    ('VAT15', 'Standard rated 15%', 'STD', 15.00, DATE '2018-04-01', TRUE),
    ('ZR',    'Zero rated',         'ZER',  0.00, DATE '1991-09-30', TRUE),
    ('EX',    'Exempt',             'EXE',  0.00, DATE '1991-09-30', FALSE)
) AS t (code, name, kind, rate, valid_from, has_account);

-- ____________________________________________________________________________
-- 7. Number sequences. NumberSequence.take() needs these rows. Each sequence starts at 1.

INSERT INTO accounting_numbersequence (company_id, name, prefix, next_number, padding)
SELECT c.id, s.name, s.prefix, 1, 5
FROM shared_company AS c, (VALUES
    ('invoice',   'INV-'),
    ('bill',      'BILL-'),
    ('quote',     'QUO-'),
    ('payment',   'PAY-'),
    ('statement', 'STM-'),
    ('supplier',  'SUP-')
) AS s (name, prefix);

COMMIT;