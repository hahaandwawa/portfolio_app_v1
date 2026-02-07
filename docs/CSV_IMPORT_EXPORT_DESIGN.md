# CSV Import/Export — Design

## 1. Overview

- **Import:** Bulk create transactions from one CSV file. Missing accounts are **auto-created** (Option A).
- **Export:** Download existing transactions as CSV (optional account filter).
- **Template:** Provide a **downloadable template CSV** (header + optional example rows) so users can fill and import.

Single CSV only; accounts inferred from `account_name`; cash = CASH_DEPOSIT / CASH_WITHDRAW. Out of scope: separate account/target CSVs, upsert/update-by-id.

---

## 2. CSV Format

- **Encoding:** UTF-8 (strip BOM on import).
- **Structure:** Header row, then one row per transaction. Delimiter: comma; standard CSV quoting.

| Column         | Required | Notes |
|----------------|----------|--------|
| `account_name` | Yes      | Auto-create account if missing. |
| `txn_type`     | Yes      | `BUY` \| `SELL` \| `CASH_DEPOSIT` \| `CASH_WITHDRAW` (case-insensitive OK). |
| `txn_time_est` | Yes      | `YYYY-MM-DDTHH:MM:SS` or `YYYY-MM-DD HH:MM:SS` (date-only acceptable). |
| `symbol`       | BUY/SELL | Empty for cash. Uppercase on import. |
| `quantity`     | BUY/SELL | > 0. |
| `price`        | BUY/SELL | >= 0. |
| `cash_amount`  | CASH_*   | > 0. Empty for BUY/SELL. |
| `fees`         | No       | Default 0, >= 0. |
| `note`         | No       | Optional. |

**Export column order:** `account_name,txn_type,txn_time_est,symbol,quantity,price,cash_amount,fees,note`

---

## 3. Account Handling on Import

Collect distinct `account_name` from parsed rows. For each, if account does not exist, create it (e.g. `AccountService.create_account`). Then create all transactions via `create_batch_transaction`.

---

## 4. API

| Method | Endpoint | Purpose |
|--------|----------|--------|
| POST   | `/transactions/import` | Body: `multipart/form-data` with `file`. Response: `201` `{ "imported", "accounts_created", "errors" }`. Choose strict (4xx on any error) or best-effort (partial import + errors). |
| GET    | `/transactions/export` | Query: optional `account` (repeatable). Response: `200`, `Content-Type: text/csv`, `Content-Disposition: attachment; filename="transactions.csv"`. |
| GET    | `/transactions/export?template=1` **or** `GET /transactions/template` | Response: CSV with **header only** (or header + one example row per txn_type). Same columns as export. Filename e.g. `transactions_template.csv`. |

---

## 5. Backend

- **New:** `src/service/csv_transaction.py` — parse CSV → list of row dicts → map to `TransactionCreate`; serialize transactions → CSV. UTF-8, header validation, date parsing.
- **Router** (in `transactions.py` or new router): `POST /transactions/import`, `GET /transactions/export`, and template endpoint (return header-only or header+example CSV using same serialization).
- **main.py:** Mount router if new file.
- **account_service:** Used in import to create missing accounts. No schema change.
- **Dependencies:** stdlib `csv` only.

---

## 6. Frontend

- **client.ts:** `importTransactionsCsv(file)`, `exportTransactionsCsv(params?)`, `downloadTransactionsTemplate()` (GET template → trigger download).
- **UI:** “Import CSV” (file input + result summary), “Export CSV” (download), **“Download template”** (download template CSV).
- **types:** Optional `TransactionImportResult` for import response.

---

## 7. Validation

UTF-8; validate required columns; empty file → clear error or `imported: 0`. Normalize `txn_type`; reject invalid dates/numbers. Optional: max rows per import (e.g. 10,000).

---

## 8. Implementation Order

1. CSV module: parse + serialize in `csv_transaction.py`.
2. Import endpoint + Option A (auto-create accounts).
3. Export endpoint + **template endpoint** (same CSV format, header-only or with example rows).
4. Frontend: API + UI for import, export, and **template download**.
