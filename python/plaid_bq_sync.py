"""Plaid -> BigQuery. Pulls full history via /transactions/sync and overwrites the tables each run."""

import os, json, datetime as dt
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from google.cloud import bigquery

D = "ranchcash-financetracker.finances"
api = plaid_api.PlaidApi(plaid.ApiClient(plaid.Configuration(
    host=getattr(plaid.Environment, os.environ.get("PLAID_ENV", "Sandbox")),
    api_key={"clientId": os.environ["PLAID_CLIENT_ID"], "secret": os.environ["PLAID_SECRET"]})))
bq = bigquery.Client()
now = dt.datetime.now(dt.timezone.utc).isoformat()

# Empty cursor = full history. has_more pages through it; no cursor stored, we overwrite each run.
txs, cursor, more = [], "", True
while more:
    kw = {"cursor": cursor} if cursor else {}
    r = json.loads(json.dumps(api.transactions_sync(TransactionsSyncRequest(
        access_token=os.environ["PLAID_ACCESS_TOKEN"], count=500, **kw)).to_dict(), default=str))
    txs += r["added"]
    cursor, more = r["next_cursor"], r["has_more"]

rows = [{"transaction_id": t["transaction_id"], "account_id": t["account_id"], "amount": t["amount"],
         "date": t["date"], "authorized_date": t.get("authorized_date"),
         "merchant_name": t.get("merchant_name"), "name": t.get("name"), "website": t.get("website"),
         "category_primary": (t.get("personal_finance_category") or {}).get("primary"),
         "category_detailed": (t.get("personal_finance_category") or {}).get("detailed"),
         "pending": t["pending"], "iso_currency_code": t.get("iso_currency_code"),
         "created_at": now} for t in txs]
accts = [{**{k: a.get(k) for k in ("account_id", "official_name", "name", "type", "subtype", "mask")},
          "last_synced_at": now} for a in r["accounts"]]

def load(table, data, mode):
    bq.load_table_from_json(data, f"{D}.{table}", job_config=bigquery.LoadJobConfig(write_disposition=mode)).result()

load("transactions", rows, "WRITE_TRUNCATE")
load("accounts", accts, "WRITE_TRUNCATE")
load("sync_log", [{"sync_id": now, "run_at": now, "transactions_pulled": len(rows), "status": "ok"}], "WRITE_APPEND")
print(f"{len(rows)} transactions, {len(accts)} accounts")
