-- Run in BigQuery after creating dataset `finance` (location: US)
-- Running on 11/6/2026:

CREATE TABLE `ranchcash-financetracker.finance.accounts` (
  account_id STRING PRIMARY KEY,
  official_name STRING,
  name STRING,
  type STRING,
  subtype STRING,
  mask STRING,
  last_synced_at TIMESTAMP
);

CREATE TABLE `ranchcash-financetracker.finance.transactions` (
  transaction_id STRING PRIMARY KEY,
  account_id STRING,
  amount NUMERIC,
  date DATE, -- posted date (or occurred date if pending)
  authorized_date DATE, -- day of swipe, when Plaid provides it
  merchant_name STRING,
  name STRING,
  website STRING,
  category_primary STRING, --pulling from 'personal_finance_category' object
  category_detailed STRING, --pulling from 'personal_finance_category' object
  pending BOOL,
  iso_currency_code STRING,
  created_at TIMESTAMP
)
PARTITION BY date;

CREATE TABLE `ranchcash-financetracker.finance.sync_log` (
  sync_id STRING PRIMARY KEY,
  run_at TIMESTAMP,
  transactions_pulled INT64,
  status STRING,
  next_cursor STRING
);


-- Future tables/views

CREATE TABLE `ranchcash-financetracker.finance.vendor_map` (
  merchant_name STRING PRIMARY KEY,
  my_category STRING
);

CREATE VIEW `ranchcash-financetracker.finance.v_transactions` AS
SELECT
  t.*,
  COALESCE(t.authorized_date, t.date) AS swipe_date,
  COALESCE(v.my_category, t.category_primary) AS category
FROM `ranchcash-financetracker.finance.transactions` t
LEFT JOIN `ranchcash-financetracker.finance.vendor_map` v USING (merchant_name);
