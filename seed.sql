-- ============================================================================
-- seed.sql — test data for the Pothos ERM project (PostgreSQL)
-- ----------------------------------------------------------------------------
-- The file is standalone: it needs only the schema of the migrations.
--
--     python manage.py migrate
--     psql "$DATABASE_URL" -f seed.sql      (or: python manage.py dbshell < seed.sql)
--
-- It REPLACES ALL DATA: it empties every table of the project first (the
-- migrations, the content types and the permissions stay). Thus you can run
-- it again at any time. It runs in one transaction: on an error nothing changes.
--
-- Each date is relative to the day of the run (CURRENT_DATE). Thus the
-- overdue invoices stay overdue, and the "not yet due" ones stay not yet due.
-- The data agrees with the posting rules of the app: each invoice, bill and
-- payment has its journal entries, and the documents agree with the journal.
--
-- Log in as admin / admin (owner), accountant / accountant, or viewer / viewer.
-- The files of filestore_storedfile are the two PDF files in var/filestore.
-- ============================================================================

BEGIN;

-- Django uses TIME_ZONE = 'UTC'. Thus "today" of the seed is the same day as in the app.
SET LOCAL TIME ZONE 'UTC';

TRUNCATE TABLE
    accounting_account,
    accounting_attachment,
    accounting_auditlog,
    accounting_bankaccount,
    accounting_banktransaction,
    accounting_budget,
    accounting_budgetline,
    accounting_costcentre,
    accounting_depreciationschedule,
    accounting_document,
    accounting_document_files,
    accounting_documentline,
    accounting_fiscalyear,
    accounting_fixedasset,
    accounting_journalentry,
    accounting_journalline,
    accounting_lead,
    accounting_note,
    accounting_note_files,
    accounting_numbersequence,
    accounting_payment,
    accounting_payment_files,
    accounting_paymentallocation,
    accounting_period,
    accounting_recurringinvoice,
    accounting_service,
    accounting_stockmovement,
    accounting_supplier,
    accounting_taxcode,
    auth_group,
    auth_group_permissions,
    auth_user,
    auth_user_groups,
    auth_user_user_permissions,
    django_admin_log,
    django_session,
    filestore_storedfile,
    inventory_item,
    inventory_item_files,
    inventory_itemrelationship,
    inventory_stocktakeschedule,
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
    shared_title
RESTART IDENTITY CASCADE;

-- Two helpers for this session only (pg_temp): the period of a date, and a content type.
CREATE OR REPLACE FUNCTION pg_temp.period_of(day date) RETURNS bigint LANGUAGE sql STABLE AS $$
    SELECT id FROM accounting_period WHERE company_id = 1 AND day BETWEEN start_date AND end_date
$$;
CREATE OR REPLACE FUNCTION pg_temp.ct(app text, name text) RETURNS integer LANGUAGE sql STABLE AS $$
    SELECT id FROM django_content_type WHERE app_label = app AND model = name
$$;

-- The content types of the generic links (Attachment, AuditLog). flush and migrate make them too.
INSERT INTO django_content_type (app_label, model) VALUES
    ('accounting', 'account'),
    ('accounting', 'bankaccount'),
    ('accounting', 'document'),
    ('accounting', 'journalentry'),
    ('accounting', 'note'),
    ('accounting', 'payment'),
    ('accounting', 'supplier')
ON CONFLICT (app_label, model) DO NOTHING;

-- ____________________________________________________________________________
-- Users. The password of each user is its user name. Change them before you share the data.

INSERT INTO auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) VALUES
    -- admin / password admin
    (1, 'pbkdf2_sha256$1500000$GRj5fXhr4X2EQonVF5StfA$TeMQCgByi5gx7bsvLKmQZp9J6mToP4sAQ97lWGdmJbU=', now() - interval '360 minutes', TRUE, 'admin', 'Nomsa', 'Khumalo', 'nomsa.khumalo@pothos.example', TRUE, TRUE, (CURRENT_DATE - 500 + time '08:00')::timestamptz),
    -- accountant / password accountant
    (2, 'pbkdf2_sha256$1500000$4FUVBVblACgxdPm0qTzJFh$0vo15+u0XUFDAu+IFc60zmWnJonwR6RMwXDRCki3oSY=', (CURRENT_DATE - 1 + time '16:20')::timestamptz, FALSE, 'accountant', 'Pieter', 'van Wyk', 'pieter.vanwyk@pothos.example', FALSE, TRUE, (CURRENT_DATE - 500 + time '08:00')::timestamptz),
    -- viewer / password viewer
    (3, 'pbkdf2_sha256$1500000$J0BuXQizn4oOBI6gZUpJaQ$Pq7ajXEoSxIdhnzYGIFoSy6uRtujoWgXCULJyEOZlsM=', NULL, FALSE, 'viewer', 'Jordan', 'Lee', 'jordan.lee@pothos.example', FALSE, TRUE, (CURRENT_DATE - 500 + time '08:00')::timestamptz);

-- ____________________________________________________________________________
-- Currencies, exchange rates and the lists of the forms

INSERT INTO shared_currency (alpha_code, numeric_code, minor_unit, name, symbol) VALUES
    ('ZAR', 710, 2, 'South African Rand', 'R'),
    ('USD', 840, 2, 'US Dollar', '$'),
    ('EUR', 978, 2, 'Euro', '€'),
    ('GBP', 826, 2, 'Pound Sterling', '£');

INSERT INTO shared_exchangerate (id, source_currency_id, target_currency_id, quotation_date, rate) VALUES
    (1, 'USD', 'ZAR', CURRENT_DATE - 30, 18.10250000),
    (2, 'USD', 'ZAR', CURRENT_DATE - 1, 17.94800000),
    (3, 'EUR', 'ZAR', CURRENT_DATE - 30, 19.61300000),
    (4, 'EUR', 'ZAR', CURRENT_DATE - 1, 19.48200000),
    (5, 'GBP', 'ZAR', CURRENT_DATE - 1, 23.40500000);

INSERT INTO shared_source (id, name) VALUES
    (1, 'Website'),
    (2, 'Referral'),
    (3, 'Trade show'),
    (4, 'Cold call'),
    (5, 'LinkedIn');

INSERT INTO shared_industry (id, sector) VALUES
    (1, 'Agriculture'),
    (2, 'Retail'),
    (3, 'Logistics'),
    (4, 'Manufacturing'),
    (5, 'Hospitality'),
    (6, 'Technology'),
    (7, 'Property'),
    (8, 'Energy');

INSERT INTO shared_title (id, job_title) VALUES
    (1, 'Owner'),
    (2, 'Chief Executive Officer'),
    (3, 'Finance Manager'),
    (4, 'Operations Manager'),
    (5, 'Procurement Officer');

INSERT INTO shared_businessrole (id, role) VALUES
    (1, 'Decision maker'),
    (2, 'Influencer'),
    (3, 'Gatekeeper'),
    (4, 'End user');

-- ____________________________________________________________________________
-- The company and the memberships

INSERT INTO shared_company (id, name, slug, tax_number, base_currency_id, accounting_basis, allocate_to_oldest, address, is_active, created_at) VALUES
    (1, 'Pothos Demo (Pty) Ltd', 'pothos-demo', '4550123456', 'ZAR', 'A', FALSE, 'Long Street, Cape Town City Centre, Cape Town, 8001, South Africa', TRUE, (CURRENT_DATE - 500 + time '08:00')::timestamptz);

INSERT INTO shared_membership (id, user_id, company_id, role, is_default, created_at) VALUES
    (1, 1, 1, 'OWN', TRUE, (CURRENT_DATE - 500 + time '08:30')::timestamptz),
    (2, 2, 1, 'ACC', TRUE, (CURRENT_DATE - 500 + time '08:30')::timestamptz),
    (3, 3, 1, 'VIE', TRUE, (CURRENT_DATE - 500 + time '08:30')::timestamptz);

-- Four financial years (March to February): two past years, the current year and the next year.
-- The oldest year is closed. Each year has 12 periods (calendar months).
INSERT INTO accounting_fiscalyear (id, company_id, name, start_date, end_date, is_closed)
SELECT n + 3, 1, 'FY' || extract(year from start)::int, start::date,
       (start + interval '1 year' - interval '1 day')::date, n = -2
FROM (SELECT n, make_date(extract(year from CURRENT_DATE - interval '2 month')::int, 3, 1) + make_interval(years => n) AS start FROM generate_series(-2, 1) AS n) AS years;

INSERT INTO accounting_period (company_id, fiscal_year_id, name, start_date, end_date, is_closed)
SELECT 1, fy.id, to_char(month, 'YYYY-MM'), month::date, (month + interval '1 month' - interval '1 day')::date,
       fy.is_closed
FROM accounting_fiscalyear AS fy, generate_series(fy.start_date, fy.end_date, interval '1 month') AS month
ORDER BY month;

-- ____________________________________________________________________________
-- Customers, leads and suppliers

INSERT INTO shared_entity (id, created_at, updated_at, created_by_id, company_id, name, type, display_name, description, owner_id, email, phone, address, is_active) VALUES
    (1, (CURRENT_DATE - 430 + time '09:00')::timestamptz, (CURRENT_DATE - 430 + time '09:00')::timestamptz, 1, 1, 'Karoo Fresh Produce (Pty) Ltd', 'O', 'Karoo Fresh', 'Fresh produce packer with two packhouses. Uses our scanners.', 1, 'accounts@karoofresh.example', '+27 23 555 0140', '14 Voortrekker Street
6970 Beaufort West', TRUE),
    (2, (CURRENT_DATE - 425 + time '09:00')::timestamptz, (CURRENT_DATE - 425 + time '09:00')::timestamptz, 2, 1, 'Halcyon Interiors CC', 'O', 'Halcyon', 'Interior design studio. Pays in parts.', 2, 'finance@halcyon.example', '+27 21 555 0172', '3 Bree Street
8001 Cape Town', TRUE),
    (3, (CURRENT_DATE - 420 + time '09:00')::timestamptz, (CURRENT_DATE - 420 + time '09:00')::timestamptz, 1, 1, 'Table Bay Marine (Pty) Ltd', 'O', 'Table Bay Marine', 'Ship chandler. Monthly support retainer.', 1, 'ap@tablebaymarine.example', '+27 21 555 0193', 'Quay 5, Duncan Dock
8001 Cape Town', TRUE),
    (4, (CURRENT_DATE - 410 + time '09:00')::timestamptz, (CURRENT_DATE - 410 + time '09:00')::timestamptz, 2, 1, 'Protea Print Works', 'O', NULL, 'Commercial printer. Often late with payments.', 2, 'admin@proteaprint.example', '+27 11 555 0121', '88 Main Reef Road
2001 Johannesburg', TRUE),
    (5, (CURRENT_DATE - 60 + time '09:00')::timestamptz, (CURRENT_DATE - 60 + time '09:00')::timestamptz, 1, 1, 'Lerato Molefe', 'I', 'Lerato', 'Independent consultant. Pays on receipt.', 1, 'lerato.molefe@mail.example', '+27 82 555 0188', '21 Jan Smuts Avenue
2196 Johannesburg', TRUE),
    (6, (CURRENT_DATE - 40 + time '09:00')::timestamptz, (CURRENT_DATE - 40 + time '09:00')::timestamptz, 1, 1, 'Umhlanga Coastal Hotels', 'O', NULL, 'Group of three hotels. Quote sent for the front desks.', 1, 'procurement@umhlangahotels.example', '+27 31 555 0150', 'Lighthouse Road
4320 Umhlanga', TRUE),
    (7, (CURRENT_DATE - 12 + time '09:00')::timestamptz, (CURRENT_DATE - 12 + time '09:00')::timestamptz, 2, 1, 'Garden Route Timber', 'O', NULL, 'New lead from the website form.', 2, 'info@grtimber.example', '+27 44 555 0117', 'N2 Industrial Park
6530 George', TRUE),
    (8, (CURRENT_DATE - 55 + time '09:00')::timestamptz, (CURRENT_DATE - 55 + time '09:00')::timestamptz, 1, 1, 'Vaal Metal Press', 'O', NULL, 'Wants a stock-count system for the warehouse.', 1, 'buyer@vaalmetal.example', '+27 16 555 0164', '7 Smelter Road
1939 Vanderbijlpark', TRUE),
    (9, (CURRENT_DATE - 35 + time '09:00')::timestamptz, (CURRENT_DATE - 35 + time '09:00')::timestamptz, 2, 1, 'Bergrivier Logistics', 'O', NULL, 'Fleet of 40 trucks. Waits for our proposal.', 2, 'ops@bergrivier.example', '+27 22 555 0109', '12 Station Road
7620 Wellington', TRUE),
    (10, (CURRENT_DATE - 20 + time '09:00')::timestamptz, (CURRENT_DATE - 20 + time '09:00')::timestamptz, 1, 1, 'Daniel Naidoo', 'I', NULL, 'Owner of a small online shop.', 1, 'daniel.naidoo@mail.example', '+27 83 555 0133', '5 Florida Road
4001 Durban', TRUE),
    (11, (CURRENT_DATE - 150 + time '09:00')::timestamptz, (CURRENT_DATE - 150 + time '09:00')::timestamptz, 1, 1, 'Sandton Data Centre', 'O', NULL, 'Chose another supplier.', 1, 'facilities@sandtondc.example', '+27 11 555 0198', 'Rivonia Road
2196 Sandton', FALSE),
    (12, (CURRENT_DATE - 410 + time '09:00')::timestamptz, (CURRENT_DATE - 410 + time '09:00')::timestamptz, 2, 1, 'Cape Office Supplies (Pty) Ltd', 'O', NULL, 'Supplier: Thabo Nkosi.', 2, 'orders@capeoffice.example', '+27 21 555 0111', '40 Voortrekker Road
7500 Parow', TRUE),
    (13, (CURRENT_DATE - 390 + time '09:00')::timestamptz, (CURRENT_DATE - 390 + time '09:00')::timestamptz, 2, 1, 'Highveld Fuel Services', 'O', NULL, 'Supplier: Marika du Plessis.', 2, 'accounts@highveldfuel.example', '+27 11 555 0155', 'N1 Service Road
1685 Midrand', TRUE),
    (14, (CURRENT_DATE - 370 + time '09:00')::timestamptz, (CURRENT_DATE - 370 + time '09:00')::timestamptz, 2, 1, 'Atlantic Cloud Hosting', 'O', NULL, 'Supplier: Support desk.', 2, 'billing@atlanticcloud.example', '+27 21 555 0166', 'Unit 4, Century City
7441 Cape Town', TRUE),
    (15, (CURRENT_DATE - 350 + time '09:00')::timestamptz, (CURRENT_DATE - 350 + time '09:00')::timestamptz, 2, 1, 'Metro Property Management', 'O', NULL, 'Supplier: Lease office.', 2, 'leases@metroproperty.example', '+27 21 555 0177', '1 Thibault Square
8001 Cape Town', TRUE),
    (16, (CURRENT_DATE - 330 + time '09:00')::timestamptz, (CURRENT_DATE - 330 + time '09:00')::timestamptz, 2, 1, 'Coastal Stock Distributors', 'O', NULL, 'Supplier: Ravi Pillay.', 2, 'sales@coastalstock.example', '+27 31 555 0144', '18 Umgeni Road
4001 Durban', TRUE);

INSERT INTO shared_organizationprofile (entity_id, legal_name, tax_number, registration_number, url, industry_id) VALUES
    (1, 'Karoo Fresh Produce (Pty) Ltd', '4120556781', '2011/104552/07', 'https://karoofresh.example', 1),
    (2, 'Halcyon Interiors CC', '4870223904', '2007/033871/23', 'https://halcyon.example', 2),
    (3, 'Table Bay Marine (Pty) Ltd', '4300118826', '2015/220198/07', 'https://tablebaymarine.example', 3),
    (4, 'Protea Print Works (Pty) Ltd', '4590331287', '2009/018455/07', NULL, 4),
    (6, 'Umhlanga Coastal Hotels (Pty) Ltd', '4410778213', '2002/011247/07', 'https://umhlangahotels.example', 5),
    (7, 'Garden Route Timber (Pty) Ltd', NULL, NULL, 'https://grtimber.example', 4),
    (8, 'Vaal Metal Press (Pty) Ltd', '4210664009', '1998/006632/07', NULL, 4),
    (9, 'Bergrivier Logistics (Pty) Ltd', '4930017742', '2013/090321/07', 'https://bergrivier.example', 3),
    (11, 'Sandton Data Centre (Pty) Ltd', '4780119340', '2016/004418/07', NULL, 6),
    (12, 'Cape Office Supplies (Pty) Ltd', '4510188112', '2001/014411/07', 'https://capeoffice.example', 2),
    (13, 'Highveld Fuel Services', '4520288212', '2002/024411/07', 'https://highveld.example', 8),
    (14, 'Atlantic Cloud Hosting', '4530388312', '2003/034411/07', 'https://atlantic.example', 6),
    (15, 'Metro Property Management', '4540488412', '2004/044411/07', 'https://metro.example', 7),
    (16, 'Coastal Stock Distributors', '4550588512', '2005/054411/07', 'https://coastal.example', 2);

INSERT INTO shared_individualprofile (entity_id, first_name, last_name, date_of_birth, role_id, title_id) VALUES
    (5, 'Lerato', 'Molefe', DATE '1988-04-12', 1, 1),
    (10, 'Daniel', 'Naidoo', NULL, 4, 1);

INSERT INTO accounting_lead (id, created_at, updated_at, created_by_id, company_id, entity_id, source_id, description, status, stage, size, qualifying_score, temperature, responsiveness, turn) VALUES
    (1, (CURRENT_DATE - 400 + time '09:00')::timestamptz, (CURRENT_DATE - 30 + time '09:00')::timestamptz, 1, 1, 1, 2, 'Two packhouses. Won after the pilot.', 'WL', 'C', 120, 85, 'H', NULL, FALSE),
    (2, (CURRENT_DATE - 400 + time '09:00')::timestamptz, (CURRENT_DATE - 30 + time '09:00')::timestamptz, 1, 1, 2, 1, 'Showroom fit-out and support.', 'WL', 'C', 60, 70, 'W', NULL, FALSE),
    (3, (CURRENT_DATE - 400 + time '09:00')::timestamptz, (CURRENT_DATE - 30 + time '09:00')::timestamptz, 1, 1, 3, 3, 'Met at the maritime trade show.', 'WL', 'C', 200, 90, 'H', NULL, FALSE),
    (4, (CURRENT_DATE - 400 + time '09:00')::timestamptz, (CURRENT_DATE - 30 + time '09:00')::timestamptz, 1, 1, 4, 4, 'Small account. Watch the payments.', 'WL', 'C', 40, 55, 'LW', NULL, FALSE),
    (5, (CURRENT_DATE - 400 + time '09:00')::timestamptz, (CURRENT_DATE - 30 + time '09:00')::timestamptz, 1, 1, 5, 5, 'Consultant who resells our setup work.', 'WL', 'C', 5, 60, 'W', NULL, FALSE),
    (6, (CURRENT_DATE - 60 + time '09:00')::timestamptz, (CURRENT_DATE - 1 + time '09:00')::timestamptz, 1, 1, 6, 2, 'Quote sent for three front desks.', 'QO', 'E', 500, 75, 'W', now() - interval '2 days 3 hours', TRUE),
    (7, (CURRENT_DATE - 60 + time '09:00')::timestamptz, (CURRENT_DATE - 30 + time '09:00')::timestamptz, 1, 1, 7, 1, 'Asked for a call back.', 'NL', 'N', 300, 20, 'CL', NULL, TRUE),
    (8, (CURRENT_DATE - 60 + time '09:00')::timestamptz, (CURRENT_DATE - 1 + time '09:00')::timestamptz, 1, 1, 8, 3, 'Budget approved for next quarter.', 'OL', 'Q', 150, 60, 'LW', now() - interval '4 days 3 hours', FALSE),
    (9, (CURRENT_DATE - 60 + time '09:00')::timestamptz, (CURRENT_DATE - 1 + time '09:00')::timestamptz, 1, 1, 9, 5, 'Waits for the fleet proposal.', 'IP', 'A', 250, 80, 'H', now() - interval '1 days 3 hours', FALSE),
    (10, (CURRENT_DATE - 60 + time '09:00')::timestamptz, (CURRENT_DATE - 1 + time '09:00')::timestamptz, 1, 1, 10, 1, 'Small online shop. Price sensitive.', 'OL', 'P', 3, 35, 'N', now() - interval '6 days 3 hours', TRUE),
    (11, (CURRENT_DATE - 400 + time '09:00')::timestamptz, (CURRENT_DATE - 30 + time '09:00')::timestamptz, 1, 1, 11, 4, 'Lost on price.', 'LL', 'C', 800, 30, 'I', NULL, FALSE);

INSERT INTO accounting_supplier (id, created_at, updated_at, created_by_id, company_id, entity_id, code, contact, terms, bank_account) VALUES
    (1, (CURRENT_DATE - 410 + time '09:00')::timestamptz, (CURRENT_DATE - 410 + time '09:00')::timestamptz, 2, 1, 12, 'SUP-00001', 'Thabo Nkosi', '30', 'FNB 62012345678, branch 250655'),
    (2, (CURRENT_DATE - 390 + time '09:00')::timestamptz, (CURRENT_DATE - 390 + time '09:00')::timestamptz, 2, 1, 13, 'SUP-00002', 'Marika du Plessis', '15', 'ABSA 4071234567, branch 632005'),
    (3, (CURRENT_DATE - 370 + time '09:00')::timestamptz, (CURRENT_DATE - 370 + time '09:00')::timestamptz, 2, 1, 14, 'SUP-00003', 'Support desk', 'M', 'Nedbank 1012345678, branch 198765'),
    (4, (CURRENT_DATE - 350 + time '09:00')::timestamptz, (CURRENT_DATE - 350 + time '09:00')::timestamptz, 2, 1, 15, 'SUP-00004', 'Lease office', 'R', 'Standard Bank 071234567, branch 051001'),
    (5, (CURRENT_DATE - 330 + time '09:00')::timestamptz, (CURRENT_DATE - 330 + time '09:00')::timestamptz, 2, 1, 16, 'SUP-00005', 'Ravi Pillay', '30', 'Capitec 1234567890, branch 470010');

INSERT INTO shared_project (id, company_id, code, name, customer_id, start_date, end_date, is_active) VALUES
    (1, 1, 'PRJ-001', 'Karoo packhouse rollout', 1, CURRENT_DATE - 170, CURRENT_DATE + 60, TRUE),
    (2, 1, 'PRJ-002', 'Halcyon showroom fit-out', 2, CURRENT_DATE - 160, CURRENT_DATE - 10, FALSE),
    (3, 1, 'PRJ-003', 'Internal systems upgrade', NULL, CURRENT_DATE - 210, NULL, TRUE);

-- ____________________________________________________________________________
-- Chart of accounts, tax codes, cost centres, services and bank accounts

INSERT INTO accounting_account (id, company_id, code, name, type, normal_side, parent_id, currency_id, is_active, description) VALUES
    (1, 1, '1000', 'Main Bank Account', 'CA', 'D', NULL, 'ZAR', TRUE, 'The current account. Payments and receipts go through it.'),
    (2, 1, '1010', 'Savings Account', 'CA', 'D', NULL, 'ZAR', TRUE, 'Money market savings. Earns monthly interest.'),
    (3, 1, '1050', 'Petty Cash', 'CA', 'D', NULL, NULL, TRUE, 'Cash on hand at the office.'),
    (4, 1, '1100', 'Accounts Receivable', 'CA', 'D', NULL, NULL, TRUE, 'The open invoices. The posting finds it by name.'),
    (5, 1, '1200', 'Inventory', 'CA', 'D', NULL, NULL, TRUE, 'Stock for resale, at cost.'),
    (6, 1, '1300', 'Prepaid Expenses', 'CA', 'D', NULL, NULL, TRUE, NULL),
    (7, 1, '1500', 'Computer Equipment', 'NCA', 'D', NULL, NULL, TRUE, 'Laptops and printers.'),
    (8, 1, '1510', 'Accumulated Depreciation — Computer Equipment', 'NCA', 'D', 7, NULL, TRUE, NULL),
    (9, 1, '1520', 'Vehicles', 'NCA', 'D', NULL, NULL, TRUE, 'The delivery vehicle.'),
    (10, 1, '1530', 'Accumulated Depreciation — Vehicles', 'NCA', 'D', 9, NULL, TRUE, NULL),
    (11, 1, '1900', 'Suspense', 'CA', 'D', NULL, NULL, TRUE, 'Unallocated money (cash basis). The posting finds it by name.'),
    (12, 1, '2000', 'Accounts Payable', 'CL', 'C', NULL, NULL, TRUE, 'The unpaid bills. The posting finds it by name.'),
    (13, 1, '2100', 'VAT Control', 'CL', 'C', NULL, NULL, TRUE, 'Output VAT less input VAT.'),
    (14, 1, '2200', 'PAYE Payable', 'CL', 'C', NULL, NULL, TRUE, 'Employees'' tax, paid monthly.'),
    (15, 1, '2300', 'Credit Card', 'CL', 'C', NULL, 'ZAR', TRUE, 'The company credit card.'),
    (16, 1, '2400', 'Accrued Expenses', 'CL', 'C', NULL, NULL, TRUE, NULL),
    (17, 1, '2500', 'Income Tax Payable', 'CL', 'C', NULL, NULL, TRUE, NULL),
    (18, 1, '2700', 'Vehicle Finance Loan', 'NCL', 'C', NULL, NULL, TRUE, '60 months, monthly instalments.'),
    (19, 1, '3000', 'Share Capital', 'EQ', 'C', NULL, NULL, TRUE, NULL),
    (20, 1, '3100', 'Retained Earnings', 'EQ', 'C', NULL, NULL, TRUE, NULL),
    (21, 1, '4000', 'Sales', 'SALES', 'C', NULL, NULL, TRUE, 'The invoices post here.'),
    (22, 1, '4500', 'Interest Received', 'OTHINC', 'C', NULL, NULL, TRUE, NULL),
    (23, 1, '5000', 'Cost of Sales', 'COS', 'D', NULL, NULL, TRUE, 'The cost of the stock that was sold.'),
    (24, 1, '6000', 'Salaries and Wages', 'EXP', 'D', NULL, NULL, TRUE, NULL),
    (25, 1, '6100', 'Rent', 'EXP', 'D', NULL, NULL, TRUE, NULL),
    (26, 1, '6200', 'Office Supplies', 'EXP', 'D', NULL, NULL, TRUE, NULL),
    (27, 1, '6300', 'Fuel and Travel', 'EXP', 'D', NULL, NULL, TRUE, NULL),
    (28, 1, '6400', 'Software and Hosting', 'EXP', 'D', NULL, NULL, TRUE, NULL),
    (29, 1, '6500', 'Bank Charges', 'EXP', 'D', NULL, NULL, TRUE, NULL),
    (30, 1, '6600', 'Depreciation', 'EXP', 'D', NULL, NULL, TRUE, NULL),
    (31, 1, '6700', 'Telephone and Internet', 'EXP', 'D', NULL, NULL, TRUE, NULL),
    (32, 1, '7000', 'Income Tax Expense', 'TAX', 'D', NULL, NULL, TRUE, NULL),
    (33, 1, '9000', 'Clearing Account', 'FN', 'D', NULL, NULL, TRUE, 'A floating account for transfers. It stays at zero.');

INSERT INTO accounting_taxcode (id, company_id, code, name, kind, rate, valid_from, valid_to, input_account_id, output_account_id) VALUES
    (1, 1, 'VAT15', 'Standard rated 15%', 'STD', 15.00, DATE '2018-04-01', NULL, 13, 13),
    (2, 1, 'VAT14', 'Standard rated 14% (before April 2018)', 'STD', 14.00, DATE '2015-01-01', DATE '2018-03-31', 13, 13),
    (3, 1, 'ZR', 'Zero rated (exports)', 'ZER', 0.00, DATE '2018-04-01', NULL, 13, 13),
    (4, 1, 'EX', 'Exempt', 'EXE', 0.00, DATE '2018-04-01', NULL, NULL, NULL);

INSERT INTO accounting_costcentre (id, company_id, code, name, is_active) VALUES
    (1, 1, 'SAL', 'Sales', TRUE),
    (2, 1, 'OPS', 'Operations', TRUE),
    (3, 1, 'ADM', 'Administration', TRUE),
    (4, 1, 'LEG', 'Legacy branch (closed)', FALSE);

INSERT INTO accounting_service (id, company_id, code, name, account_id) VALUES
    (1, 1, 'CONSULT', 'Consulting (per hour)', 21),
    (2, 1, 'INSTALL', 'Installation and setup', 21),
    (3, 1, 'SUPPORT', 'Support retainer (monthly)', 21),
    (4, 1, 'EXPORT', 'Export documentation', 21);

INSERT INTO accounting_bankaccount (id, company_id, name, account_number, sort_code, iban, currency_id, account_id, is_active) VALUES
    (1, 1, 'Main Bank Account', '62012345678', '250655', '', 'ZAR', 1, TRUE),
    (2, 1, 'Savings Account', '74098765432', '250655', '', 'ZAR', 2, TRUE);

-- ____________________________________________________________________________
-- Inventory and stored files

INSERT INTO inventory_item (id, sku, tag, serial, name, cost, depreciate, lifespan, lifeunits, item_type, description, obsoleted, active) VALUES
    (1, 'SCN-BS200', NULL, NULL, 'Barcode Scanner BS-200', 2100.00, FALSE, NULL, NULL, 'STOCK', 'Handheld scanner with a USB cradle.', FALSE, TRUE),
    (2, 'LBL-100150', NULL, NULL, 'Thermal Label Roll 100x150', 95.00, FALSE, NULL, NULL, 'STOCK', '500 labels a roll.', FALSE, TRUE),
    (3, 'LTP-14-32', 'a3f1c9e2b7d84f60a1e5c3b9d2f7e801', 'LTP-2026-0001', 'Laptop 14 inch, 32 GB', 18000.00, TRUE, 3.00, 'Y', 'ASSET', 'Issued to the operations team.', FALSE, TRUE),
    (4, 'LTP-14-32', 'b4e2d0f3c8e95a71b2f6d4c0e3a8f912', 'LTP-2026-0002', 'Laptop 14 inch, 32 GB', 18000.00, TRUE, 3.00, 'Y', 'ASSET', 'Issued to the finance team.', FALSE, TRUE),
    (5, 'LTP-14-32', 'c5f3e1a4d9fa6b82c3a7e5d1f4b9a023', 'LTP-2026-0003', 'Laptop 14 inch, 32 GB', 18000.00, TRUE, 3.00, 'Y', 'ASSET', 'Spare unit.', FALSE, TRUE),
    (6, 'PRN-LJ400', 'd6a4f2b5eaab7c93d4b8f6e2a5c0b134', 'PRN-2019-0001', 'Laser Printer (old)', 8000.00, TRUE, 4.00, 'Y', 'ASSET', 'Sold when it was fully depreciated.', TRUE, FALSE),
    (7, 'TNR-CF259', NULL, NULL, 'Printer Toner Cartridge', 690.00, FALSE, NULL, NULL, 'CONSUMABLE', NULL, FALSE, TRUE),
    (8, 'BRK-100', NULL, NULL, 'Mounting Bracket', 85.00, FALSE, NULL, NULL, 'COMPONENT', NULL, FALSE, TRUE),
    (9, 'PSU-12V2A', NULL, NULL, 'Power Supply 12V 2A', 140.00, FALSE, 18.00, 'M', 'COMPONENT', 'Replace when faulty.', FALSE, TRUE),
    (10, 'KIT-SCN-01', NULL, NULL, 'Scanner Station Kit', 2325.00, FALSE, NULL, NULL, 'STOCK', 'A scanner with its bracket and power supply.', FALSE, TRUE);

INSERT INTO inventory_itemrelationship (id, parent_id, child_id, relationship_type, quantity) VALUES
    (1, 10, 1, 'CONTAINS', 1.000),
    (2, 10, 8, 'CONTAINS', 1.000),
    (3, 10, 9, 'CONTAINS', 1.000),
    (4, 1, 2, 'ACCESSORY', 2.000),
    (5, 1, 9, 'DEPENDENCY', 1.000);

INSERT INTO inventory_stocktakeschedule (id, item_id, interval_days, start_date, next_due, active) VALUES
    (1, 1, 30, CURRENT_DATE - 60, CURRENT_DATE, TRUE),
    (2, 2, 90, CURRENT_DATE - 100, CURRENT_DATE - 10, TRUE);

INSERT INTO filestore_storedfile (id, file, original_name, content_type, size, checksum, uploaded_by_id, created_at) VALUES
    -- var/filestore/2026/09: a quote PDF
    ('e38832a5-13f0-470e-a81b-428b75bae864', '2026/09/e38832a5-13f0-470e-a81b-428b75bae864.pdf', 'QUO-2026-0017.pdf', 'application/pdf', 15131, 'fab7d770938240bd7eae2356106f5a879fa9c1e107437df8502793375c1bffdf', 1, (CURRENT_DATE - 9 + time '11:00')::timestamptz),
    -- var/filestore/2026/10: an invoice PDF
    ('3733b825-7fcd-4d7e-8d4b-5f0b53f04d04', '2026/10/3733b825-7fcd-4d7e-8d4b-5f0b53f04d04.pdf', 'INV-00014.pdf', 'application/pdf', 14500, '1e3f4ee915dc788ac325de08939d56aea4d030bc64de0308964161bf9d142e60', 2, (CURRENT_DATE - 2 + time '10:00')::timestamptz);

INSERT INTO inventory_item_files (item_id, storedfile_id) VALUES
    (3, '3733b825-7fcd-4d7e-8d4b-5f0b53f04d04');

INSERT INTO accounting_attachment (id, company_id, content_type_id, object_id, source, file, filename, uploaded_at) VALUES
    -- The bank statement of the main account
    (1, 1, pg_temp.ct('accounting', 'bankaccount'), 1, 'Bank Statements', 'attachments/seed/main-account-statement.csv', 'main-account-statement.csv', now() - interval '375 minutes'),
    -- The receipt of CC-001
    (2, 1, pg_temp.ct('accounting', 'journalentry'), 225, 'Receipts', 'attachments/seed/software-licence-receipt.pdf', 'software-licence-receipt.pdf', (CURRENT_DATE - 60 + time '12:00')::timestamptz);

-- ____________________________________________________________________________
-- Journal entries and their lines. Each entry balances.

INSERT INTO accounting_journalentry (id, created_at, updated_at, created_by_id, company_id, date, period_id, entry_type, status, basis, reference, narration, source_id, reverses_id, posted_at) VALUES
    (1, (CURRENT_DATE - 420 + time '08:30')::timestamptz, (CURRENT_DATE - 420 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 420, pg_temp.period_of(CURRENT_DATE - 420), 'G', 'P', 'B', 'OB-001', 'Opening balances', NULL, NULL, (CURRENT_DATE - 420 + time '17:00')::timestamptz),
    (2, (CURRENT_DATE - 390 + time '08:30')::timestamptz, (CURRENT_DATE - 390 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 390, pg_temp.period_of(CURRENT_DATE - 390), 'S', 'P', 'A', 'INV-00001', 'Karoo Fresh Produce (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 390 + time '17:00')::timestamptz),
    (3, (CURRENT_DATE - 375 + time '08:30')::timestamptz, (CURRENT_DATE - 375 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 375, pg_temp.period_of(CURRENT_DATE - 375), 'S', 'P', 'A', 'INV-00002', 'Halcyon Interiors CC', NULL, NULL, (CURRENT_DATE - 375 + time '17:00')::timestamptz),
    (4, (CURRENT_DATE - 364 + time '08:30')::timestamptz, (CURRENT_DATE - 364 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 364, pg_temp.period_of(CURRENT_DATE - 364), 'CR', 'P', 'A', 'PAY-00001', 'Karoo Fresh Produce (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 364 + time '17:00')::timestamptz),
    (5, (CURRENT_DATE - 364 + time '08:30')::timestamptz, (CURRENT_DATE - 364 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 364, pg_temp.period_of(CURRENT_DATE - 364), 'CR', 'P', 'C', 'PAY-00001', 'Karoo Fresh Produce (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 364 + time '17:00')::timestamptz),
    (6, (CURRENT_DATE - 360 + time '08:30')::timestamptz, (CURRENT_DATE - 360 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 360, pg_temp.period_of(CURRENT_DATE - 360), 'S', 'P', 'A', 'INV-00003', 'Table Bay Marine (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 360 + time '17:00')::timestamptz),
    (7, (CURRENT_DATE - 349 + time '08:30')::timestamptz, (CURRENT_DATE - 349 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 349, pg_temp.period_of(CURRENT_DATE - 349), 'CR', 'P', 'A', 'PAY-00002', 'Halcyon Interiors CC', NULL, NULL, (CURRENT_DATE - 349 + time '17:00')::timestamptz),
    (8, (CURRENT_DATE - 349 + time '08:30')::timestamptz, (CURRENT_DATE - 349 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 349, pg_temp.period_of(CURRENT_DATE - 349), 'CR', 'P', 'C', 'PAY-00002', 'Halcyon Interiors CC (cash basis)', NULL, NULL, (CURRENT_DATE - 349 + time '17:00')::timestamptz),
    (9, (CURRENT_DATE - 345 + time '08:30')::timestamptz, (CURRENT_DATE - 345 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 345, pg_temp.period_of(CURRENT_DATE - 345), 'S', 'P', 'A', 'INV-00004', 'Protea Print Works', NULL, NULL, (CURRENT_DATE - 345 + time '17:00')::timestamptz),
    (10, (CURRENT_DATE - 345 + time '08:30')::timestamptz, (CURRENT_DATE - 345 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 345, pg_temp.period_of(CURRENT_DATE - 345), 'P', 'P', 'A', 'BILL-00001', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 345 + time '17:00')::timestamptz),
    (11, (CURRENT_DATE - 340 + time '08:30')::timestamptz, (CURRENT_DATE - 340 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 340, pg_temp.period_of(CURRENT_DATE - 340), 'CP', 'P', 'B', 'BCH-001', 'Bank charges', NULL, NULL, (CURRENT_DATE - 340 + time '17:00')::timestamptz),
    (12, (CURRENT_DATE - 340 + time '08:30')::timestamptz, (CURRENT_DATE - 340 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 340, pg_temp.period_of(CURRENT_DATE - 340), 'CP', 'P', 'A', 'PAY-00003', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 340 + time '17:00')::timestamptz),
    (13, (CURRENT_DATE - 340 + time '08:30')::timestamptz, (CURRENT_DATE - 340 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 340, pg_temp.period_of(CURRENT_DATE - 340), 'CP', 'P', 'C', 'PAY-00003', 'Atlantic Cloud Hosting (cash basis)', NULL, NULL, (CURRENT_DATE - 340 + time '17:00')::timestamptz),
    (14, (CURRENT_DATE - 340 + time '08:30')::timestamptz, (CURRENT_DATE - 340 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 340, pg_temp.period_of(CURRENT_DATE - 340), 'CP', 'P', 'B', 'VAT-001', 'VAT return paid', NULL, NULL, (CURRENT_DATE - 340 + time '17:00')::timestamptz),
    (15, (CURRENT_DATE - 335 + time '08:30')::timestamptz, (CURRENT_DATE - 335 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 335, pg_temp.period_of(CURRENT_DATE - 335), 'G', 'P', 'B', 'SAL-001', 'Salaries for the month', NULL, NULL, (CURRENT_DATE - 335 + time '17:00')::timestamptz),
    (16, (CURRENT_DATE - 335 + time '08:30')::timestamptz, (CURRENT_DATE - 335 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 335, pg_temp.period_of(CURRENT_DATE - 335), 'P', 'P', 'A', 'BILL-00002', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 335 + time '17:00')::timestamptz),
    (17, (CURRENT_DATE - 334 + time '08:30')::timestamptz, (CURRENT_DATE - 334 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 334, pg_temp.period_of(CURRENT_DATE - 334), 'CR', 'P', 'A', 'PAY-00004', 'Table Bay Marine (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 334 + time '17:00')::timestamptz),
    (18, (CURRENT_DATE - 334 + time '08:30')::timestamptz, (CURRENT_DATE - 334 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 334, pg_temp.period_of(CURRENT_DATE - 334), 'CR', 'P', 'C', 'PAY-00004', 'Table Bay Marine (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 334 + time '17:00')::timestamptz),
    (19, (CURRENT_DATE - 331 + time '08:30')::timestamptz, (CURRENT_DATE - 331 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 331, pg_temp.period_of(CURRENT_DATE - 331), 'P', 'P', 'A', 'BILL-00003', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 331 + time '17:00')::timestamptz),
    (20, (CURRENT_DATE - 331 + time '08:30')::timestamptz, (CURRENT_DATE - 331 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 331, pg_temp.period_of(CURRENT_DATE - 331), 'CP', 'P', 'A', 'PAY-00005', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 331 + time '17:00')::timestamptz),
    (21, (CURRENT_DATE - 331 + time '08:30')::timestamptz, (CURRENT_DATE - 331 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 331, pg_temp.period_of(CURRENT_DATE - 331), 'CP', 'P', 'C', 'PAY-00005', 'Metro Property Management (cash basis)', NULL, NULL, (CURRENT_DATE - 331 + time '17:00')::timestamptz),
    (22, (CURRENT_DATE - 330 + time '08:30')::timestamptz, (CURRENT_DATE - 330 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 330, pg_temp.period_of(CURRENT_DATE - 330), 'S', 'P', 'A', 'INV-00005', 'Karoo Fresh Produce (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 330 + time '17:00')::timestamptz),
    (23, (CURRENT_DATE - 328 + time '08:30')::timestamptz, (CURRENT_DATE - 328 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 328, pg_temp.period_of(CURRENT_DATE - 328), 'CP', 'P', 'B', 'PAYE-001', 'PAYE paid', NULL, NULL, (CURRENT_DATE - 328 + time '17:00')::timestamptz),
    (24, (CURRENT_DATE - 323 + time '08:30')::timestamptz, (CURRENT_DATE - 323 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 323, pg_temp.period_of(CURRENT_DATE - 323), 'CP', 'P', 'A', 'PAY-00006', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 323 + time '17:00')::timestamptz),
    (25, (CURRENT_DATE - 323 + time '08:30')::timestamptz, (CURRENT_DATE - 323 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 323, pg_temp.period_of(CURRENT_DATE - 323), 'CP', 'P', 'C', 'PAY-00006', 'Highveld Fuel Services (cash basis)', NULL, NULL, (CURRENT_DATE - 323 + time '17:00')::timestamptz),
    (26, (CURRENT_DATE - 320 + time '08:30')::timestamptz, (CURRENT_DATE - 320 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 320, pg_temp.period_of(CURRENT_DATE - 320), 'CR', 'P', 'B', 'INT-001', 'Interest received', NULL, NULL, (CURRENT_DATE - 320 + time '17:00')::timestamptz),
    (27, (CURRENT_DATE - 320 + time '08:30')::timestamptz, (CURRENT_DATE - 320 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 320, pg_temp.period_of(CURRENT_DATE - 320), 'P', 'P', 'A', 'BILL-00004', 'Cape Office Supplies (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 320 + time '17:00')::timestamptz),
    (28, (CURRENT_DATE - 319 + time '08:30')::timestamptz, (CURRENT_DATE - 319 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 319, pg_temp.period_of(CURRENT_DATE - 319), 'CR', 'P', 'A', 'PAY-00007', 'Protea Print Works', NULL, NULL, (CURRENT_DATE - 319 + time '17:00')::timestamptz),
    (29, (CURRENT_DATE - 319 + time '08:30')::timestamptz, (CURRENT_DATE - 319 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 319, pg_temp.period_of(CURRENT_DATE - 319), 'CR', 'P', 'C', 'PAY-00007', 'Protea Print Works (cash basis)', NULL, NULL, (CURRENT_DATE - 319 + time '17:00')::timestamptz),
    (30, (CURRENT_DATE - 315 + time '08:30')::timestamptz, (CURRENT_DATE - 315 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 315, pg_temp.period_of(CURRENT_DATE - 315), 'S', 'P', 'A', 'INV-00006', 'Table Bay Marine (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 315 + time '17:00')::timestamptz),
    (31, (CURRENT_DATE - 315 + time '08:30')::timestamptz, (CURRENT_DATE - 315 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 315, pg_temp.period_of(CURRENT_DATE - 315), 'P', 'P', 'A', 'BILL-00005', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 315 + time '17:00')::timestamptz),
    (32, (CURRENT_DATE - 310 + time '08:30')::timestamptz, (CURRENT_DATE - 310 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 310, pg_temp.period_of(CURRENT_DATE - 310), 'CP', 'P', 'B', 'BCH-002', 'Bank charges', NULL, NULL, (CURRENT_DATE - 310 + time '17:00')::timestamptz),
    (33, (CURRENT_DATE - 310 + time '08:30')::timestamptz, (CURRENT_DATE - 310 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 310, pg_temp.period_of(CURRENT_DATE - 310), 'CP', 'P', 'A', 'PAY-00008', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 310 + time '17:00')::timestamptz),
    (34, (CURRENT_DATE - 310 + time '08:30')::timestamptz, (CURRENT_DATE - 310 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 310, pg_temp.period_of(CURRENT_DATE - 310), 'CP', 'P', 'C', 'PAY-00008', 'Atlantic Cloud Hosting (cash basis)', NULL, NULL, (CURRENT_DATE - 310 + time '17:00')::timestamptz),
    (35, (CURRENT_DATE - 305 + time '08:30')::timestamptz, (CURRENT_DATE - 305 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 305, pg_temp.period_of(CURRENT_DATE - 305), 'G', 'P', 'B', 'SAL-002', 'Salaries for the month', NULL, NULL, (CURRENT_DATE - 305 + time '17:00')::timestamptz),
    (36, (CURRENT_DATE - 305 + time '08:30')::timestamptz, (CURRENT_DATE - 305 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 305, pg_temp.period_of(CURRENT_DATE - 305), 'P', 'P', 'A', 'BILL-00006', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 305 + time '17:00')::timestamptz),
    (37, (CURRENT_DATE - 304 + time '08:30')::timestamptz, (CURRENT_DATE - 304 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 304, pg_temp.period_of(CURRENT_DATE - 304), 'CR', 'P', 'A', 'PAY-00009', 'Karoo Fresh Produce (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 304 + time '17:00')::timestamptz),
    (38, (CURRENT_DATE - 304 + time '08:30')::timestamptz, (CURRENT_DATE - 304 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 304, pg_temp.period_of(CURRENT_DATE - 304), 'CR', 'P', 'C', 'PAY-00009', 'Karoo Fresh Produce (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 304 + time '17:00')::timestamptz),
    (39, (CURRENT_DATE - 301 + time '08:30')::timestamptz, (CURRENT_DATE - 301 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 301, pg_temp.period_of(CURRENT_DATE - 301), 'P', 'P', 'A', 'BILL-00007', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 301 + time '17:00')::timestamptz),
    (40, (CURRENT_DATE - 301 + time '08:30')::timestamptz, (CURRENT_DATE - 301 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 301, pg_temp.period_of(CURRENT_DATE - 301), 'CP', 'P', 'A', 'PAY-00010', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 301 + time '17:00')::timestamptz),
    (41, (CURRENT_DATE - 301 + time '08:30')::timestamptz, (CURRENT_DATE - 301 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 301, pg_temp.period_of(CURRENT_DATE - 301), 'CP', 'P', 'C', 'PAY-00010', 'Metro Property Management (cash basis)', NULL, NULL, (CURRENT_DATE - 301 + time '17:00')::timestamptz),
    (42, (CURRENT_DATE - 300 + time '08:30')::timestamptz, (CURRENT_DATE - 300 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 300, pg_temp.period_of(CURRENT_DATE - 300), 'CP', 'P', 'B', 'TRF-001', 'Transfer to savings', NULL, NULL, (CURRENT_DATE - 300 + time '17:00')::timestamptz),
    (43, (CURRENT_DATE - 300 + time '08:30')::timestamptz, (CURRENT_DATE - 300 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 300, pg_temp.period_of(CURRENT_DATE - 300), 'S', 'P', 'A', 'INV-00007', 'Halcyon Interiors CC', NULL, NULL, (CURRENT_DATE - 300 + time '17:00')::timestamptz),
    (44, (CURRENT_DATE - 300 + time '08:30')::timestamptz, (CURRENT_DATE - 300 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 300, pg_temp.period_of(CURRENT_DATE - 300), 'CP', 'P', 'A', 'PAY-00011', 'Cape Office Supplies (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 300 + time '17:00')::timestamptz),
    (45, (CURRENT_DATE - 300 + time '08:30')::timestamptz, (CURRENT_DATE - 300 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 300, pg_temp.period_of(CURRENT_DATE - 300), 'CP', 'P', 'C', 'PAY-00011', 'Cape Office Supplies (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 300 + time '17:00')::timestamptz),
    (46, (CURRENT_DATE - 298 + time '08:30')::timestamptz, (CURRENT_DATE - 298 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 298, pg_temp.period_of(CURRENT_DATE - 298), 'CP', 'P', 'B', 'PAYE-002', 'PAYE paid', NULL, NULL, (CURRENT_DATE - 298 + time '17:00')::timestamptz),
    (47, (CURRENT_DATE - 293 + time '08:30')::timestamptz, (CURRENT_DATE - 293 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 293, pg_temp.period_of(CURRENT_DATE - 293), 'CP', 'P', 'A', 'PAY-00012', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 293 + time '17:00')::timestamptz),
    (48, (CURRENT_DATE - 293 + time '08:30')::timestamptz, (CURRENT_DATE - 293 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 293, pg_temp.period_of(CURRENT_DATE - 293), 'CP', 'P', 'C', 'PAY-00012', 'Highveld Fuel Services (cash basis)', NULL, NULL, (CURRENT_DATE - 293 + time '17:00')::timestamptz),
    (49, (CURRENT_DATE - 290 + time '08:30')::timestamptz, (CURRENT_DATE - 290 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 290, pg_temp.period_of(CURRENT_DATE - 290), 'CR', 'P', 'B', 'INT-002', 'Interest received', NULL, NULL, (CURRENT_DATE - 290 + time '17:00')::timestamptz),
    (50, (CURRENT_DATE - 289 + time '08:30')::timestamptz, (CURRENT_DATE - 289 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 289, pg_temp.period_of(CURRENT_DATE - 289), 'CR', 'P', 'A', 'PAY-00013', 'Table Bay Marine (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 289 + time '17:00')::timestamptz),
    (51, (CURRENT_DATE - 289 + time '08:30')::timestamptz, (CURRENT_DATE - 289 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 289, pg_temp.period_of(CURRENT_DATE - 289), 'CR', 'P', 'C', 'PAY-00013', 'Table Bay Marine (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 289 + time '17:00')::timestamptz),
    (52, (CURRENT_DATE - 285 + time '08:30')::timestamptz, (CURRENT_DATE - 285 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 285, pg_temp.period_of(CURRENT_DATE - 285), 'S', 'P', 'A', 'INV-00008', 'Karoo Fresh Produce (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 285 + time '17:00')::timestamptz),
    (53, (CURRENT_DATE - 285 + time '08:30')::timestamptz, (CURRENT_DATE - 285 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 285, pg_temp.period_of(CURRENT_DATE - 285), 'P', 'P', 'A', 'BILL-00008', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 285 + time '17:00')::timestamptz),
    (54, (CURRENT_DATE - 280 + time '08:30')::timestamptz, (CURRENT_DATE - 280 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 280, pg_temp.period_of(CURRENT_DATE - 280), 'CP', 'P', 'B', 'BCH-003', 'Bank charges', NULL, NULL, (CURRENT_DATE - 280 + time '17:00')::timestamptz),
    (55, (CURRENT_DATE - 280 + time '08:30')::timestamptz, (CURRENT_DATE - 280 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 280, pg_temp.period_of(CURRENT_DATE - 280), 'CP', 'P', 'A', 'PAY-00014', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 280 + time '17:00')::timestamptz),
    (56, (CURRENT_DATE - 280 + time '08:30')::timestamptz, (CURRENT_DATE - 280 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 280, pg_temp.period_of(CURRENT_DATE - 280), 'CP', 'P', 'C', 'PAY-00014', 'Atlantic Cloud Hosting (cash basis)', NULL, NULL, (CURRENT_DATE - 280 + time '17:00')::timestamptz),
    (57, (CURRENT_DATE - 280 + time '08:30')::timestamptz, (CURRENT_DATE - 280 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 280, pg_temp.period_of(CURRENT_DATE - 280), 'CP', 'P', 'B', 'VAT-002', 'VAT return paid', NULL, NULL, (CURRENT_DATE - 280 + time '17:00')::timestamptz),
    (58, (CURRENT_DATE - 275 + time '08:30')::timestamptz, (CURRENT_DATE - 275 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 275, pg_temp.period_of(CURRENT_DATE - 275), 'G', 'P', 'B', 'SAL-003', 'Salaries for the month', NULL, NULL, (CURRENT_DATE - 275 + time '17:00')::timestamptz),
    (59, (CURRENT_DATE - 275 + time '08:30')::timestamptz, (CURRENT_DATE - 275 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 275, pg_temp.period_of(CURRENT_DATE - 275), 'P', 'P', 'A', 'BILL-00009', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 275 + time '17:00')::timestamptz),
    (60, (CURRENT_DATE - 274 + time '08:30')::timestamptz, (CURRENT_DATE - 274 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 274, pg_temp.period_of(CURRENT_DATE - 274), 'CR', 'P', 'A', 'PAY-00015', 'Halcyon Interiors CC', NULL, NULL, (CURRENT_DATE - 274 + time '17:00')::timestamptz),
    (61, (CURRENT_DATE - 274 + time '08:30')::timestamptz, (CURRENT_DATE - 274 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 274, pg_temp.period_of(CURRENT_DATE - 274), 'CR', 'P', 'C', 'PAY-00015', 'Halcyon Interiors CC (cash basis)', NULL, NULL, (CURRENT_DATE - 274 + time '17:00')::timestamptz),
    (62, (CURRENT_DATE - 271 + time '08:30')::timestamptz, (CURRENT_DATE - 271 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 271, pg_temp.period_of(CURRENT_DATE - 271), 'P', 'P', 'A', 'BILL-00010', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 271 + time '17:00')::timestamptz),
    (63, (CURRENT_DATE - 271 + time '08:30')::timestamptz, (CURRENT_DATE - 271 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 271, pg_temp.period_of(CURRENT_DATE - 271), 'CP', 'P', 'A', 'PAY-00016', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 271 + time '17:00')::timestamptz),
    (64, (CURRENT_DATE - 271 + time '08:30')::timestamptz, (CURRENT_DATE - 271 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 271, pg_temp.period_of(CURRENT_DATE - 271), 'CP', 'P', 'C', 'PAY-00016', 'Metro Property Management (cash basis)', NULL, NULL, (CURRENT_DATE - 271 + time '17:00')::timestamptz),
    (65, (CURRENT_DATE - 270 + time '08:30')::timestamptz, (CURRENT_DATE - 270 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 270, pg_temp.period_of(CURRENT_DATE - 270), 'S', 'P', 'A', 'INV-00009', 'Halcyon Interiors CC', NULL, NULL, (CURRENT_DATE - 270 + time '17:00')::timestamptz),
    (66, (CURRENT_DATE - 268 + time '08:30')::timestamptz, (CURRENT_DATE - 268 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 268, pg_temp.period_of(CURRENT_DATE - 268), 'CP', 'P', 'B', 'PAYE-003', 'PAYE paid', NULL, NULL, (CURRENT_DATE - 268 + time '17:00')::timestamptz),
    (67, (CURRENT_DATE - 263 + time '08:30')::timestamptz, (CURRENT_DATE - 263 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 263, pg_temp.period_of(CURRENT_DATE - 263), 'CP', 'P', 'A', 'PAY-00017', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 263 + time '17:00')::timestamptz),
    (68, (CURRENT_DATE - 263 + time '08:30')::timestamptz, (CURRENT_DATE - 263 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 263, pg_temp.period_of(CURRENT_DATE - 263), 'CP', 'P', 'C', 'PAY-00017', 'Highveld Fuel Services (cash basis)', NULL, NULL, (CURRENT_DATE - 263 + time '17:00')::timestamptz),
    (69, (CURRENT_DATE - 260 + time '08:30')::timestamptz, (CURRENT_DATE - 260 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 260, pg_temp.period_of(CURRENT_DATE - 260), 'CR', 'P', 'B', 'INT-003', 'Interest received', NULL, NULL, (CURRENT_DATE - 260 + time '17:00')::timestamptz),
    (70, (CURRENT_DATE - 259 + time '08:30')::timestamptz, (CURRENT_DATE - 259 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 259, pg_temp.period_of(CURRENT_DATE - 259), 'CR', 'P', 'A', 'PAY-00018', 'Karoo Fresh Produce (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 259 + time '17:00')::timestamptz),
    (71, (CURRENT_DATE - 259 + time '08:30')::timestamptz, (CURRENT_DATE - 259 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 259, pg_temp.period_of(CURRENT_DATE - 259), 'CR', 'P', 'C', 'PAY-00018', 'Karoo Fresh Produce (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 259 + time '17:00')::timestamptz),
    (72, (CURRENT_DATE - 255 + time '08:30')::timestamptz, (CURRENT_DATE - 255 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 255, pg_temp.period_of(CURRENT_DATE - 255), 'S', 'P', 'A', 'INV-00010', 'Table Bay Marine (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 255 + time '17:00')::timestamptz),
    (73, (CURRENT_DATE - 255 + time '08:30')::timestamptz, (CURRENT_DATE - 255 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 255, pg_temp.period_of(CURRENT_DATE - 255), 'P', 'P', 'A', 'BILL-00011', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 255 + time '17:00')::timestamptz),
    (74, (CURRENT_DATE - 250 + time '08:30')::timestamptz, (CURRENT_DATE - 250 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 250, pg_temp.period_of(CURRENT_DATE - 250), 'CP', 'P', 'B', 'BCH-004', 'Bank charges', NULL, NULL, (CURRENT_DATE - 250 + time '17:00')::timestamptz),
    (75, (CURRENT_DATE - 250 + time '08:30')::timestamptz, (CURRENT_DATE - 250 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 250, pg_temp.period_of(CURRENT_DATE - 250), 'CP', 'P', 'A', 'PAY-00019', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 250 + time '17:00')::timestamptz),
    (76, (CURRENT_DATE - 250 + time '08:30')::timestamptz, (CURRENT_DATE - 250 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 250, pg_temp.period_of(CURRENT_DATE - 250), 'CP', 'P', 'C', 'PAY-00019', 'Atlantic Cloud Hosting (cash basis)', NULL, NULL, (CURRENT_DATE - 250 + time '17:00')::timestamptz),
    (77, (CURRENT_DATE - 245 + time '08:30')::timestamptz, (CURRENT_DATE - 245 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 245, pg_temp.period_of(CURRENT_DATE - 245), 'G', 'P', 'B', 'SAL-004', 'Salaries for the month', NULL, NULL, (CURRENT_DATE - 245 + time '17:00')::timestamptz),
    (78, (CURRENT_DATE - 245 + time '08:30')::timestamptz, (CURRENT_DATE - 245 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 245, pg_temp.period_of(CURRENT_DATE - 245), 'P', 'P', 'A', 'BILL-00012', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 245 + time '17:00')::timestamptz),
    (79, (CURRENT_DATE - 244 + time '08:30')::timestamptz, (CURRENT_DATE - 244 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 244, pg_temp.period_of(CURRENT_DATE - 244), 'CR', 'P', 'A', 'PAY-00020', 'Halcyon Interiors CC', NULL, NULL, (CURRENT_DATE - 244 + time '17:00')::timestamptz),
    (80, (CURRENT_DATE - 244 + time '08:30')::timestamptz, (CURRENT_DATE - 244 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 244, pg_temp.period_of(CURRENT_DATE - 244), 'CR', 'P', 'C', 'PAY-00020', 'Halcyon Interiors CC (cash basis)', NULL, NULL, (CURRENT_DATE - 244 + time '17:00')::timestamptz),
    (81, (CURRENT_DATE - 241 + time '08:30')::timestamptz, (CURRENT_DATE - 241 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 241, pg_temp.period_of(CURRENT_DATE - 241), 'P', 'P', 'A', 'BILL-00013', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 241 + time '17:00')::timestamptz),
    (82, (CURRENT_DATE - 241 + time '08:30')::timestamptz, (CURRENT_DATE - 241 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 241, pg_temp.period_of(CURRENT_DATE - 241), 'CP', 'P', 'A', 'PAY-00021', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 241 + time '17:00')::timestamptz),
    (83, (CURRENT_DATE - 241 + time '08:30')::timestamptz, (CURRENT_DATE - 241 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 241, pg_temp.period_of(CURRENT_DATE - 241), 'CP', 'P', 'C', 'PAY-00021', 'Metro Property Management (cash basis)', NULL, NULL, (CURRENT_DATE - 241 + time '17:00')::timestamptz),
    (84, (CURRENT_DATE - 240 + time '08:30')::timestamptz, (CURRENT_DATE - 240 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 240, pg_temp.period_of(CURRENT_DATE - 240), 'S', 'P', 'A', 'INV-00011', 'Protea Print Works', NULL, NULL, (CURRENT_DATE - 240 + time '17:00')::timestamptz),
    (85, (CURRENT_DATE - 238 + time '08:30')::timestamptz, (CURRENT_DATE - 238 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 238, pg_temp.period_of(CURRENT_DATE - 238), 'CP', 'P', 'B', 'PAYE-004', 'PAYE paid', NULL, NULL, (CURRENT_DATE - 238 + time '17:00')::timestamptz),
    (86, (CURRENT_DATE - 233 + time '08:30')::timestamptz, (CURRENT_DATE - 233 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 233, pg_temp.period_of(CURRENT_DATE - 233), 'CP', 'P', 'A', 'PAY-00022', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 233 + time '17:00')::timestamptz),
    (87, (CURRENT_DATE - 233 + time '08:30')::timestamptz, (CURRENT_DATE - 233 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 233, pg_temp.period_of(CURRENT_DATE - 233), 'CP', 'P', 'C', 'PAY-00022', 'Highveld Fuel Services (cash basis)', NULL, NULL, (CURRENT_DATE - 233 + time '17:00')::timestamptz),
    (88, (CURRENT_DATE - 230 + time '08:30')::timestamptz, (CURRENT_DATE - 230 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 230, pg_temp.period_of(CURRENT_DATE - 230), 'CR', 'P', 'B', 'INT-004', 'Interest received', NULL, NULL, (CURRENT_DATE - 230 + time '17:00')::timestamptz),
    (89, (CURRENT_DATE - 230 + time '08:30')::timestamptz, (CURRENT_DATE - 230 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 230, pg_temp.period_of(CURRENT_DATE - 230), 'P', 'P', 'A', 'BILL-00014', 'Cape Office Supplies (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 230 + time '17:00')::timestamptz),
    (90, (CURRENT_DATE - 225 + time '08:30')::timestamptz, (CURRENT_DATE - 225 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 225, pg_temp.period_of(CURRENT_DATE - 225), 'S', 'P', 'A', 'INV-00012', 'Karoo Fresh Produce (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 225 + time '17:00')::timestamptz),
    (91, (CURRENT_DATE - 225 + time '08:30')::timestamptz, (CURRENT_DATE - 225 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 225, pg_temp.period_of(CURRENT_DATE - 225), 'P', 'P', 'A', 'BILL-00015', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 225 + time '17:00')::timestamptz),
    (92, (CURRENT_DATE - 220 + time '08:30')::timestamptz, (CURRENT_DATE - 220 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 220, pg_temp.period_of(CURRENT_DATE - 220), 'CP', 'P', 'B', 'BCH-005', 'Bank charges', NULL, NULL, (CURRENT_DATE - 220 + time '17:00')::timestamptz),
    (93, (CURRENT_DATE - 220 + time '08:30')::timestamptz, (CURRENT_DATE - 220 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 220, pg_temp.period_of(CURRENT_DATE - 220), 'CP', 'P', 'A', 'PAY-00023', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 220 + time '17:00')::timestamptz),
    (94, (CURRENT_DATE - 220 + time '08:30')::timestamptz, (CURRENT_DATE - 220 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 220, pg_temp.period_of(CURRENT_DATE - 220), 'CP', 'P', 'C', 'PAY-00023', 'Atlantic Cloud Hosting (cash basis)', NULL, NULL, (CURRENT_DATE - 220 + time '17:00')::timestamptz),
    (95, (CURRENT_DATE - 220 + time '08:30')::timestamptz, (CURRENT_DATE - 220 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 220, pg_temp.period_of(CURRENT_DATE - 220), 'CP', 'P', 'B', 'VAT-003', 'VAT return paid', NULL, NULL, (CURRENT_DATE - 220 + time '17:00')::timestamptz),
    (96, (CURRENT_DATE - 215 + time '08:30')::timestamptz, (CURRENT_DATE - 215 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 215, pg_temp.period_of(CURRENT_DATE - 215), 'G', 'P', 'B', 'SAL-005', 'Salaries for the month', NULL, NULL, (CURRENT_DATE - 215 + time '17:00')::timestamptz),
    (97, (CURRENT_DATE - 215 + time '08:30')::timestamptz, (CURRENT_DATE - 215 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 215, pg_temp.period_of(CURRENT_DATE - 215), 'P', 'P', 'A', 'BILL-00016', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 215 + time '17:00')::timestamptz),
    (98, (CURRENT_DATE - 215 + time '08:30')::timestamptz, (CURRENT_DATE - 215 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 215, pg_temp.period_of(CURRENT_DATE - 215), 'CR', 'P', 'A', 'PAY-00024', 'Table Bay Marine (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 215 + time '17:00')::timestamptz),
    (99, (CURRENT_DATE - 215 + time '08:30')::timestamptz, (CURRENT_DATE - 215 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 215, pg_temp.period_of(CURRENT_DATE - 215), 'CR', 'P', 'C', 'PAY-00024', 'Table Bay Marine (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 215 + time '17:00')::timestamptz),
    (100, (CURRENT_DATE - 214 + time '08:30')::timestamptz, (CURRENT_DATE - 214 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 214, pg_temp.period_of(CURRENT_DATE - 214), 'CR', 'P', 'A', 'PAY-00025', 'Protea Print Works', NULL, NULL, (CURRENT_DATE - 214 + time '17:00')::timestamptz),
    (101, (CURRENT_DATE - 214 + time '08:30')::timestamptz, (CURRENT_DATE - 214 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 214, pg_temp.period_of(CURRENT_DATE - 214), 'CR', 'P', 'C', 'PAY-00025', 'Protea Print Works (cash basis)', NULL, NULL, (CURRENT_DATE - 214 + time '17:00')::timestamptz),
    (102, (CURRENT_DATE - 211 + time '08:30')::timestamptz, (CURRENT_DATE - 211 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 211, pg_temp.period_of(CURRENT_DATE - 211), 'P', 'P', 'A', 'BILL-00017', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 211 + time '17:00')::timestamptz),
    (103, (CURRENT_DATE - 211 + time '08:30')::timestamptz, (CURRENT_DATE - 211 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 211, pg_temp.period_of(CURRENT_DATE - 211), 'CP', 'P', 'A', 'PAY-00026', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 211 + time '17:00')::timestamptz),
    (104, (CURRENT_DATE - 211 + time '08:30')::timestamptz, (CURRENT_DATE - 211 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 211, pg_temp.period_of(CURRENT_DATE - 211), 'CP', 'P', 'C', 'PAY-00026', 'Metro Property Management (cash basis)', NULL, NULL, (CURRENT_DATE - 211 + time '17:00')::timestamptz),
    (105, (CURRENT_DATE - 210 + time '08:30')::timestamptz, (CURRENT_DATE - 210 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 210, pg_temp.period_of(CURRENT_DATE - 210), 'S', 'P', 'A', 'INV-00013', 'Table Bay Marine (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 210 + time '17:00')::timestamptz),
    (106, (CURRENT_DATE - 210 + time '08:30')::timestamptz, (CURRENT_DATE - 210 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 210, pg_temp.period_of(CURRENT_DATE - 210), 'CP', 'P', 'A', 'PAY-00027', 'Cape Office Supplies (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 210 + time '17:00')::timestamptz),
    (107, (CURRENT_DATE - 210 + time '08:30')::timestamptz, (CURRENT_DATE - 210 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 210, pg_temp.period_of(CURRENT_DATE - 210), 'CP', 'P', 'C', 'PAY-00027', 'Cape Office Supplies (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 210 + time '17:00')::timestamptz),
    (108, (CURRENT_DATE - 208 + time '08:30')::timestamptz, (CURRENT_DATE - 208 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 208, pg_temp.period_of(CURRENT_DATE - 208), 'CP', 'P', 'B', 'PAYE-005', 'PAYE paid', NULL, NULL, (CURRENT_DATE - 208 + time '17:00')::timestamptz),
    (109, (CURRENT_DATE - 203 + time '08:30')::timestamptz, (CURRENT_DATE - 203 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 203, pg_temp.period_of(CURRENT_DATE - 203), 'CP', 'P', 'A', 'PAY-00028', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 203 + time '17:00')::timestamptz),
    (110, (CURRENT_DATE - 203 + time '08:30')::timestamptz, (CURRENT_DATE - 203 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 203, pg_temp.period_of(CURRENT_DATE - 203), 'CP', 'P', 'C', 'PAY-00028', 'Highveld Fuel Services (cash basis)', NULL, NULL, (CURRENT_DATE - 203 + time '17:00')::timestamptz),
    (111, (CURRENT_DATE - 200 + time '08:30')::timestamptz, (CURRENT_DATE - 200 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 200, pg_temp.period_of(CURRENT_DATE - 200), 'CR', 'P', 'B', 'INT-005', 'Interest received', NULL, NULL, (CURRENT_DATE - 200 + time '17:00')::timestamptz),
    (112, (CURRENT_DATE - 200 + time '08:30')::timestamptz, (CURRENT_DATE - 200 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 200, pg_temp.period_of(CURRENT_DATE - 200), 'P', 'P', 'A', 'BILL-00018', 'Cape Office Supplies (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 200 + time '17:00')::timestamptz),
    (113, (CURRENT_DATE - 199 + time '08:30')::timestamptz, (CURRENT_DATE - 199 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 199, pg_temp.period_of(CURRENT_DATE - 199), 'CR', 'P', 'A', 'PAY-00029', 'Karoo Fresh Produce (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 199 + time '17:00')::timestamptz),
    (114, (CURRENT_DATE - 199 + time '08:30')::timestamptz, (CURRENT_DATE - 199 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 199, pg_temp.period_of(CURRENT_DATE - 199), 'CR', 'P', 'C', 'PAY-00029', 'Karoo Fresh Produce (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 199 + time '17:00')::timestamptz),
    (115, (CURRENT_DATE - 195 + time '08:30')::timestamptz, (CURRENT_DATE - 195 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 195, pg_temp.period_of(CURRENT_DATE - 195), 'S', 'P', 'A', 'INV-00014', 'Halcyon Interiors CC', NULL, NULL, (CURRENT_DATE - 195 + time '17:00')::timestamptz),
    (116, (CURRENT_DATE - 195 + time '08:30')::timestamptz, (CURRENT_DATE - 195 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 195, pg_temp.period_of(CURRENT_DATE - 195), 'P', 'P', 'A', 'BILL-00019', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 195 + time '17:00')::timestamptz),
    (117, (CURRENT_DATE - 190 + time '08:30')::timestamptz, (CURRENT_DATE - 190 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 190, pg_temp.period_of(CURRENT_DATE - 190), 'CP', 'P', 'B', 'BCH-006', 'Bank charges', NULL, NULL, (CURRENT_DATE - 190 + time '17:00')::timestamptz),
    (118, (CURRENT_DATE - 190 + time '08:30')::timestamptz, (CURRENT_DATE - 190 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 190, pg_temp.period_of(CURRENT_DATE - 190), 'CP', 'P', 'A', 'PAY-00030', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 190 + time '17:00')::timestamptz),
    (119, (CURRENT_DATE - 190 + time '08:30')::timestamptz, (CURRENT_DATE - 190 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 190, pg_temp.period_of(CURRENT_DATE - 190), 'CP', 'P', 'C', 'PAY-00030', 'Atlantic Cloud Hosting (cash basis)', NULL, NULL, (CURRENT_DATE - 190 + time '17:00')::timestamptz),
    (120, (CURRENT_DATE - 185 + time '08:30')::timestamptz, (CURRENT_DATE - 185 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 185, pg_temp.period_of(CURRENT_DATE - 185), 'G', 'P', 'B', 'SAL-006', 'Salaries for the month', NULL, NULL, (CURRENT_DATE - 185 + time '17:00')::timestamptz),
    (121, (CURRENT_DATE - 185 + time '08:30')::timestamptz, (CURRENT_DATE - 185 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 185, pg_temp.period_of(CURRENT_DATE - 185), 'P', 'P', 'A', 'BILL-00020', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 185 + time '17:00')::timestamptz),
    (122, (CURRENT_DATE - 184 + time '08:30')::timestamptz, (CURRENT_DATE - 184 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 184, pg_temp.period_of(CURRENT_DATE - 184), 'CR', 'P', 'A', 'PAY-00031', 'Table Bay Marine (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 184 + time '17:00')::timestamptz),
    (123, (CURRENT_DATE - 184 + time '08:30')::timestamptz, (CURRENT_DATE - 184 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 184, pg_temp.period_of(CURRENT_DATE - 184), 'CR', 'P', 'C', 'PAY-00031', 'Table Bay Marine (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 184 + time '17:00')::timestamptz),
    (124, (CURRENT_DATE - 183 + time '08:30')::timestamptz, (CURRENT_DATE - 183 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 183, pg_temp.period_of(CURRENT_DATE - 183), 'CR', 'P', 'A', 'PAY-00032', 'Halcyon Interiors CC', NULL, NULL, (CURRENT_DATE - 183 + time '17:00')::timestamptz),
    (125, (CURRENT_DATE - 183 + time '08:30')::timestamptz, (CURRENT_DATE - 183 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 183, pg_temp.period_of(CURRENT_DATE - 183), 'CR', 'P', 'C', 'PAY-00032', 'Halcyon Interiors CC (cash basis)', NULL, NULL, (CURRENT_DATE - 183 + time '17:00')::timestamptz),
    (126, (CURRENT_DATE - 181 + time '08:30')::timestamptz, (CURRENT_DATE - 181 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 181, pg_temp.period_of(CURRENT_DATE - 181), 'P', 'P', 'A', 'BILL-00021', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 181 + time '17:00')::timestamptz),
    (127, (CURRENT_DATE - 181 + time '08:30')::timestamptz, (CURRENT_DATE - 181 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 181, pg_temp.period_of(CURRENT_DATE - 181), 'CP', 'P', 'A', 'PAY-00033', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 181 + time '17:00')::timestamptz),
    (128, (CURRENT_DATE - 181 + time '08:30')::timestamptz, (CURRENT_DATE - 181 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 181, pg_temp.period_of(CURRENT_DATE - 181), 'CP', 'P', 'C', 'PAY-00033', 'Metro Property Management (cash basis)', NULL, NULL, (CURRENT_DATE - 181 + time '17:00')::timestamptz),
    (129, (CURRENT_DATE - 180 + time '08:30')::timestamptz, (CURRENT_DATE - 180 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 180, pg_temp.period_of(CURRENT_DATE - 180), 'S', 'P', 'A', 'INV-00015', 'Karoo Fresh Produce (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 180 + time '17:00')::timestamptz),
    (130, (CURRENT_DATE - 178 + time '08:30')::timestamptz, (CURRENT_DATE - 178 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 178, pg_temp.period_of(CURRENT_DATE - 178), 'CP', 'P', 'B', 'PAYE-006', 'PAYE paid', NULL, NULL, (CURRENT_DATE - 178 + time '17:00')::timestamptz),
    (131, (CURRENT_DATE - 173 + time '08:30')::timestamptz, (CURRENT_DATE - 173 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 173, pg_temp.period_of(CURRENT_DATE - 173), 'CP', 'P', 'A', 'PAY-00034', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 173 + time '17:00')::timestamptz),
    (132, (CURRENT_DATE - 173 + time '08:30')::timestamptz, (CURRENT_DATE - 173 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 173, pg_temp.period_of(CURRENT_DATE - 173), 'CP', 'P', 'C', 'PAY-00034', 'Highveld Fuel Services (cash basis)', NULL, NULL, (CURRENT_DATE - 173 + time '17:00')::timestamptz),
    (133, (CURRENT_DATE - 172 + time '08:30')::timestamptz, (CURRENT_DATE - 172 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 172, pg_temp.period_of(CURRENT_DATE - 172), 'CP', 'P', 'A', 'PAY-00035', 'Cape Office Supplies (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 172 + time '17:00')::timestamptz),
    (134, (CURRENT_DATE - 172 + time '08:30')::timestamptz, (CURRENT_DATE - 172 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 172, pg_temp.period_of(CURRENT_DATE - 172), 'CP', 'P', 'C', 'PAY-00035', 'Cape Office Supplies (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 172 + time '17:00')::timestamptz),
    (135, (CURRENT_DATE - 170 + time '08:30')::timestamptz, (CURRENT_DATE - 170 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 170, pg_temp.period_of(CURRENT_DATE - 170), 'CR', 'P', 'B', 'INT-006', 'Interest received', NULL, NULL, (CURRENT_DATE - 170 + time '17:00')::timestamptz),
    (136, (CURRENT_DATE - 165 + time '08:30')::timestamptz, (CURRENT_DATE - 165 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 165, pg_temp.period_of(CURRENT_DATE - 165), 'S', 'P', 'A', 'INV-00016', 'Halcyon Interiors CC', NULL, NULL, (CURRENT_DATE - 165 + time '17:00')::timestamptz),
    (137, (CURRENT_DATE - 165 + time '08:30')::timestamptz, (CURRENT_DATE - 165 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 165, pg_temp.period_of(CURRENT_DATE - 165), 'P', 'P', 'A', 'BILL-00022', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 165 + time '17:00')::timestamptz),
    (138, (CURRENT_DATE - 160 + time '08:30')::timestamptz, (CURRENT_DATE - 160 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 160, pg_temp.period_of(CURRENT_DATE - 160), 'CP', 'P', 'B', 'BCH-007', 'Bank charges', NULL, NULL, (CURRENT_DATE - 160 + time '17:00')::timestamptz),
    (139, (CURRENT_DATE - 160 + time '08:30')::timestamptz, (CURRENT_DATE - 160 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 160, pg_temp.period_of(CURRENT_DATE - 160), 'CP', 'P', 'A', 'PAY-00036', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 160 + time '17:00')::timestamptz),
    (140, (CURRENT_DATE - 160 + time '08:30')::timestamptz, (CURRENT_DATE - 160 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 160, pg_temp.period_of(CURRENT_DATE - 160), 'CP', 'P', 'C', 'PAY-00036', 'Atlantic Cloud Hosting (cash basis)', NULL, NULL, (CURRENT_DATE - 160 + time '17:00')::timestamptz),
    (141, (CURRENT_DATE - 160 + time '08:30')::timestamptz, (CURRENT_DATE - 160 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 160, pg_temp.period_of(CURRENT_DATE - 160), 'CP', 'P', 'B', 'VAT-004', 'VAT return paid', NULL, NULL, (CURRENT_DATE - 160 + time '17:00')::timestamptz),
    (142, (CURRENT_DATE - 155 + time '08:30')::timestamptz, (CURRENT_DATE - 155 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 155, pg_temp.period_of(CURRENT_DATE - 155), 'G', 'P', 'B', 'SAL-007', 'Salaries for the month', NULL, NULL, (CURRENT_DATE - 155 + time '17:00')::timestamptz),
    (143, (CURRENT_DATE - 155 + time '08:30')::timestamptz, (CURRENT_DATE - 155 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 155, pg_temp.period_of(CURRENT_DATE - 155), 'P', 'P', 'A', 'BILL-00023', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 155 + time '17:00')::timestamptz),
    (144, (CURRENT_DATE - 154 + time '08:30')::timestamptz, (CURRENT_DATE - 154 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 154, pg_temp.period_of(CURRENT_DATE - 154), 'CR', 'P', 'A', 'PAY-00037', 'Karoo Fresh Produce (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 154 + time '17:00')::timestamptz),
    (145, (CURRENT_DATE - 154 + time '08:30')::timestamptz, (CURRENT_DATE - 154 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 154, pg_temp.period_of(CURRENT_DATE - 154), 'CR', 'P', 'C', 'PAY-00037', 'Karoo Fresh Produce (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 154 + time '17:00')::timestamptz),
    (146, (CURRENT_DATE - 151 + time '08:30')::timestamptz, (CURRENT_DATE - 151 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 151, pg_temp.period_of(CURRENT_DATE - 151), 'P', 'P', 'A', 'BILL-00024', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 151 + time '17:00')::timestamptz),
    (147, (CURRENT_DATE - 151 + time '08:30')::timestamptz, (CURRENT_DATE - 151 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 151, pg_temp.period_of(CURRENT_DATE - 151), 'CP', 'P', 'A', 'PAY-00038', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 151 + time '17:00')::timestamptz),
    (148, (CURRENT_DATE - 151 + time '08:30')::timestamptz, (CURRENT_DATE - 151 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 151, pg_temp.period_of(CURRENT_DATE - 151), 'CP', 'P', 'C', 'PAY-00038', 'Metro Property Management (cash basis)', NULL, NULL, (CURRENT_DATE - 151 + time '17:00')::timestamptz),
    (149, (CURRENT_DATE - 150 + time '08:30')::timestamptz, (CURRENT_DATE - 150 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 150, pg_temp.period_of(CURRENT_DATE - 150), 'S', 'P', 'A', 'INV-00017', 'Table Bay Marine (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 150 + time '17:00')::timestamptz),
    (150, (CURRENT_DATE - 150 + time '08:30')::timestamptz, (CURRENT_DATE - 150 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 150, pg_temp.period_of(CURRENT_DATE - 150), 'G', 'P', 'B', 'VEH-001', 'Delivery vehicle on finance', NULL, NULL, (CURRENT_DATE - 150 + time '17:00')::timestamptz),
    (151, (CURRENT_DATE - 148 + time '08:30')::timestamptz, (CURRENT_DATE - 148 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 148, pg_temp.period_of(CURRENT_DATE - 148), 'CP', 'P', 'B', 'PAYE-007', 'PAYE paid', NULL, NULL, (CURRENT_DATE - 148 + time '17:00')::timestamptz),
    (152, (CURRENT_DATE - 143 + time '08:30')::timestamptz, (CURRENT_DATE - 143 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 143, pg_temp.period_of(CURRENT_DATE - 143), 'CP', 'P', 'A', 'PAY-00039', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 143 + time '17:00')::timestamptz),
    (153, (CURRENT_DATE - 143 + time '08:30')::timestamptz, (CURRENT_DATE - 143 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 143, pg_temp.period_of(CURRENT_DATE - 143), 'CP', 'P', 'C', 'PAY-00039', 'Highveld Fuel Services (cash basis)', NULL, NULL, (CURRENT_DATE - 143 + time '17:00')::timestamptz),
    (154, (CURRENT_DATE - 140 + time '08:30')::timestamptz, (CURRENT_DATE - 140 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 140, pg_temp.period_of(CURRENT_DATE - 140), 'CR', 'P', 'B', 'INT-007', 'Interest received', NULL, NULL, (CURRENT_DATE - 140 + time '17:00')::timestamptz),
    (155, (CURRENT_DATE - 140 + time '08:30')::timestamptz, (CURRENT_DATE - 140 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 140, pg_temp.period_of(CURRENT_DATE - 140), 'P', 'P', 'A', 'BILL-00025', 'Cape Office Supplies (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 140 + time '17:00')::timestamptz),
    (156, (CURRENT_DATE - 140 + time '08:30')::timestamptz, (CURRENT_DATE - 140 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 140, pg_temp.period_of(CURRENT_DATE - 140), 'CP', 'P', 'B', 'LOAN-001', 'Vehicle finance instalment', NULL, NULL, (CURRENT_DATE - 140 + time '17:00')::timestamptz),
    (157, (CURRENT_DATE - 139 + time '08:30')::timestamptz, (CURRENT_DATE - 139 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 139, pg_temp.period_of(CURRENT_DATE - 139), 'CR', 'P', 'A', 'PAY-00040', 'Halcyon Interiors CC', NULL, NULL, (CURRENT_DATE - 139 + time '17:00')::timestamptz),
    (158, (CURRENT_DATE - 139 + time '08:30')::timestamptz, (CURRENT_DATE - 139 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 139, pg_temp.period_of(CURRENT_DATE - 139), 'CR', 'P', 'C', 'PAY-00040', 'Halcyon Interiors CC (cash basis)', NULL, NULL, (CURRENT_DATE - 139 + time '17:00')::timestamptz),
    (159, (CURRENT_DATE - 135 + time '08:30')::timestamptz, (CURRENT_DATE - 135 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 135, pg_temp.period_of(CURRENT_DATE - 135), 'S', 'P', 'A', 'INV-00018', 'Protea Print Works', NULL, NULL, (CURRENT_DATE - 135 + time '17:00')::timestamptz),
    (160, (CURRENT_DATE - 135 + time '08:30')::timestamptz, (CURRENT_DATE - 135 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 135, pg_temp.period_of(CURRENT_DATE - 135), 'P', 'P', 'A', 'BILL-00026', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 135 + time '17:00')::timestamptz),
    (161, (CURRENT_DATE - 130 + time '08:30')::timestamptz, (CURRENT_DATE - 130 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 130, pg_temp.period_of(CURRENT_DATE - 130), 'CP', 'P', 'B', 'BCH-008', 'Bank charges', NULL, NULL, (CURRENT_DATE - 130 + time '17:00')::timestamptz),
    (162, (CURRENT_DATE - 130 + time '08:30')::timestamptz, (CURRENT_DATE - 130 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 130, pg_temp.period_of(CURRENT_DATE - 130), 'CP', 'P', 'A', 'PAY-00041', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 130 + time '17:00')::timestamptz),
    (163, (CURRENT_DATE - 130 + time '08:30')::timestamptz, (CURRENT_DATE - 130 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 130, pg_temp.period_of(CURRENT_DATE - 130), 'CP', 'P', 'C', 'PAY-00041', 'Atlantic Cloud Hosting (cash basis)', NULL, NULL, (CURRENT_DATE - 130 + time '17:00')::timestamptz),
    (164, (CURRENT_DATE - 125 + time '08:30')::timestamptz, (CURRENT_DATE - 125 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 125, pg_temp.period_of(CURRENT_DATE - 125), 'G', 'P', 'B', 'SAL-008', 'Salaries for the month', NULL, NULL, (CURRENT_DATE - 125 + time '17:00')::timestamptz),
    (165, (CURRENT_DATE - 125 + time '08:30')::timestamptz, (CURRENT_DATE - 125 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 125, pg_temp.period_of(CURRENT_DATE - 125), 'P', 'P', 'A', 'BILL-00027', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 125 + time '17:00')::timestamptz),
    (166, (CURRENT_DATE - 124 + time '08:30')::timestamptz, (CURRENT_DATE - 124 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 124, pg_temp.period_of(CURRENT_DATE - 124), 'CR', 'P', 'A', 'PAY-00042', 'Table Bay Marine (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 124 + time '17:00')::timestamptz),
    (167, (CURRENT_DATE - 124 + time '08:30')::timestamptz, (CURRENT_DATE - 124 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 124, pg_temp.period_of(CURRENT_DATE - 124), 'CR', 'P', 'C', 'PAY-00042', 'Table Bay Marine (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 124 + time '17:00')::timestamptz),
    (168, (CURRENT_DATE - 121 + time '08:30')::timestamptz, (CURRENT_DATE - 121 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 121, pg_temp.period_of(CURRENT_DATE - 121), 'P', 'P', 'A', 'BILL-00028', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 121 + time '17:00')::timestamptz),
    (169, (CURRENT_DATE - 121 + time '08:30')::timestamptz, (CURRENT_DATE - 121 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 121, pg_temp.period_of(CURRENT_DATE - 121), 'CP', 'P', 'A', 'PAY-00043', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 121 + time '17:00')::timestamptz),
    (170, (CURRENT_DATE - 121 + time '08:30')::timestamptz, (CURRENT_DATE - 121 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 121, pg_temp.period_of(CURRENT_DATE - 121), 'CP', 'P', 'C', 'PAY-00043', 'Metro Property Management (cash basis)', NULL, NULL, (CURRENT_DATE - 121 + time '17:00')::timestamptz),
    (171, (CURRENT_DATE - 120 + time '08:30')::timestamptz, (CURRENT_DATE - 120 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 120, pg_temp.period_of(CURRENT_DATE - 120), 'S', 'P', 'A', 'INV-00019', 'Karoo Fresh Produce (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 120 + time '17:00')::timestamptz),
    (172, (CURRENT_DATE - 120 + time '08:30')::timestamptz, (CURRENT_DATE - 120 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 120, pg_temp.period_of(CURRENT_DATE - 120), 'CP', 'P', 'A', 'PAY-00044', 'Cape Office Supplies (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 120 + time '17:00')::timestamptz),
    (173, (CURRENT_DATE - 120 + time '08:30')::timestamptz, (CURRENT_DATE - 120 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 120, pg_temp.period_of(CURRENT_DATE - 120), 'CP', 'P', 'C', 'PAY-00044', 'Cape Office Supplies (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 120 + time '17:00')::timestamptz),
    (174, (CURRENT_DATE - 118 + time '08:30')::timestamptz, (CURRENT_DATE - 118 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 118, pg_temp.period_of(CURRENT_DATE - 118), 'CP', 'P', 'B', 'PAYE-008', 'PAYE paid', NULL, NULL, (CURRENT_DATE - 118 + time '17:00')::timestamptz),
    (175, (CURRENT_DATE - 113 + time '08:30')::timestamptz, (CURRENT_DATE - 113 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 113, pg_temp.period_of(CURRENT_DATE - 113), 'CP', 'P', 'A', 'PAY-00045', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 113 + time '17:00')::timestamptz),
    (176, (CURRENT_DATE - 113 + time '08:30')::timestamptz, (CURRENT_DATE - 113 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 113, pg_temp.period_of(CURRENT_DATE - 113), 'CP', 'P', 'C', 'PAY-00045', 'Highveld Fuel Services (cash basis)', NULL, NULL, (CURRENT_DATE - 113 + time '17:00')::timestamptz),
    (177, (CURRENT_DATE - 110 + time '08:30')::timestamptz, (CURRENT_DATE - 110 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 110, pg_temp.period_of(CURRENT_DATE - 110), 'CR', 'P', 'B', 'INT-008', 'Interest received', NULL, NULL, (CURRENT_DATE - 110 + time '17:00')::timestamptz),
    (178, (CURRENT_DATE - 110 + time '08:30')::timestamptz, (CURRENT_DATE - 110 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 110, pg_temp.period_of(CURRENT_DATE - 110), 'CP', 'P', 'B', 'LOAN-002', 'Vehicle finance instalment', NULL, NULL, (CURRENT_DATE - 110 + time '17:00')::timestamptz),
    (179, (CURRENT_DATE - 105 + time '08:30')::timestamptz, (CURRENT_DATE - 105 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 105, pg_temp.period_of(CURRENT_DATE - 105), 'S', 'P', 'A', 'INV-00020', 'Table Bay Marine (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 105 + time '17:00')::timestamptz),
    (180, (CURRENT_DATE - 105 + time '08:30')::timestamptz, (CURRENT_DATE - 105 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 105, pg_temp.period_of(CURRENT_DATE - 105), 'P', 'P', 'A', 'BILL-00029', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 105 + time '17:00')::timestamptz),
    (181, (CURRENT_DATE - 100 + time '08:30')::timestamptz, (CURRENT_DATE - 100 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 100, pg_temp.period_of(CURRENT_DATE - 100), 'CP', 'P', 'B', 'BCH-009', 'Bank charges', NULL, NULL, (CURRENT_DATE - 100 + time '17:00')::timestamptz),
    (182, (CURRENT_DATE - 100 + time '08:30')::timestamptz, (CURRENT_DATE - 100 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 100, pg_temp.period_of(CURRENT_DATE - 100), 'P', 'P', 'A', 'BILL-00030', 'Coastal Stock Distributors', NULL, NULL, (CURRENT_DATE - 100 + time '17:00')::timestamptz),
    (183, (CURRENT_DATE - 100 + time '08:30')::timestamptz, (CURRENT_DATE - 100 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 100, pg_temp.period_of(CURRENT_DATE - 100), 'G', 'P', 'B', 'TAX-001', 'Provisional tax — first period', NULL, NULL, (CURRENT_DATE - 100 + time '17:00')::timestamptz),
    (184, (CURRENT_DATE - 100 + time '08:30')::timestamptz, (CURRENT_DATE - 100 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 100, pg_temp.period_of(CURRENT_DATE - 100), 'CP', 'P', 'A', 'PAY-00046', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 100 + time '17:00')::timestamptz),
    (185, (CURRENT_DATE - 100 + time '08:30')::timestamptz, (CURRENT_DATE - 100 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 100, pg_temp.period_of(CURRENT_DATE - 100), 'CP', 'P', 'C', 'PAY-00046', 'Atlantic Cloud Hosting (cash basis)', NULL, NULL, (CURRENT_DATE - 100 + time '17:00')::timestamptz),
    (186, (CURRENT_DATE - 100 + time '08:30')::timestamptz, (CURRENT_DATE - 100 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 100, pg_temp.period_of(CURRENT_DATE - 100), 'CP', 'P', 'B', 'VAT-005', 'VAT return paid', NULL, NULL, (CURRENT_DATE - 100 + time '17:00')::timestamptz),
    (187, (CURRENT_DATE - 95 + time '08:30')::timestamptz, (CURRENT_DATE - 95 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 95, pg_temp.period_of(CURRENT_DATE - 95), 'G', 'P', 'B', 'SAL-009', 'Salaries for the month', NULL, NULL, (CURRENT_DATE - 95 + time '17:00')::timestamptz),
    (188, (CURRENT_DATE - 95 + time '08:30')::timestamptz, (CURRENT_DATE - 95 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 95, pg_temp.period_of(CURRENT_DATE - 95), 'P', 'P', 'A', 'BILL-00031', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 95 + time '17:00')::timestamptz),
    (189, (CURRENT_DATE - 95 + time '08:30')::timestamptz, (CURRENT_DATE - 95 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 95, pg_temp.period_of(CURRENT_DATE - 95), 'CP', 'P', 'B', 'TAX-002', 'Provisional tax paid', NULL, NULL, (CURRENT_DATE - 95 + time '17:00')::timestamptz),
    (190, (CURRENT_DATE - 95 + time '08:30')::timestamptz, (CURRENT_DATE - 95 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 95, pg_temp.period_of(CURRENT_DATE - 95), 'S', 'P', 'A', 'INV-00021', 'Karoo Fresh Produce (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 95 + time '17:00')::timestamptz),
    (191, (CURRENT_DATE - 95 + time '08:30')::timestamptz, (CURRENT_DATE - 95 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 95, pg_temp.period_of(CURRENT_DATE - 95), 'G', 'P', 'B', 'COS-001', 'Cost of the stock sold', NULL, NULL, (CURRENT_DATE - 95 + time '17:00')::timestamptz),
    (192, (CURRENT_DATE - 94 + time '08:30')::timestamptz, (CURRENT_DATE - 94 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 94, pg_temp.period_of(CURRENT_DATE - 94), 'CR', 'P', 'A', 'PAY-00047', 'Karoo Fresh Produce (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 94 + time '17:00')::timestamptz),
    (193, (CURRENT_DATE - 94 + time '08:30')::timestamptz, (CURRENT_DATE - 94 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 94, pg_temp.period_of(CURRENT_DATE - 94), 'CR', 'P', 'C', 'PAY-00047', 'Karoo Fresh Produce (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 94 + time '17:00')::timestamptz),
    (194, (CURRENT_DATE - 91 + time '08:30')::timestamptz, (CURRENT_DATE - 91 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 91, pg_temp.period_of(CURRENT_DATE - 91), 'P', 'P', 'A', 'BILL-00032', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 91 + time '17:00')::timestamptz),
    (195, (CURRENT_DATE - 91 + time '08:30')::timestamptz, (CURRENT_DATE - 91 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 91, pg_temp.period_of(CURRENT_DATE - 91), 'CP', 'P', 'A', 'PAY-00048', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 91 + time '17:00')::timestamptz),
    (196, (CURRENT_DATE - 91 + time '08:30')::timestamptz, (CURRENT_DATE - 91 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 91, pg_temp.period_of(CURRENT_DATE - 91), 'CP', 'P', 'C', 'PAY-00048', 'Metro Property Management (cash basis)', NULL, NULL, (CURRENT_DATE - 91 + time '17:00')::timestamptz),
    (197, (CURRENT_DATE - 90 + time '08:30')::timestamptz, (CURRENT_DATE - 90 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 90, pg_temp.period_of(CURRENT_DATE - 90), 'S', 'P', 'A', 'INV-00022', 'Halcyon Interiors CC', NULL, NULL, (CURRENT_DATE - 90 + time '17:00')::timestamptz),
    (198, (CURRENT_DATE - 90 + time '08:30')::timestamptz, (CURRENT_DATE - 90 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 90, pg_temp.period_of(CURRENT_DATE - 90), 'G', 'P', 'B', 'DSP-001', 'Old laser printer sold', NULL, NULL, (CURRENT_DATE - 90 + time '17:00')::timestamptz),
    (199, (CURRENT_DATE - 88 + time '08:30')::timestamptz, (CURRENT_DATE - 88 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 88, pg_temp.period_of(CURRENT_DATE - 88), 'CP', 'P', 'B', 'PAYE-009', 'PAYE paid', NULL, NULL, (CURRENT_DATE - 88 + time '17:00')::timestamptz),
    (200, (CURRENT_DATE - 85 + time '08:30')::timestamptz, (CURRENT_DATE - 85 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 85, pg_temp.period_of(CURRENT_DATE - 85), 'CR', 'P', 'A', 'PAY-00049', 'Protea Print Works', NULL, NULL, (CURRENT_DATE - 85 + time '17:00')::timestamptz),
    (201, (CURRENT_DATE - 85 + time '08:30')::timestamptz, (CURRENT_DATE - 85 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 85, pg_temp.period_of(CURRENT_DATE - 85), 'CR', 'P', 'C', 'PAY-00049', 'Protea Print Works (cash basis)', NULL, NULL, (CURRENT_DATE - 85 + time '17:00')::timestamptz),
    (202, (CURRENT_DATE - 83 + time '08:30')::timestamptz, (CURRENT_DATE - 83 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 83, pg_temp.period_of(CURRENT_DATE - 83), 'CP', 'P', 'A', 'PAY-00050', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 83 + time '17:00')::timestamptz),
    (203, (CURRENT_DATE - 83 + time '08:30')::timestamptz, (CURRENT_DATE - 83 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 83, pg_temp.period_of(CURRENT_DATE - 83), 'CP', 'P', 'C', 'PAY-00050', 'Highveld Fuel Services (cash basis)', NULL, NULL, (CURRENT_DATE - 83 + time '17:00')::timestamptz),
    (204, (CURRENT_DATE - 80 + time '08:30')::timestamptz, (CURRENT_DATE - 80 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 80, pg_temp.period_of(CURRENT_DATE - 80), 'CR', 'P', 'B', 'INT-009', 'Interest received', NULL, NULL, (CURRENT_DATE - 80 + time '17:00')::timestamptz),
    (205, (CURRENT_DATE - 80 + time '08:30')::timestamptz, (CURRENT_DATE - 80 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 80, pg_temp.period_of(CURRENT_DATE - 80), 'CP', 'P', 'B', 'LOAN-003', 'Vehicle finance instalment', NULL, NULL, (CURRENT_DATE - 80 + time '17:00')::timestamptz),
    (206, (CURRENT_DATE - 79 + time '08:30')::timestamptz, (CURRENT_DATE - 79 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 79, pg_temp.period_of(CURRENT_DATE - 79), 'CR', 'P', 'A', 'PAY-00051', 'Table Bay Marine (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 79 + time '17:00')::timestamptz),
    (207, (CURRENT_DATE - 79 + time '08:30')::timestamptz, (CURRENT_DATE - 79 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 79, pg_temp.period_of(CURRENT_DATE - 79), 'CR', 'P', 'C', 'PAY-00051', 'Table Bay Marine (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 79 + time '17:00')::timestamptz),
    (208, (CURRENT_DATE - 75 + time '08:30')::timestamptz, (CURRENT_DATE - 75 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 75, pg_temp.period_of(CURRENT_DATE - 75), 'S', 'P', 'A', 'INV-00023', 'Table Bay Marine (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 75 + time '17:00')::timestamptz),
    (209, (CURRENT_DATE - 75 + time '08:30')::timestamptz, (CURRENT_DATE - 75 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 75, pg_temp.period_of(CURRENT_DATE - 75), 'P', 'P', 'A', 'BILL-00033', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 75 + time '17:00')::timestamptz),
    (210, (CURRENT_DATE - 70 + time '08:30')::timestamptz, (CURRENT_DATE - 70 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 70, pg_temp.period_of(CURRENT_DATE - 70), 'CP', 'P', 'B', 'BCH-010', 'Bank charges', NULL, NULL, (CURRENT_DATE - 70 + time '17:00')::timestamptz),
    (211, (CURRENT_DATE - 70 + time '08:30')::timestamptz, (CURRENT_DATE - 70 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 70, pg_temp.period_of(CURRENT_DATE - 70), 'S', 'P', 'A', 'INV-00024', 'Table Bay Marine (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 70 + time '17:00')::timestamptz),
    (212, (CURRENT_DATE - 70 + time '08:30')::timestamptz, (CURRENT_DATE - 70 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 70, pg_temp.period_of(CURRENT_DATE - 70), 'CP', 'P', 'A', 'PAY-00052', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 70 + time '17:00')::timestamptz),
    (213, (CURRENT_DATE - 70 + time '08:30')::timestamptz, (CURRENT_DATE - 70 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 70, pg_temp.period_of(CURRENT_DATE - 70), 'CP', 'P', 'C', 'PAY-00052', 'Atlantic Cloud Hosting (cash basis)', NULL, NULL, (CURRENT_DATE - 70 + time '17:00')::timestamptz),
    (214, (CURRENT_DATE - 70 + time '08:30')::timestamptz, (CURRENT_DATE - 70 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 70, pg_temp.period_of(CURRENT_DATE - 70), 'CP', 'P', 'A', 'PAY-00053', 'Coastal Stock Distributors', NULL, NULL, (CURRENT_DATE - 70 + time '17:00')::timestamptz),
    (215, (CURRENT_DATE - 70 + time '08:30')::timestamptz, (CURRENT_DATE - 70 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 70, pg_temp.period_of(CURRENT_DATE - 70), 'CP', 'P', 'C', 'PAY-00053', 'Coastal Stock Distributors (cash basis)', NULL, NULL, (CURRENT_DATE - 70 + time '17:00')::timestamptz),
    (216, (CURRENT_DATE - 70 + time '08:30')::timestamptz, (CURRENT_DATE - 70 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 70, pg_temp.period_of(CURRENT_DATE - 70), 'G', 'P', 'B', 'COS-002', 'Cost of the stock sold', NULL, NULL, (CURRENT_DATE - 70 + time '17:00')::timestamptz),
    (217, (CURRENT_DATE - 65 + time '08:30')::timestamptz, (CURRENT_DATE - 65 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 65, pg_temp.period_of(CURRENT_DATE - 65), 'G', 'P', 'B', 'SAL-010', 'Salaries for the month', NULL, NULL, (CURRENT_DATE - 65 + time '17:00')::timestamptz),
    (218, (CURRENT_DATE - 65 + time '08:30')::timestamptz, (CURRENT_DATE - 65 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 65, pg_temp.period_of(CURRENT_DATE - 65), 'P', 'P', 'A', 'BILL-00034', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 65 + time '17:00')::timestamptz),
    (219, (CURRENT_DATE - 64 + time '08:30')::timestamptz, (CURRENT_DATE - 64 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 64, pg_temp.period_of(CURRENT_DATE - 64), 'CR', 'P', 'A', 'PAY-00054', 'Halcyon Interiors CC', NULL, NULL, (CURRENT_DATE - 64 + time '17:00')::timestamptz),
    (220, (CURRENT_DATE - 64 + time '08:30')::timestamptz, (CURRENT_DATE - 64 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 64, pg_temp.period_of(CURRENT_DATE - 64), 'CR', 'P', 'C', 'PAY-00054', 'Halcyon Interiors CC (cash basis)', NULL, NULL, (CURRENT_DATE - 64 + time '17:00')::timestamptz),
    (221, (CURRENT_DATE - 61 + time '08:30')::timestamptz, (CURRENT_DATE - 61 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 61, pg_temp.period_of(CURRENT_DATE - 61), 'P', 'P', 'A', 'BILL-00035', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 61 + time '17:00')::timestamptz),
    (222, (CURRENT_DATE - 61 + time '08:30')::timestamptz, (CURRENT_DATE - 61 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 61, pg_temp.period_of(CURRENT_DATE - 61), 'CP', 'P', 'A', 'PAY-00055', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 61 + time '17:00')::timestamptz),
    (223, (CURRENT_DATE - 61 + time '08:30')::timestamptz, (CURRENT_DATE - 61 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 61, pg_temp.period_of(CURRENT_DATE - 61), 'CP', 'P', 'C', 'PAY-00055', 'Metro Property Management (cash basis)', NULL, NULL, (CURRENT_DATE - 61 + time '17:00')::timestamptz),
    (224, (CURRENT_DATE - 60 + time '08:30')::timestamptz, (CURRENT_DATE - 60 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 60, pg_temp.period_of(CURRENT_DATE - 60), 'S', 'P', 'A', 'INV-00025', 'Protea Print Works', NULL, NULL, (CURRENT_DATE - 60 + time '17:00')::timestamptz),
    (225, (CURRENT_DATE - 60 + time '08:30')::timestamptz, (CURRENT_DATE - 60 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 60, pg_temp.period_of(CURRENT_DATE - 60), 'G', 'P', 'B', 'CC-001', 'Design software licence (credit card)', 2, NULL, (CURRENT_DATE - 60 + time '17:00')::timestamptz),
    (226, (CURRENT_DATE - 60 + time '08:30')::timestamptz, (CURRENT_DATE - 60 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 60, pg_temp.period_of(CURRENT_DATE - 60), 'S', 'P', 'A', 'INV-00026', 'Halcyon Interiors CC', NULL, NULL, (CURRENT_DATE - 60 + time '17:00')::timestamptz),
    (227, (CURRENT_DATE - 58 + time '08:30')::timestamptz, (CURRENT_DATE - 58 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 58, pg_temp.period_of(CURRENT_DATE - 58), 'CP', 'P', 'B', 'PAYE-010', 'PAYE paid', NULL, NULL, (CURRENT_DATE - 58 + time '17:00')::timestamptz),
    (228, (CURRENT_DATE - 53 + time '08:30')::timestamptz, (CURRENT_DATE - 53 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 53, pg_temp.period_of(CURRENT_DATE - 53), 'CP', 'P', 'A', 'PAY-00056', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 53 + time '17:00')::timestamptz),
    (229, (CURRENT_DATE - 53 + time '08:30')::timestamptz, (CURRENT_DATE - 53 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 53, pg_temp.period_of(CURRENT_DATE - 53), 'CP', 'P', 'C', 'PAY-00056', 'Highveld Fuel Services (cash basis)', NULL, NULL, (CURRENT_DATE - 53 + time '17:00')::timestamptz),
    (230, (CURRENT_DATE - 50 + time '08:30')::timestamptz, (CURRENT_DATE - 50 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 50, pg_temp.period_of(CURRENT_DATE - 50), 'CR', 'P', 'B', 'INT-010', 'Interest received', NULL, NULL, (CURRENT_DATE - 50 + time '17:00')::timestamptz),
    (231, (CURRENT_DATE - 50 + time '08:30')::timestamptz, (CURRENT_DATE - 50 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 50, pg_temp.period_of(CURRENT_DATE - 50), 'CP', 'P', 'B', 'LOAN-004', 'Vehicle finance instalment', NULL, NULL, (CURRENT_DATE - 50 + time '17:00')::timestamptz),
    (232, (CURRENT_DATE - 50 + time '08:30')::timestamptz, (CURRENT_DATE - 50 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 50, pg_temp.period_of(CURRENT_DATE - 50), 'S', 'P', 'A', 'INV-00027', 'Protea Print Works', NULL, NULL, (CURRENT_DATE - 50 + time '17:00')::timestamptz),
    (233, (CURRENT_DATE - 49 + time '08:30')::timestamptz, (CURRENT_DATE - 49 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 49, pg_temp.period_of(CURRENT_DATE - 49), 'CR', 'P', 'A', 'PAY-00057', 'Table Bay Marine (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 49 + time '17:00')::timestamptz),
    (234, (CURRENT_DATE - 49 + time '08:30')::timestamptz, (CURRENT_DATE - 49 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 49, pg_temp.period_of(CURRENT_DATE - 49), 'CR', 'P', 'C', 'PAY-00057', 'Table Bay Marine (Pty) Ltd (cash basis)', NULL, NULL, (CURRENT_DATE - 49 + time '17:00')::timestamptz),
    (235, (CURRENT_DATE - 45 + time '08:30')::timestamptz, (CURRENT_DATE - 45 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 45, pg_temp.period_of(CURRENT_DATE - 45), 'P', 'P', 'A', 'BILL-00037', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 45 + time '17:00')::timestamptz),
    (236, (CURRENT_DATE - 45 + time '08:30')::timestamptz, (CURRENT_DATE - 45 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 45, pg_temp.period_of(CURRENT_DATE - 45), 'P', 'P', 'A', 'BILL-00038', 'Cape Office Supplies (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 45 + time '17:00')::timestamptz),
    (237, (CURRENT_DATE - 40 + time '08:30')::timestamptz, (CURRENT_DATE - 40 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 40, pg_temp.period_of(CURRENT_DATE - 40), 'CP', 'P', 'B', 'BCH-011', 'Bank charges', NULL, NULL, (CURRENT_DATE - 40 + time '17:00')::timestamptz),
    (238, (CURRENT_DATE - 40 + time '08:30')::timestamptz, (CURRENT_DATE - 40 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 40, pg_temp.period_of(CURRENT_DATE - 40), 'S', 'P', 'A', 'INV-00028', 'Karoo Fresh Produce (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 40 + time '17:00')::timestamptz),
    (239, (CURRENT_DATE - 40 + time '08:30')::timestamptz, (CURRENT_DATE - 40 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 40, pg_temp.period_of(CURRENT_DATE - 40), 'P', 'P', 'A', 'BILL-00039', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 40 + time '17:00')::timestamptz),
    (240, (CURRENT_DATE - 40 + time '08:30')::timestamptz, (CURRENT_DATE - 40 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 40, pg_temp.period_of(CURRENT_DATE - 40), 'CP', 'P', 'A', 'PAY-00058', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 40 + time '17:00')::timestamptz),
    (241, (CURRENT_DATE - 40 + time '08:30')::timestamptz, (CURRENT_DATE - 40 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 40, pg_temp.period_of(CURRENT_DATE - 40), 'CP', 'P', 'C', 'PAY-00058', 'Atlantic Cloud Hosting (cash basis)', NULL, NULL, (CURRENT_DATE - 40 + time '17:00')::timestamptz),
    (242, (CURRENT_DATE - 40 + time '08:30')::timestamptz, (CURRENT_DATE - 40 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 40, pg_temp.period_of(CURRENT_DATE - 40), 'CP', 'P', 'B', 'VAT-006', 'VAT return paid', NULL, NULL, (CURRENT_DATE - 40 + time '17:00')::timestamptz),
    (243, (CURRENT_DATE - 40 + time '08:30')::timestamptz, (CURRENT_DATE - 40 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 40, pg_temp.period_of(CURRENT_DATE - 40), 'G', 'P', 'B', 'COS-003', 'Cost of the stock sold', NULL, NULL, (CURRENT_DATE - 40 + time '17:00')::timestamptz),
    (244, (CURRENT_DATE - 35 + time '08:30')::timestamptz, (CURRENT_DATE - 35 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 35, pg_temp.period_of(CURRENT_DATE - 35), 'G', 'P', 'B', 'SAL-011', 'Salaries for the month', NULL, NULL, (CURRENT_DATE - 35 + time '17:00')::timestamptz),
    (245, (CURRENT_DATE - 35 + time '08:30')::timestamptz, (CURRENT_DATE - 35 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 35, pg_temp.period_of(CURRENT_DATE - 35), 'CR', 'P', 'A', 'PAY-00059', 'Halcyon Interiors CC', NULL, NULL, (CURRENT_DATE - 35 + time '17:00')::timestamptz),
    (246, (CURRENT_DATE - 35 + time '08:30')::timestamptz, (CURRENT_DATE - 35 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 35, pg_temp.period_of(CURRENT_DATE - 35), 'CR', 'P', 'C', 'PAY-00059', 'Halcyon Interiors CC (cash basis)', NULL, NULL, (CURRENT_DATE - 35 + time '17:00')::timestamptz),
    (247, (CURRENT_DATE - 34 + time '08:30')::timestamptz, (CURRENT_DATE - 34 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 34, pg_temp.period_of(CURRENT_DATE - 34), 'CR', 'P', 'A', 'PAY-00060', 'Protea Print Works', NULL, NULL, (CURRENT_DATE - 34 + time '17:00')::timestamptz),
    (248, (CURRENT_DATE - 34 + time '08:30')::timestamptz, (CURRENT_DATE - 34 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 34, pg_temp.period_of(CURRENT_DATE - 34), 'CR', 'P', 'C', 'PAY-00060', 'Protea Print Works (cash basis)', NULL, NULL, (CURRENT_DATE - 34 + time '17:00')::timestamptz),
    (249, (CURRENT_DATE - 32 + time '08:30')::timestamptz, (CURRENT_DATE - 32 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 32, pg_temp.period_of(CURRENT_DATE - 32), 'G', 'P', 'A', 'ACR-001', 'Telephone accrual at month end', NULL, NULL, (CURRENT_DATE - 32 + time '17:00')::timestamptz),
    (250, (CURRENT_DATE - 31 + time '08:30')::timestamptz, (CURRENT_DATE - 31 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 31, pg_temp.period_of(CURRENT_DATE - 31), 'P', 'P', 'A', 'BILL-00040', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 31 + time '17:00')::timestamptz),
    (251, (CURRENT_DATE - 31 + time '08:30')::timestamptz, (CURRENT_DATE - 31 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 31, pg_temp.period_of(CURRENT_DATE - 31), 'CP', 'P', 'A', 'PAY-00061', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 31 + time '17:00')::timestamptz),
    (252, (CURRENT_DATE - 31 + time '08:30')::timestamptz, (CURRENT_DATE - 31 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 31, pg_temp.period_of(CURRENT_DATE - 31), 'CP', 'P', 'C', 'PAY-00061', 'Metro Property Management (cash basis)', NULL, NULL, (CURRENT_DATE - 31 + time '17:00')::timestamptz),
    (253, (CURRENT_DATE - 30 + time '08:30')::timestamptz, (CURRENT_DATE - 30 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 30, pg_temp.period_of(CURRENT_DATE - 30), 'CP', 'P', 'B', 'CC-002', 'Credit card statement paid', NULL, NULL, (CURRENT_DATE - 30 + time '17:00')::timestamptz),
    (254, (CURRENT_DATE - 30 + time '08:30')::timestamptz, (CURRENT_DATE - 30 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 30, pg_temp.period_of(CURRENT_DATE - 30), 'S', 'P', 'A', 'INV-00029', 'Lerato Molefe', NULL, NULL, (CURRENT_DATE - 30 + time '17:00')::timestamptz),
    (255, (CURRENT_DATE - 30 + time '08:30')::timestamptz, (CURRENT_DATE - 30 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 30, pg_temp.period_of(CURRENT_DATE - 30), 'G', 'P', 'A', 'ACR-001R', 'Reversal of ACR-001', NULL, 249, (CURRENT_DATE - 30 + time '17:00')::timestamptz),
    (256, (CURRENT_DATE - 29 + time '08:30')::timestamptz, (CURRENT_DATE - 29 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 29, pg_temp.period_of(CURRENT_DATE - 29), 'G', 'P', 'B', 'CC-003', 'Mobile and fibre (credit card)', NULL, NULL, (CURRENT_DATE - 29 + time '17:00')::timestamptz),
    (257, (CURRENT_DATE - 28 + time '08:30')::timestamptz, (CURRENT_DATE - 28 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 28, pg_temp.period_of(CURRENT_DATE - 28), 'CP', 'P', 'B', 'PAYE-011', 'PAYE paid', NULL, NULL, (CURRENT_DATE - 28 + time '17:00')::timestamptz),
    (258, (CURRENT_DATE - 28 + time '08:30')::timestamptz, (CURRENT_DATE - 28 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 28, pg_temp.period_of(CURRENT_DATE - 28), 'P', 'P', 'A', 'BILL-00041', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 28 + time '17:00')::timestamptz),
    (259, (CURRENT_DATE - 28 + time '08:30')::timestamptz, (CURRENT_DATE - 28 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 28, pg_temp.period_of(CURRENT_DATE - 28), 'CR', 'P', 'A', 'PAY-00062', 'Lerato Molefe', NULL, NULL, (CURRENT_DATE - 28 + time '17:00')::timestamptz),
    (260, (CURRENT_DATE - 28 + time '08:30')::timestamptz, (CURRENT_DATE - 28 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 28, pg_temp.period_of(CURRENT_DATE - 28), 'CR', 'P', 'C', 'PAY-00062', 'Lerato Molefe (cash basis)', NULL, NULL, (CURRENT_DATE - 28 + time '17:00')::timestamptz),
    (261, (CURRENT_DATE - 26 + time '08:30')::timestamptz, (CURRENT_DATE - 26 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 26, pg_temp.period_of(CURRENT_DATE - 26), 'CP', 'P', 'A', 'PAY-00063', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 26 + time '17:00')::timestamptz),
    (262, (CURRENT_DATE - 26 + time '08:30')::timestamptz, (CURRENT_DATE - 26 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 26, pg_temp.period_of(CURRENT_DATE - 26), 'CP', 'P', 'C', 'PAY-00063', 'Highveld Fuel Services (cash basis)', NULL, NULL, (CURRENT_DATE - 26 + time '17:00')::timestamptz),
    (263, (CURRENT_DATE - 25 + time '08:30')::timestamptz, (CURRENT_DATE - 25 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 25, pg_temp.period_of(CURRENT_DATE - 25), 'S', 'P', 'A', 'INV-00030', 'Table Bay Marine (Pty) Ltd', NULL, NULL, (CURRENT_DATE - 25 + time '17:00')::timestamptz),
    (264, (CURRENT_DATE - 20 + time '08:30')::timestamptz, (CURRENT_DATE - 20 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 20, pg_temp.period_of(CURRENT_DATE - 20), 'CR', 'P', 'B', 'INT-011', 'Interest received', NULL, NULL, (CURRENT_DATE - 20 + time '17:00')::timestamptz),
    (265, (CURRENT_DATE - 20 + time '08:30')::timestamptz, (CURRENT_DATE - 20 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 20, pg_temp.period_of(CURRENT_DATE - 20), 'CP', 'P', 'B', 'LOAN-005', 'Vehicle finance instalment', NULL, NULL, (CURRENT_DATE - 20 + time '17:00')::timestamptz),
    (266, (CURRENT_DATE - 20 + time '08:30')::timestamptz, (CURRENT_DATE - 20 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 20, pg_temp.period_of(CURRENT_DATE - 20), 'G', 'P', 'B', 'CC-004', 'Travel to Durban (credit card)', NULL, NULL, (CURRENT_DATE - 20 + time '17:00')::timestamptz),
    (267, (CURRENT_DATE - 20 + time '08:30')::timestamptz, (CURRENT_DATE - 20 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 20, pg_temp.period_of(CURRENT_DATE - 20), 'S', 'P', 'A', 'INV-00031', 'Halcyon Interiors CC', NULL, NULL, (CURRENT_DATE - 20 + time '17:00')::timestamptz),
    (268, (CURRENT_DATE - 20 + time '08:30')::timestamptz, (CURRENT_DATE - 20 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 20, pg_temp.period_of(CURRENT_DATE - 20), 'CP', 'P', 'A', 'PAY-00064', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 20 + time '17:00')::timestamptz),
    (269, (CURRENT_DATE - 20 + time '08:30')::timestamptz, (CURRENT_DATE - 20 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 20, pg_temp.period_of(CURRENT_DATE - 20), 'CP', 'P', 'C', 'PAY-00064', 'Highveld Fuel Services (cash basis)', NULL, NULL, (CURRENT_DATE - 20 + time '17:00')::timestamptz),
    (270, (CURRENT_DATE - 18 + time '08:30')::timestamptz, (CURRENT_DATE - 18 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 18, pg_temp.period_of(CURRENT_DATE - 18), 'G', 'P', 'B', 'PC-001', 'Courier fees (petty cash)', NULL, NULL, (CURRENT_DATE - 18 + time '17:00')::timestamptz),
    (271, (CURRENT_DATE - 15 + time '08:30')::timestamptz, (CURRENT_DATE - 15 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 15, pg_temp.period_of(CURRENT_DATE - 15), 'P', 'P', 'A', 'BILL-00042', 'Atlantic Cloud Hosting', NULL, NULL, (CURRENT_DATE - 15 + time '17:00')::timestamptz),
    (272, (CURRENT_DATE - 15 + time '08:30')::timestamptz, (CURRENT_DATE - 15 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 15, pg_temp.period_of(CURRENT_DATE - 15), 'G', 'P', 'B', 'ADJ-001', 'Stock count: damaged labels', NULL, NULL, (CURRENT_DATE - 15 + time '17:00')::timestamptz),
    (273, (CURRENT_DATE - 12 + time '08:30')::timestamptz, (CURRENT_DATE - 12 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 12, pg_temp.period_of(CURRENT_DATE - 12), 'S', 'P', 'A', 'INV-00032', 'Protea Print Works', NULL, NULL, (CURRENT_DATE - 12 + time '17:00')::timestamptz),
    (274, (CURRENT_DATE - 10 + time '08:30')::timestamptz, (CURRENT_DATE - 10 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 10, pg_temp.period_of(CURRENT_DATE - 10), 'CP', 'P', 'B', 'BCH-012', 'Bank charges', 1, NULL, (CURRENT_DATE - 10 + time '17:00')::timestamptz),
    (275, (CURRENT_DATE - 10 + time '08:30')::timestamptz, (CURRENT_DATE - 10 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 10, pg_temp.period_of(CURRENT_DATE - 10), 'G', 'P', 'B', 'TAX-003', 'Income tax accrual for the quarter', NULL, NULL, (CURRENT_DATE - 10 + time '17:00')::timestamptz),
    (276, (CURRENT_DATE - 10 + time '08:30')::timestamptz, (CURRENT_DATE - 10 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 10, pg_temp.period_of(CURRENT_DATE - 10), 'P', 'P', 'A', 'BILL-00043', 'Highveld Fuel Services', NULL, NULL, (CURRENT_DATE - 10 + time '17:00')::timestamptz),
    (277, (CURRENT_DATE - 8 + time '08:30')::timestamptz, (CURRENT_DATE - 8 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 8, pg_temp.period_of(CURRENT_DATE - 8), 'CR', 'P', 'A', 'PAY-00065', 'Halcyon Interiors CC', NULL, NULL, (CURRENT_DATE - 8 + time '17:00')::timestamptz),
    (278, (CURRENT_DATE - 8 + time '08:30')::timestamptz, (CURRENT_DATE - 8 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 8, pg_temp.period_of(CURRENT_DATE - 8), 'CR', 'P', 'C', 'PAY-00065', 'Halcyon Interiors CC (cash basis)', NULL, NULL, (CURRENT_DATE - 8 + time '17:00')::timestamptz),
    (279, (CURRENT_DATE - 6 + time '08:30')::timestamptz, (CURRENT_DATE - 6 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 6, pg_temp.period_of(CURRENT_DATE - 6), 'G', 'V', 'B', 'JNL-001', 'Office supplies (captured twice)', NULL, NULL, NULL),
    (280, (CURRENT_DATE - 5 + time '08:30')::timestamptz, (CURRENT_DATE - 5 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 5, pg_temp.period_of(CURRENT_DATE - 5), 'G', 'P', 'B', 'SAL-012', 'Salaries for the month', NULL, NULL, (CURRENT_DATE - 5 + time '17:00')::timestamptz),
    (281, (CURRENT_DATE - 4 + time '08:30')::timestamptz, (CURRENT_DATE - 4 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 4, pg_temp.period_of(CURRENT_DATE - 4), 'CR', 'D', 'A', 'PAY-00066', 'Protea Print Works', NULL, NULL, NULL),
    (282, (CURRENT_DATE - 4 + time '08:30')::timestamptz, (CURRENT_DATE - 4 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 4, pg_temp.period_of(CURRENT_DATE - 4), 'CR', 'D', 'C', 'PAY-00066', 'Protea Print Works (cash basis)', NULL, NULL, NULL),
    (283, (CURRENT_DATE - 3 + time '08:30')::timestamptz, (CURRENT_DATE - 3 + time '08:30')::timestamptz, 1, 1, CURRENT_DATE - 3, pg_temp.period_of(CURRENT_DATE - 3), 'S', 'D', 'A', 'INV-00033', 'Karoo Fresh Produce (Pty) Ltd', NULL, NULL, NULL),
    (284, (CURRENT_DATE - 1 + time '08:30')::timestamptz, (CURRENT_DATE - 1 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 1, pg_temp.period_of(CURRENT_DATE - 1), 'P', 'P', 'A', 'BILL-00045', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 1 + time '17:00')::timestamptz),
    (285, (CURRENT_DATE - 1 + time '08:30')::timestamptz, (CURRENT_DATE - 1 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 1, pg_temp.period_of(CURRENT_DATE - 1), 'G', 'D', 'A', 'ACR-002', 'Telephone accrual at month end', NULL, NULL, NULL),
    (286, (CURRENT_DATE - 1 + time '08:30')::timestamptz, (CURRENT_DATE - 1 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 1, pg_temp.period_of(CURRENT_DATE - 1), 'CP', 'P', 'A', 'PAY-00067', 'Metro Property Management', NULL, NULL, (CURRENT_DATE - 1 + time '17:00')::timestamptz),
    (287, (CURRENT_DATE - 1 + time '08:30')::timestamptz, (CURRENT_DATE - 1 + time '08:30')::timestamptz, 2, 1, CURRENT_DATE - 1, pg_temp.period_of(CURRENT_DATE - 1), 'CP', 'P', 'C', 'PAY-00067', 'Metro Property Management (cash basis)', NULL, NULL, (CURRENT_DATE - 1 + time '17:00')::timestamptz),
    (288, ((date_trunc('month', CURRENT_DATE) - interval '4 month' - interval '1 day')::date + time '08:30')::timestamptz, ((date_trunc('month', CURRENT_DATE) - interval '4 month' - interval '1 day')::date + time '08:30')::timestamptz, 2, 1, (date_trunc('month', CURRENT_DATE) - interval '4 month' - interval '1 day')::date, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '4 month' - interval '1 day')::date), 'G', 'P', 'B', 'DEP-001-01', 'Depreciation — Laptops (3)', NULL, NULL, ((date_trunc('month', CURRENT_DATE) - interval '4 month' - interval '1 day')::date + time '17:00')::timestamptz),
    (289, ((date_trunc('month', CURRENT_DATE) - interval '3 month' - interval '1 day')::date + time '08:30')::timestamptz, ((date_trunc('month', CURRENT_DATE) - interval '3 month' - interval '1 day')::date + time '08:30')::timestamptz, 2, 1, (date_trunc('month', CURRENT_DATE) - interval '3 month' - interval '1 day')::date, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '3 month' - interval '1 day')::date), 'G', 'P', 'B', 'DEP-001-02', 'Depreciation — Laptops (3)', NULL, NULL, ((date_trunc('month', CURRENT_DATE) - interval '3 month' - interval '1 day')::date + time '17:00')::timestamptz),
    (290, ((date_trunc('month', CURRENT_DATE) - interval '2 month' - interval '1 day')::date + time '08:30')::timestamptz, ((date_trunc('month', CURRENT_DATE) - interval '2 month' - interval '1 day')::date + time '08:30')::timestamptz, 2, 1, (date_trunc('month', CURRENT_DATE) - interval '2 month' - interval '1 day')::date, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '2 month' - interval '1 day')::date), 'G', 'P', 'B', 'DEP-001-03', 'Depreciation — Laptops (3)', NULL, NULL, ((date_trunc('month', CURRENT_DATE) - interval '2 month' - interval '1 day')::date + time '17:00')::timestamptz),
    (291, ((date_trunc('month', CURRENT_DATE) - interval '1 month' - interval '1 day')::date + time '08:30')::timestamptz, ((date_trunc('month', CURRENT_DATE) - interval '1 month' - interval '1 day')::date + time '08:30')::timestamptz, 2, 1, (date_trunc('month', CURRENT_DATE) - interval '1 month' - interval '1 day')::date, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '1 month' - interval '1 day')::date), 'G', 'P', 'B', 'DEP-001-04', 'Depreciation — Laptops (3)', NULL, NULL, ((date_trunc('month', CURRENT_DATE) - interval '1 month' - interval '1 day')::date + time '17:00')::timestamptz),
    (292, ((date_trunc('month', CURRENT_DATE) - interval '0 month' - interval '1 day')::date + time '08:30')::timestamptz, ((date_trunc('month', CURRENT_DATE) - interval '0 month' - interval '1 day')::date + time '08:30')::timestamptz, 2, 1, (date_trunc('month', CURRENT_DATE) - interval '0 month' - interval '1 day')::date, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '0 month' - interval '1 day')::date), 'G', 'P', 'B', 'DEP-001-05', 'Depreciation — Laptops (3)', NULL, NULL, ((date_trunc('month', CURRENT_DATE) - interval '0 month' - interval '1 day')::date + time '17:00')::timestamptz),
    (293, ((date_trunc('month', CURRENT_DATE) - interval '3 month' - interval '1 day')::date + time '08:30')::timestamptz, ((date_trunc('month', CURRENT_DATE) - interval '3 month' - interval '1 day')::date + time '08:30')::timestamptz, 2, 1, (date_trunc('month', CURRENT_DATE) - interval '3 month' - interval '1 day')::date, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '3 month' - interval '1 day')::date), 'G', 'P', 'B', 'DEP-002-01', 'Depreciation — Delivery vehicle', NULL, NULL, ((date_trunc('month', CURRENT_DATE) - interval '3 month' - interval '1 day')::date + time '17:00')::timestamptz),
    (294, ((date_trunc('month', CURRENT_DATE) - interval '2 month' - interval '1 day')::date + time '08:30')::timestamptz, ((date_trunc('month', CURRENT_DATE) - interval '2 month' - interval '1 day')::date + time '08:30')::timestamptz, 2, 1, (date_trunc('month', CURRENT_DATE) - interval '2 month' - interval '1 day')::date, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '2 month' - interval '1 day')::date), 'G', 'P', 'B', 'DEP-002-02', 'Depreciation — Delivery vehicle', NULL, NULL, ((date_trunc('month', CURRENT_DATE) - interval '2 month' - interval '1 day')::date + time '17:00')::timestamptz),
    (295, ((date_trunc('month', CURRENT_DATE) - interval '1 month' - interval '1 day')::date + time '08:30')::timestamptz, ((date_trunc('month', CURRENT_DATE) - interval '1 month' - interval '1 day')::date + time '08:30')::timestamptz, 2, 1, (date_trunc('month', CURRENT_DATE) - interval '1 month' - interval '1 day')::date, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '1 month' - interval '1 day')::date), 'G', 'P', 'B', 'DEP-002-03', 'Depreciation — Delivery vehicle', NULL, NULL, ((date_trunc('month', CURRENT_DATE) - interval '1 month' - interval '1 day')::date + time '17:00')::timestamptz),
    (296, ((date_trunc('month', CURRENT_DATE) - interval '0 month' - interval '1 day')::date + time '08:30')::timestamptz, ((date_trunc('month', CURRENT_DATE) - interval '0 month' - interval '1 day')::date + time '08:30')::timestamptz, 2, 1, (date_trunc('month', CURRENT_DATE) - interval '0 month' - interval '1 day')::date, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '0 month' - interval '1 day')::date), 'G', 'P', 'B', 'DEP-002-04', 'Depreciation — Delivery vehicle', NULL, NULL, ((date_trunc('month', CURRENT_DATE) - interval '0 month' - interval '1 day')::date + time '17:00')::timestamptz);

INSERT INTO accounting_journalline (id, entry_id, account_id, description, currency_id, exchange_rate, debit, credit, base_debit, base_credit, tax_code_id, entity_id, cost_centre_id, project_id) VALUES
    -- OB-001 · Opening balances
    (1, 1, 1, '', 'ZAR', 1.00000000, 380000.00, 0, 380000.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (2, 1, 2, '', 'ZAR', 1.00000000, 120000.00, 0, 120000.00, 0, NULL, NULL, NULL, NULL),  -- Savings Account
    (3, 1, 3, '', 'ZAR', 1.00000000, 2000.00, 0, 2000.00, 0, NULL, NULL, NULL, NULL),  -- Petty Cash
    (4, 1, 7, '', 'ZAR', 1.00000000, 8000.00, 0, 8000.00, 0, NULL, NULL, NULL, NULL),  -- Computer Equipment
    (5, 1, 8, '', 'ZAR', 1.00000000, 0, 7500.00, 0, 7500.00, NULL, NULL, NULL, NULL),  -- Accumulated Depreciation — Computer Equipment
    (6, 1, 19, '', 'ZAR', 1.00000000, 0, 100000.00, 0, 100000.00, NULL, NULL, NULL, NULL),  -- Share Capital
    (7, 1, 20, '', 'ZAR', 1.00000000, 0, 402500.00, 0, 402500.00, NULL, NULL, NULL, NULL),  -- Retained Earnings
    -- INV-00001 · Karoo Fresh Produce (Pty) Ltd
    (8, 2, 4, '', 'ZAR', 1.00000000, 53705.00, 0, 53705.00, 0, NULL, 1, NULL, NULL),  -- Accounts Receivable · Karoo Fresh Produce (Pty) Ltd
    (9, 2, 21, '', 'ZAR', 1.00000000, 0, 46700.00, 0, 46700.00, NULL, NULL, NULL, NULL),  -- Sales
    (10, 2, 13, '', 'ZAR', 1.00000000, 0, 7005.00, 0, 7005.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00002 · Halcyon Interiors CC
    (11, 3, 4, '', 'ZAR', 1.00000000, 56752.50, 0, 56752.50, 0, NULL, 2, NULL, NULL),  -- Accounts Receivable · Halcyon Interiors CC
    (12, 3, 21, '', 'ZAR', 1.00000000, 0, 49350.00, 0, 49350.00, NULL, NULL, NULL, NULL),  -- Sales
    (13, 3, 13, '', 'ZAR', 1.00000000, 0, 7402.50, 0, 7402.50, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAY-00001 · Karoo Fresh Produce (Pty) Ltd
    (14, 4, 1, '', 'ZAR', 1.00000000, 53705.00, 0, 53705.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (15, 4, 4, '', 'ZAR', 1.00000000, 0, 53705.00, 0, 53705.00, NULL, 1, NULL, NULL),  -- Accounts Receivable · Karoo Fresh Produce (Pty) Ltd
    -- PAY-00001 · Karoo Fresh Produce (Pty) Ltd (cash basis)
    (16, 5, 1, '', 'ZAR', 1.00000000, 53705.00, 0, 53705.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (17, 5, 21, '', 'ZAR', 1.00000000, 0, 34200.00, 0, 34200.00, NULL, NULL, NULL, NULL),  -- Sales
    (18, 5, 13, '', 'ZAR', 1.00000000, 0, 5130.00, 0, 5130.00, NULL, NULL, NULL, NULL),  -- VAT Control
    (19, 5, 21, '', 'ZAR', 1.00000000, 0, 12500.00, 0, 12500.00, NULL, NULL, NULL, NULL),  -- Sales
    (20, 5, 13, '', 'ZAR', 1.00000000, 0, 1875.00, 0, 1875.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00003 · Table Bay Marine (Pty) Ltd
    (21, 6, 4, '', 'ZAR', 1.00000000, 64400.00, 0, 64400.00, 0, NULL, 3, NULL, NULL),  -- Accounts Receivable · Table Bay Marine (Pty) Ltd
    (22, 6, 21, '', 'ZAR', 1.00000000, 0, 56000.00, 0, 56000.00, NULL, NULL, NULL, NULL),  -- Sales
    (23, 6, 13, '', 'ZAR', 1.00000000, 0, 8400.00, 0, 8400.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAY-00002 · Halcyon Interiors CC
    (24, 7, 1, '', 'ZAR', 1.00000000, 56752.50, 0, 56752.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (25, 7, 4, '', 'ZAR', 1.00000000, 0, 56752.50, 0, 56752.50, NULL, 2, NULL, NULL),  -- Accounts Receivable · Halcyon Interiors CC
    -- PAY-00002 · Halcyon Interiors CC (cash basis)
    (26, 8, 1, '', 'ZAR', 1.00000000, 56752.50, 0, 56752.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (27, 8, 21, '', 'ZAR', 1.00000000, 0, 40850.00, 0, 40850.00, NULL, NULL, NULL, NULL),  -- Sales
    (28, 8, 13, '', 'ZAR', 1.00000000, 0, 6127.50, 0, 6127.50, NULL, NULL, NULL, NULL),  -- VAT Control
    (29, 8, 21, '', 'ZAR', 1.00000000, 0, 8500.00, 0, 8500.00, NULL, NULL, NULL, NULL),  -- Sales
    (30, 8, 13, '', 'ZAR', 1.00000000, 0, 1275.00, 0, 1275.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00004 · Protea Print Works
    (31, 9, 4, '', 'ZAR', 1.00000000, 76647.50, 0, 76647.50, 0, NULL, 4, NULL, NULL),  -- Accounts Receivable · Protea Print Works
    (32, 9, 21, '', 'ZAR', 1.00000000, 0, 66650.00, 0, 66650.00, NULL, NULL, NULL, NULL),  -- Sales
    (33, 9, 13, '', 'ZAR', 1.00000000, 0, 9997.50, 0, 9997.50, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00001 · Atlantic Cloud Hosting
    (34, 10, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (35, 10, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (36, 10, 12, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- BCH-001 · Bank charges
    (37, 11, 29, '', 'ZAR', 1.00000000, 245.00, 0, 245.00, 0, NULL, NULL, NULL, NULL),  -- Bank Charges
    (38, 11, 1, '', 'ZAR', 1.00000000, 0, 245.00, 0, 245.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00003 · Atlantic Cloud Hosting
    (39, 12, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (40, 12, 12, '', 'ZAR', 1.00000000, 4485.00, 0, 4485.00, 0, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- PAY-00003 · Atlantic Cloud Hosting (cash basis)
    (41, 13, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (42, 13, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (43, 13, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- VAT-001 · VAT return paid
    (44, 14, 13, '', 'ZAR', 1.00000000, 22807.50, 0, 22807.50, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (45, 14, 1, '', 'ZAR', 1.00000000, 0, 22807.50, 0, 22807.50, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- SAL-001 · Salaries for the month
    (46, 15, 24, 'Gross salaries', 'ZAR', 1.00000000, 52000.00, 0, 52000.00, 0, NULL, NULL, 3, NULL),  -- Salaries and Wages
    (47, 15, 1, 'Net pay', 'ZAR', 1.00000000, 0, 43160.00, 0, 43160.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (48, 15, 14, 'PAYE withheld', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- PAYE Payable
    -- BILL-00002 · Highveld Fuel Services
    (49, 16, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (50, 16, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (51, 16, 12, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00004 · Table Bay Marine (Pty) Ltd
    (52, 17, 1, '', 'ZAR', 1.00000000, 64400.00, 0, 64400.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (53, 17, 4, '', 'ZAR', 1.00000000, 0, 64400.00, 0, 64400.00, NULL, 3, NULL, NULL),  -- Accounts Receivable · Table Bay Marine (Pty) Ltd
    -- PAY-00004 · Table Bay Marine (Pty) Ltd (cash basis)
    (54, 18, 1, '', 'ZAR', 1.00000000, 64400.00, 0, 64400.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (55, 18, 21, '', 'ZAR', 1.00000000, 0, 47500.00, 0, 47500.00, NULL, NULL, NULL, NULL),  -- Sales
    (56, 18, 13, '', 'ZAR', 1.00000000, 0, 7125.00, 0, 7125.00, NULL, NULL, NULL, NULL),  -- VAT Control
    (57, 18, 21, '', 'ZAR', 1.00000000, 0, 8500.00, 0, 8500.00, NULL, NULL, NULL, NULL),  -- Sales
    (58, 18, 13, '', 'ZAR', 1.00000000, 0, 1275.00, 0, 1275.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00003 · Metro Property Management
    (59, 19, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (60, 19, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (61, 19, 12, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00005 · Metro Property Management
    (62, 20, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (63, 20, 12, '', 'ZAR', 1.00000000, 25300.00, 0, 25300.00, 0, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00005 · Metro Property Management (cash basis)
    (64, 21, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (65, 21, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (66, 21, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00005 · Karoo Fresh Produce (Pty) Ltd
    (67, 22, 4, '', 'ZAR', 1.00000000, 39330.00, 0, 39330.00, 0, NULL, 1, NULL, NULL),  -- Accounts Receivable · Karoo Fresh Produce (Pty) Ltd
    (68, 22, 21, '', 'ZAR', 1.00000000, 0, 34200.00, 0, 34200.00, NULL, NULL, NULL, NULL),  -- Sales
    (69, 22, 13, '', 'ZAR', 1.00000000, 0, 5130.00, 0, 5130.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAYE-001 · PAYE paid
    (70, 23, 14, '', 'ZAR', 1.00000000, 8840.00, 0, 8840.00, 0, NULL, NULL, NULL, NULL),  -- PAYE Payable
    (71, 23, 1, '', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00006 · Highveld Fuel Services
    (72, 24, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (73, 24, 12, '', 'ZAR', 1.00000000, 3220.00, 0, 3220.00, 0, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00006 · Highveld Fuel Services (cash basis)
    (74, 25, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (75, 25, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (76, 25, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INT-001 · Interest received
    (77, 26, 2, '', 'ZAR', 1.00000000, 610.00, 0, 610.00, 0, NULL, NULL, NULL, NULL),  -- Savings Account
    (78, 26, 22, '', 'ZAR', 1.00000000, 0, 610.00, 0, 610.00, NULL, NULL, NULL, NULL),  -- Interest Received
    -- BILL-00004 · Cape Office Supplies (Pty) Ltd
    (79, 27, 26, '', 'ZAR', 1.00000000, 1700.00, 0, 1700.00, 0, NULL, NULL, NULL, NULL),  -- Office Supplies
    (80, 27, 13, '', 'ZAR', 1.00000000, 255.00, 0, 255.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (81, 27, 26, '', 'ZAR', 1.00000000, 700.00, 0, 700.00, 0, NULL, NULL, NULL, NULL),  -- Office Supplies
    (82, 27, 13, '', 'ZAR', 1.00000000, 105.00, 0, 105.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (83, 27, 12, '', 'ZAR', 1.00000000, 0, 2760.00, 0, 2760.00, NULL, 12, NULL, NULL),  -- Accounts Payable · Cape Office Supplies (Pty) Ltd
    -- PAY-00007 · Protea Print Works
    (84, 28, 1, '', 'ZAR', 1.00000000, 76647.50, 0, 76647.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (85, 28, 4, '', 'ZAR', 1.00000000, 0, 76647.50, 0, 76647.50, NULL, 4, NULL, NULL),  -- Accounts Receivable · Protea Print Works
    -- PAY-00007 · Protea Print Works (cash basis)
    (86, 29, 1, '', 'ZAR', 1.00000000, 76647.50, 0, 76647.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (87, 29, 21, '', 'ZAR', 1.00000000, 0, 54150.00, 0, 54150.00, NULL, NULL, NULL, NULL),  -- Sales
    (88, 29, 13, '', 'ZAR', 1.00000000, 0, 8122.50, 0, 8122.50, NULL, NULL, NULL, NULL),  -- VAT Control
    (89, 29, 21, '', 'ZAR', 1.00000000, 0, 12500.00, 0, 12500.00, NULL, NULL, NULL, NULL),  -- Sales
    (90, 29, 13, '', 'ZAR', 1.00000000, 0, 1875.00, 0, 1875.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00006 · Table Bay Marine (Pty) Ltd
    (91, 30, 4, '', 'ZAR', 1.00000000, 56752.50, 0, 56752.50, 0, NULL, 3, NULL, NULL),  -- Accounts Receivable · Table Bay Marine (Pty) Ltd
    (92, 30, 21, '', 'ZAR', 1.00000000, 0, 49350.00, 0, 49350.00, NULL, NULL, NULL, NULL),  -- Sales
    (93, 30, 13, '', 'ZAR', 1.00000000, 0, 7402.50, 0, 7402.50, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00005 · Atlantic Cloud Hosting
    (94, 31, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (95, 31, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (96, 31, 12, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- BCH-002 · Bank charges
    (97, 32, 29, '', 'ZAR', 1.00000000, 245.00, 0, 245.00, 0, NULL, NULL, NULL, NULL),  -- Bank Charges
    (98, 32, 1, '', 'ZAR', 1.00000000, 0, 245.00, 0, 245.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00008 · Atlantic Cloud Hosting
    (99, 33, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (100, 33, 12, '', 'ZAR', 1.00000000, 4485.00, 0, 4485.00, 0, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- PAY-00008 · Atlantic Cloud Hosting (cash basis)
    (101, 34, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (102, 34, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (103, 34, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- SAL-002 · Salaries for the month
    (104, 35, 24, 'Gross salaries', 'ZAR', 1.00000000, 52000.00, 0, 52000.00, 0, NULL, NULL, 3, NULL),  -- Salaries and Wages
    (105, 35, 1, 'Net pay', 'ZAR', 1.00000000, 0, 43160.00, 0, 43160.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (106, 35, 14, 'PAYE withheld', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- PAYE Payable
    -- BILL-00006 · Highveld Fuel Services
    (107, 36, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (108, 36, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (109, 36, 12, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00009 · Karoo Fresh Produce (Pty) Ltd
    (110, 37, 1, '', 'ZAR', 1.00000000, 39330.00, 0, 39330.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (111, 37, 4, '', 'ZAR', 1.00000000, 0, 39330.00, 0, 39330.00, NULL, 1, NULL, NULL),  -- Accounts Receivable · Karoo Fresh Produce (Pty) Ltd
    -- PAY-00009 · Karoo Fresh Produce (Pty) Ltd (cash basis)
    (112, 38, 1, '', 'ZAR', 1.00000000, 39330.00, 0, 39330.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (113, 38, 21, '', 'ZAR', 1.00000000, 0, 34200.00, 0, 34200.00, NULL, NULL, NULL, NULL),  -- Sales
    (114, 38, 13, '', 'ZAR', 1.00000000, 0, 5130.00, 0, 5130.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00007 · Metro Property Management
    (115, 39, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (116, 39, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (117, 39, 12, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00010 · Metro Property Management
    (118, 40, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (119, 40, 12, '', 'ZAR', 1.00000000, 25300.00, 0, 25300.00, 0, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00010 · Metro Property Management (cash basis)
    (120, 41, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (121, 41, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (122, 41, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- TRF-001 · Transfer to savings
    (123, 42, 2, '', 'ZAR', 1.00000000, 100000.00, 0, 100000.00, 0, NULL, NULL, NULL, NULL),  -- Savings Account
    (124, 42, 1, '', 'ZAR', 1.00000000, 0, 100000.00, 0, 100000.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- INV-00007 · Halcyon Interiors CC
    (125, 43, 4, '', 'ZAR', 1.00000000, 78775.00, 0, 78775.00, 0, NULL, 2, NULL, NULL),  -- Accounts Receivable · Halcyon Interiors CC
    (126, 43, 21, '', 'ZAR', 1.00000000, 0, 68500.00, 0, 68500.00, NULL, NULL, NULL, NULL),  -- Sales
    (127, 43, 13, '', 'ZAR', 1.00000000, 0, 10275.00, 0, 10275.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAY-00011 · Cape Office Supplies (Pty) Ltd
    (128, 44, 1, '', 'ZAR', 1.00000000, 0, 2760.00, 0, 2760.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (129, 44, 12, '', 'ZAR', 1.00000000, 2760.00, 0, 2760.00, 0, NULL, 12, NULL, NULL),  -- Accounts Payable · Cape Office Supplies (Pty) Ltd
    -- PAY-00011 · Cape Office Supplies (Pty) Ltd (cash basis)
    (130, 45, 1, '', 'ZAR', 1.00000000, 0, 2760.00, 0, 2760.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (131, 45, 26, '', 'ZAR', 1.00000000, 1700.00, 0, 1700.00, 0, NULL, NULL, NULL, NULL),  -- Office Supplies
    (132, 45, 13, '', 'ZAR', 1.00000000, 255.00, 0, 255.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (133, 45, 26, '', 'ZAR', 1.00000000, 700.00, 0, 700.00, 0, NULL, NULL, NULL, NULL),  -- Office Supplies
    (134, 45, 13, '', 'ZAR', 1.00000000, 105.00, 0, 105.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAYE-002 · PAYE paid
    (135, 46, 14, '', 'ZAR', 1.00000000, 8840.00, 0, 8840.00, 0, NULL, NULL, NULL, NULL),  -- PAYE Payable
    (136, 46, 1, '', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00012 · Highveld Fuel Services
    (137, 47, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (138, 47, 12, '', 'ZAR', 1.00000000, 3220.00, 0, 3220.00, 0, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00012 · Highveld Fuel Services (cash basis)
    (139, 48, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (140, 48, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (141, 48, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INT-002 · Interest received
    (142, 49, 2, '', 'ZAR', 1.00000000, 610.00, 0, 610.00, 0, NULL, NULL, NULL, NULL),  -- Savings Account
    (143, 49, 22, '', 'ZAR', 1.00000000, 0, 610.00, 0, 610.00, NULL, NULL, NULL, NULL),  -- Interest Received
    -- PAY-00013 · Table Bay Marine (Pty) Ltd
    (144, 50, 1, '', 'ZAR', 1.00000000, 56752.50, 0, 56752.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (145, 50, 4, '', 'ZAR', 1.00000000, 0, 56752.50, 0, 56752.50, NULL, 3, NULL, NULL),  -- Accounts Receivable · Table Bay Marine (Pty) Ltd
    -- PAY-00013 · Table Bay Marine (Pty) Ltd (cash basis)
    (146, 51, 1, '', 'ZAR', 1.00000000, 56752.50, 0, 56752.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (147, 51, 21, '', 'ZAR', 1.00000000, 0, 40850.00, 0, 40850.00, NULL, NULL, NULL, NULL),  -- Sales
    (148, 51, 13, '', 'ZAR', 1.00000000, 0, 6127.50, 0, 6127.50, NULL, NULL, NULL, NULL),  -- VAT Control
    (149, 51, 21, '', 'ZAR', 1.00000000, 0, 8500.00, 0, 8500.00, NULL, NULL, NULL, NULL),  -- Sales
    (150, 51, 13, '', 'ZAR', 1.00000000, 0, 1275.00, 0, 1275.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00008 · Karoo Fresh Produce (Pty) Ltd
    (151, 52, 4, '', 'ZAR', 1.00000000, 62272.50, 0, 62272.50, 0, NULL, 1, NULL, NULL),  -- Accounts Receivable · Karoo Fresh Produce (Pty) Ltd
    (152, 52, 21, '', 'ZAR', 1.00000000, 0, 54150.00, 0, 54150.00, NULL, NULL, NULL, NULL),  -- Sales
    (153, 52, 13, '', 'ZAR', 1.00000000, 0, 8122.50, 0, 8122.50, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00008 · Atlantic Cloud Hosting
    (154, 53, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (155, 53, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (156, 53, 12, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- BCH-003 · Bank charges
    (157, 54, 29, '', 'ZAR', 1.00000000, 245.00, 0, 245.00, 0, NULL, NULL, NULL, NULL),  -- Bank Charges
    (158, 54, 1, '', 'ZAR', 1.00000000, 0, 245.00, 0, 245.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00014 · Atlantic Cloud Hosting
    (159, 55, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (160, 55, 12, '', 'ZAR', 1.00000000, 4485.00, 0, 4485.00, 0, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- PAY-00014 · Atlantic Cloud Hosting (cash basis)
    (161, 56, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (162, 56, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (163, 56, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- VAT-002 · VAT return paid
    (164, 57, 13, '', 'ZAR', 1.00000000, 23835.00, 0, 23835.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (165, 57, 1, '', 'ZAR', 1.00000000, 0, 23835.00, 0, 23835.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- SAL-003 · Salaries for the month
    (166, 58, 24, 'Gross salaries', 'ZAR', 1.00000000, 52000.00, 0, 52000.00, 0, NULL, NULL, 3, NULL),  -- Salaries and Wages
    (167, 58, 1, 'Net pay', 'ZAR', 1.00000000, 0, 43160.00, 0, 43160.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (168, 58, 14, 'PAYE withheld', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- PAYE Payable
    -- BILL-00009 · Highveld Fuel Services
    (169, 59, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (170, 59, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (171, 59, 12, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00015 · Halcyon Interiors CC
    (172, 60, 1, '', 'ZAR', 1.00000000, 78775.00, 0, 78775.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (173, 60, 4, '', 'ZAR', 1.00000000, 0, 78775.00, 0, 78775.00, NULL, 2, NULL, NULL),  -- Accounts Receivable · Halcyon Interiors CC
    -- PAY-00015 · Halcyon Interiors CC (cash basis)
    (174, 61, 1, '', 'ZAR', 1.00000000, 78775.00, 0, 78775.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (175, 61, 21, '', 'ZAR', 1.00000000, 0, 47500.00, 0, 47500.00, NULL, NULL, NULL, NULL),  -- Sales
    (176, 61, 13, '', 'ZAR', 1.00000000, 0, 7125.00, 0, 7125.00, NULL, NULL, NULL, NULL),  -- VAT Control
    (177, 61, 21, '', 'ZAR', 1.00000000, 0, 12500.00, 0, 12500.00, NULL, NULL, NULL, NULL),  -- Sales
    (178, 61, 13, '', 'ZAR', 1.00000000, 0, 1875.00, 0, 1875.00, NULL, NULL, NULL, NULL),  -- VAT Control
    (179, 61, 21, '', 'ZAR', 1.00000000, 0, 8500.00, 0, 8500.00, NULL, NULL, NULL, NULL),  -- Sales
    (180, 61, 13, '', 'ZAR', 1.00000000, 0, 1275.00, 0, 1275.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00010 · Metro Property Management
    (181, 62, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (182, 62, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (183, 62, 12, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00016 · Metro Property Management
    (184, 63, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (185, 63, 12, '', 'ZAR', 1.00000000, 25300.00, 0, 25300.00, 0, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00016 · Metro Property Management (cash basis)
    (186, 64, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (187, 64, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (188, 64, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00009 · Halcyon Interiors CC
    (189, 65, 4, '', 'ZAR', 1.00000000, 49105.00, 0, 49105.00, 0, NULL, 2, NULL, NULL),  -- Accounts Receivable · Halcyon Interiors CC
    (190, 65, 21, '', 'ZAR', 1.00000000, 0, 42700.00, 0, 42700.00, NULL, NULL, NULL, NULL),  -- Sales
    (191, 65, 13, '', 'ZAR', 1.00000000, 0, 6405.00, 0, 6405.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAYE-003 · PAYE paid
    (192, 66, 14, '', 'ZAR', 1.00000000, 8840.00, 0, 8840.00, 0, NULL, NULL, NULL, NULL),  -- PAYE Payable
    (193, 66, 1, '', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00017 · Highveld Fuel Services
    (194, 67, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (195, 67, 12, '', 'ZAR', 1.00000000, 3220.00, 0, 3220.00, 0, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00017 · Highveld Fuel Services (cash basis)
    (196, 68, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (197, 68, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (198, 68, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INT-003 · Interest received
    (199, 69, 2, '', 'ZAR', 1.00000000, 610.00, 0, 610.00, 0, NULL, NULL, NULL, NULL),  -- Savings Account
    (200, 69, 22, '', 'ZAR', 1.00000000, 0, 610.00, 0, 610.00, NULL, NULL, NULL, NULL),  -- Interest Received
    -- PAY-00018 · Karoo Fresh Produce (Pty) Ltd
    (201, 70, 1, '', 'ZAR', 1.00000000, 62272.50, 0, 62272.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (202, 70, 4, '', 'ZAR', 1.00000000, 0, 62272.50, 0, 62272.50, NULL, 1, NULL, NULL),  -- Accounts Receivable · Karoo Fresh Produce (Pty) Ltd
    -- PAY-00018 · Karoo Fresh Produce (Pty) Ltd (cash basis)
    (203, 71, 1, '', 'ZAR', 1.00000000, 62272.50, 0, 62272.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (204, 71, 21, '', 'ZAR', 1.00000000, 0, 54150.00, 0, 54150.00, NULL, NULL, NULL, NULL),  -- Sales
    (205, 71, 13, '', 'ZAR', 1.00000000, 0, 8122.50, 0, 8122.50, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00010 · Table Bay Marine (Pty) Ltd
    (206, 72, 4, '', 'ZAR', 1.00000000, 71127.50, 0, 71127.50, 0, NULL, 3, NULL, NULL),  -- Accounts Receivable · Table Bay Marine (Pty) Ltd
    (207, 72, 21, '', 'ZAR', 1.00000000, 0, 61850.00, 0, 61850.00, NULL, NULL, NULL, NULL),  -- Sales
    (208, 72, 13, '', 'ZAR', 1.00000000, 0, 9277.50, 0, 9277.50, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00011 · Atlantic Cloud Hosting
    (209, 73, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (210, 73, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (211, 73, 12, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- BCH-004 · Bank charges
    (212, 74, 29, '', 'ZAR', 1.00000000, 245.00, 0, 245.00, 0, NULL, NULL, NULL, NULL),  -- Bank Charges
    (213, 74, 1, '', 'ZAR', 1.00000000, 0, 245.00, 0, 245.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00019 · Atlantic Cloud Hosting
    (214, 75, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (215, 75, 12, '', 'ZAR', 1.00000000, 4485.00, 0, 4485.00, 0, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- PAY-00019 · Atlantic Cloud Hosting (cash basis)
    (216, 76, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (217, 76, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (218, 76, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- SAL-004 · Salaries for the month
    (219, 77, 24, 'Gross salaries', 'ZAR', 1.00000000, 52000.00, 0, 52000.00, 0, NULL, NULL, 3, NULL),  -- Salaries and Wages
    (220, 77, 1, 'Net pay', 'ZAR', 1.00000000, 0, 43160.00, 0, 43160.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (221, 77, 14, 'PAYE withheld', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- PAYE Payable
    -- BILL-00012 · Highveld Fuel Services
    (222, 78, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (223, 78, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (224, 78, 12, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00020 · Halcyon Interiors CC
    (225, 79, 1, '', 'ZAR', 1.00000000, 49105.00, 0, 49105.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (226, 79, 4, '', 'ZAR', 1.00000000, 0, 49105.00, 0, 49105.00, NULL, 2, NULL, NULL),  -- Accounts Receivable · Halcyon Interiors CC
    -- PAY-00020 · Halcyon Interiors CC (cash basis)
    (227, 80, 1, '', 'ZAR', 1.00000000, 49105.00, 0, 49105.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (228, 80, 21, '', 'ZAR', 1.00000000, 0, 34200.00, 0, 34200.00, NULL, NULL, NULL, NULL),  -- Sales
    (229, 80, 13, '', 'ZAR', 1.00000000, 0, 5130.00, 0, 5130.00, NULL, NULL, NULL, NULL),  -- VAT Control
    (230, 80, 21, '', 'ZAR', 1.00000000, 0, 8500.00, 0, 8500.00, NULL, NULL, NULL, NULL),  -- Sales
    (231, 80, 13, '', 'ZAR', 1.00000000, 0, 1275.00, 0, 1275.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00013 · Metro Property Management
    (232, 81, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (233, 81, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (234, 81, 12, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00021 · Metro Property Management
    (235, 82, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (236, 82, 12, '', 'ZAR', 1.00000000, 25300.00, 0, 25300.00, 0, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00021 · Metro Property Management (cash basis)
    (237, 83, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (238, 83, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (239, 83, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00011 · Protea Print Works
    (240, 84, 4, '', 'ZAR', 1.00000000, 54625.00, 0, 54625.00, 0, NULL, 4, NULL, NULL),  -- Accounts Receivable · Protea Print Works
    (241, 84, 21, '', 'ZAR', 1.00000000, 0, 47500.00, 0, 47500.00, NULL, NULL, NULL, NULL),  -- Sales
    (242, 84, 13, '', 'ZAR', 1.00000000, 0, 7125.00, 0, 7125.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAYE-004 · PAYE paid
    (243, 85, 14, '', 'ZAR', 1.00000000, 8840.00, 0, 8840.00, 0, NULL, NULL, NULL, NULL),  -- PAYE Payable
    (244, 85, 1, '', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00022 · Highveld Fuel Services
    (245, 86, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (246, 86, 12, '', 'ZAR', 1.00000000, 3220.00, 0, 3220.00, 0, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00022 · Highveld Fuel Services (cash basis)
    (247, 87, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (248, 87, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (249, 87, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INT-004 · Interest received
    (250, 88, 2, '', 'ZAR', 1.00000000, 610.00, 0, 610.00, 0, NULL, NULL, NULL, NULL),  -- Savings Account
    (251, 88, 22, '', 'ZAR', 1.00000000, 0, 610.00, 0, 610.00, NULL, NULL, NULL, NULL),  -- Interest Received
    -- BILL-00014 · Cape Office Supplies (Pty) Ltd
    (252, 89, 26, '', 'ZAR', 1.00000000, 1700.00, 0, 1700.00, 0, NULL, NULL, NULL, NULL),  -- Office Supplies
    (253, 89, 13, '', 'ZAR', 1.00000000, 255.00, 0, 255.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (254, 89, 26, '', 'ZAR', 1.00000000, 700.00, 0, 700.00, 0, NULL, NULL, NULL, NULL),  -- Office Supplies
    (255, 89, 13, '', 'ZAR', 1.00000000, 105.00, 0, 105.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (256, 89, 12, '', 'ZAR', 1.00000000, 0, 2760.00, 0, 2760.00, NULL, 12, NULL, NULL),  -- Accounts Payable · Cape Office Supplies (Pty) Ltd
    -- INV-00012 · Karoo Fresh Produce (Pty) Ltd
    (257, 90, 4, '', 'ZAR', 1.00000000, 62272.50, 0, 62272.50, 0, NULL, 1, NULL, NULL),  -- Accounts Receivable · Karoo Fresh Produce (Pty) Ltd
    (258, 90, 21, '', 'ZAR', 1.00000000, 0, 54150.00, 0, 54150.00, NULL, NULL, NULL, NULL),  -- Sales
    (259, 90, 13, '', 'ZAR', 1.00000000, 0, 8122.50, 0, 8122.50, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00015 · Atlantic Cloud Hosting
    (260, 91, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (261, 91, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (262, 91, 12, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- BCH-005 · Bank charges
    (263, 92, 29, '', 'ZAR', 1.00000000, 245.00, 0, 245.00, 0, NULL, NULL, NULL, NULL),  -- Bank Charges
    (264, 92, 1, '', 'ZAR', 1.00000000, 0, 245.00, 0, 245.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00023 · Atlantic Cloud Hosting
    (265, 93, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (266, 93, 12, '', 'ZAR', 1.00000000, 4485.00, 0, 4485.00, 0, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- PAY-00023 · Atlantic Cloud Hosting (cash basis)
    (267, 94, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (268, 94, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (269, 94, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- VAT-003 · VAT return paid
    (270, 95, 13, '', 'ZAR', 1.00000000, 22320.00, 0, 22320.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (271, 95, 1, '', 'ZAR', 1.00000000, 0, 22320.00, 0, 22320.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- SAL-005 · Salaries for the month
    (272, 96, 24, 'Gross salaries', 'ZAR', 1.00000000, 52000.00, 0, 52000.00, 0, NULL, NULL, 3, NULL),  -- Salaries and Wages
    (273, 96, 1, 'Net pay', 'ZAR', 1.00000000, 0, 43160.00, 0, 43160.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (274, 96, 14, 'PAYE withheld', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- PAYE Payable
    -- BILL-00016 · Highveld Fuel Services
    (275, 97, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (276, 97, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (277, 97, 12, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00024 · Table Bay Marine (Pty) Ltd
    (278, 98, 1, '', 'ZAR', 1.00000000, 71127.50, 0, 71127.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (279, 98, 4, '', 'ZAR', 1.00000000, 0, 71127.50, 0, 71127.50, NULL, 3, NULL, NULL),  -- Accounts Receivable · Table Bay Marine (Pty) Ltd
    -- PAY-00024 · Table Bay Marine (Pty) Ltd (cash basis)
    (280, 99, 1, '', 'ZAR', 1.00000000, 71127.50, 0, 71127.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (281, 99, 21, '', 'ZAR', 1.00000000, 0, 40850.00, 0, 40850.00, NULL, NULL, NULL, NULL),  -- Sales
    (282, 99, 13, '', 'ZAR', 1.00000000, 0, 6127.50, 0, 6127.50, NULL, NULL, NULL, NULL),  -- VAT Control
    (283, 99, 21, '', 'ZAR', 1.00000000, 0, 12500.00, 0, 12500.00, NULL, NULL, NULL, NULL),  -- Sales
    (284, 99, 13, '', 'ZAR', 1.00000000, 0, 1875.00, 0, 1875.00, NULL, NULL, NULL, NULL),  -- VAT Control
    (285, 99, 21, '', 'ZAR', 1.00000000, 0, 8500.00, 0, 8500.00, NULL, NULL, NULL, NULL),  -- Sales
    (286, 99, 13, '', 'ZAR', 1.00000000, 0, 1275.00, 0, 1275.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAY-00025 · Protea Print Works
    (287, 100, 1, '', 'ZAR', 1.00000000, 54625.00, 0, 54625.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (288, 100, 4, '', 'ZAR', 1.00000000, 0, 54625.00, 0, 54625.00, NULL, 4, NULL, NULL),  -- Accounts Receivable · Protea Print Works
    -- PAY-00025 · Protea Print Works (cash basis)
    (289, 101, 1, '', 'ZAR', 1.00000000, 54625.00, 0, 54625.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (290, 101, 21, '', 'ZAR', 1.00000000, 0, 47500.00, 0, 47500.00, NULL, NULL, NULL, NULL),  -- Sales
    (291, 101, 13, '', 'ZAR', 1.00000000, 0, 7125.00, 0, 7125.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00017 · Metro Property Management
    (292, 102, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (293, 102, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (294, 102, 12, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00026 · Metro Property Management
    (295, 103, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (296, 103, 12, '', 'ZAR', 1.00000000, 25300.00, 0, 25300.00, 0, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00026 · Metro Property Management (cash basis)
    (297, 104, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (298, 104, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (299, 104, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00013 · Table Bay Marine (Pty) Ltd
    (300, 105, 4, '', 'ZAR', 1.00000000, 63480.00, 0, 63480.00, 0, NULL, 3, NULL, NULL),  -- Accounts Receivable · Table Bay Marine (Pty) Ltd
    (301, 105, 21, '', 'ZAR', 1.00000000, 0, 55200.00, 0, 55200.00, NULL, NULL, NULL, NULL),  -- Sales
    (302, 105, 13, '', 'ZAR', 1.00000000, 0, 8280.00, 0, 8280.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAY-00027 · Cape Office Supplies (Pty) Ltd
    (303, 106, 1, '', 'ZAR', 1.00000000, 0, 2760.00, 0, 2760.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (304, 106, 12, '', 'ZAR', 1.00000000, 2760.00, 0, 2760.00, 0, NULL, 12, NULL, NULL),  -- Accounts Payable · Cape Office Supplies (Pty) Ltd
    -- PAY-00027 · Cape Office Supplies (Pty) Ltd (cash basis)
    (305, 107, 1, '', 'ZAR', 1.00000000, 0, 2760.00, 0, 2760.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (306, 107, 26, '', 'ZAR', 1.00000000, 1700.00, 0, 1700.00, 0, NULL, NULL, NULL, NULL),  -- Office Supplies
    (307, 107, 13, '', 'ZAR', 1.00000000, 255.00, 0, 255.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (308, 107, 26, '', 'ZAR', 1.00000000, 700.00, 0, 700.00, 0, NULL, NULL, NULL, NULL),  -- Office Supplies
    (309, 107, 13, '', 'ZAR', 1.00000000, 105.00, 0, 105.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAYE-005 · PAYE paid
    (310, 108, 14, '', 'ZAR', 1.00000000, 8840.00, 0, 8840.00, 0, NULL, NULL, NULL, NULL),  -- PAYE Payable
    (311, 108, 1, '', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00028 · Highveld Fuel Services
    (312, 109, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (313, 109, 12, '', 'ZAR', 1.00000000, 3220.00, 0, 3220.00, 0, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00028 · Highveld Fuel Services (cash basis)
    (314, 110, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (315, 110, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (316, 110, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INT-005 · Interest received
    (317, 111, 2, '', 'ZAR', 1.00000000, 610.00, 0, 610.00, 0, NULL, NULL, NULL, NULL),  -- Savings Account
    (318, 111, 22, '', 'ZAR', 1.00000000, 0, 610.00, 0, 610.00, NULL, NULL, NULL, NULL),  -- Interest Received
    -- BILL-00018 · Cape Office Supplies (Pty) Ltd
    (319, 112, 7, '', 'ZAR', 1.00000000, 18000.00, 0, 18000.00, 0, NULL, NULL, NULL, NULL),  -- Computer Equipment
    (320, 112, 13, '', 'ZAR', 1.00000000, 2700.00, 0, 2700.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (321, 112, 7, '', 'ZAR', 1.00000000, 18000.00, 0, 18000.00, 0, NULL, NULL, NULL, NULL),  -- Computer Equipment
    (322, 112, 13, '', 'ZAR', 1.00000000, 2700.00, 0, 2700.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (323, 112, 7, '', 'ZAR', 1.00000000, 18000.00, 0, 18000.00, 0, NULL, NULL, NULL, NULL),  -- Computer Equipment
    (324, 112, 13, '', 'ZAR', 1.00000000, 2700.00, 0, 2700.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (325, 112, 12, '', 'ZAR', 1.00000000, 0, 62100.00, 0, 62100.00, NULL, 12, NULL, NULL),  -- Accounts Payable · Cape Office Supplies (Pty) Ltd
    -- PAY-00029 · Karoo Fresh Produce (Pty) Ltd
    (326, 113, 1, '', 'ZAR', 1.00000000, 62272.50, 0, 62272.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (327, 113, 4, '', 'ZAR', 1.00000000, 0, 62272.50, 0, 62272.50, NULL, 1, NULL, NULL),  -- Accounts Receivable · Karoo Fresh Produce (Pty) Ltd
    -- PAY-00029 · Karoo Fresh Produce (Pty) Ltd (cash basis)
    (328, 114, 1, '', 'ZAR', 1.00000000, 62272.50, 0, 62272.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (329, 114, 21, '', 'ZAR', 1.00000000, 0, 54150.00, 0, 54150.00, NULL, NULL, NULL, NULL),  -- Sales
    (330, 114, 13, '', 'ZAR', 1.00000000, 0, 8122.50, 0, 8122.50, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00014 · Halcyon Interiors CC
    (331, 115, 4, '', 'ZAR', 1.00000000, 56752.50, 0, 56752.50, 0, NULL, 2, NULL, NULL),  -- Accounts Receivable · Halcyon Interiors CC
    (332, 115, 21, '', 'ZAR', 1.00000000, 0, 49350.00, 0, 49350.00, NULL, NULL, NULL, NULL),  -- Sales
    (333, 115, 13, '', 'ZAR', 1.00000000, 0, 7402.50, 0, 7402.50, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00019 · Atlantic Cloud Hosting
    (334, 116, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (335, 116, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (336, 116, 12, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- BCH-006 · Bank charges
    (337, 117, 29, '', 'ZAR', 1.00000000, 245.00, 0, 245.00, 0, NULL, NULL, NULL, NULL),  -- Bank Charges
    (338, 117, 1, '', 'ZAR', 1.00000000, 0, 245.00, 0, 245.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00030 · Atlantic Cloud Hosting
    (339, 118, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (340, 118, 12, '', 'ZAR', 1.00000000, 4485.00, 0, 4485.00, 0, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- PAY-00030 · Atlantic Cloud Hosting (cash basis)
    (341, 119, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (342, 119, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (343, 119, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- SAL-006 · Salaries for the month
    (344, 120, 24, 'Gross salaries', 'ZAR', 1.00000000, 52000.00, 0, 52000.00, 0, NULL, NULL, 3, NULL),  -- Salaries and Wages
    (345, 120, 1, 'Net pay', 'ZAR', 1.00000000, 0, 43160.00, 0, 43160.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (346, 120, 14, 'PAYE withheld', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- PAYE Payable
    -- BILL-00020 · Highveld Fuel Services
    (347, 121, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (348, 121, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (349, 121, 12, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00031 · Table Bay Marine (Pty) Ltd
    (350, 122, 1, '', 'ZAR', 1.00000000, 63480.00, 0, 63480.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (351, 122, 4, '', 'ZAR', 1.00000000, 0, 63480.00, 0, 63480.00, NULL, 3, NULL, NULL),  -- Accounts Receivable · Table Bay Marine (Pty) Ltd
    -- PAY-00031 · Table Bay Marine (Pty) Ltd (cash basis)
    (352, 123, 1, '', 'ZAR', 1.00000000, 63480.00, 0, 63480.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (353, 123, 21, '', 'ZAR', 1.00000000, 0, 34200.00, 0, 34200.00, NULL, NULL, NULL, NULL),  -- Sales
    (354, 123, 13, '', 'ZAR', 1.00000000, 0, 5130.00, 0, 5130.00, NULL, NULL, NULL, NULL),  -- VAT Control
    (355, 123, 21, '', 'ZAR', 1.00000000, 0, 12500.00, 0, 12500.00, NULL, NULL, NULL, NULL),  -- Sales
    (356, 123, 13, '', 'ZAR', 1.00000000, 0, 1875.00, 0, 1875.00, NULL, NULL, NULL, NULL),  -- VAT Control
    (357, 123, 21, '', 'ZAR', 1.00000000, 0, 8500.00, 0, 8500.00, NULL, NULL, NULL, NULL),  -- Sales
    (358, 123, 13, '', 'ZAR', 1.00000000, 0, 1275.00, 0, 1275.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAY-00032 · Halcyon Interiors CC
    (359, 124, 1, '', 'ZAR', 1.00000000, 56752.50, 0, 56752.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (360, 124, 4, '', 'ZAR', 1.00000000, 0, 56752.50, 0, 56752.50, NULL, 2, NULL, NULL),  -- Accounts Receivable · Halcyon Interiors CC
    -- PAY-00032 · Halcyon Interiors CC (cash basis)
    (361, 125, 1, '', 'ZAR', 1.00000000, 56752.50, 0, 56752.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (362, 125, 21, '', 'ZAR', 1.00000000, 0, 40850.00, 0, 40850.00, NULL, NULL, NULL, NULL),  -- Sales
    (363, 125, 13, '', 'ZAR', 1.00000000, 0, 6127.50, 0, 6127.50, NULL, NULL, NULL, NULL),  -- VAT Control
    (364, 125, 21, '', 'ZAR', 1.00000000, 0, 8500.00, 0, 8500.00, NULL, NULL, NULL, NULL),  -- Sales
    (365, 125, 13, '', 'ZAR', 1.00000000, 0, 1275.00, 0, 1275.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00021 · Metro Property Management
    (366, 126, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (367, 126, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (368, 126, 12, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00033 · Metro Property Management
    (369, 127, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (370, 127, 12, '', 'ZAR', 1.00000000, 25300.00, 0, 25300.00, 0, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00033 · Metro Property Management (cash basis)
    (371, 128, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (372, 128, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (373, 128, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00015 · Karoo Fresh Produce (Pty) Ltd
    (374, 129, 4, '', 'ZAR', 1.00000000, 54625.00, 0, 54625.00, 0, NULL, 1, NULL, NULL),  -- Accounts Receivable · Karoo Fresh Produce (Pty) Ltd
    (375, 129, 21, '', 'ZAR', 1.00000000, 0, 47500.00, 0, 47500.00, NULL, NULL, NULL, NULL),  -- Sales
    (376, 129, 13, '', 'ZAR', 1.00000000, 0, 7125.00, 0, 7125.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAYE-006 · PAYE paid
    (377, 130, 14, '', 'ZAR', 1.00000000, 8840.00, 0, 8840.00, 0, NULL, NULL, NULL, NULL),  -- PAYE Payable
    (378, 130, 1, '', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00034 · Highveld Fuel Services
    (379, 131, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (380, 131, 12, '', 'ZAR', 1.00000000, 3220.00, 0, 3220.00, 0, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00034 · Highveld Fuel Services (cash basis)
    (381, 132, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (382, 132, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (383, 132, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAY-00035 · Cape Office Supplies (Pty) Ltd
    (384, 133, 1, '', 'ZAR', 1.00000000, 0, 62100.00, 0, 62100.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (385, 133, 12, '', 'ZAR', 1.00000000, 62100.00, 0, 62100.00, 0, NULL, 12, NULL, NULL),  -- Accounts Payable · Cape Office Supplies (Pty) Ltd
    -- PAY-00035 · Cape Office Supplies (Pty) Ltd (cash basis)
    (386, 134, 1, '', 'ZAR', 1.00000000, 0, 62100.00, 0, 62100.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (387, 134, 7, '', 'ZAR', 1.00000000, 18000.00, 0, 18000.00, 0, NULL, NULL, NULL, NULL),  -- Computer Equipment
    (388, 134, 13, '', 'ZAR', 1.00000000, 2700.00, 0, 2700.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (389, 134, 7, '', 'ZAR', 1.00000000, 18000.00, 0, 18000.00, 0, NULL, NULL, NULL, NULL),  -- Computer Equipment
    (390, 134, 13, '', 'ZAR', 1.00000000, 2700.00, 0, 2700.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (391, 134, 7, '', 'ZAR', 1.00000000, 18000.00, 0, 18000.00, 0, NULL, NULL, NULL, NULL),  -- Computer Equipment
    (392, 134, 13, '', 'ZAR', 1.00000000, 2700.00, 0, 2700.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INT-006 · Interest received
    (393, 135, 2, '', 'ZAR', 1.00000000, 610.00, 0, 610.00, 0, NULL, NULL, NULL, NULL),  -- Savings Account
    (394, 135, 22, '', 'ZAR', 1.00000000, 0, 610.00, 0, 610.00, NULL, NULL, NULL, NULL),  -- Interest Received
    -- INV-00016 · Halcyon Interiors CC
    (395, 136, 4, '', 'ZAR', 1.00000000, 86422.50, 0, 86422.50, 0, NULL, 2, NULL, NULL),  -- Accounts Receivable · Halcyon Interiors CC
    (396, 136, 21, '', 'ZAR', 1.00000000, 0, 75150.00, 0, 75150.00, NULL, NULL, NULL, NULL),  -- Sales
    (397, 136, 13, '', 'ZAR', 1.00000000, 0, 11272.50, 0, 11272.50, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00022 · Atlantic Cloud Hosting
    (398, 137, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (399, 137, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (400, 137, 12, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- BCH-007 · Bank charges
    (401, 138, 29, '', 'ZAR', 1.00000000, 245.00, 0, 245.00, 0, NULL, NULL, NULL, NULL),  -- Bank Charges
    (402, 138, 1, '', 'ZAR', 1.00000000, 0, 245.00, 0, 245.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00036 · Atlantic Cloud Hosting
    (403, 139, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (404, 139, 12, '', 'ZAR', 1.00000000, 4485.00, 0, 4485.00, 0, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- PAY-00036 · Atlantic Cloud Hosting (cash basis)
    (405, 140, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (406, 140, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (407, 140, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- VAT-004 · VAT return paid
    (408, 141, 13, '', 'ZAR', 1.00000000, 13860.00, 0, 13860.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (409, 141, 1, '', 'ZAR', 1.00000000, 0, 13860.00, 0, 13860.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- SAL-007 · Salaries for the month
    (410, 142, 24, 'Gross salaries', 'ZAR', 1.00000000, 52000.00, 0, 52000.00, 0, NULL, NULL, 3, NULL),  -- Salaries and Wages
    (411, 142, 1, 'Net pay', 'ZAR', 1.00000000, 0, 43160.00, 0, 43160.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (412, 142, 14, 'PAYE withheld', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- PAYE Payable
    -- BILL-00023 · Highveld Fuel Services
    (413, 143, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (414, 143, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (415, 143, 12, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00037 · Karoo Fresh Produce (Pty) Ltd
    (416, 144, 1, '', 'ZAR', 1.00000000, 54625.00, 0, 54625.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (417, 144, 4, '', 'ZAR', 1.00000000, 0, 54625.00, 0, 54625.00, NULL, 1, NULL, NULL),  -- Accounts Receivable · Karoo Fresh Produce (Pty) Ltd
    -- PAY-00037 · Karoo Fresh Produce (Pty) Ltd (cash basis)
    (418, 145, 1, '', 'ZAR', 1.00000000, 54625.00, 0, 54625.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (419, 145, 21, '', 'ZAR', 1.00000000, 0, 47500.00, 0, 47500.00, NULL, NULL, NULL, NULL),  -- Sales
    (420, 145, 13, '', 'ZAR', 1.00000000, 0, 7125.00, 0, 7125.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00024 · Metro Property Management
    (421, 146, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (422, 146, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (423, 146, 12, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00038 · Metro Property Management
    (424, 147, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (425, 147, 12, '', 'ZAR', 1.00000000, 25300.00, 0, 25300.00, 0, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00038 · Metro Property Management (cash basis)
    (426, 148, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (427, 148, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (428, 148, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00017 · Table Bay Marine (Pty) Ltd
    (429, 149, 4, '', 'ZAR', 1.00000000, 49105.00, 0, 49105.00, 0, NULL, 3, NULL, NULL),  -- Accounts Receivable · Table Bay Marine (Pty) Ltd
    (430, 149, 21, '', 'ZAR', 1.00000000, 0, 42700.00, 0, 42700.00, NULL, NULL, NULL, NULL),  -- Sales
    (431, 149, 13, '', 'ZAR', 1.00000000, 0, 6405.00, 0, 6405.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- VEH-001 · Delivery vehicle on finance
    (432, 150, 9, '', 'ZAR', 1.00000000, 420000.00, 0, 420000.00, 0, NULL, NULL, NULL, NULL),  -- Vehicles
    (433, 150, 1, 'Deposit', 'ZAR', 1.00000000, 0, 60000.00, 0, 60000.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (434, 150, 18, '', 'ZAR', 1.00000000, 0, 360000.00, 0, 360000.00, NULL, NULL, NULL, NULL),  -- Vehicle Finance Loan
    -- PAYE-007 · PAYE paid
    (435, 151, 14, '', 'ZAR', 1.00000000, 8840.00, 0, 8840.00, 0, NULL, NULL, NULL, NULL),  -- PAYE Payable
    (436, 151, 1, '', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00039 · Highveld Fuel Services
    (437, 152, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (438, 152, 12, '', 'ZAR', 1.00000000, 3220.00, 0, 3220.00, 0, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00039 · Highveld Fuel Services (cash basis)
    (439, 153, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (440, 153, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (441, 153, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INT-007 · Interest received
    (442, 154, 2, '', 'ZAR', 1.00000000, 610.00, 0, 610.00, 0, NULL, NULL, NULL, NULL),  -- Savings Account
    (443, 154, 22, '', 'ZAR', 1.00000000, 0, 610.00, 0, 610.00, NULL, NULL, NULL, NULL),  -- Interest Received
    -- BILL-00025 · Cape Office Supplies (Pty) Ltd
    (444, 155, 26, '', 'ZAR', 1.00000000, 1700.00, 0, 1700.00, 0, NULL, NULL, NULL, NULL),  -- Office Supplies
    (445, 155, 13, '', 'ZAR', 1.00000000, 255.00, 0, 255.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (446, 155, 26, '', 'ZAR', 1.00000000, 700.00, 0, 700.00, 0, NULL, NULL, NULL, NULL),  -- Office Supplies
    (447, 155, 13, '', 'ZAR', 1.00000000, 105.00, 0, 105.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (448, 155, 12, '', 'ZAR', 1.00000000, 0, 2760.00, 0, 2760.00, NULL, 12, NULL, NULL),  -- Accounts Payable · Cape Office Supplies (Pty) Ltd
    -- LOAN-001 · Vehicle finance instalment
    (449, 156, 18, '', 'ZAR', 1.00000000, 7500.00, 0, 7500.00, 0, NULL, NULL, NULL, NULL),  -- Vehicle Finance Loan
    (450, 156, 1, '', 'ZAR', 1.00000000, 0, 7500.00, 0, 7500.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00040 · Halcyon Interiors CC
    (451, 157, 1, '', 'ZAR', 1.00000000, 86422.50, 0, 86422.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (452, 157, 4, '', 'ZAR', 1.00000000, 0, 86422.50, 0, 86422.50, NULL, 2, NULL, NULL),  -- Accounts Receivable · Halcyon Interiors CC
    -- PAY-00040 · Halcyon Interiors CC (cash basis)
    (453, 158, 1, '', 'ZAR', 1.00000000, 86422.50, 0, 86422.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (454, 158, 21, '', 'ZAR', 1.00000000, 0, 54150.00, 0, 54150.00, NULL, NULL, NULL, NULL),  -- Sales
    (455, 158, 13, '', 'ZAR', 1.00000000, 0, 8122.50, 0, 8122.50, NULL, NULL, NULL, NULL),  -- VAT Control
    (456, 158, 21, '', 'ZAR', 1.00000000, 0, 12500.00, 0, 12500.00, NULL, NULL, NULL, NULL),  -- Sales
    (457, 158, 13, '', 'ZAR', 1.00000000, 0, 1875.00, 0, 1875.00, NULL, NULL, NULL, NULL),  -- VAT Control
    (458, 158, 21, '', 'ZAR', 1.00000000, 0, 8500.00, 0, 8500.00, NULL, NULL, NULL, NULL),  -- Sales
    (459, 158, 13, '', 'ZAR', 1.00000000, 0, 1275.00, 0, 1275.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00018 · Protea Print Works
    (460, 159, 4, '', 'ZAR', 1.00000000, 46977.50, 0, 46977.50, 0, NULL, 4, NULL, NULL),  -- Accounts Receivable · Protea Print Works
    (461, 159, 21, '', 'ZAR', 1.00000000, 0, 40850.00, 0, 40850.00, NULL, NULL, NULL, NULL),  -- Sales
    (462, 159, 13, '', 'ZAR', 1.00000000, 0, 6127.50, 0, 6127.50, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00026 · Atlantic Cloud Hosting
    (463, 160, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (464, 160, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (465, 160, 12, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- BCH-008 · Bank charges
    (466, 161, 29, '', 'ZAR', 1.00000000, 245.00, 0, 245.00, 0, NULL, NULL, NULL, NULL),  -- Bank Charges
    (467, 161, 1, '', 'ZAR', 1.00000000, 0, 245.00, 0, 245.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00041 · Atlantic Cloud Hosting
    (468, 162, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (469, 162, 12, '', 'ZAR', 1.00000000, 4485.00, 0, 4485.00, 0, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- PAY-00041 · Atlantic Cloud Hosting (cash basis)
    (470, 163, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (471, 163, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (472, 163, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- SAL-008 · Salaries for the month
    (473, 164, 24, 'Gross salaries', 'ZAR', 1.00000000, 52000.00, 0, 52000.00, 0, NULL, NULL, 3, NULL),  -- Salaries and Wages
    (474, 164, 1, 'Net pay', 'ZAR', 1.00000000, 0, 43160.00, 0, 43160.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (475, 164, 14, 'PAYE withheld', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- PAYE Payable
    -- BILL-00027 · Highveld Fuel Services
    (476, 165, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (477, 165, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (478, 165, 12, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00042 · Table Bay Marine (Pty) Ltd
    (479, 166, 1, '', 'ZAR', 1.00000000, 49105.00, 0, 49105.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (480, 166, 4, '', 'ZAR', 1.00000000, 0, 49105.00, 0, 49105.00, NULL, 3, NULL, NULL),  -- Accounts Receivable · Table Bay Marine (Pty) Ltd
    -- PAY-00042 · Table Bay Marine (Pty) Ltd (cash basis)
    (481, 167, 1, '', 'ZAR', 1.00000000, 49105.00, 0, 49105.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (482, 167, 21, '', 'ZAR', 1.00000000, 0, 34200.00, 0, 34200.00, NULL, NULL, NULL, NULL),  -- Sales
    (483, 167, 13, '', 'ZAR', 1.00000000, 0, 5130.00, 0, 5130.00, NULL, NULL, NULL, NULL),  -- VAT Control
    (484, 167, 21, '', 'ZAR', 1.00000000, 0, 8500.00, 0, 8500.00, NULL, NULL, NULL, NULL),  -- Sales
    (485, 167, 13, '', 'ZAR', 1.00000000, 0, 1275.00, 0, 1275.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00028 · Metro Property Management
    (486, 168, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (487, 168, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (488, 168, 12, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00043 · Metro Property Management
    (489, 169, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (490, 169, 12, '', 'ZAR', 1.00000000, 25300.00, 0, 25300.00, 0, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00043 · Metro Property Management (cash basis)
    (491, 170, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (492, 170, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (493, 170, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00019 · Karoo Fresh Produce (Pty) Ltd
    (494, 171, 4, '', 'ZAR', 1.00000000, 69000.00, 0, 69000.00, 0, NULL, 1, NULL, NULL),  -- Accounts Receivable · Karoo Fresh Produce (Pty) Ltd
    (495, 171, 21, '', 'ZAR', 1.00000000, 0, 60000.00, 0, 60000.00, NULL, NULL, NULL, NULL),  -- Sales
    (496, 171, 13, '', 'ZAR', 1.00000000, 0, 9000.00, 0, 9000.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAY-00044 · Cape Office Supplies (Pty) Ltd
    (497, 172, 1, '', 'ZAR', 1.00000000, 0, 2760.00, 0, 2760.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (498, 172, 12, '', 'ZAR', 1.00000000, 2760.00, 0, 2760.00, 0, NULL, 12, NULL, NULL),  -- Accounts Payable · Cape Office Supplies (Pty) Ltd
    -- PAY-00044 · Cape Office Supplies (Pty) Ltd (cash basis)
    (499, 173, 1, '', 'ZAR', 1.00000000, 0, 2760.00, 0, 2760.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (500, 173, 26, '', 'ZAR', 1.00000000, 1700.00, 0, 1700.00, 0, NULL, NULL, NULL, NULL),  -- Office Supplies
    (501, 173, 13, '', 'ZAR', 1.00000000, 255.00, 0, 255.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (502, 173, 26, '', 'ZAR', 1.00000000, 700.00, 0, 700.00, 0, NULL, NULL, NULL, NULL),  -- Office Supplies
    (503, 173, 13, '', 'ZAR', 1.00000000, 105.00, 0, 105.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAYE-008 · PAYE paid
    (504, 174, 14, '', 'ZAR', 1.00000000, 8840.00, 0, 8840.00, 0, NULL, NULL, NULL, NULL),  -- PAYE Payable
    (505, 174, 1, '', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00045 · Highveld Fuel Services
    (506, 175, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (507, 175, 12, '', 'ZAR', 1.00000000, 3220.00, 0, 3220.00, 0, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00045 · Highveld Fuel Services (cash basis)
    (508, 176, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (509, 176, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (510, 176, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INT-008 · Interest received
    (511, 177, 2, '', 'ZAR', 1.00000000, 610.00, 0, 610.00, 0, NULL, NULL, NULL, NULL),  -- Savings Account
    (512, 177, 22, '', 'ZAR', 1.00000000, 0, 610.00, 0, 610.00, NULL, NULL, NULL, NULL),  -- Interest Received
    -- LOAN-002 · Vehicle finance instalment
    (513, 178, 18, '', 'ZAR', 1.00000000, 7500.00, 0, 7500.00, 0, NULL, NULL, NULL, NULL),  -- Vehicle Finance Loan
    (514, 178, 1, '', 'ZAR', 1.00000000, 0, 7500.00, 0, 7500.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- INV-00020 · Table Bay Marine (Pty) Ltd
    (515, 179, 4, '', 'ZAR', 1.00000000, 72047.50, 0, 72047.50, 0, NULL, 3, NULL, NULL),  -- Accounts Receivable · Table Bay Marine (Pty) Ltd
    (516, 179, 21, '', 'ZAR', 1.00000000, 0, 62650.00, 0, 62650.00, NULL, NULL, NULL, NULL),  -- Sales
    (517, 179, 13, '', 'ZAR', 1.00000000, 0, 9397.50, 0, 9397.50, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00029 · Atlantic Cloud Hosting
    (518, 180, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (519, 180, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (520, 180, 12, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- BCH-009 · Bank charges
    (521, 181, 29, '', 'ZAR', 1.00000000, 245.00, 0, 245.00, 0, NULL, NULL, NULL, NULL),  -- Bank Charges
    (522, 181, 1, '', 'ZAR', 1.00000000, 0, 245.00, 0, 245.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- BILL-00030 · Coastal Stock Distributors
    (523, 182, 5, '', 'ZAR', 1.00000000, 42000.00, 0, 42000.00, 0, NULL, NULL, NULL, NULL),  -- Inventory
    (524, 182, 13, '', 'ZAR', 1.00000000, 6300.00, 0, 6300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (525, 182, 5, '', 'ZAR', 1.00000000, 9500.00, 0, 9500.00, 0, NULL, NULL, NULL, NULL),  -- Inventory
    (526, 182, 13, '', 'ZAR', 1.00000000, 1425.00, 0, 1425.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (527, 182, 12, '', 'ZAR', 1.00000000, 0, 59225.00, 0, 59225.00, NULL, 16, NULL, NULL),  -- Accounts Payable · Coastal Stock Distributors
    -- TAX-001 · Provisional tax — first period
    (528, 183, 32, '', 'ZAR', 1.00000000, 35000.00, 0, 35000.00, 0, NULL, NULL, NULL, NULL),  -- Income Tax Expense
    (529, 183, 17, '', 'ZAR', 1.00000000, 0, 35000.00, 0, 35000.00, NULL, NULL, NULL, NULL),  -- Income Tax Payable
    -- PAY-00046 · Atlantic Cloud Hosting
    (530, 184, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (531, 184, 12, '', 'ZAR', 1.00000000, 4485.00, 0, 4485.00, 0, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- PAY-00046 · Atlantic Cloud Hosting (cash basis)
    (532, 185, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (533, 185, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (534, 185, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- VAT-005 · VAT return paid
    (535, 186, 13, '', 'ZAR', 1.00000000, 23835.00, 0, 23835.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (536, 186, 1, '', 'ZAR', 1.00000000, 0, 23835.00, 0, 23835.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- SAL-009 · Salaries for the month
    (537, 187, 24, 'Gross salaries', 'ZAR', 1.00000000, 52000.00, 0, 52000.00, 0, NULL, NULL, 3, NULL),  -- Salaries and Wages
    (538, 187, 1, 'Net pay', 'ZAR', 1.00000000, 0, 43160.00, 0, 43160.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (539, 187, 14, 'PAYE withheld', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- PAYE Payable
    -- BILL-00031 · Highveld Fuel Services
    (540, 188, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (541, 188, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (542, 188, 12, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- TAX-002 · Provisional tax paid
    (543, 189, 17, '', 'ZAR', 1.00000000, 35000.00, 0, 35000.00, 0, NULL, NULL, NULL, NULL),  -- Income Tax Payable
    (544, 189, 1, '', 'ZAR', 1.00000000, 0, 35000.00, 0, 35000.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- INV-00021 · Karoo Fresh Produce (Pty) Ltd
    (545, 190, 4, '', 'ZAR', 1.00000000, 61007.50, 0, 61007.50, 0, NULL, 1, NULL, NULL),  -- Accounts Receivable · Karoo Fresh Produce (Pty) Ltd
    (546, 190, 21, '', 'ZAR', 1.00000000, 0, 53050.00, 0, 53050.00, NULL, NULL, NULL, NULL),  -- Sales
    (547, 190, 13, '', 'ZAR', 1.00000000, 0, 7957.50, 0, 7957.50, NULL, NULL, NULL, NULL),  -- VAT Control
    -- COS-001 · Cost of the stock sold
    (548, 191, 23, '', 'ZAR', 1.00000000, 2850.00, 0, 2850.00, 0, NULL, NULL, NULL, NULL),  -- Cost of Sales
    (549, 191, 5, '', 'ZAR', 1.00000000, 0, 2850.00, 0, 2850.00, NULL, NULL, NULL, NULL),  -- Inventory
    -- PAY-00047 · Karoo Fresh Produce (Pty) Ltd
    (550, 192, 1, '', 'ZAR', 1.00000000, 69000.00, 0, 69000.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (551, 192, 4, '', 'ZAR', 1.00000000, 0, 69000.00, 0, 69000.00, NULL, 1, NULL, NULL),  -- Accounts Receivable · Karoo Fresh Produce (Pty) Ltd
    -- PAY-00047 · Karoo Fresh Produce (Pty) Ltd (cash basis)
    (552, 193, 1, '', 'ZAR', 1.00000000, 69000.00, 0, 69000.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (553, 193, 21, '', 'ZAR', 1.00000000, 0, 47500.00, 0, 47500.00, NULL, NULL, NULL, NULL),  -- Sales
    (554, 193, 13, '', 'ZAR', 1.00000000, 0, 7125.00, 0, 7125.00, NULL, NULL, NULL, NULL),  -- VAT Control
    (555, 193, 21, '', 'ZAR', 1.00000000, 0, 12500.00, 0, 12500.00, NULL, NULL, NULL, NULL),  -- Sales
    (556, 193, 13, '', 'ZAR', 1.00000000, 0, 1875.00, 0, 1875.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00032 · Metro Property Management
    (557, 194, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (558, 194, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (559, 194, 12, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00048 · Metro Property Management
    (560, 195, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (561, 195, 12, '', 'ZAR', 1.00000000, 25300.00, 0, 25300.00, 0, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00048 · Metro Property Management (cash basis)
    (562, 196, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (563, 196, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (564, 196, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00022 · Halcyon Interiors CC
    (565, 197, 4, '', 'ZAR', 1.00000000, 49105.00, 0, 49105.00, 0, NULL, 2, NULL, NULL),  -- Accounts Receivable · Halcyon Interiors CC
    (566, 197, 21, '', 'ZAR', 1.00000000, 0, 42700.00, 0, 42700.00, NULL, NULL, NULL, NULL),  -- Sales
    (567, 197, 13, '', 'ZAR', 1.00000000, 0, 6405.00, 0, 6405.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- DSP-001 · Old laser printer sold
    (568, 198, 1, '', 'ZAR', 1.00000000, 500.00, 0, 500.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (569, 198, 8, '', 'ZAR', 1.00000000, 7500.00, 0, 7500.00, 0, NULL, NULL, NULL, NULL),  -- Accumulated Depreciation — Computer Equipment
    (570, 198, 7, '', 'ZAR', 1.00000000, 0, 8000.00, 0, 8000.00, NULL, NULL, NULL, NULL),  -- Computer Equipment
    -- PAYE-009 · PAYE paid
    (571, 199, 14, '', 'ZAR', 1.00000000, 8840.00, 0, 8840.00, 0, NULL, NULL, NULL, NULL),  -- PAYE Payable
    (572, 199, 1, '', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00049 · Protea Print Works
    (573, 200, 1, '', 'ZAR', 1.00000000, 46977.50, 0, 46977.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (574, 200, 4, '', 'ZAR', 1.00000000, 0, 46977.50, 0, 46977.50, NULL, 4, NULL, NULL),  -- Accounts Receivable · Protea Print Works
    -- PAY-00049 · Protea Print Works (cash basis)
    (575, 201, 1, '', 'ZAR', 1.00000000, 46977.50, 0, 46977.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (576, 201, 21, '', 'ZAR', 1.00000000, 0, 40850.00, 0, 40850.00, NULL, NULL, NULL, NULL),  -- Sales
    (577, 201, 13, '', 'ZAR', 1.00000000, 0, 6127.50, 0, 6127.50, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAY-00050 · Highveld Fuel Services
    (578, 202, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (579, 202, 12, '', 'ZAR', 1.00000000, 3220.00, 0, 3220.00, 0, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00050 · Highveld Fuel Services (cash basis)
    (580, 203, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (581, 203, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (582, 203, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INT-009 · Interest received
    (583, 204, 2, '', 'ZAR', 1.00000000, 610.00, 0, 610.00, 0, NULL, NULL, NULL, NULL),  -- Savings Account
    (584, 204, 22, '', 'ZAR', 1.00000000, 0, 610.00, 0, 610.00, NULL, NULL, NULL, NULL),  -- Interest Received
    -- LOAN-003 · Vehicle finance instalment
    (585, 205, 18, '', 'ZAR', 1.00000000, 7500.00, 0, 7500.00, 0, NULL, NULL, NULL, NULL),  -- Vehicle Finance Loan
    (586, 205, 1, '', 'ZAR', 1.00000000, 0, 7500.00, 0, 7500.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00051 · Table Bay Marine (Pty) Ltd
    (587, 206, 1, '', 'ZAR', 1.00000000, 72047.50, 0, 72047.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (588, 206, 4, '', 'ZAR', 1.00000000, 0, 72047.50, 0, 72047.50, NULL, 3, NULL, NULL),  -- Accounts Receivable · Table Bay Marine (Pty) Ltd
    -- PAY-00051 · Table Bay Marine (Pty) Ltd (cash basis)
    (589, 207, 1, '', 'ZAR', 1.00000000, 72047.50, 0, 72047.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (590, 207, 21, '', 'ZAR', 1.00000000, 0, 54150.00, 0, 54150.00, NULL, NULL, NULL, NULL),  -- Sales
    (591, 207, 13, '', 'ZAR', 1.00000000, 0, 8122.50, 0, 8122.50, NULL, NULL, NULL, NULL),  -- VAT Control
    (592, 207, 21, '', 'ZAR', 1.00000000, 0, 8500.00, 0, 8500.00, NULL, NULL, NULL, NULL),  -- Sales
    (593, 207, 13, '', 'ZAR', 1.00000000, 0, 1275.00, 0, 1275.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00023 · Table Bay Marine (Pty) Ltd
    (594, 208, 4, '', 'ZAR', 1.00000000, 71127.50, 0, 71127.50, 0, NULL, 3, NULL, NULL),  -- Accounts Receivable · Table Bay Marine (Pty) Ltd
    (595, 208, 21, '', 'ZAR', 1.00000000, 0, 61850.00, 0, 61850.00, NULL, NULL, NULL, NULL),  -- Sales
    (596, 208, 13, '', 'ZAR', 1.00000000, 0, 9277.50, 0, 9277.50, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00033 · Atlantic Cloud Hosting
    (597, 209, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (598, 209, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (599, 209, 12, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- BCH-010 · Bank charges
    (600, 210, 29, '', 'ZAR', 1.00000000, 245.00, 0, 245.00, 0, NULL, NULL, NULL, NULL),  -- Bank Charges
    (601, 210, 1, '', 'ZAR', 1.00000000, 0, 245.00, 0, 245.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- INV-00024 · Table Bay Marine (Pty) Ltd
    (602, 211, 4, '', 'ZAR', 1.00000000, 30245.00, 0, 30245.00, 0, NULL, 3, NULL, NULL),  -- Accounts Receivable · Table Bay Marine (Pty) Ltd
    (603, 211, 21, '', 'ZAR', 1.00000000, 0, 26300.00, 0, 26300.00, NULL, NULL, NULL, NULL),  -- Sales
    (604, 211, 13, '', 'ZAR', 1.00000000, 0, 3945.00, 0, 3945.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAY-00052 · Atlantic Cloud Hosting
    (605, 212, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (606, 212, 12, '', 'ZAR', 1.00000000, 4485.00, 0, 4485.00, 0, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- PAY-00052 · Atlantic Cloud Hosting (cash basis)
    (607, 213, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (608, 213, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (609, 213, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAY-00053 · Coastal Stock Distributors
    (610, 214, 1, '', 'ZAR', 1.00000000, 0, 59225.00, 0, 59225.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (611, 214, 12, '', 'ZAR', 1.00000000, 59225.00, 0, 59225.00, 0, NULL, 16, NULL, NULL),  -- Accounts Payable · Coastal Stock Distributors
    -- PAY-00053 · Coastal Stock Distributors (cash basis)
    (612, 215, 1, '', 'ZAR', 1.00000000, 0, 59225.00, 0, 59225.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (613, 215, 5, '', 'ZAR', 1.00000000, 42000.00, 0, 42000.00, 0, NULL, NULL, NULL, NULL),  -- Inventory
    (614, 215, 13, '', 'ZAR', 1.00000000, 6300.00, 0, 6300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (615, 215, 5, '', 'ZAR', 1.00000000, 9500.00, 0, 9500.00, 0, NULL, NULL, NULL, NULL),  -- Inventory
    (616, 215, 13, '', 'ZAR', 1.00000000, 1425.00, 0, 1425.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- COS-002 · Cost of the stock sold
    (617, 216, 23, '', 'ZAR', 1.00000000, 8400.00, 0, 8400.00, 0, NULL, NULL, NULL, NULL),  -- Cost of Sales
    (618, 216, 5, '', 'ZAR', 1.00000000, 0, 8400.00, 0, 8400.00, NULL, NULL, NULL, NULL),  -- Inventory
    -- SAL-010 · Salaries for the month
    (619, 217, 24, 'Gross salaries', 'ZAR', 1.00000000, 52000.00, 0, 52000.00, 0, NULL, NULL, 3, NULL),  -- Salaries and Wages
    (620, 217, 1, 'Net pay', 'ZAR', 1.00000000, 0, 43160.00, 0, 43160.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (621, 217, 14, 'PAYE withheld', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- PAYE Payable
    -- BILL-00034 · Highveld Fuel Services
    (622, 218, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (623, 218, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (624, 218, 12, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00054 · Halcyon Interiors CC
    (625, 219, 1, '', 'ZAR', 1.00000000, 49105.00, 0, 49105.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (626, 219, 4, '', 'ZAR', 1.00000000, 0, 49105.00, 0, 49105.00, NULL, 2, NULL, NULL),  -- Accounts Receivable · Halcyon Interiors CC
    -- PAY-00054 · Halcyon Interiors CC (cash basis)
    (627, 220, 1, '', 'ZAR', 1.00000000, 49105.00, 0, 49105.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (628, 220, 21, '', 'ZAR', 1.00000000, 0, 34200.00, 0, 34200.00, NULL, NULL, NULL, NULL),  -- Sales
    (629, 220, 13, '', 'ZAR', 1.00000000, 0, 5130.00, 0, 5130.00, NULL, NULL, NULL, NULL),  -- VAT Control
    (630, 220, 21, '', 'ZAR', 1.00000000, 0, 8500.00, 0, 8500.00, NULL, NULL, NULL, NULL),  -- Sales
    (631, 220, 13, '', 'ZAR', 1.00000000, 0, 1275.00, 0, 1275.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00035 · Metro Property Management
    (632, 221, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (633, 221, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (634, 221, 12, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00055 · Metro Property Management
    (635, 222, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (636, 222, 12, '', 'ZAR', 1.00000000, 25300.00, 0, 25300.00, 0, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00055 · Metro Property Management (cash basis)
    (637, 223, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (638, 223, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (639, 223, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00025 · Protea Print Works
    (640, 224, 4, '', 'ZAR', 1.00000000, 54625.00, 0, 54625.00, 0, NULL, 4, NULL, NULL),  -- Accounts Receivable · Protea Print Works
    (641, 224, 21, '', 'ZAR', 1.00000000, 0, 47500.00, 0, 47500.00, NULL, NULL, NULL, NULL),  -- Sales
    (642, 224, 13, '', 'ZAR', 1.00000000, 0, 7125.00, 0, 7125.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- CC-001 · Design software licence (credit card)
    (643, 225, 28, '', 'ZAR', 1.00000000, 1250.00, 0, 1250.00, 0, 1, NULL, 2, NULL),  -- Software and Hosting
    (644, 225, 13, '', 'ZAR', 1.00000000, 187.50, 0, 187.50, 0, 1, NULL, NULL, NULL),  -- VAT Control
    (645, 225, 15, '', 'ZAR', 1.00000000, 0, 1437.50, 0, 1437.50, 1, NULL, NULL, NULL),  -- Credit Card
    -- INV-00026 · Halcyon Interiors CC
    (646, 226, 4, '', 'ZAR', 1.00000000, 57845.00, 0, 57845.00, 0, NULL, 2, NULL, NULL),  -- Accounts Receivable · Halcyon Interiors CC
    (647, 226, 21, '', 'ZAR', 1.00000000, 0, 50300.00, 0, 50300.00, NULL, NULL, NULL, NULL),  -- Sales
    (648, 226, 13, '', 'ZAR', 1.00000000, 0, 7545.00, 0, 7545.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAYE-010 · PAYE paid
    (649, 227, 14, '', 'ZAR', 1.00000000, 8840.00, 0, 8840.00, 0, NULL, NULL, NULL, NULL),  -- PAYE Payable
    (650, 227, 1, '', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- PAY-00056 · Highveld Fuel Services
    (651, 228, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (652, 228, 12, '', 'ZAR', 1.00000000, 3220.00, 0, 3220.00, 0, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00056 · Highveld Fuel Services (cash basis)
    (653, 229, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (654, 229, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (655, 229, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INT-010 · Interest received
    (656, 230, 2, '', 'ZAR', 1.00000000, 610.00, 0, 610.00, 0, NULL, NULL, NULL, NULL),  -- Savings Account
    (657, 230, 22, '', 'ZAR', 1.00000000, 0, 610.00, 0, 610.00, NULL, NULL, NULL, NULL),  -- Interest Received
    -- LOAN-004 · Vehicle finance instalment
    (658, 231, 18, '', 'ZAR', 1.00000000, 7500.00, 0, 7500.00, 0, NULL, NULL, NULL, NULL),  -- Vehicle Finance Loan
    (659, 231, 1, '', 'ZAR', 1.00000000, 0, 7500.00, 0, 7500.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- INV-00027 · Protea Print Works
    (660, 232, 4, '', 'ZAR', 1.00000000, 32775.00, 0, 32775.00, 0, NULL, 4, NULL, NULL),  -- Accounts Receivable · Protea Print Works
    (661, 232, 21, '', 'ZAR', 1.00000000, 0, 28500.00, 0, 28500.00, NULL, NULL, NULL, NULL),  -- Sales
    (662, 232, 13, '', 'ZAR', 1.00000000, 0, 4275.00, 0, 4275.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAY-00057 · Table Bay Marine (Pty) Ltd
    (663, 233, 1, '', 'ZAR', 1.00000000, 71127.50, 0, 71127.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (664, 233, 4, '', 'ZAR', 1.00000000, 0, 71127.50, 0, 71127.50, NULL, 3, NULL, NULL),  -- Accounts Receivable · Table Bay Marine (Pty) Ltd
    -- PAY-00057 · Table Bay Marine (Pty) Ltd (cash basis)
    (665, 234, 1, '', 'ZAR', 1.00000000, 71127.50, 0, 71127.50, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (666, 234, 21, '', 'ZAR', 1.00000000, 0, 40850.00, 0, 40850.00, NULL, NULL, NULL, NULL),  -- Sales
    (667, 234, 13, '', 'ZAR', 1.00000000, 0, 6127.50, 0, 6127.50, NULL, NULL, NULL, NULL),  -- VAT Control
    (668, 234, 21, '', 'ZAR', 1.00000000, 0, 12500.00, 0, 12500.00, NULL, NULL, NULL, NULL),  -- Sales
    (669, 234, 13, '', 'ZAR', 1.00000000, 0, 1875.00, 0, 1875.00, NULL, NULL, NULL, NULL),  -- VAT Control
    (670, 234, 21, '', 'ZAR', 1.00000000, 0, 8500.00, 0, 8500.00, NULL, NULL, NULL, NULL),  -- Sales
    (671, 234, 13, '', 'ZAR', 1.00000000, 0, 1275.00, 0, 1275.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00037 · Atlantic Cloud Hosting
    (672, 235, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (673, 235, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (674, 235, 12, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- BILL-00038 · Cape Office Supplies (Pty) Ltd
    (675, 236, 26, '', 'ZAR', 1.00000000, 1850.00, 0, 1850.00, 0, NULL, NULL, NULL, NULL),  -- Office Supplies
    (676, 236, 13, '', 'ZAR', 1.00000000, 277.50, 0, 277.50, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (677, 236, 26, '', 'ZAR', 1.00000000, 1380.00, 0, 1380.00, 0, NULL, NULL, NULL, NULL),  -- Office Supplies
    (678, 236, 13, '', 'ZAR', 1.00000000, 207.00, 0, 207.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (679, 236, 12, '', 'ZAR', 1.00000000, 0, 3714.50, 0, 3714.50, NULL, 12, NULL, NULL),  -- Accounts Payable · Cape Office Supplies (Pty) Ltd
    -- BCH-011 · Bank charges
    (680, 237, 29, '', 'ZAR', 1.00000000, 245.00, 0, 245.00, 0, NULL, NULL, NULL, NULL),  -- Bank Charges
    (681, 237, 1, '', 'ZAR', 1.00000000, 0, 245.00, 0, 245.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- INV-00028 · Karoo Fresh Produce (Pty) Ltd
    (682, 238, 4, '', 'ZAR', 1.00000000, 45839.00, 0, 45839.00, 0, NULL, 1, NULL, NULL),  -- Accounts Receivable · Karoo Fresh Produce (Pty) Ltd
    (683, 238, 21, '', 'ZAR', 1.00000000, 0, 39860.00, 0, 39860.00, NULL, NULL, NULL, NULL),  -- Sales
    (684, 238, 13, '', 'ZAR', 1.00000000, 0, 5979.00, 0, 5979.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00039 · Highveld Fuel Services
    (685, 239, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (686, 239, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (687, 239, 12, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00058 · Atlantic Cloud Hosting
    (688, 240, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (689, 240, 12, '', 'ZAR', 1.00000000, 4485.00, 0, 4485.00, 0, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- PAY-00058 · Atlantic Cloud Hosting (cash basis)
    (690, 241, 1, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (691, 241, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (692, 241, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- VAT-006 · VAT return paid
    (693, 242, 13, '', 'ZAR', 1.00000000, 35130.00, 0, 35130.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (694, 242, 1, '', 'ZAR', 1.00000000, 0, 35130.00, 0, 35130.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- COS-003 · Cost of the stock sold
    (695, 243, 23, '', 'ZAR', 1.00000000, 16400.00, 0, 16400.00, 0, NULL, NULL, NULL, NULL),  -- Cost of Sales
    (696, 243, 5, '', 'ZAR', 1.00000000, 0, 16400.00, 0, 16400.00, NULL, NULL, NULL, NULL),  -- Inventory
    -- SAL-011 · Salaries for the month
    (697, 244, 24, 'Gross salaries', 'ZAR', 1.00000000, 52000.00, 0, 52000.00, 0, NULL, NULL, 3, NULL),  -- Salaries and Wages
    (698, 244, 1, 'Net pay', 'ZAR', 1.00000000, 0, 43160.00, 0, 43160.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (699, 244, 14, 'PAYE withheld', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- PAYE Payable
    -- PAY-00059 · Halcyon Interiors CC
    (700, 245, 1, '', 'ZAR', 1.00000000, 30000.00, 0, 30000.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (701, 245, 4, '', 'ZAR', 1.00000000, 0, 30000.00, 0, 30000.00, NULL, 2, NULL, NULL),  -- Accounts Receivable · Halcyon Interiors CC
    -- PAY-00059 · Halcyon Interiors CC (cash basis)
    (702, 246, 1, '', 'ZAR', 1.00000000, 30000.00, 0, 30000.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (703, 246, 21, '', 'ZAR', 1.00000000, 0, 21678.62, 0, 21678.62, NULL, NULL, NULL, NULL),  -- Sales
    (704, 246, 13, '', 'ZAR', 1.00000000, 0, 3251.79, 0, 3251.79, NULL, NULL, NULL, NULL),  -- VAT Control
    (705, 246, 21, '', 'ZAR', 1.00000000, 0, 4408.33, 0, 4408.33, NULL, NULL, NULL, NULL),  -- Sales
    (706, 246, 13, '', 'ZAR', 1.00000000, 0, 661.25, 0, 661.25, NULL, NULL, NULL, NULL),  -- VAT Control
    (707, 246, 11, '', 'ZAR', 1.00000000, 0, 0.01, 0, 0.01, NULL, NULL, NULL, NULL),  -- Suspense
    -- PAY-00060 · Protea Print Works
    (708, 247, 1, '', 'ZAR', 1.00000000, 54625.00, 0, 54625.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (709, 247, 4, '', 'ZAR', 1.00000000, 0, 54625.00, 0, 54625.00, NULL, 4, NULL, NULL),  -- Accounts Receivable · Protea Print Works
    -- PAY-00060 · Protea Print Works (cash basis)
    (710, 248, 1, '', 'ZAR', 1.00000000, 54625.00, 0, 54625.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (711, 248, 21, '', 'ZAR', 1.00000000, 0, 47500.00, 0, 47500.00, NULL, NULL, NULL, NULL),  -- Sales
    (712, 248, 13, '', 'ZAR', 1.00000000, 0, 7125.00, 0, 7125.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- ACR-001 · Telephone accrual at month end
    (713, 249, 31, '', 'ZAR', 1.00000000, 980.00, 0, 980.00, 0, NULL, NULL, NULL, NULL),  -- Telephone and Internet
    (714, 249, 16, '', 'ZAR', 1.00000000, 0, 980.00, 0, 980.00, NULL, NULL, NULL, NULL),  -- Accrued Expenses
    -- BILL-00040 · Metro Property Management
    (715, 250, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (716, 250, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (717, 250, 12, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00061 · Metro Property Management
    (718, 251, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (719, 251, 12, '', 'ZAR', 1.00000000, 25300.00, 0, 25300.00, 0, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00061 · Metro Property Management (cash basis)
    (720, 252, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (721, 252, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (722, 252, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- CC-002 · Credit card statement paid
    (723, 253, 15, '', 'ZAR', 1.00000000, 1437.50, 0, 1437.50, 0, NULL, NULL, NULL, NULL),  -- Credit Card
    (724, 253, 1, '', 'ZAR', 1.00000000, 0, 1437.50, 0, 1437.50, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- INV-00029 · Lerato Molefe
    (725, 254, 4, '', 'ZAR', 1.00000000, 8740.00, 0, 8740.00, 0, NULL, 5, NULL, NULL),  -- Accounts Receivable · Lerato Molefe
    (726, 254, 21, '', 'ZAR', 1.00000000, 0, 7600.00, 0, 7600.00, NULL, NULL, NULL, NULL),  -- Sales
    (727, 254, 13, '', 'ZAR', 1.00000000, 0, 1140.00, 0, 1140.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- ACR-001R · Reversal of ACR-001
    (728, 255, 16, '', 'ZAR', 1.00000000, 980.00, 0, 980.00, 0, NULL, NULL, NULL, NULL),  -- Accrued Expenses
    (729, 255, 31, '', 'ZAR', 1.00000000, 0, 980.00, 0, 980.00, NULL, NULL, NULL, NULL),  -- Telephone and Internet
    -- CC-003 · Mobile and fibre (credit card)
    (730, 256, 31, '', 'ZAR', 1.00000000, 980.00, 0, 980.00, 0, 1, NULL, NULL, NULL),  -- Telephone and Internet
    (731, 256, 13, '', 'ZAR', 1.00000000, 147.00, 0, 147.00, 0, 1, NULL, NULL, NULL),  -- VAT Control
    (732, 256, 15, '', 'ZAR', 1.00000000, 0, 1127.00, 0, 1127.00, 1, NULL, NULL, NULL),  -- Credit Card
    -- PAYE-011 · PAYE paid
    (733, 257, 14, '', 'ZAR', 1.00000000, 8840.00, 0, 8840.00, 0, NULL, NULL, NULL, NULL),  -- PAYE Payable
    (734, 257, 1, '', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- BILL-00041 · Highveld Fuel Services
    (735, 258, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (736, 258, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (737, 258, 12, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00062 · Lerato Molefe
    (738, 259, 1, '', 'ZAR', 1.00000000, 8740.00, 0, 8740.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (739, 259, 4, '', 'ZAR', 1.00000000, 0, 8740.00, 0, 8740.00, NULL, 5, NULL, NULL),  -- Accounts Receivable · Lerato Molefe
    -- PAY-00062 · Lerato Molefe (cash basis)
    (740, 260, 1, '', 'ZAR', 1.00000000, 8740.00, 0, 8740.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (741, 260, 21, '', 'ZAR', 1.00000000, 0, 7600.00, 0, 7600.00, NULL, NULL, NULL, NULL),  -- Sales
    (742, 260, 13, '', 'ZAR', 1.00000000, 0, 1140.00, 0, 1140.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAY-00063 · Highveld Fuel Services
    (743, 261, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (744, 261, 12, '', 'ZAR', 1.00000000, 3220.00, 0, 3220.00, 0, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00063 · Highveld Fuel Services (cash basis)
    (745, 262, 1, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (746, 262, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (747, 262, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00030 · Table Bay Marine (Pty) Ltd
    (748, 263, 4, '', 'ZAR', 1.00000000, 21900.00, 0, 21900.00, 0, NULL, 3, NULL, NULL),  -- Accounts Receivable · Table Bay Marine (Pty) Ltd
    (749, 263, 21, '', 'ZAR', 1.00000000, 0, 19200.00, 0, 19200.00, NULL, NULL, NULL, NULL),  -- Sales
    (750, 263, 13, '', 'ZAR', 1.00000000, 0, 2700.00, 0, 2700.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INT-011 · Interest received
    (751, 264, 2, '', 'ZAR', 1.00000000, 610.00, 0, 610.00, 0, NULL, NULL, NULL, NULL),  -- Savings Account
    (752, 264, 22, '', 'ZAR', 1.00000000, 0, 610.00, 0, 610.00, NULL, NULL, NULL, NULL),  -- Interest Received
    -- LOAN-005 · Vehicle finance instalment
    (753, 265, 18, '', 'ZAR', 1.00000000, 7500.00, 0, 7500.00, 0, NULL, NULL, NULL, NULL),  -- Vehicle Finance Loan
    (754, 265, 1, '', 'ZAR', 1.00000000, 0, 7500.00, 0, 7500.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- CC-004 · Travel to Durban (credit card)
    (755, 266, 27, '', 'ZAR', 1.00000000, 2300.00, 0, 2300.00, 0, 1, NULL, 1, 1),  -- Fuel and Travel
    (756, 266, 13, '', 'ZAR', 1.00000000, 345.00, 0, 345.00, 0, 1, NULL, NULL, NULL),  -- VAT Control
    (757, 266, 15, '', 'ZAR', 1.00000000, 0, 2645.00, 0, 2645.00, 1, NULL, NULL, NULL),  -- Credit Card
    -- INV-00031 · Halcyon Interiors CC
    (758, 267, 4, '', 'ZAR', 1.00000000, 21850.00, 0, 21850.00, 0, NULL, 2, NULL, NULL),  -- Accounts Receivable · Halcyon Interiors CC
    (759, 267, 21, '', 'ZAR', 1.00000000, 0, 19000.00, 0, 19000.00, NULL, NULL, NULL, NULL),  -- Sales
    (760, 267, 13, '', 'ZAR', 1.00000000, 0, 2850.00, 0, 2850.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PAY-00064 · Highveld Fuel Services
    (761, 268, 1, '', 'ZAR', 1.00000000, 0, 1000.00, 0, 1000.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (762, 268, 12, '', 'ZAR', 1.00000000, 1000.00, 0, 1000.00, 0, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00064 · Highveld Fuel Services (cash basis)
    (763, 269, 1, '', 'ZAR', 1.00000000, 0, 1000.00, 0, 1000.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (764, 269, 27, '', 'ZAR', 1.00000000, 869.57, 0, 869.57, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (765, 269, 13, '', 'ZAR', 1.00000000, 130.43, 0, 130.43, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- PC-001 · Courier fees (petty cash)
    (766, 270, 26, '', 'ZAR', 1.00000000, 150.00, 0, 150.00, 0, NULL, NULL, NULL, NULL),  -- Office Supplies
    (767, 270, 3, '', 'ZAR', 1.00000000, 0, 150.00, 0, 150.00, NULL, NULL, NULL, NULL),  -- Petty Cash
    -- BILL-00042 · Atlantic Cloud Hosting
    (768, 271, 28, '', 'ZAR', 1.00000000, 3900.00, 0, 3900.00, 0, NULL, NULL, NULL, NULL),  -- Software and Hosting
    (769, 271, 13, '', 'ZAR', 1.00000000, 585.00, 0, 585.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (770, 271, 12, '', 'ZAR', 1.00000000, 0, 4485.00, 0, 4485.00, NULL, 14, NULL, NULL),  -- Accounts Payable · Atlantic Cloud Hosting
    -- ADJ-001 · Stock count: damaged labels
    (771, 272, 23, '', 'ZAR', 1.00000000, 190.00, 0, 190.00, 0, NULL, NULL, NULL, NULL),  -- Cost of Sales
    (772, 272, 5, '', 'ZAR', 1.00000000, 0, 190.00, 0, 190.00, NULL, NULL, NULL, NULL),  -- Inventory
    -- INV-00032 · Protea Print Works
    (773, 273, 4, '', 'ZAR', 1.00000000, 13110.00, 0, 13110.00, 0, NULL, 4, NULL, NULL),  -- Accounts Receivable · Protea Print Works
    (774, 273, 21, '', 'ZAR', 1.00000000, 0, 11400.00, 0, 11400.00, NULL, NULL, NULL, NULL),  -- Sales
    (775, 273, 13, '', 'ZAR', 1.00000000, 0, 1710.00, 0, 1710.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BCH-012 · Bank charges
    (776, 274, 29, '', 'ZAR', 1.00000000, 245.00, 0, 245.00, 0, NULL, NULL, NULL, NULL),  -- Bank Charges
    (777, 274, 1, '', 'ZAR', 1.00000000, 0, 245.00, 0, 245.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- TAX-003 · Income tax accrual for the quarter
    (778, 275, 32, '', 'ZAR', 1.00000000, 12000.00, 0, 12000.00, 0, NULL, NULL, NULL, NULL),  -- Income Tax Expense
    (779, 275, 17, '', 'ZAR', 1.00000000, 0, 12000.00, 0, 12000.00, NULL, NULL, NULL, NULL),  -- Income Tax Payable
    -- BILL-00043 · Highveld Fuel Services
    (780, 276, 27, '', 'ZAR', 1.00000000, 2800.00, 0, 2800.00, 0, NULL, NULL, NULL, NULL),  -- Fuel and Travel
    (781, 276, 13, '', 'ZAR', 1.00000000, 420.00, 0, 420.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (782, 276, 12, '', 'ZAR', 1.00000000, 0, 3220.00, 0, 3220.00, NULL, 13, NULL, NULL),  -- Accounts Payable · Highveld Fuel Services
    -- PAY-00065 · Halcyon Interiors CC
    (783, 277, 1, '', 'ZAR', 1.00000000, 21850.00, 0, 21850.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (784, 277, 4, '', 'ZAR', 1.00000000, 0, 21850.00, 0, 21850.00, NULL, 2, NULL, NULL),  -- Accounts Receivable · Halcyon Interiors CC
    -- PAY-00065 · Halcyon Interiors CC (cash basis)
    (785, 278, 1, '', 'ZAR', 1.00000000, 21850.00, 0, 21850.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (786, 278, 21, '', 'ZAR', 1.00000000, 0, 19000.00, 0, 19000.00, NULL, NULL, NULL, NULL),  -- Sales
    (787, 278, 13, '', 'ZAR', 1.00000000, 0, 2850.00, 0, 2850.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- JNL-001 · Office supplies (captured twice)
    (788, 279, 26, '', 'ZAR', 1.00000000, 500.00, 0, 500.00, 0, NULL, NULL, NULL, NULL),  -- Office Supplies
    (789, 279, 1, '', 'ZAR', 1.00000000, 0, 500.00, 0, 500.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    -- SAL-012 · Salaries for the month
    (790, 280, 24, 'Gross salaries', 'ZAR', 1.00000000, 52000.00, 0, 52000.00, 0, NULL, NULL, 3, NULL),  -- Salaries and Wages
    (791, 280, 1, 'Net pay', 'ZAR', 1.00000000, 0, 43160.00, 0, 43160.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (792, 280, 14, 'PAYE withheld', 'ZAR', 1.00000000, 0, 8840.00, 0, 8840.00, NULL, NULL, NULL, NULL),  -- PAYE Payable
    -- PAY-00066 · Protea Print Works
    (793, 281, 1, '', 'ZAR', 1.00000000, 13110.00, 0, 13110.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (794, 281, 4, '', 'ZAR', 1.00000000, 0, 13110.00, 0, 13110.00, NULL, 4, NULL, NULL),  -- Accounts Receivable · Protea Print Works
    -- PAY-00066 · Protea Print Works (cash basis)
    (795, 282, 1, '', 'ZAR', 1.00000000, 13110.00, 0, 13110.00, 0, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (796, 282, 21, '', 'ZAR', 1.00000000, 0, 11400.00, 0, 11400.00, NULL, NULL, NULL, NULL),  -- Sales
    (797, 282, 13, '', 'ZAR', 1.00000000, 0, 1710.00, 0, 1710.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- INV-00033 · Karoo Fresh Produce (Pty) Ltd
    (798, 283, 4, '', 'ZAR', 1.00000000, 24150.00, 0, 24150.00, 0, NULL, 1, NULL, NULL),  -- Accounts Receivable · Karoo Fresh Produce (Pty) Ltd
    (799, 283, 21, '', 'ZAR', 1.00000000, 0, 21000.00, 0, 21000.00, NULL, NULL, NULL, NULL),  -- Sales
    (800, 283, 13, '', 'ZAR', 1.00000000, 0, 3150.00, 0, 3150.00, NULL, NULL, NULL, NULL),  -- VAT Control
    -- BILL-00045 · Metro Property Management
    (801, 284, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (802, 284, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    (803, 284, 12, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- ACR-002 · Telephone accrual at month end
    (804, 285, 31, 'Fibre line, not billed yet', 'ZAR', 1.00000000, 1100.00, 0, 1100.00, 0, NULL, NULL, NULL, NULL),  -- Telephone and Internet
    (805, 285, 16, 'Fibre line, not billed yet', 'ZAR', 1.00000000, 0, 1100.00, 0, 1100.00, NULL, NULL, NULL, NULL),  -- Accrued Expenses
    -- PAY-00067 · Metro Property Management
    (806, 286, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (807, 286, 12, '', 'ZAR', 1.00000000, 25300.00, 0, 25300.00, 0, NULL, 15, NULL, NULL),  -- Accounts Payable · Metro Property Management
    -- PAY-00067 · Metro Property Management (cash basis)
    (808, 287, 1, '', 'ZAR', 1.00000000, 0, 25300.00, 0, 25300.00, NULL, NULL, NULL, NULL),  -- Main Bank Account
    (809, 287, 25, '', 'ZAR', 1.00000000, 22000.00, 0, 22000.00, 0, NULL, NULL, NULL, NULL),  -- Rent
    (810, 287, 13, '', 'ZAR', 1.00000000, 3300.00, 0, 3300.00, 0, NULL, NULL, NULL, NULL),  -- VAT Control
    -- DEP-001-01 · Depreciation — Laptops (3)
    (811, 288, 30, '', 'ZAR', 1.00000000, 1500.00, 0, 1500.00, 0, NULL, NULL, 2, NULL),  -- Depreciation
    (812, 288, 8, '', 'ZAR', 1.00000000, 0, 1500.00, 0, 1500.00, NULL, NULL, NULL, NULL),  -- Accumulated Depreciation — Computer Equipment
    -- DEP-001-02 · Depreciation — Laptops (3)
    (813, 289, 30, '', 'ZAR', 1.00000000, 1500.00, 0, 1500.00, 0, NULL, NULL, 2, NULL),  -- Depreciation
    (814, 289, 8, '', 'ZAR', 1.00000000, 0, 1500.00, 0, 1500.00, NULL, NULL, NULL, NULL),  -- Accumulated Depreciation — Computer Equipment
    -- DEP-001-03 · Depreciation — Laptops (3)
    (815, 290, 30, '', 'ZAR', 1.00000000, 1500.00, 0, 1500.00, 0, NULL, NULL, 2, NULL),  -- Depreciation
    (816, 290, 8, '', 'ZAR', 1.00000000, 0, 1500.00, 0, 1500.00, NULL, NULL, NULL, NULL),  -- Accumulated Depreciation — Computer Equipment
    -- DEP-001-04 · Depreciation — Laptops (3)
    (817, 291, 30, '', 'ZAR', 1.00000000, 1500.00, 0, 1500.00, 0, NULL, NULL, 2, NULL),  -- Depreciation
    (818, 291, 8, '', 'ZAR', 1.00000000, 0, 1500.00, 0, 1500.00, NULL, NULL, NULL, NULL),  -- Accumulated Depreciation — Computer Equipment
    -- DEP-001-05 · Depreciation — Laptops (3)
    (819, 292, 30, '', 'ZAR', 1.00000000, 1500.00, 0, 1500.00, 0, NULL, NULL, 2, NULL),  -- Depreciation
    (820, 292, 8, '', 'ZAR', 1.00000000, 0, 1500.00, 0, 1500.00, NULL, NULL, NULL, NULL),  -- Accumulated Depreciation — Computer Equipment
    -- DEP-002-01 · Depreciation — Delivery vehicle
    (821, 293, 30, '', 'ZAR', 1.00000000, 6000.00, 0, 6000.00, 0, NULL, NULL, 2, NULL),  -- Depreciation
    (822, 293, 10, '', 'ZAR', 1.00000000, 0, 6000.00, 0, 6000.00, NULL, NULL, NULL, NULL),  -- Accumulated Depreciation — Vehicles
    -- DEP-002-02 · Depreciation — Delivery vehicle
    (823, 294, 30, '', 'ZAR', 1.00000000, 6000.00, 0, 6000.00, 0, NULL, NULL, 2, NULL),  -- Depreciation
    (824, 294, 10, '', 'ZAR', 1.00000000, 0, 6000.00, 0, 6000.00, NULL, NULL, NULL, NULL),  -- Accumulated Depreciation — Vehicles
    -- DEP-002-03 · Depreciation — Delivery vehicle
    (825, 295, 30, '', 'ZAR', 1.00000000, 6000.00, 0, 6000.00, 0, NULL, NULL, 2, NULL),  -- Depreciation
    (826, 295, 10, '', 'ZAR', 1.00000000, 0, 6000.00, 0, 6000.00, NULL, NULL, NULL, NULL),  -- Accumulated Depreciation — Vehicles
    -- DEP-002-04 · Depreciation — Delivery vehicle
    (827, 296, 30, '', 'ZAR', 1.00000000, 6000.00, 0, 6000.00, 0, NULL, NULL, 2, NULL),  -- Depreciation
    (828, 296, 10, '', 'ZAR', 1.00000000, 0, 6000.00, 0, 6000.00, NULL, NULL, NULL, NULL);  -- Accumulated Depreciation — Vehicles

-- ____________________________________________________________________________
-- Documents: invoices, bills, quotes and a credit note

INSERT INTO accounting_document (id, created_at, updated_at, created_by_id, company_id, direction, doc_type, number, date, due, terms, entity_id, status, currency_id, exchange_rate, notes, source_doc_id, journal_entry_id) VALUES
    -- INV-00001 · Karoo Fresh Produce (Pty) Ltd · paid
    (1, (CURRENT_DATE - 390 + time '10:15')::timestamptz, (CURRENT_DATE - 390 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00001', CURRENT_DATE - 390, CURRENT_DATE - 360, '30', 1, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 2),
    -- INV-00002 · Halcyon Interiors CC · paid
    (2, (CURRENT_DATE - 375 + time '10:15')::timestamptz, (CURRENT_DATE - 375 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00002', CURRENT_DATE - 375, CURRENT_DATE - 345, '30', 2, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 3),
    -- INV-00003 · Table Bay Marine (Pty) Ltd · paid
    (3, (CURRENT_DATE - 360 + time '10:15')::timestamptz, (CURRENT_DATE - 360 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00003', CURRENT_DATE - 360, CURRENT_DATE - 330, '30', 3, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 6),
    -- INV-00004 · Protea Print Works · paid
    (4, (CURRENT_DATE - 345 + time '10:15')::timestamptz, (CURRENT_DATE - 345 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00004', CURRENT_DATE - 345, CURRENT_DATE - 315, '30', 4, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 9),
    -- BILL-00001 · Atlantic Cloud Hosting · paid
    (5, (CURRENT_DATE - 345 + time '10:15')::timestamptz, (CURRENT_DATE - 345 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00001', CURRENT_DATE - 345, CURRENT_DATE - 315, '', 14, 'P', 'ZAR', 1.00000000, '', NULL, 10),
    -- BILL-00002 · Highveld Fuel Services · paid
    (6, (CURRENT_DATE - 335 + time '10:15')::timestamptz, (CURRENT_DATE - 335 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00002', CURRENT_DATE - 335, CURRENT_DATE - 320, '', 13, 'P', 'ZAR', 1.00000000, '', NULL, 16),
    -- BILL-00003 · Metro Property Management · paid
    (7, (CURRENT_DATE - 331 + time '10:15')::timestamptz, (CURRENT_DATE - 331 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00003', CURRENT_DATE - 331, CURRENT_DATE - 331, '', 15, 'P', 'ZAR', 1.00000000, 'Lease 2024/118', NULL, 19),
    -- INV-00005 · Karoo Fresh Produce (Pty) Ltd · paid
    (8, (CURRENT_DATE - 330 + time '10:15')::timestamptz, (CURRENT_DATE - 330 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00005', CURRENT_DATE - 330, (date_trunc('month', CURRENT_DATE - 330) + interval '1 month' - interval '1 day')::date, 'EOM', 1, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 22),
    -- BILL-00004 · Cape Office Supplies (Pty) Ltd · paid
    (9, (CURRENT_DATE - 320 + time '10:15')::timestamptz, (CURRENT_DATE - 320 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00004', CURRENT_DATE - 320, CURRENT_DATE - 290, '', 12, 'P', 'ZAR', 1.00000000, '', NULL, 27),
    -- INV-00006 · Table Bay Marine (Pty) Ltd · paid
    (10, (CURRENT_DATE - 315 + time '10:15')::timestamptz, (CURRENT_DATE - 315 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00006', CURRENT_DATE - 315, CURRENT_DATE - 285, '30', 3, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 30),
    -- BILL-00005 · Atlantic Cloud Hosting · paid
    (11, (CURRENT_DATE - 315 + time '10:15')::timestamptz, (CURRENT_DATE - 315 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00005', CURRENT_DATE - 315, CURRENT_DATE - 285, '', 14, 'P', 'ZAR', 1.00000000, '', NULL, 31),
    -- BILL-00006 · Highveld Fuel Services · paid
    (12, (CURRENT_DATE - 305 + time '10:15')::timestamptz, (CURRENT_DATE - 305 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00006', CURRENT_DATE - 305, CURRENT_DATE - 290, '', 13, 'P', 'ZAR', 1.00000000, '', NULL, 36),
    -- BILL-00007 · Metro Property Management · paid
    (13, (CURRENT_DATE - 301 + time '10:15')::timestamptz, (CURRENT_DATE - 301 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00007', CURRENT_DATE - 301, CURRENT_DATE - 301, '', 15, 'P', 'ZAR', 1.00000000, 'Lease 2024/118', NULL, 39),
    -- INV-00007 · Halcyon Interiors CC · paid
    (14, (CURRENT_DATE - 300 + time '10:15')::timestamptz, (CURRENT_DATE - 300 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00007', CURRENT_DATE - 300, CURRENT_DATE - 270, '30', 2, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 43),
    -- INV-00008 · Karoo Fresh Produce (Pty) Ltd · paid
    (15, (CURRENT_DATE - 285 + time '10:15')::timestamptz, (CURRENT_DATE - 285 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00008', CURRENT_DATE - 285, CURRENT_DATE - 255, '30', 1, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 52),
    -- BILL-00008 · Atlantic Cloud Hosting · paid
    (16, (CURRENT_DATE - 285 + time '10:15')::timestamptz, (CURRENT_DATE - 285 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00008', CURRENT_DATE - 285, CURRENT_DATE - 255, '', 14, 'P', 'ZAR', 1.00000000, '', NULL, 53),
    -- BILL-00009 · Highveld Fuel Services · paid
    (17, (CURRENT_DATE - 275 + time '10:15')::timestamptz, (CURRENT_DATE - 275 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00009', CURRENT_DATE - 275, CURRENT_DATE - 260, '', 13, 'P', 'ZAR', 1.00000000, '', NULL, 59),
    -- BILL-00010 · Metro Property Management · paid
    (18, (CURRENT_DATE - 271 + time '10:15')::timestamptz, (CURRENT_DATE - 271 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00010', CURRENT_DATE - 271, CURRENT_DATE - 271, '', 15, 'P', 'ZAR', 1.00000000, 'Lease 2024/118', NULL, 62),
    -- INV-00009 · Halcyon Interiors CC · paid
    (19, (CURRENT_DATE - 270 + time '10:15')::timestamptz, (CURRENT_DATE - 270 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00009', CURRENT_DATE - 270, CURRENT_DATE - 240, '30', 2, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 65),
    -- INV-00010 · Table Bay Marine (Pty) Ltd · paid
    (20, (CURRENT_DATE - 255 + time '10:15')::timestamptz, (CURRENT_DATE - 255 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00010', CURRENT_DATE - 255, CURRENT_DATE - 210, 'C', 3, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 72),
    -- BILL-00011 · Atlantic Cloud Hosting · paid
    (21, (CURRENT_DATE - 255 + time '10:15')::timestamptz, (CURRENT_DATE - 255 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00011', CURRENT_DATE - 255, CURRENT_DATE - 225, '', 14, 'P', 'ZAR', 1.00000000, '', NULL, 73),
    -- BILL-00012 · Highveld Fuel Services · paid
    (22, (CURRENT_DATE - 245 + time '10:15')::timestamptz, (CURRENT_DATE - 245 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00012', CURRENT_DATE - 245, CURRENT_DATE - 230, '', 13, 'P', 'ZAR', 1.00000000, '', NULL, 78),
    -- BILL-00013 · Metro Property Management · paid
    (23, (CURRENT_DATE - 241 + time '10:15')::timestamptz, (CURRENT_DATE - 241 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00013', CURRENT_DATE - 241, CURRENT_DATE - 241, '', 15, 'P', 'ZAR', 1.00000000, 'Lease 2024/118', NULL, 81),
    -- INV-00011 · Protea Print Works · paid
    (24, (CURRENT_DATE - 240 + time '10:15')::timestamptz, (CURRENT_DATE - 240 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00011', CURRENT_DATE - 240, CURRENT_DATE - 210, '30', 4, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 84),
    -- BILL-00014 · Cape Office Supplies (Pty) Ltd · paid
    (25, (CURRENT_DATE - 230 + time '10:15')::timestamptz, (CURRENT_DATE - 230 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00014', CURRENT_DATE - 230, CURRENT_DATE - 200, '', 12, 'P', 'ZAR', 1.00000000, '', NULL, 89),
    -- INV-00012 · Karoo Fresh Produce (Pty) Ltd · paid
    (26, (CURRENT_DATE - 225 + time '10:15')::timestamptz, (CURRENT_DATE - 225 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00012', CURRENT_DATE - 225, CURRENT_DATE - 195, '30', 1, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 90),
    -- BILL-00015 · Atlantic Cloud Hosting · paid
    (27, (CURRENT_DATE - 225 + time '10:15')::timestamptz, (CURRENT_DATE - 225 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00015', CURRENT_DATE - 225, CURRENT_DATE - 195, '', 14, 'P', 'ZAR', 1.00000000, '', NULL, 91),
    -- BILL-00016 · Highveld Fuel Services · paid
    (28, (CURRENT_DATE - 215 + time '10:15')::timestamptz, (CURRENT_DATE - 215 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00016', CURRENT_DATE - 215, CURRENT_DATE - 200, '', 13, 'P', 'ZAR', 1.00000000, '', NULL, 97),
    -- BILL-00017 · Metro Property Management · paid
    (29, (CURRENT_DATE - 211 + time '10:15')::timestamptz, (CURRENT_DATE - 211 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00017', CURRENT_DATE - 211, CURRENT_DATE - 211, '', 15, 'P', 'ZAR', 1.00000000, 'Lease 2024/118', NULL, 102),
    -- INV-00013 · Table Bay Marine (Pty) Ltd · paid
    (30, (CURRENT_DATE - 210 + time '10:15')::timestamptz, (CURRENT_DATE - 210 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00013', CURRENT_DATE - 210, CURRENT_DATE - 180, '30', 3, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 105),
    -- BILL-00018 · Cape Office Supplies (Pty) Ltd · paid
    (31, (CURRENT_DATE - 200 + time '10:15')::timestamptz, (CURRENT_DATE - 200 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00018', CURRENT_DATE - 200, CURRENT_DATE - 170, '', 12, 'P', 'ZAR', 1.00000000, 'Three laptops for the new staff.', NULL, 112),
    -- INV-00014 · Halcyon Interiors CC · paid
    (32, (CURRENT_DATE - 195 + time '10:15')::timestamptz, (CURRENT_DATE - 195 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00014', CURRENT_DATE - 195, CURRENT_DATE - 181, '14', 2, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 115),
    -- BILL-00019 · Atlantic Cloud Hosting · paid
    (33, (CURRENT_DATE - 195 + time '10:15')::timestamptz, (CURRENT_DATE - 195 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00019', CURRENT_DATE - 195, CURRENT_DATE - 165, '', 14, 'P', 'ZAR', 1.00000000, '', NULL, 116),
    -- BILL-00020 · Highveld Fuel Services · paid
    (34, (CURRENT_DATE - 185 + time '10:15')::timestamptz, (CURRENT_DATE - 185 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00020', CURRENT_DATE - 185, CURRENT_DATE - 170, '', 13, 'P', 'ZAR', 1.00000000, '', NULL, 121),
    -- BILL-00021 · Metro Property Management · paid
    (35, (CURRENT_DATE - 181 + time '10:15')::timestamptz, (CURRENT_DATE - 181 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00021', CURRENT_DATE - 181, CURRENT_DATE - 181, '', 15, 'P', 'ZAR', 1.00000000, 'Lease 2024/118', NULL, 126),
    -- INV-00015 · Karoo Fresh Produce (Pty) Ltd · paid
    (36, (CURRENT_DATE - 180 + time '10:15')::timestamptz, (CURRENT_DATE - 180 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00015', CURRENT_DATE - 180, CURRENT_DATE - 150, '30', 1, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 129),
    -- INV-00016 · Halcyon Interiors CC · paid
    (37, (CURRENT_DATE - 165 + time '10:15')::timestamptz, (CURRENT_DATE - 165 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00016', CURRENT_DATE - 165, CURRENT_DATE - 135, '30', 2, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 136),
    -- BILL-00022 · Atlantic Cloud Hosting · paid
    (38, (CURRENT_DATE - 165 + time '10:15')::timestamptz, (CURRENT_DATE - 165 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00022', CURRENT_DATE - 165, CURRENT_DATE - 135, '', 14, 'P', 'ZAR', 1.00000000, '', NULL, 137),
    -- BILL-00023 · Highveld Fuel Services · paid
    (39, (CURRENT_DATE - 155 + time '10:15')::timestamptz, (CURRENT_DATE - 155 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00023', CURRENT_DATE - 155, CURRENT_DATE - 140, '', 13, 'P', 'ZAR', 1.00000000, '', NULL, 143),
    -- BILL-00024 · Metro Property Management · paid
    (40, (CURRENT_DATE - 151 + time '10:15')::timestamptz, (CURRENT_DATE - 151 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00024', CURRENT_DATE - 151, CURRENT_DATE - 151, '', 15, 'P', 'ZAR', 1.00000000, 'Lease 2024/118', NULL, 146),
    -- INV-00017 · Table Bay Marine (Pty) Ltd · paid
    (41, (CURRENT_DATE - 150 + time '10:15')::timestamptz, (CURRENT_DATE - 150 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00017', CURRENT_DATE - 150, CURRENT_DATE - 120, '30', 3, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 149),
    -- BILL-00025 · Cape Office Supplies (Pty) Ltd · paid
    (42, (CURRENT_DATE - 140 + time '10:15')::timestamptz, (CURRENT_DATE - 140 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00025', CURRENT_DATE - 140, CURRENT_DATE - 110, '', 12, 'P', 'ZAR', 1.00000000, '', NULL, 155),
    -- INV-00018 · Protea Print Works · paid
    (43, (CURRENT_DATE - 135 + time '10:15')::timestamptz, (CURRENT_DATE - 135 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00018', CURRENT_DATE - 135, CURRENT_DATE - 75, '60', 4, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 159),
    -- BILL-00026 · Atlantic Cloud Hosting · paid
    (44, (CURRENT_DATE - 135 + time '10:15')::timestamptz, (CURRENT_DATE - 135 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00026', CURRENT_DATE - 135, CURRENT_DATE - 105, '', 14, 'P', 'ZAR', 1.00000000, '', NULL, 160),
    -- BILL-00027 · Highveld Fuel Services · paid
    (45, (CURRENT_DATE - 125 + time '10:15')::timestamptz, (CURRENT_DATE - 125 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00027', CURRENT_DATE - 125, CURRENT_DATE - 110, '', 13, 'P', 'ZAR', 1.00000000, '', NULL, 165),
    -- BILL-00028 · Metro Property Management · paid
    (46, (CURRENT_DATE - 121 + time '10:15')::timestamptz, (CURRENT_DATE - 121 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00028', CURRENT_DATE - 121, CURRENT_DATE - 121, '', 15, 'P', 'ZAR', 1.00000000, 'Lease 2024/118', NULL, 168),
    -- INV-00019 · Karoo Fresh Produce (Pty) Ltd · paid
    (47, (CURRENT_DATE - 120 + time '10:15')::timestamptz, (CURRENT_DATE - 120 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00019', CURRENT_DATE - 120, CURRENT_DATE - 90, '30', 1, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 171),
    -- INV-00020 · Table Bay Marine (Pty) Ltd · paid
    (48, (CURRENT_DATE - 105 + time '10:15')::timestamptz, (CURRENT_DATE - 105 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00020', CURRENT_DATE - 105, CURRENT_DATE - 75, '30', 3, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 179),
    -- BILL-00029 · Atlantic Cloud Hosting · paid
    (49, (CURRENT_DATE - 105 + time '10:15')::timestamptz, (CURRENT_DATE - 105 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00029', CURRENT_DATE - 105, CURRENT_DATE - 75, '', 14, 'P', 'ZAR', 1.00000000, '', NULL, 180),
    -- BILL-00030 · Coastal Stock Distributors · paid
    (50, (CURRENT_DATE - 100 + time '10:15')::timestamptz, (CURRENT_DATE - 100 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00030', CURRENT_DATE - 100, CURRENT_DATE - 70, '', 16, 'P', 'ZAR', 1.00000000, 'Delivery note DN-7781', NULL, 182),
    -- BILL-00031 · Highveld Fuel Services · paid
    (51, (CURRENT_DATE - 95 + time '10:15')::timestamptz, (CURRENT_DATE - 95 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00031', CURRENT_DATE - 95, CURRENT_DATE - 80, '', 13, 'P', 'ZAR', 1.00000000, '', NULL, 188),
    -- INV-00021 · Karoo Fresh Produce (Pty) Ltd · sent · 81 days after the due date: Default Risk
    (52, (CURRENT_DATE - 95 + time '10:15')::timestamptz, (CURRENT_DATE - 95 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00021', CURRENT_DATE - 95, CURRENT_DATE - 81, '14', 1, 'S', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 190),
    -- BILL-00032 · Metro Property Management · paid
    (53, (CURRENT_DATE - 91 + time '10:15')::timestamptz, (CURRENT_DATE - 91 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00032', CURRENT_DATE - 91, CURRENT_DATE - 91, '', 15, 'P', 'ZAR', 1.00000000, 'Lease 2024/118', NULL, 194),
    -- INV-00022 · Halcyon Interiors CC · paid
    (54, (CURRENT_DATE - 90 + time '10:15')::timestamptz, (CURRENT_DATE - 90 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00022', CURRENT_DATE - 90, CURRENT_DATE - 60, '30', 2, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 197),
    -- INV-00023 · Table Bay Marine (Pty) Ltd · paid
    (55, (CURRENT_DATE - 75 + time '10:15')::timestamptz, (CURRENT_DATE - 75 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00023', CURRENT_DATE - 75, CURRENT_DATE - 45, '30', 3, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 208),
    -- BILL-00033 · Atlantic Cloud Hosting · paid
    (56, (CURRENT_DATE - 75 + time '10:15')::timestamptz, (CURRENT_DATE - 75 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00033', CURRENT_DATE - 75, CURRENT_DATE - 45, '', 14, 'P', 'ZAR', 1.00000000, '', NULL, 209),
    -- QUO-00001 · Table Bay Marine (Pty) Ltd · approved · Accepted quote: invoice S3 comes from it
    (57, (CURRENT_DATE - 75 + time '10:15')::timestamptz, (CURRENT_DATE - 75 + time '10:15')::timestamptz, 1, 1, 'S', 'Q', 'QUO-00001', CURRENT_DATE - 75, CURRENT_DATE - 61, '30', 3, 'A', 'ZAR', 1.00000000, 'Valid for 14 days.', NULL, NULL),
    -- INV-00024 · Table Bay Marine (Pty) Ltd · sent
    (58, (CURRENT_DATE - 70 + time '10:15')::timestamptz, (CURRENT_DATE - 70 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00024', CURRENT_DATE - 70, CURRENT_DATE - 40, '30', 3, 'S', 'ZAR', 1.00000000, 'Thank you for your business.', 57, 211),
    -- BILL-00034 · Highveld Fuel Services · paid
    (59, (CURRENT_DATE - 65 + time '10:15')::timestamptz, (CURRENT_DATE - 65 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00034', CURRENT_DATE - 65, CURRENT_DATE - 50, '', 13, 'P', 'ZAR', 1.00000000, '', NULL, 218),
    -- BILL-00035 · Metro Property Management · paid
    (60, (CURRENT_DATE - 61 + time '10:15')::timestamptz, (CURRENT_DATE - 61 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00035', CURRENT_DATE - 61, CURRENT_DATE - 61, '', 15, 'P', 'ZAR', 1.00000000, 'Lease 2024/118', NULL, 221),
    -- INV-00025 · Protea Print Works · paid
    (61, (CURRENT_DATE - 60 + time '10:15')::timestamptz, (CURRENT_DATE - 60 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00025', CURRENT_DATE - 60, CURRENT_DATE - 30, '30', 4, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 224),
    -- INV-00026 · Halcyon Interiors CC · partly paid · Partly paid, 30 days after the due date
    (62, (CURRENT_DATE - 60 + time '10:15')::timestamptz, (CURRENT_DATE - 60 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00026', CURRENT_DATE - 60, CURRENT_DATE - 30, '30', 2, 'PP', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 226),
    -- BILL-00036 · Atlantic Cloud Hosting · void
    (63, (CURRENT_DATE - 60 + time '10:15')::timestamptz, (CURRENT_DATE - 60 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00036', CURRENT_DATE - 60, CURRENT_DATE - 30, '', 14, 'V', 'ZAR', 1.00000000, 'Denied: the supplier charged twice.', NULL, NULL),
    -- INV-00027 · Protea Print Works · sent · 36 days after the due date
    (64, (CURRENT_DATE - 50 + time '10:15')::timestamptz, (CURRENT_DATE - 50 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00027', CURRENT_DATE - 50, CURRENT_DATE - 36, '14', 4, 'S', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 232),
    -- BILL-00037 · Atlantic Cloud Hosting · paid
    (65, (CURRENT_DATE - 45 + time '10:15')::timestamptz, (CURRENT_DATE - 45 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00037', CURRENT_DATE - 45, CURRENT_DATE - 15, '', 14, 'P', 'ZAR', 1.00000000, '', NULL, 235),
    -- BILL-00038 · Cape Office Supplies (Pty) Ltd · approved · Unpaid, 15 days after the due date
    (66, (CURRENT_DATE - 45 + time '10:15')::timestamptz, (CURRENT_DATE - 45 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00038', CURRENT_DATE - 45, CURRENT_DATE - 15, '', 12, 'A', 'ZAR', 1.00000000, '', NULL, 236),
    -- INV-00028 · Karoo Fresh Produce (Pty) Ltd · sent · 10 days after the due date
    (67, (CURRENT_DATE - 40 + time '10:15')::timestamptz, (CURRENT_DATE - 40 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00028', CURRENT_DATE - 40, CURRENT_DATE - 10, '30', 1, 'S', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 238),
    -- BILL-00039 · Highveld Fuel Services · paid
    (68, (CURRENT_DATE - 40 + time '10:15')::timestamptz, (CURRENT_DATE - 40 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00039', CURRENT_DATE - 40, CURRENT_DATE - 25, '', 13, 'P', 'ZAR', 1.00000000, '', NULL, 239),
    -- BILL-00040 · Metro Property Management · paid
    (69, (CURRENT_DATE - 31 + time '10:15')::timestamptz, (CURRENT_DATE - 31 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00040', CURRENT_DATE - 31, CURRENT_DATE - 31, '', 15, 'P', 'ZAR', 1.00000000, 'Lease 2024/118', NULL, 250),
    -- INV-00029 · Lerato Molefe · paid
    (70, (CURRENT_DATE - 30 + time '10:15')::timestamptz, (CURRENT_DATE - 30 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00029', CURRENT_DATE - 30, CURRENT_DATE - 30, '0', 5, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 254),
    -- BILL-00041 · Highveld Fuel Services · partly paid · Partly paid, after the due date
    (71, (CURRENT_DATE - 28 + time '10:15')::timestamptz, (CURRENT_DATE - 28 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00041', CURRENT_DATE - 28, CURRENT_DATE - 13, '', 13, 'PP', 'ZAR', 1.00000000, '', NULL, 258),
    -- INV-00030 · Table Bay Marine (Pty) Ltd · sent · Not yet due
    (72, (CURRENT_DATE - 25 + time '10:15')::timestamptz, (CURRENT_DATE - 25 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00030', CURRENT_DATE - 25, CURRENT_DATE + 5, '30', 3, 'S', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 263),
    -- INV-00031 · Halcyon Interiors CC · paid
    (73, (CURRENT_DATE - 20 + time '10:15')::timestamptz, (CURRENT_DATE - 20 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00031', CURRENT_DATE - 20, CURRENT_DATE + 10, '30', 2, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 267),
    -- CRN-00001 · Halcyon Interiors CC · draft
    (74, (CURRENT_DATE - 18 + time '10:15')::timestamptz, (CURRENT_DATE - 18 + time '10:15')::timestamptz, 2, 1, 'S', 'C', 'CRN-00001', CURRENT_DATE - 18, NULL, '', 2, 'D', 'ZAR', 1.00000000, 'Draft credit note for invoice S4.', NULL, NULL),
    -- BILL-00042 · Atlantic Cloud Hosting · approved
    (75, (CURRENT_DATE - 15 + time '10:15')::timestamptz, (CURRENT_DATE - 15 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00042', CURRENT_DATE - 15, CURRENT_DATE + 15, '', 14, 'A', 'ZAR', 1.00000000, '', NULL, 271),
    -- INV-00032 · Protea Print Works · paid
    (76, (CURRENT_DATE - 12 + time '10:15')::timestamptz, (CURRENT_DATE - 12 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00032', CURRENT_DATE - 12, CURRENT_DATE - 5, '7', 4, 'P', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 273),
    -- BILL-00043 · Highveld Fuel Services · approved · Due in the next 7 days
    (77, (CURRENT_DATE - 10 + time '10:15')::timestamptz, (CURRENT_DATE - 10 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00043', CURRENT_DATE - 10, CURRENT_DATE + 5, '', 13, 'A', 'ZAR', 1.00000000, '', NULL, 276),
    -- QUO-00002 · Umhlanga Coastal Hotels · sent
    (78, (CURRENT_DATE - 9 + time '10:15')::timestamptz, (CURRENT_DATE - 9 + time '10:15')::timestamptz, 1, 1, 'S', 'Q', 'QUO-00002', CURRENT_DATE - 9, CURRENT_DATE + 5, '30', 6, 'S', 'ZAR', 1.00000000, 'Three front desks. Valid for 14 days.', NULL, NULL),
    -- INV-00033 · Karoo Fresh Produce (Pty) Ltd · sent · Its entry waits for acceptance
    (79, (CURRENT_DATE - 3 + time '10:15')::timestamptz, (CURRENT_DATE - 3 + time '10:15')::timestamptz, 1, 1, 'S', 'I', 'INV-00033', CURRENT_DATE - 3, CURRENT_DATE + 27, '30', 1, 'S', 'ZAR', 1.00000000, 'Thank you for your business.', NULL, 283),
    -- BILL-00044 · Cape Office Supplies (Pty) Ltd · draft · Waits for a review
    (80, (CURRENT_DATE - 2 + time '10:15')::timestamptz, (CURRENT_DATE - 2 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00044', CURRENT_DATE - 2, CURRENT_DATE + 12, '', 12, 'D', 'ZAR', 1.00000000, 'Supplier invoice INV-00014 attached.', NULL, NULL),
    -- BILL-00045 · Metro Property Management · paid
    (81, (CURRENT_DATE - 1 + time '10:15')::timestamptz, (CURRENT_DATE - 1 + time '10:15')::timestamptz, 2, 1, 'P', 'B', 'BILL-00045', CURRENT_DATE - 1, CURRENT_DATE - 1, '', 15, 'P', 'ZAR', 1.00000000, 'Lease 2024/118', NULL, 284);

INSERT INTO accounting_documentline (id, document_id, item_id, service_id, account_id, tax_code_id, cost_centre_id, project_id, description, quantity, unit_price, discount, sort_order) VALUES
    (1, 1, NULL, 1, 21, 1, 1, 1, 'Consulting — systems analysis', 36.00, 950.00, 0.00, 0),
    (2, 1, NULL, 2, 21, 1, 1, 1, 'Installation and setup', 1.00, 12500.00, 0.00, 1),
    (3, 2, NULL, 1, 21, 1, 1, 2, 'Consulting — systems analysis', 43.00, 950.00, 0.00, 0),
    (4, 2, NULL, 3, 21, 1, 1, NULL, 'Support retainer — one month', 1.00, 8500.00, 0.00, 1),
    (5, 3, NULL, 1, 21, 1, 1, NULL, 'Consulting — systems analysis', 50.00, 950.00, 0.00, 0),
    (6, 3, NULL, 3, 21, 1, 1, NULL, 'Support retainer — one month', 1.00, 8500.00, 0.00, 1),
    (7, 4, NULL, 1, 21, 1, 1, NULL, 'Consulting — systems analysis', 57.00, 950.00, 0.00, 0),
    (8, 4, NULL, 2, 21, 1, 1, NULL, 'Installation and setup', 1.00, 12500.00, 0.00, 1),
    (9, 5, NULL, NULL, 28, 1, 2, NULL, 'Cloud hosting and backups — one month', 1.00, 3900.00, 0.00, 0),
    (10, 6, NULL, NULL, 27, 1, 2, NULL, 'Diesel — delivery vehicle', 1.00, 2800.00, 0.00, 0),
    (11, 7, NULL, NULL, 25, 1, 3, NULL, 'Office rent — one month', 1.00, 22000.00, 0.00, 0),
    (12, 8, NULL, 1, 21, 1, 1, 1, 'Consulting — systems analysis', 36.00, 950.00, 0.00, 0),
    (13, 9, NULL, NULL, 26, 1, NULL, NULL, 'Paper, files and stationery', 1.00, 1700.00, 0.00, 0),
    (14, 9, 7, NULL, 26, 1, NULL, NULL, 'Printer Toner Cartridge', 1.00, 700.00, 0.00, 1),
    (15, 10, NULL, 1, 21, 1, 1, NULL, 'Consulting — systems analysis', 43.00, 950.00, 0.00, 0),
    (16, 10, NULL, 3, 21, 1, 1, NULL, 'Support retainer — one month', 1.00, 8500.00, 0.00, 1),
    (17, 11, NULL, NULL, 28, 1, 2, NULL, 'Cloud hosting and backups — one month', 1.00, 3900.00, 0.00, 0),
    (18, 12, NULL, NULL, 27, 1, 2, NULL, 'Diesel — delivery vehicle', 1.00, 2800.00, 0.00, 0),
    (19, 13, NULL, NULL, 25, 1, 3, NULL, 'Office rent — one month', 1.00, 22000.00, 0.00, 0),
    (20, 14, NULL, 1, 21, 1, 1, 2, 'Consulting — systems analysis', 50.00, 950.00, 0.00, 0),
    (21, 14, NULL, 2, 21, 1, 1, 2, 'Installation and setup', 1.00, 12500.00, 0.00, 1),
    (22, 14, NULL, 3, 21, 1, 1, NULL, 'Support retainer — one month', 1.00, 8500.00, 0.00, 2),
    (23, 15, NULL, 1, 21, 1, 1, 1, 'Consulting — systems analysis', 57.00, 950.00, 0.00, 0),
    (24, 16, NULL, NULL, 28, 1, 2, NULL, 'Cloud hosting and backups — one month', 1.00, 3900.00, 0.00, 0),
    (25, 17, NULL, NULL, 27, 1, 2, NULL, 'Diesel — delivery vehicle', 1.00, 2800.00, 0.00, 0),
    (26, 18, NULL, NULL, 25, 1, 3, NULL, 'Office rent — one month', 1.00, 22000.00, 0.00, 0),
    (27, 19, NULL, 1, 21, 1, 1, 2, 'Consulting — systems analysis', 36.00, 950.00, 0.00, 0),
    (28, 19, NULL, 3, 21, 1, 1, NULL, 'Support retainer — one month', 1.00, 8500.00, 0.00, 1),
    (29, 20, NULL, 1, 21, 1, 1, NULL, 'Consulting — systems analysis', 43.00, 950.00, 0.00, 0),
    (30, 20, NULL, 2, 21, 1, 1, NULL, 'Installation and setup', 1.00, 12500.00, 0.00, 1),
    (31, 20, NULL, 3, 21, 1, 1, NULL, 'Support retainer — one month', 1.00, 8500.00, 0.00, 2),
    (32, 21, NULL, NULL, 28, 1, 2, NULL, 'Cloud hosting and backups — one month', 1.00, 3900.00, 0.00, 0),
    (33, 22, NULL, NULL, 27, 1, 2, NULL, 'Diesel — delivery vehicle', 1.00, 2800.00, 0.00, 0),
    (34, 23, NULL, NULL, 25, 1, 3, NULL, 'Office rent — one month', 1.00, 22000.00, 0.00, 0),
    (35, 24, NULL, 1, 21, 1, 1, NULL, 'Consulting — systems analysis', 50.00, 950.00, 0.00, 0),
    (36, 25, NULL, NULL, 26, 1, NULL, NULL, 'Paper, files and stationery', 1.00, 1700.00, 0.00, 0),
    (37, 25, 7, NULL, 26, 1, NULL, NULL, 'Printer Toner Cartridge', 1.00, 700.00, 0.00, 1),
    (38, 26, NULL, 1, 21, 1, 1, 1, 'Consulting — systems analysis', 57.00, 950.00, 0.00, 0),
    (39, 27, NULL, NULL, 28, 1, 2, NULL, 'Cloud hosting and backups — one month', 1.00, 3900.00, 0.00, 0),
    (40, 28, NULL, NULL, 27, 1, 2, NULL, 'Diesel — delivery vehicle', 1.00, 2800.00, 0.00, 0),
    (41, 29, NULL, NULL, 25, 1, 3, NULL, 'Office rent — one month', 1.00, 22000.00, 0.00, 0),
    (42, 30, NULL, 1, 21, 1, 1, NULL, 'Consulting — systems analysis', 36.00, 950.00, 0.00, 0),
    (43, 30, NULL, 2, 21, 1, 1, NULL, 'Installation and setup', 1.00, 12500.00, 0.00, 1),
    (44, 30, NULL, 3, 21, 1, 1, NULL, 'Support retainer — one month', 1.00, 8500.00, 0.00, 2),
    (45, 31, 3, NULL, 7, 1, NULL, 3, 'Laptop 14 inch, 32 GB — serial LTP-2026-0001', 1.00, 18000.00, 0.00, 0),
    (46, 31, 4, NULL, 7, 1, NULL, 3, 'Laptop 14 inch, 32 GB — serial LTP-2026-0002', 1.00, 18000.00, 0.00, 1),
    (47, 31, 5, NULL, 7, 1, NULL, 3, 'Laptop 14 inch, 32 GB — serial LTP-2026-0003', 1.00, 18000.00, 0.00, 2),
    (48, 32, NULL, 1, 21, 1, 1, 2, 'Consulting — systems analysis', 43.00, 950.00, 0.00, 0),
    (49, 32, NULL, 3, 21, 1, 1, NULL, 'Support retainer — one month', 1.00, 8500.00, 0.00, 1),
    (50, 33, NULL, NULL, 28, 1, 2, NULL, 'Cloud hosting and backups — one month', 1.00, 3900.00, 0.00, 0),
    (51, 34, NULL, NULL, 27, 1, 2, NULL, 'Diesel — delivery vehicle', 1.00, 2800.00, 0.00, 0),
    (52, 35, NULL, NULL, 25, 1, 3, NULL, 'Office rent — one month', 1.00, 22000.00, 0.00, 0),
    (53, 36, NULL, 1, 21, 1, 1, 1, 'Consulting — systems analysis', 50.00, 950.00, 0.00, 0),
    (54, 37, NULL, 1, 21, 1, 1, 2, 'Consulting — systems analysis', 57.00, 950.00, 0.00, 0),
    (55, 37, NULL, 2, 21, 1, 1, 2, 'Installation and setup', 1.00, 12500.00, 0.00, 1),
    (56, 37, NULL, 3, 21, 1, 1, NULL, 'Support retainer — one month', 1.00, 8500.00, 0.00, 2),
    (57, 38, NULL, NULL, 28, 1, 2, NULL, 'Cloud hosting and backups — one month', 1.00, 3900.00, 0.00, 0),
    (58, 39, NULL, NULL, 27, 1, 2, NULL, 'Diesel — delivery vehicle', 1.00, 2800.00, 0.00, 0),
    (59, 40, NULL, NULL, 25, 1, 3, NULL, 'Office rent — one month', 1.00, 22000.00, 0.00, 0),
    (60, 41, NULL, 1, 21, 1, 1, NULL, 'Consulting — systems analysis', 36.00, 950.00, 0.00, 0),
    (61, 41, NULL, 3, 21, 1, 1, NULL, 'Support retainer — one month', 1.00, 8500.00, 0.00, 1),
    (62, 42, NULL, NULL, 26, 1, NULL, NULL, 'Paper, files and stationery', 1.00, 1700.00, 0.00, 0),
    (63, 42, 7, NULL, 26, 1, NULL, NULL, 'Printer Toner Cartridge', 1.00, 700.00, 0.00, 1),
    (64, 43, NULL, 1, 21, 1, 1, NULL, 'Consulting — systems analysis', 43.00, 950.00, 0.00, 0),
    (65, 44, NULL, NULL, 28, 1, 2, NULL, 'Cloud hosting and backups — one month', 1.00, 3900.00, 0.00, 0),
    (66, 45, NULL, NULL, 27, 1, 2, NULL, 'Diesel — delivery vehicle', 1.00, 2800.00, 0.00, 0),
    (67, 46, NULL, NULL, 25, 1, 3, NULL, 'Office rent — one month', 1.00, 22000.00, 0.00, 0),
    (68, 47, NULL, 1, 21, 1, 1, 1, 'Consulting — systems analysis', 50.00, 950.00, 0.00, 0),
    (69, 47, NULL, 2, 21, 1, 1, 1, 'Installation and setup', 1.00, 12500.00, 0.00, 1),
    (70, 48, NULL, 1, 21, 1, 1, NULL, 'Consulting — systems analysis', 57.00, 950.00, 0.00, 0),
    (71, 48, NULL, 3, 21, 1, 1, NULL, 'Support retainer — one month', 1.00, 8500.00, 0.00, 1),
    (72, 49, NULL, NULL, 28, 1, 2, NULL, 'Cloud hosting and backups — one month', 1.00, 3900.00, 0.00, 0),
    (73, 50, 1, NULL, 5, 1, NULL, NULL, 'Barcode Scanner BS-200', 20.00, 2100.00, 0.00, 0),
    (74, 50, 2, NULL, 5, 1, NULL, NULL, 'Thermal Label Roll 100x150', 100.00, 95.00, 0.00, 1),
    (75, 51, NULL, NULL, 27, 1, 2, NULL, 'Diesel — delivery vehicle', 1.00, 2800.00, 0.00, 0),
    (76, 52, NULL, 1, 21, 1, 1, 1, 'Consulting — systems analysis', 50.00, 950.00, 0.00, 0),
    (77, 52, 2, NULL, 21, 1, 1, NULL, 'Thermal Label Roll 100x150', 30.00, 185.00, 0.00, 1),
    (78, 53, NULL, NULL, 25, 1, 3, NULL, 'Office rent — one month', 1.00, 22000.00, 0.00, 0),
    (79, 54, NULL, 1, 21, 1, 1, 2, 'Consulting — systems analysis', 36.00, 950.00, 0.00, 0),
    (80, 54, NULL, 3, 21, 1, 1, NULL, 'Support retainer — one month', 1.00, 8500.00, 0.00, 1),
    (81, 55, NULL, 1, 21, 1, 1, NULL, 'Consulting — systems analysis', 43.00, 950.00, 0.00, 0),
    (82, 55, NULL, 2, 21, 1, 1, NULL, 'Installation and setup', 1.00, 12500.00, 0.00, 1),
    (83, 55, NULL, 3, 21, 1, 1, NULL, 'Support retainer — one month', 1.00, 8500.00, 0.00, 2),
    (84, 56, NULL, NULL, 28, 1, 2, NULL, 'Cloud hosting and backups — one month', 1.00, 3900.00, 0.00, 0),
    (85, 57, 1, NULL, 21, 1, 1, NULL, 'Barcode Scanner BS-200', 4.00, 3450.00, 0.00, 0),
    (86, 57, NULL, 2, 21, 1, 1, NULL, 'Installation and setup', 1.00, 12500.00, 0.00, 1),
    (87, 58, 1, NULL, 21, 1, 1, NULL, 'Barcode Scanner BS-200', 4.00, 3450.00, 0.00, 0),
    (88, 58, NULL, 2, 21, 1, 1, NULL, 'Installation and setup', 1.00, 12500.00, 0.00, 1),
    (89, 59, NULL, NULL, 27, 1, 2, NULL, 'Diesel — delivery vehicle', 1.00, 2800.00, 0.00, 0),
    (90, 60, NULL, NULL, 25, 1, 3, NULL, 'Office rent — one month', 1.00, 22000.00, 0.00, 0),
    (91, 61, NULL, 1, 21, 1, 1, NULL, 'Consulting — systems analysis', 50.00, 950.00, 0.00, 0),
    (92, 62, NULL, 1, 21, 1, 1, 2, 'Consulting — systems analysis', 44.00, 950.00, 0.00, 0),
    (93, 62, NULL, 3, 21, 1, 1, NULL, 'Support retainer — one month', 1.00, 8500.00, 0.00, 1),
    (94, 63, NULL, NULL, 28, 1, NULL, NULL, 'Hosting — charged twice', 1.00, 3900.00, 0.00, 0),
    (95, 64, NULL, 1, 21, 1, 1, NULL, 'Consulting — systems analysis', 30.00, 950.00, 0.00, 0),
    (96, 65, NULL, NULL, 28, 1, 2, NULL, 'Cloud hosting and backups — one month', 1.00, 3900.00, 0.00, 0),
    (97, 66, NULL, NULL, 26, 1, 3, NULL, 'Paper, files and stationery', 1.00, 1850.00, 0.00, 0),
    (98, 66, 7, NULL, 26, 1, NULL, NULL, 'Printer Toner Cartridge', 2.00, 690.00, 0.00, 1),
    (99, 67, 1, NULL, 21, 1, 1, 1, 'Barcode Scanner BS-200', 6.00, 3450.00, 0.00, 0),
    (100, 67, 2, NULL, 21, 1, 1, 1, 'Thermal Label Roll 100x150', 40.00, 185.00, 10.00, 1),
    (101, 67, NULL, 2, 21, 1, 1, 1, 'Installation and setup', 1.00, 12500.00, 0.00, 2),
    (102, 68, NULL, NULL, 27, 1, 2, NULL, 'Diesel — delivery vehicle', 1.00, 2800.00, 0.00, 0),
    (103, 69, NULL, NULL, 25, 1, 3, NULL, 'Office rent — one month', 1.00, 22000.00, 0.00, 0),
    (104, 70, NULL, 1, 21, 1, 1, NULL, 'Consulting — systems analysis', 8.00, 950.00, 0.00, 0),
    (105, 71, NULL, NULL, 27, 1, 2, NULL, 'Diesel — delivery vehicle', 1.00, 2800.00, 0.00, 0),
    (106, 72, NULL, 3, 21, 1, 1, NULL, 'Support retainer — one month', 1.00, 8500.00, 0.00, 0),
    (107, 72, NULL, 1, 21, 1, 1, NULL, 'Consulting — systems analysis', 10.00, 950.00, 0.00, 1),
    (108, 72, NULL, 4, 21, 3, NULL, NULL, 'Export documentation', 1.00, 1200.00, 0.00, 2),
    (109, 73, NULL, 1, 21, 1, 1, 2, 'Consulting — systems analysis', 20.00, 950.00, 0.00, 0),
    (110, 74, NULL, NULL, 21, 1, NULL, NULL, 'Discount for the late delivery', 1.00, 2000.00, 0.00, 0),
    (111, 75, NULL, NULL, 28, 1, 2, NULL, 'Cloud hosting and backups — one month', 1.00, 3900.00, 0.00, 0),
    (112, 76, NULL, 1, 21, 1, 1, NULL, 'Consulting — systems analysis', 12.00, 950.00, 0.00, 0),
    (113, 77, NULL, NULL, 27, 1, 2, NULL, 'Diesel — delivery vehicle', 1.00, 2800.00, 0.00, 0),
    (114, 78, NULL, 1, 21, 1, 1, NULL, 'Consulting — systems analysis', 80.00, 950.00, 0.00, 0),
    (115, 78, NULL, 2, 21, 1, 1, NULL, 'Installation and setup', 3.00, 12500.00, 0.00, 1),
    (116, 79, NULL, 2, 21, 1, 1, 1, 'Installation and setup', 1.00, 12500.00, 0.00, 0),
    (117, 79, NULL, 3, 21, 1, 1, NULL, 'Support retainer — one month', 1.00, 8500.00, 0.00, 1),
    (118, 80, NULL, NULL, 26, 1, 3, NULL, 'Ergonomic chairs', 2.00, 2450.00, 0.00, 0),
    (119, 81, NULL, NULL, 25, 1, 3, NULL, 'Office rent — one month', 1.00, 22000.00, 0.00, 0);

INSERT INTO accounting_document_files (document_id, storedfile_id) VALUES
    (78, 'e38832a5-13f0-470e-a81b-428b75bae864'),
    (80, '3733b825-7fcd-4d7e-8d4b-5f0b53f04d04');

-- ____________________________________________________________________________
-- Payments and their allocations

INSERT INTO accounting_payment (id, created_at, updated_at, created_by_id, company_id, number, date, direction, entity_id, bank_account_id, currency_id, exchange_rate, amount, reference, journal_entry_id, cash_entry_id) VALUES
    -- PAY-00001 · Karoo Fresh Produce (Pty) Ltd · pays INV-00001 (53705.00)
    (1, (CURRENT_DATE - 364 + time '11:40')::timestamptz, (CURRENT_DATE - 364 + time '11:40')::timestamptz, 2, 1, 'PAY-00001', CURRENT_DATE - 364, 'IN', 1, 1, 'ZAR', 1.00000000, 53705.00, 'INV-00001', 4, 5),
    -- PAY-00002 · Halcyon Interiors CC · pays INV-00002 (56752.50)
    (2, (CURRENT_DATE - 349 + time '11:40')::timestamptz, (CURRENT_DATE - 349 + time '11:40')::timestamptz, 2, 1, 'PAY-00002', CURRENT_DATE - 349, 'IN', 2, 1, 'ZAR', 1.00000000, 56752.50, 'INV-00002', 7, 8),
    -- PAY-00003 · Atlantic Cloud Hosting · pays BILL-00001 (4485.00)
    (3, (CURRENT_DATE - 340 + time '11:40')::timestamptz, (CURRENT_DATE - 340 + time '11:40')::timestamptz, 2, 1, 'PAY-00003', CURRENT_DATE - 340, 'OUT', 14, 1, 'ZAR', 1.00000000, 4485.00, 'BILL-00001', 12, 13),
    -- PAY-00004 · Table Bay Marine (Pty) Ltd · pays INV-00003 (64400.00)
    (4, (CURRENT_DATE - 334 + time '11:40')::timestamptz, (CURRENT_DATE - 334 + time '11:40')::timestamptz, 2, 1, 'PAY-00004', CURRENT_DATE - 334, 'IN', 3, 1, 'ZAR', 1.00000000, 64400.00, 'INV-00003', 17, 18),
    -- PAY-00005 · Metro Property Management · pays BILL-00003 (25300.00)
    (5, (CURRENT_DATE - 331 + time '11:40')::timestamptz, (CURRENT_DATE - 331 + time '11:40')::timestamptz, 2, 1, 'PAY-00005', CURRENT_DATE - 331, 'OUT', 15, 1, 'ZAR', 1.00000000, 25300.00, 'BILL-00003', 20, 21),
    -- PAY-00006 · Highveld Fuel Services · pays BILL-00002 (3220.00)
    (6, (CURRENT_DATE - 323 + time '11:40')::timestamptz, (CURRENT_DATE - 323 + time '11:40')::timestamptz, 2, 1, 'PAY-00006', CURRENT_DATE - 323, 'OUT', 13, 1, 'ZAR', 1.00000000, 3220.00, 'BILL-00002', 24, 25),
    -- PAY-00007 · Protea Print Works · pays INV-00004 (76647.50)
    (7, (CURRENT_DATE - 319 + time '11:40')::timestamptz, (CURRENT_DATE - 319 + time '11:40')::timestamptz, 2, 1, 'PAY-00007', CURRENT_DATE - 319, 'IN', 4, 1, 'ZAR', 1.00000000, 76647.50, 'INV-00004', 28, 29),
    -- PAY-00008 · Atlantic Cloud Hosting · pays BILL-00005 (4485.00)
    (8, (CURRENT_DATE - 310 + time '11:40')::timestamptz, (CURRENT_DATE - 310 + time '11:40')::timestamptz, 2, 1, 'PAY-00008', CURRENT_DATE - 310, 'OUT', 14, 1, 'ZAR', 1.00000000, 4485.00, 'BILL-00005', 33, 34),
    -- PAY-00009 · Karoo Fresh Produce (Pty) Ltd · pays INV-00005 (39330.00)
    (9, (CURRENT_DATE - 304 + time '11:40')::timestamptz, (CURRENT_DATE - 304 + time '11:40')::timestamptz, 2, 1, 'PAY-00009', CURRENT_DATE - 304, 'IN', 1, 1, 'ZAR', 1.00000000, 39330.00, 'INV-00005', 37, 38),
    -- PAY-00010 · Metro Property Management · pays BILL-00007 (25300.00)
    (10, (CURRENT_DATE - 301 + time '11:40')::timestamptz, (CURRENT_DATE - 301 + time '11:40')::timestamptz, 2, 1, 'PAY-00010', CURRENT_DATE - 301, 'OUT', 15, 1, 'ZAR', 1.00000000, 25300.00, 'BILL-00007', 40, 41),
    -- PAY-00011 · Cape Office Supplies (Pty) Ltd · pays BILL-00004 (2760.00)
    (11, (CURRENT_DATE - 300 + time '11:40')::timestamptz, (CURRENT_DATE - 300 + time '11:40')::timestamptz, 2, 1, 'PAY-00011', CURRENT_DATE - 300, 'OUT', 12, 1, 'ZAR', 1.00000000, 2760.00, 'BILL-00004', 44, 45),
    -- PAY-00012 · Highveld Fuel Services · pays BILL-00006 (3220.00)
    (12, (CURRENT_DATE - 293 + time '11:40')::timestamptz, (CURRENT_DATE - 293 + time '11:40')::timestamptz, 2, 1, 'PAY-00012', CURRENT_DATE - 293, 'OUT', 13, 1, 'ZAR', 1.00000000, 3220.00, 'BILL-00006', 47, 48),
    -- PAY-00013 · Table Bay Marine (Pty) Ltd · pays INV-00006 (56752.50)
    (13, (CURRENT_DATE - 289 + time '11:40')::timestamptz, (CURRENT_DATE - 289 + time '11:40')::timestamptz, 2, 1, 'PAY-00013', CURRENT_DATE - 289, 'IN', 3, 1, 'ZAR', 1.00000000, 56752.50, 'INV-00006', 50, 51),
    -- PAY-00014 · Atlantic Cloud Hosting · pays BILL-00008 (4485.00)
    (14, (CURRENT_DATE - 280 + time '11:40')::timestamptz, (CURRENT_DATE - 280 + time '11:40')::timestamptz, 2, 1, 'PAY-00014', CURRENT_DATE - 280, 'OUT', 14, 1, 'ZAR', 1.00000000, 4485.00, 'BILL-00008', 55, 56),
    -- PAY-00015 · Halcyon Interiors CC · pays INV-00007 (78775.00)
    (15, (CURRENT_DATE - 274 + time '11:40')::timestamptz, (CURRENT_DATE - 274 + time '11:40')::timestamptz, 2, 1, 'PAY-00015', CURRENT_DATE - 274, 'IN', 2, 1, 'ZAR', 1.00000000, 78775.00, 'INV-00007', 60, 61),
    -- PAY-00016 · Metro Property Management · pays BILL-00010 (25300.00)
    (16, (CURRENT_DATE - 271 + time '11:40')::timestamptz, (CURRENT_DATE - 271 + time '11:40')::timestamptz, 2, 1, 'PAY-00016', CURRENT_DATE - 271, 'OUT', 15, 1, 'ZAR', 1.00000000, 25300.00, 'BILL-00010', 63, 64),
    -- PAY-00017 · Highveld Fuel Services · pays BILL-00009 (3220.00)
    (17, (CURRENT_DATE - 263 + time '11:40')::timestamptz, (CURRENT_DATE - 263 + time '11:40')::timestamptz, 2, 1, 'PAY-00017', CURRENT_DATE - 263, 'OUT', 13, 1, 'ZAR', 1.00000000, 3220.00, 'BILL-00009', 67, 68),
    -- PAY-00018 · Karoo Fresh Produce (Pty) Ltd · pays INV-00008 (62272.50)
    (18, (CURRENT_DATE - 259 + time '11:40')::timestamptz, (CURRENT_DATE - 259 + time '11:40')::timestamptz, 2, 1, 'PAY-00018', CURRENT_DATE - 259, 'IN', 1, 1, 'ZAR', 1.00000000, 62272.50, 'INV-00008', 70, 71),
    -- PAY-00019 · Atlantic Cloud Hosting · pays BILL-00011 (4485.00)
    (19, (CURRENT_DATE - 250 + time '11:40')::timestamptz, (CURRENT_DATE - 250 + time '11:40')::timestamptz, 2, 1, 'PAY-00019', CURRENT_DATE - 250, 'OUT', 14, 1, 'ZAR', 1.00000000, 4485.00, 'BILL-00011', 75, 76),
    -- PAY-00020 · Halcyon Interiors CC · pays INV-00009 (49105.00)
    (20, (CURRENT_DATE - 244 + time '11:40')::timestamptz, (CURRENT_DATE - 244 + time '11:40')::timestamptz, 2, 1, 'PAY-00020', CURRENT_DATE - 244, 'IN', 2, 1, 'ZAR', 1.00000000, 49105.00, 'INV-00009', 79, 80),
    -- PAY-00021 · Metro Property Management · pays BILL-00013 (25300.00)
    (21, (CURRENT_DATE - 241 + time '11:40')::timestamptz, (CURRENT_DATE - 241 + time '11:40')::timestamptz, 2, 1, 'PAY-00021', CURRENT_DATE - 241, 'OUT', 15, 1, 'ZAR', 1.00000000, 25300.00, 'BILL-00013', 82, 83),
    -- PAY-00022 · Highveld Fuel Services · pays BILL-00012 (3220.00)
    (22, (CURRENT_DATE - 233 + time '11:40')::timestamptz, (CURRENT_DATE - 233 + time '11:40')::timestamptz, 2, 1, 'PAY-00022', CURRENT_DATE - 233, 'OUT', 13, 1, 'ZAR', 1.00000000, 3220.00, 'BILL-00012', 86, 87),
    -- PAY-00023 · Atlantic Cloud Hosting · pays BILL-00015 (4485.00)
    (23, (CURRENT_DATE - 220 + time '11:40')::timestamptz, (CURRENT_DATE - 220 + time '11:40')::timestamptz, 2, 1, 'PAY-00023', CURRENT_DATE - 220, 'OUT', 14, 1, 'ZAR', 1.00000000, 4485.00, 'BILL-00015', 93, 94),
    -- PAY-00024 · Table Bay Marine (Pty) Ltd · pays INV-00010 (71127.50)
    (24, (CURRENT_DATE - 215 + time '11:40')::timestamptz, (CURRENT_DATE - 215 + time '11:40')::timestamptz, 2, 1, 'PAY-00024', CURRENT_DATE - 215, 'IN', 3, 1, 'ZAR', 1.00000000, 71127.50, 'INV-00010', 98, 99),
    -- PAY-00025 · Protea Print Works · pays INV-00011 (54625.00)
    (25, (CURRENT_DATE - 214 + time '11:40')::timestamptz, (CURRENT_DATE - 214 + time '11:40')::timestamptz, 2, 1, 'PAY-00025', CURRENT_DATE - 214, 'IN', 4, 1, 'ZAR', 1.00000000, 54625.00, 'INV-00011', 100, 101),
    -- PAY-00026 · Metro Property Management · pays BILL-00017 (25300.00)
    (26, (CURRENT_DATE - 211 + time '11:40')::timestamptz, (CURRENT_DATE - 211 + time '11:40')::timestamptz, 2, 1, 'PAY-00026', CURRENT_DATE - 211, 'OUT', 15, 1, 'ZAR', 1.00000000, 25300.00, 'BILL-00017', 103, 104),
    -- PAY-00027 · Cape Office Supplies (Pty) Ltd · pays BILL-00014 (2760.00)
    (27, (CURRENT_DATE - 210 + time '11:40')::timestamptz, (CURRENT_DATE - 210 + time '11:40')::timestamptz, 2, 1, 'PAY-00027', CURRENT_DATE - 210, 'OUT', 12, 1, 'ZAR', 1.00000000, 2760.00, 'BILL-00014', 106, 107),
    -- PAY-00028 · Highveld Fuel Services · pays BILL-00016 (3220.00)
    (28, (CURRENT_DATE - 203 + time '11:40')::timestamptz, (CURRENT_DATE - 203 + time '11:40')::timestamptz, 2, 1, 'PAY-00028', CURRENT_DATE - 203, 'OUT', 13, 1, 'ZAR', 1.00000000, 3220.00, 'BILL-00016', 109, 110),
    -- PAY-00029 · Karoo Fresh Produce (Pty) Ltd · pays INV-00012 (62272.50)
    (29, (CURRENT_DATE - 199 + time '11:40')::timestamptz, (CURRENT_DATE - 199 + time '11:40')::timestamptz, 2, 1, 'PAY-00029', CURRENT_DATE - 199, 'IN', 1, 1, 'ZAR', 1.00000000, 62272.50, 'INV-00012', 113, 114),
    -- PAY-00030 · Atlantic Cloud Hosting · pays BILL-00019 (4485.00)
    (30, (CURRENT_DATE - 190 + time '11:40')::timestamptz, (CURRENT_DATE - 190 + time '11:40')::timestamptz, 2, 1, 'PAY-00030', CURRENT_DATE - 190, 'OUT', 14, 1, 'ZAR', 1.00000000, 4485.00, 'BILL-00019', 118, 119),
    -- PAY-00031 · Table Bay Marine (Pty) Ltd · pays INV-00013 (63480.00)
    (31, (CURRENT_DATE - 184 + time '11:40')::timestamptz, (CURRENT_DATE - 184 + time '11:40')::timestamptz, 2, 1, 'PAY-00031', CURRENT_DATE - 184, 'IN', 3, 1, 'ZAR', 1.00000000, 63480.00, 'INV-00013', 122, 123),
    -- PAY-00032 · Halcyon Interiors CC · pays INV-00014 (56752.50)
    (32, (CURRENT_DATE - 183 + time '11:40')::timestamptz, (CURRENT_DATE - 183 + time '11:40')::timestamptz, 2, 1, 'PAY-00032', CURRENT_DATE - 183, 'IN', 2, 1, 'ZAR', 1.00000000, 56752.50, 'INV-00014', 124, 125),
    -- PAY-00033 · Metro Property Management · pays BILL-00021 (25300.00)
    (33, (CURRENT_DATE - 181 + time '11:40')::timestamptz, (CURRENT_DATE - 181 + time '11:40')::timestamptz, 2, 1, 'PAY-00033', CURRENT_DATE - 181, 'OUT', 15, 1, 'ZAR', 1.00000000, 25300.00, 'BILL-00021', 127, 128),
    -- PAY-00034 · Highveld Fuel Services · pays BILL-00020 (3220.00)
    (34, (CURRENT_DATE - 173 + time '11:40')::timestamptz, (CURRENT_DATE - 173 + time '11:40')::timestamptz, 2, 1, 'PAY-00034', CURRENT_DATE - 173, 'OUT', 13, 1, 'ZAR', 1.00000000, 3220.00, 'BILL-00020', 131, 132),
    -- PAY-00035 · Cape Office Supplies (Pty) Ltd · pays BILL-00018 (62100.00)
    (35, (CURRENT_DATE - 172 + time '11:40')::timestamptz, (CURRENT_DATE - 172 + time '11:40')::timestamptz, 2, 1, 'PAY-00035', CURRENT_DATE - 172, 'OUT', 12, 1, 'ZAR', 1.00000000, 62100.00, 'BILL-00018', 133, 134),
    -- PAY-00036 · Atlantic Cloud Hosting · pays BILL-00022 (4485.00)
    (36, (CURRENT_DATE - 160 + time '11:40')::timestamptz, (CURRENT_DATE - 160 + time '11:40')::timestamptz, 2, 1, 'PAY-00036', CURRENT_DATE - 160, 'OUT', 14, 1, 'ZAR', 1.00000000, 4485.00, 'BILL-00022', 139, 140),
    -- PAY-00037 · Karoo Fresh Produce (Pty) Ltd · pays INV-00015 (54625.00)
    (37, (CURRENT_DATE - 154 + time '11:40')::timestamptz, (CURRENT_DATE - 154 + time '11:40')::timestamptz, 2, 1, 'PAY-00037', CURRENT_DATE - 154, 'IN', 1, 1, 'ZAR', 1.00000000, 54625.00, 'INV-00015', 144, 145),
    -- PAY-00038 · Metro Property Management · pays BILL-00024 (25300.00)
    (38, (CURRENT_DATE - 151 + time '11:40')::timestamptz, (CURRENT_DATE - 151 + time '11:40')::timestamptz, 2, 1, 'PAY-00038', CURRENT_DATE - 151, 'OUT', 15, 1, 'ZAR', 1.00000000, 25300.00, 'BILL-00024', 147, 148),
    -- PAY-00039 · Highveld Fuel Services · pays BILL-00023 (3220.00)
    (39, (CURRENT_DATE - 143 + time '11:40')::timestamptz, (CURRENT_DATE - 143 + time '11:40')::timestamptz, 2, 1, 'PAY-00039', CURRENT_DATE - 143, 'OUT', 13, 1, 'ZAR', 1.00000000, 3220.00, 'BILL-00023', 152, 153),
    -- PAY-00040 · Halcyon Interiors CC · pays INV-00016 (86422.50)
    (40, (CURRENT_DATE - 139 + time '11:40')::timestamptz, (CURRENT_DATE - 139 + time '11:40')::timestamptz, 2, 1, 'PAY-00040', CURRENT_DATE - 139, 'IN', 2, 1, 'ZAR', 1.00000000, 86422.50, 'INV-00016', 157, 158),
    -- PAY-00041 · Atlantic Cloud Hosting · pays BILL-00026 (4485.00)
    (41, (CURRENT_DATE - 130 + time '11:40')::timestamptz, (CURRENT_DATE - 130 + time '11:40')::timestamptz, 2, 1, 'PAY-00041', CURRENT_DATE - 130, 'OUT', 14, 1, 'ZAR', 1.00000000, 4485.00, 'BILL-00026', 162, 163),
    -- PAY-00042 · Table Bay Marine (Pty) Ltd · pays INV-00017 (49105.00)
    (42, (CURRENT_DATE - 124 + time '11:40')::timestamptz, (CURRENT_DATE - 124 + time '11:40')::timestamptz, 2, 1, 'PAY-00042', CURRENT_DATE - 124, 'IN', 3, 1, 'ZAR', 1.00000000, 49105.00, 'INV-00017', 166, 167),
    -- PAY-00043 · Metro Property Management · pays BILL-00028 (25300.00)
    (43, (CURRENT_DATE - 121 + time '11:40')::timestamptz, (CURRENT_DATE - 121 + time '11:40')::timestamptz, 2, 1, 'PAY-00043', CURRENT_DATE - 121, 'OUT', 15, 1, 'ZAR', 1.00000000, 25300.00, 'BILL-00028', 169, 170),
    -- PAY-00044 · Cape Office Supplies (Pty) Ltd · pays BILL-00025 (2760.00)
    (44, (CURRENT_DATE - 120 + time '11:40')::timestamptz, (CURRENT_DATE - 120 + time '11:40')::timestamptz, 2, 1, 'PAY-00044', CURRENT_DATE - 120, 'OUT', 12, 1, 'ZAR', 1.00000000, 2760.00, 'BILL-00025', 172, 173),
    -- PAY-00045 · Highveld Fuel Services · pays BILL-00027 (3220.00)
    (45, (CURRENT_DATE - 113 + time '11:40')::timestamptz, (CURRENT_DATE - 113 + time '11:40')::timestamptz, 2, 1, 'PAY-00045', CURRENT_DATE - 113, 'OUT', 13, 1, 'ZAR', 1.00000000, 3220.00, 'BILL-00027', 175, 176),
    -- PAY-00046 · Atlantic Cloud Hosting · pays BILL-00029 (4485.00)
    (46, (CURRENT_DATE - 100 + time '11:40')::timestamptz, (CURRENT_DATE - 100 + time '11:40')::timestamptz, 2, 1, 'PAY-00046', CURRENT_DATE - 100, 'OUT', 14, 1, 'ZAR', 1.00000000, 4485.00, 'BILL-00029', 184, 185),
    -- PAY-00047 · Karoo Fresh Produce (Pty) Ltd · pays INV-00019 (69000.00)
    (47, (CURRENT_DATE - 94 + time '11:40')::timestamptz, (CURRENT_DATE - 94 + time '11:40')::timestamptz, 2, 1, 'PAY-00047', CURRENT_DATE - 94, 'IN', 1, 1, 'ZAR', 1.00000000, 69000.00, 'INV-00019', 192, 193),
    -- PAY-00048 · Metro Property Management · pays BILL-00032 (25300.00)
    (48, (CURRENT_DATE - 91 + time '11:40')::timestamptz, (CURRENT_DATE - 91 + time '11:40')::timestamptz, 2, 1, 'PAY-00048', CURRENT_DATE - 91, 'OUT', 15, 1, 'ZAR', 1.00000000, 25300.00, 'BILL-00032', 195, 196),
    -- PAY-00049 · Protea Print Works · pays INV-00018 (46977.50)
    (49, (CURRENT_DATE - 85 + time '11:40')::timestamptz, (CURRENT_DATE - 85 + time '11:40')::timestamptz, 2, 1, 'PAY-00049', CURRENT_DATE - 85, 'IN', 4, 1, 'ZAR', 1.00000000, 46977.50, 'INV-00018', 200, 201),
    -- PAY-00050 · Highveld Fuel Services · pays BILL-00031 (3220.00)
    (50, (CURRENT_DATE - 83 + time '11:40')::timestamptz, (CURRENT_DATE - 83 + time '11:40')::timestamptz, 2, 1, 'PAY-00050', CURRENT_DATE - 83, 'OUT', 13, 1, 'ZAR', 1.00000000, 3220.00, 'BILL-00031', 202, 203),
    -- PAY-00051 · Table Bay Marine (Pty) Ltd · pays INV-00020 (72047.50)
    (51, (CURRENT_DATE - 79 + time '11:40')::timestamptz, (CURRENT_DATE - 79 + time '11:40')::timestamptz, 2, 1, 'PAY-00051', CURRENT_DATE - 79, 'IN', 3, 1, 'ZAR', 1.00000000, 72047.50, 'INV-00020', 206, 207),
    -- PAY-00052 · Atlantic Cloud Hosting · pays BILL-00033 (4485.00)
    (52, (CURRENT_DATE - 70 + time '11:40')::timestamptz, (CURRENT_DATE - 70 + time '11:40')::timestamptz, 2, 1, 'PAY-00052', CURRENT_DATE - 70, 'OUT', 14, 1, 'ZAR', 1.00000000, 4485.00, 'BILL-00033', 212, 213),
    -- PAY-00053 · Coastal Stock Distributors · pays BILL-00030 (59225.00)
    (53, (CURRENT_DATE - 70 + time '11:40')::timestamptz, (CURRENT_DATE - 70 + time '11:40')::timestamptz, 2, 1, 'PAY-00053', CURRENT_DATE - 70, 'OUT', 16, 1, 'ZAR', 1.00000000, 59225.00, 'BILL-00030', 214, 215),
    -- PAY-00054 · Halcyon Interiors CC · pays INV-00022 (49105.00)
    (54, (CURRENT_DATE - 64 + time '11:40')::timestamptz, (CURRENT_DATE - 64 + time '11:40')::timestamptz, 2, 1, 'PAY-00054', CURRENT_DATE - 64, 'IN', 2, 1, 'ZAR', 1.00000000, 49105.00, 'INV-00022', 219, 220),
    -- PAY-00055 · Metro Property Management · pays BILL-00035 (25300.00)
    (55, (CURRENT_DATE - 61 + time '11:40')::timestamptz, (CURRENT_DATE - 61 + time '11:40')::timestamptz, 2, 1, 'PAY-00055', CURRENT_DATE - 61, 'OUT', 15, 1, 'ZAR', 1.00000000, 25300.00, 'BILL-00035', 222, 223),
    -- PAY-00056 · Highveld Fuel Services · pays BILL-00034 (3220.00)
    (56, (CURRENT_DATE - 53 + time '11:40')::timestamptz, (CURRENT_DATE - 53 + time '11:40')::timestamptz, 2, 1, 'PAY-00056', CURRENT_DATE - 53, 'OUT', 13, 1, 'ZAR', 1.00000000, 3220.00, 'BILL-00034', 228, 229),
    -- PAY-00057 · Table Bay Marine (Pty) Ltd · pays INV-00023 (71127.50)
    (57, (CURRENT_DATE - 49 + time '11:40')::timestamptz, (CURRENT_DATE - 49 + time '11:40')::timestamptz, 2, 1, 'PAY-00057', CURRENT_DATE - 49, 'IN', 3, 1, 'ZAR', 1.00000000, 71127.50, 'INV-00023', 233, 234),
    -- PAY-00058 · Atlantic Cloud Hosting · pays BILL-00037 (4485.00)
    (58, (CURRENT_DATE - 40 + time '11:40')::timestamptz, (CURRENT_DATE - 40 + time '11:40')::timestamptz, 2, 1, 'PAY-00058', CURRENT_DATE - 40, 'OUT', 14, 1, 'ZAR', 1.00000000, 4485.00, 'BILL-00037', 240, 241),
    -- PAY-00059 · Halcyon Interiors CC · pays INV-00026 (30000.00)
    (59, (CURRENT_DATE - 35 + time '11:40')::timestamptz, (CURRENT_DATE - 35 + time '11:40')::timestamptz, 2, 1, 'PAY-00059', CURRENT_DATE - 35, 'IN', 2, 1, 'ZAR', 1.00000000, 30000.00, 'INV-00026', 245, 246),
    -- PAY-00060 · Protea Print Works · pays INV-00025 (54625.00)
    (60, (CURRENT_DATE - 34 + time '11:40')::timestamptz, (CURRENT_DATE - 34 + time '11:40')::timestamptz, 2, 1, 'PAY-00060', CURRENT_DATE - 34, 'IN', 4, 1, 'ZAR', 1.00000000, 54625.00, 'INV-00025', 247, 248),
    -- PAY-00061 · Metro Property Management · pays BILL-00040 (25300.00)
    (61, (CURRENT_DATE - 31 + time '11:40')::timestamptz, (CURRENT_DATE - 31 + time '11:40')::timestamptz, 2, 1, 'PAY-00061', CURRENT_DATE - 31, 'OUT', 15, 1, 'ZAR', 1.00000000, 25300.00, 'BILL-00040', 251, 252),
    -- PAY-00062 · Lerato Molefe · pays INV-00029 (8740.00)
    (62, (CURRENT_DATE - 28 + time '11:40')::timestamptz, (CURRENT_DATE - 28 + time '11:40')::timestamptz, 2, 1, 'PAY-00062', CURRENT_DATE - 28, 'IN', 5, 1, 'ZAR', 1.00000000, 8740.00, 'INV-00029', 259, 260),
    -- PAY-00063 · Highveld Fuel Services · pays BILL-00039 (3220.00) · no reference: the oldest bill first
    (63, (CURRENT_DATE - 26 + time '11:40')::timestamptz, (CURRENT_DATE - 26 + time '11:40')::timestamptz, 2, 1, 'PAY-00063', CURRENT_DATE - 26, 'OUT', 13, 1, 'ZAR', 1.00000000, 3220.00, '', 261, 262),
    -- PAY-00064 · Highveld Fuel Services · pays BILL-00041 (1000.00)
    (64, (CURRENT_DATE - 20 + time '11:40')::timestamptz, (CURRENT_DATE - 20 + time '11:40')::timestamptz, 2, 1, 'PAY-00064', CURRENT_DATE - 20, 'OUT', 13, 1, 'ZAR', 1.00000000, 1000.00, 'BILL-00041', 268, 269),
    -- PAY-00065 · Halcyon Interiors CC · pays INV-00031 (21850.00)
    (65, (CURRENT_DATE - 8 + time '11:40')::timestamptz, (CURRENT_DATE - 8 + time '11:40')::timestamptz, 2, 1, 'PAY-00065', CURRENT_DATE - 8, 'IN', 2, 1, 'ZAR', 1.00000000, 21850.00, 'INV-00031', 277, 278),
    -- PAY-00066 · Protea Print Works · pays INV-00032 (13110.00)
    (66, (CURRENT_DATE - 4 + time '11:40')::timestamptz, (CURRENT_DATE - 4 + time '11:40')::timestamptz, 2, 1, 'PAY-00066', CURRENT_DATE - 4, 'IN', 4, 1, 'ZAR', 1.00000000, 13110.00, 'INV-00032', 281, 282),
    -- PAY-00067 · Metro Property Management · pays BILL-00045 (25300.00)
    (67, (CURRENT_DATE - 1 + time '11:40')::timestamptz, (CURRENT_DATE - 1 + time '11:40')::timestamptz, 2, 1, 'PAY-00067', CURRENT_DATE - 1, 'OUT', 15, 1, 'ZAR', 1.00000000, 25300.00, 'BILL-00045', 286, 287);

INSERT INTO accounting_paymentallocation (id, payment_id, document_id, amount) VALUES
    (1, 1, 1, 53705.00),
    (2, 2, 2, 56752.50),
    (3, 3, 5, 4485.00),
    (4, 4, 3, 64400.00),
    (5, 5, 7, 25300.00),
    (6, 6, 6, 3220.00),
    (7, 7, 4, 76647.50),
    (8, 8, 11, 4485.00),
    (9, 9, 8, 39330.00),
    (10, 10, 13, 25300.00),
    (11, 11, 9, 2760.00),
    (12, 12, 12, 3220.00),
    (13, 13, 10, 56752.50),
    (14, 14, 16, 4485.00),
    (15, 15, 14, 78775.00),
    (16, 16, 18, 25300.00),
    (17, 17, 17, 3220.00),
    (18, 18, 15, 62272.50),
    (19, 19, 21, 4485.00),
    (20, 20, 19, 49105.00),
    (21, 21, 23, 25300.00),
    (22, 22, 22, 3220.00),
    (23, 23, 27, 4485.00),
    (24, 24, 20, 71127.50),
    (25, 25, 24, 54625.00),
    (26, 26, 29, 25300.00),
    (27, 27, 25, 2760.00),
    (28, 28, 28, 3220.00),
    (29, 29, 26, 62272.50),
    (30, 30, 33, 4485.00),
    (31, 31, 30, 63480.00),
    (32, 32, 32, 56752.50),
    (33, 33, 35, 25300.00),
    (34, 34, 34, 3220.00),
    (35, 35, 31, 62100.00),
    (36, 36, 38, 4485.00),
    (37, 37, 36, 54625.00),
    (38, 38, 40, 25300.00),
    (39, 39, 39, 3220.00),
    (40, 40, 37, 86422.50),
    (41, 41, 44, 4485.00),
    (42, 42, 41, 49105.00),
    (43, 43, 46, 25300.00),
    (44, 44, 42, 2760.00),
    (45, 45, 45, 3220.00),
    (46, 46, 49, 4485.00),
    (47, 47, 47, 69000.00),
    (48, 48, 53, 25300.00),
    (49, 49, 43, 46977.50),
    (50, 50, 51, 3220.00),
    (51, 51, 48, 72047.50),
    (52, 52, 56, 4485.00),
    (53, 53, 50, 59225.00),
    (54, 54, 54, 49105.00),
    (55, 55, 60, 25300.00),
    (56, 56, 59, 3220.00),
    (57, 57, 55, 71127.50),
    (58, 58, 65, 4485.00),
    (59, 59, 62, 30000.00),
    (60, 60, 61, 54625.00),
    (61, 61, 69, 25300.00),
    (62, 62, 70, 8740.00),
    (63, 63, 68, 3220.00),
    (64, 64, 71, 1000.00),
    (65, 65, 73, 21850.00),
    (66, 66, 76, 13110.00),
    (67, 67, 81, 25300.00);

INSERT INTO accounting_payment_files (payment_id, storedfile_id) VALUES
    (11, '3733b825-7fcd-4d7e-8d4b-5f0b53f04d04');

-- ____________________________________________________________________________
-- Fixed assets, depreciation and stock movements

INSERT INTO accounting_fixedasset (id, created_at, updated_at, created_by_id, company_id, code, name, purchase_date, cost, residual_value, useful_life_months, method, asset_account_id, accumulated_account_id, expense_account_id, disposal_date, disposal_amount) VALUES
    (1, (CURRENT_DATE - 200 + time '09:00')::timestamptz, (CURRENT_DATE - 90 + time '09:00')::timestamptz, 1, 1, 'FA-001', 'Laptops (3)', CURRENT_DATE - 200, 54000.00, 0.00, 36, 'SL', 7, 8, 30, NULL, NULL),
    (2, (CURRENT_DATE - 150 + time '09:00')::timestamptz, (CURRENT_DATE - 90 + time '09:00')::timestamptz, 1, 1, 'FA-002', 'Delivery vehicle', CURRENT_DATE - 150, 420000.00, 60000.00, 60, 'SL', 9, 10, 30, NULL, NULL),
    (3, (CURRENT_DATE - 420 + time '09:00')::timestamptz, (CURRENT_DATE - 90 + time '09:00')::timestamptz, 1, 1, 'FA-003', 'Laser printer', CURRENT_DATE - 1500, 8000.00, 500.00, 48, 'RB', 7, 8, 30, CURRENT_DATE - 90, 500.00);

INSERT INTO accounting_depreciationschedule (id, asset_id, period_id, amount, posted, journal_entry_id) VALUES
    (1, 1, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '4 month' - interval '1 day')::date), 1500.00, TRUE, 288),
    (2, 1, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '3 month' - interval '1 day')::date), 1500.00, TRUE, 289),
    (3, 1, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '2 month' - interval '1 day')::date), 1500.00, TRUE, 290),
    (4, 1, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '1 month' - interval '1 day')::date), 1500.00, TRUE, 291),
    (5, 1, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '0 month' - interval '1 day')::date), 1500.00, TRUE, 292),
    (6, 1, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '-1 month' - interval '1 day')::date), 1500.00, FALSE, NULL),
    (7, 1, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '-2 month' - interval '1 day')::date), 1500.00, FALSE, NULL),
    (8, 2, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '3 month' - interval '1 day')::date), 6000.00, TRUE, 293),
    (9, 2, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '2 month' - interval '1 day')::date), 6000.00, TRUE, 294),
    (10, 2, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '1 month' - interval '1 day')::date), 6000.00, TRUE, 295),
    (11, 2, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '0 month' - interval '1 day')::date), 6000.00, TRUE, 296),
    (12, 2, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '-1 month' - interval '1 day')::date), 6000.00, FALSE, NULL),
    (13, 2, pg_temp.period_of((date_trunc('month', CURRENT_DATE) - interval '-2 month' - interval '1 day')::date), 6000.00, FALSE, NULL);

INSERT INTO accounting_stockmovement (id, company_id, item_id, date, direction, quantity, unit_cost, total_cost, method, journal_entry_id) VALUES
    (1, 1, 1, CURRENT_DATE - 100, 'IN', 20.0000, 2100.0000, 42000.00, 'AVG', 182),
    (2, 1, 2, CURRENT_DATE - 100, 'IN', 100.0000, 95.0000, 9500.00, 'FIFO', 182),
    (3, 1, 2, CURRENT_DATE - 95, 'OUT', 30.0000, 95.0000, 2850.00, 'FIFO', 191),
    (4, 1, 1, CURRENT_DATE - 70, 'OUT', 4.0000, 2100.0000, 8400.00, 'AVG', 216),
    (5, 1, 1, CURRENT_DATE - 40, 'OUT', 6.0000, 2100.0000, 12600.00, 'AVG', 243),
    (6, 1, 2, CURRENT_DATE - 40, 'OUT', 40.0000, 95.0000, 3800.00, 'FIFO', 243),
    (7, 1, 2, CURRENT_DATE - 15, 'ADJ', -2.0000, 95.0000, -190.00, 'FIFO', 272);

-- ____________________________________________________________________________
-- Bank statement lines, recurring invoices, notes, the audit trail and the number sequences

INSERT INTO accounting_banktransaction (id, company_id, bank_account_id, date, description, amount, external_id, reconciled, payment_id, journal_entry_id, source_id) VALUES
    (1, 1, 1, CURRENT_DATE - 40, 'Bank charges', -245.00, 'FNB-00001', TRUE, NULL, 237, 1),
    (2, 1, 1, CURRENT_DATE - 40, 'Atlantic Cloud Hosting', -4485.00, 'FNB-00002', TRUE, 58, NULL, 1),
    (3, 1, 1, CURRENT_DATE - 40, 'VAT return paid', -35130.00, 'FNB-00003', TRUE, NULL, 242, 1),
    (4, 1, 1, CURRENT_DATE - 35, 'Salaries for the month', -43160.00, 'FNB-00004', TRUE, NULL, 244, 1),
    (5, 1, 1, CURRENT_DATE - 35, 'Halcyon Interiors CC', 30000.00, 'FNB-00005', TRUE, 59, NULL, 1),
    (6, 1, 1, CURRENT_DATE - 34, 'Protea Print Works', 54625.00, 'FNB-00006', TRUE, 60, NULL, 1),
    (7, 1, 1, CURRENT_DATE - 31, 'Metro Property Management', -25300.00, 'FNB-00007', TRUE, 61, NULL, 1),
    (8, 1, 1, CURRENT_DATE - 30, 'Credit card statement paid', -1437.50, 'FNB-00008', TRUE, NULL, 253, 1),
    (9, 1, 1, CURRENT_DATE - 28, 'PAYE paid', -8840.00, 'FNB-00009', TRUE, NULL, 257, 1),
    (10, 1, 1, CURRENT_DATE - 28, 'Lerato Molefe', 8740.00, 'FNB-00010', TRUE, 62, NULL, 1),
    (11, 1, 1, CURRENT_DATE - 26, 'Highveld Fuel Services', -3220.00, 'FNB-00011', TRUE, 63, NULL, 1),
    (12, 1, 1, CURRENT_DATE - 20, 'Vehicle finance instalment', -7500.00, 'FNB-00012', TRUE, NULL, 265, 1),
    (13, 1, 1, CURRENT_DATE - 20, 'Highveld Fuel Services', -1000.00, 'FNB-00013', TRUE, 64, NULL, 1),
    (14, 1, 1, CURRENT_DATE - 10, 'Bank charges', -245.00, 'FNB-00014', TRUE, NULL, 274, 1),
    (15, 1, 1, CURRENT_DATE - 8, 'Halcyon Interiors CC', 21850.00, 'FNB-00015', TRUE, 65, NULL, 1),
    (16, 1, 1, CURRENT_DATE - 5, 'Salaries for the month', -43160.00, 'FNB-00016', FALSE, NULL, 280, 1),
    (17, 1, 1, CURRENT_DATE - 4, 'Protea Print Works', 13110.00, 'FNB-00017', FALSE, 66, NULL, 1),
    (18, 1, 1, CURRENT_DATE - 2, 'Deposit — reference unknown', 1250.00, 'FNB-00018', FALSE, NULL, NULL, 1),
    (19, 1, 1, CURRENT_DATE - 1, 'Metro Property Management', -25300.00, 'FNB-00019', FALSE, 67, NULL, 1),
    (20, 1, 1, CURRENT_DATE - 1, 'Debit order — MOBILE CONTRACT', -899.00, 'FNB-00020', FALSE, NULL, NULL, 1);

INSERT INTO accounting_recurringinvoice (id, created_at, updated_at, created_by_id, company_id, name, customer_id, template_id, frequency, next_run, end_date, is_active) VALUES
    (1, (CURRENT_DATE - 25 + time '09:00')::timestamptz, (CURRENT_DATE - 25 + time '09:00')::timestamptz, 1, 1, 'Monthly support retainer', 3, 72, 'M', CURRENT_DATE + 5, CURRENT_DATE + 365, TRUE),
    (2, (CURRENT_DATE - 25 + time '09:00')::timestamptz, (CURRENT_DATE - 10 + time '09:00')::timestamptz, 1, 1, 'Quarterly review', 1, 8, 'Q', CURRENT_DATE - 10, CURRENT_DATE - 10, FALSE);

INSERT INTO accounting_note (id, created_at, updated_at, created_by_id, company_id, kind, visibility, page, range_start, range_end, title, body, expires_on, is_permanent) VALUES
    (1, (CURRENT_DATE - 2 + time '14:00')::timestamptz, (CURRENT_DATE - 2 + time '14:00')::timestamptz, 2, 1, 'C', 'P', 'accounting:balancesheet', make_date(extract(year from CURRENT_DATE - interval '2 month')::int, 3, 1), (make_date(extract(year from CURRENT_DATE - interval '2 month')::int, 3, 1) + interval '1 year' - interval '1 day')::date, 'Vehicle finance', '<p>The vehicle loan runs for <strong>48 more months</strong>. The bank sends the statement on the 1st.</p>', CURRENT_DATE + 30, FALSE),
    (2, (CURRENT_DATE - 2 + time '14:00')::timestamptz, (CURRENT_DATE - 2 + time '14:00')::timestamptz, 1, 1, 'F', 'P', 'accounting:incomestatement', make_date(extract(year from CURRENT_DATE - interval '2 month')::int, 3, 1), (make_date(extract(year from CURRENT_DATE - interval '2 month')::int, 3, 1) + interval '1 year' - interval '1 day')::date, 'Revenue recognition', '<p>Revenue is recognised when the invoice is issued. Support retainers are invoiced monthly.</p>', CURRENT_DATE + 365, TRUE),
    (3, (CURRENT_DATE - 2 + time '14:00')::timestamptz, (CURRENT_DATE - 2 + time '14:00')::timestamptz, 1, 1, 'C', 'I', 'accounting:bills', make_date(extract(year from CURRENT_DATE - interval '2 month')::int, 3, 1), (make_date(extract(year from CURRENT_DATE - interval '2 month')::int, 3, 1) + interval '1 year' - interval '1 day')::date, 'Check the chair quote', '<p>The supplier quoted R 2 300 a chair. Check the bill before you approve it.</p>', CURRENT_DATE + 14, FALSE),
    (4, (CURRENT_DATE - 2 + time '14:00')::timestamptz, (CURRENT_DATE - 2 + time '14:00')::timestamptz, 2, 1, 'C', 'P', 'accounting:dashboard', make_date(extract(year from CURRENT_DATE - interval '2 month')::int, 3, 1), (make_date(extract(year from CURRENT_DATE - interval '2 month')::int, 3, 1) + interval '1 year' - interval '1 day')::date, 'Month-end close', '<p>Accept the draft entries and reconcile the bank before the 5th.</p>', CURRENT_DATE + 7, FALSE),
    (5, (CURRENT_DATE - 40 + time '14:00')::timestamptz, (CURRENT_DATE - 2 + time '14:00')::timestamptz, 2, 1, 'C', 'P', 'accounting:journals', make_date(extract(year from CURRENT_DATE - interval '2 month')::int, 3, 1), (make_date(extract(year from CURRENT_DATE - interval '2 month')::int, 3, 1) + interval '1 year' - interval '1 day')::date, 'Old reminder', '<p>This note expired. It does not show.</p>', CURRENT_DATE - 3, FALSE);

INSERT INTO accounting_note_files (note_id, storedfile_id) VALUES
    (3, '3733b825-7fcd-4d7e-8d4b-5f0b53f04d04');

INSERT INTO accounting_auditlog (id, company_id, content_type_id, object_id, action, user_id, timestamp, changes) VALUES
    (1, 1, pg_temp.ct('accounting', 'supplier'), 2, 'U', 2, (CURRENT_DATE - 28 + time '10:00')::timestamptz, '{}'::jsonb),
    (2, 1, pg_temp.ct('accounting', 'document'), 74, 'C', 2, (CURRENT_DATE - 18 + time '09:30')::timestamptz, '{}'::jsonb),
    (3, 1, pg_temp.ct('accounting', 'account'), 16, 'C', 1, (CURRENT_DATE - 12 + time '09:10')::timestamptz, '{}'::jsonb),
    (4, 1, pg_temp.ct('accounting', 'document'), 77, 'P', 1, (CURRENT_DATE - 10 + time '15:30')::timestamptz, '{}'::jsonb),
    (5, 1, pg_temp.ct('accounting', 'document'), 78, 'C', 1, (CURRENT_DATE - 9 + time '11:00')::timestamptz, '{}'::jsonb),
    (6, 1, pg_temp.ct('accounting', 'payment'), 65, 'C', 2, (CURRENT_DATE - 8 + time '11:40')::timestamptz, '{}'::jsonb),
    (7, 1, pg_temp.ct('accounting', 'document'), 73, 'U', 2, (CURRENT_DATE - 8 + time '11:41')::timestamptz, '{}'::jsonb),
    (8, 1, pg_temp.ct('accounting', 'journalentry'), 277, 'P', 1, (CURRENT_DATE - 7 + time '08:45')::timestamptz, '{}'::jsonb),
    (9, 1, pg_temp.ct('accounting', 'journalentry'), 279, 'V', 1, (CURRENT_DATE - 6 + time '16:05')::timestamptz, '{}'::jsonb),
    (10, 1, pg_temp.ct('accounting', 'payment'), 66, 'C', 2, (CURRENT_DATE - 4 + time '11:40')::timestamptz, '{}'::jsonb),
    (11, 1, pg_temp.ct('accounting', 'document'), 76, 'U', 2, (CURRENT_DATE - 4 + time '11:41')::timestamptz, '{}'::jsonb),
    (12, 1, pg_temp.ct('accounting', 'document'), 79, 'C', 1, (CURRENT_DATE - 3 + time '10:15')::timestamptz, '{}'::jsonb),
    (13, 1, pg_temp.ct('accounting', 'document'), 80, 'C', 2, (CURRENT_DATE - 2 + time '10:00')::timestamptz, '{}'::jsonb),
    (14, 1, pg_temp.ct('accounting', 'note'), 3, 'C', 1, (CURRENT_DATE - 2 + time '14:00')::timestamptz, '{}'::jsonb),
    (15, 1, pg_temp.ct('accounting', 'journalentry'), 285, 'C', 2, (CURRENT_DATE - 1 + time '16:20')::timestamptz, '{}'::jsonb);

INSERT INTO accounting_numbersequence (id, company_id, name, prefix, next_number, padding) VALUES
    (1, 1, 'invoice', 'INV-', 34, 5),
    (2, 1, 'payment', 'PAY-', 68, 5),
    (3, 1, 'bill', 'BILL-', 46, 5),
    (4, 1, 'quote', 'QUO-', 3, 5),
    (5, 1, 'statement', 'STM-', 1, 5),
    (6, 1, 'supplier', 'SUP-', 6, 5);

-- The budget of the current financial year: one line for each account and each month.
INSERT INTO accounting_budget (id, company_id, name, fiscal_year_id, is_active)
SELECT 1, 1, 'Operating budget', id, TRUE FROM accounting_fiscalyear WHERE start_date = make_date(extract(year from CURRENT_DATE - interval '2 month')::int, 3, 1);

INSERT INTO accounting_budgetline (budget_id, account_id, period_id, cost_centre_id, amount)
SELECT 1, line.account_id, p.id, line.cost_centre_id, line.amount
FROM accounting_period AS p
JOIN accounting_budget AS b ON b.fiscal_year_id = p.fiscal_year_id AND b.id = 1
CROSS JOIN (VALUES
    (21, NULL, 120000.00),
    (24, 3, 52000.00),
    (25, 3, 22000.00),
    (28, 2, 4500.00),
    (27, 2, 3500.00)
) AS line (account_id, cost_centre_id, amount)
ORDER BY p.start_date, line.account_id;

-- ____________________________________________________________________________
-- The identity sequences continue after the rows of the seed.

DO $$
DECLARE name text;
BEGIN
    FOREACH name IN ARRAY ARRAY[
        'accounting_account',
        'accounting_attachment',
        'accounting_auditlog',
        'accounting_bankaccount',
        'accounting_banktransaction',
        'accounting_budget',
        'accounting_costcentre',
        'accounting_depreciationschedule',
        'accounting_document',
        'accounting_documentline',
        'accounting_fiscalyear',
        'accounting_fixedasset',
        'accounting_journalentry',
        'accounting_journalline',
        'accounting_lead',
        'accounting_note',
        'accounting_numbersequence',
        'accounting_payment',
        'accounting_paymentallocation',
        'accounting_recurringinvoice',
        'accounting_service',
        'accounting_stockmovement',
        'accounting_supplier',
        'accounting_taxcode',
        'auth_user',
        'inventory_item',
        'inventory_itemrelationship',
        'inventory_stocktakeschedule',
        'shared_businessrole',
        'shared_company',
        'shared_entity',
        'shared_exchangerate',
        'shared_industry',
        'shared_membership',
        'shared_project',
        'shared_source',
        'shared_title'
    ] LOOP
        EXECUTE format('SELECT setval(pg_get_serial_sequence(%L, ''id''), COALESCE((SELECT MAX(id) FROM %I), 0) + 1, false)', name, name);
    END LOOP;
END $$;

COMMIT;