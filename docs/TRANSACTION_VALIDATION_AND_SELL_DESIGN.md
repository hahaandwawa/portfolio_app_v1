# Transaction Validation & Sell Enhancements — Design Document

## 1. Overview

**Goal:** Improve the add-transaction flow with three behaviors:

1. **Symbol validation** — Reject invalid stock symbols using Yahoo Finance; show a clear error to the user.
2. **Sell validation** — Reject sell transactions when the user does not hold the stock or has insufficient quantity in the chosen account.
3. **Sell cash destination** — For sells, let the user choose which account receives the sale proceeds; default to the account that holds the most of that symbol.

This document is for engineers to verify logic and implement where needed.

---

## 2. Current State (Summary)

- **Transactions:** BUY/SELL have `account_name`, `symbol`, `quantity`, `price`; cash movements use `cash_amount`. No `cash_destination_account`.
- **Portfolio:** `GET /portfolio` returns aggregated positions (one row per symbol across selected accounts) and per-account cash. There is **no** per-account per-symbol position data exposed.
- **Quotes:** `QuoteService` (yfinance) already fetches `current_price` and `display_name` per symbol; invalid or failed lookups return `current_price: None` and `display_name: symbol`.
- **Transaction service:** `_validate_transaction_create` has TODOs for (1) validating symbol and (2) validating sufficient shares for SELL. No sell cash-destination field.

---

## 3. Feature 1: Symbol Validation

### 3.1 Behavior

- When the user enters a **stock symbol** (BUY or SELL), the system must treat it as **invalid** if Yahoo Finance does not recognize it.
- Invalid symbols must **not** be accepted on create (and optionally on edit). The user must see an explicit error (e.g. “Invalid symbol: XYZ” or “Symbol not found”).
- Validation must happen **server-side** on create/edit; client-side validation (e.g. on blur or before submit) is optional and must not replace server checks.

### 3.2 Definition of “Valid”

- Use the existing **Yahoo Finance** integration (`QuoteService` / yfinance).
- Consider a symbol **valid** if we get usable data: e.g. either a **current price** or a **recognizable display name** (longName/shortName) from Yahoo. Symbols that return no price and no proper name (or that yfinance does not return at all) are **invalid**.
- Implementation detail: Reuse `QuoteService.get_quotes([symbol])`. If `current_price` is not None, treat as valid. If `current_price` is None, treat as valid only if `display_name` is present and differs from the raw symbol (e.g. expanded company name). Otherwise treat as invalid. Engineers may refine (e.g. handle rate limits, timeouts) as long as invalid symbols are rejected and a clear error is returned.

### 3.3 API / Integration

- **Option A (recommended):** Validate inside `TransactionService._validate_transaction_create` (and edit path) for BUY/SELL: inject or resolve `QuoteService`, call `get_quotes([normalized_symbol])`, apply the rule above; if invalid, raise `ValidationError("Invalid symbol: SYMBOL"` or similar).
- **Option B:** Add a dedicated endpoint e.g. `GET /symbols/validate?symbol=AAPL` that returns `{ "valid": true, "display_name": "Apple Inc." }` or `{ "valid": false }`. Frontend can call on blur for immediate feedback; backend **must still** validate again on POST/PUT.

### 3.4 Error Handling

- On invalid symbol: HTTP 400 with a clear `detail` message (e.g. “Invalid or unknown symbol: XYZ”). Frontend should display this message and prevent submit until the user changes the symbol or confirms.

---

## 4. Feature 2: Sell Validation (Sufficient Holdings)

### 4.1 Behavior

- For a **SELL** transaction:
  - The **account** (`account_name`) is the **source account** (the account from which shares are debited).
  - The system must **reject** the transaction if:
    - The user **does not hold** that `symbol` in that account (position in that account is zero or missing), or
    - The user holds **less than** the sell `quantity` in that account.

### 4.2 Per-Account Position Quantity

- Today, portfolio is computed **aggregated** by symbol across accounts; there is no API that returns “quantity of symbol X in account Y”.
- To validate sells, the backend needs **per-account, per-symbol quantity** (or at least quantity for the single account used in the sell).
- **Approach:** Reuse the same cash/position logic as `PortfolioService.get_summary`, but run it **per account** (or with a single account filter) and expose **positions per account** for the symbol in question.
  - **Option A:** Extend `PortfolioService` with a method such as `get_positions_by_account(account_names=None)` that returns a structure like `[{ "account_name": "A", "symbol": "AAPL", "quantity": 10 }, ...]`, or a helper `get_quantity_held(account_name: str, symbol: str) -> Decimal`.
  - **Option B:** Call existing `get_summary(account_names=[data.account_name])` and, from the returned `positions`, find the entry for `data.symbol` and use its `quantity`. This works because when filtering by one account, the aggregated positions for that account are exactly that account’s positions.

So: for a SELL with `account_name=A` and `symbol=X`, compute portfolio for `account_names=[A]`, get positions, find symbol X; if not found or `quantity < sell quantity`, raise `ValidationError` (e.g. “Insufficient shares of X in account A” or “You do not hold X in account A”).

### 4.3 When to Run Validation

- On **create** transaction (POST) and on **edit** transaction (PUT) when the transaction is or is being changed to a SELL (and symbol/quantity/account are present). Validate using the **current** transaction set (excluding the current transaction on edit, or including the new one on create — for create, validate before persisting; for edit, validate after building the “new” transaction and ensure that account would have sufficient shares with the new state).

### 4.4 Dependency

- `TransactionService` must have access to portfolio-level logic (e.g. `PortfolioService` or a thin helper that computes per-account quantity for a symbol). Inject this to avoid circular dependencies and to keep tests simple (e.g. mock the “get quantity held” call).

---

## 5. Feature 3: Sell Cash Destination Account

### 5.1 Semantics

- For a **SELL**:
  - **Source account** (`account_name`): the account from which **shares** are debited (same as today).
  - **Cash destination account**: the account to which **sale proceeds** (quantity × price − fees) are credited.
  - **Default:** Cash destination = **the account that holds the most of that symbol**. If the user has already chosen the source account (e.g. “sell from Broker A”), then the default cash destination is that same account. So in the UI, when the user selects “SELL” and picks an account (or the UI defaults to “account with most shares”), the default for “where does the cash go?” is that same account; the user can override to another account.

### 5.2 Data Model

- Add an optional field **`cash_destination_account`** (nullable) to the transaction model.
  - **Meaning:** For SELL only. If set, sale proceeds are credited to this account; if null/omitted, proceeds are credited to `account_name` (current behavior).
  - **Storage:** New column in `transactions` table, e.g. `cash_destination_account TEXT NULL`. Only used when `txn_type = 'SELL'`; ignore for other types.
  - **Validation:** If present, `cash_destination_account` must be an existing account name (same as `account_name` validation).

### 5.3 Portfolio / Cash Computation

- Today, for a SELL, cash is credited to `account_name`. This must be extended:
  - For SELL, credit (quantity × price − fees) to **`cash_destination_account` if non-null, else `account_name`**.
  - Debit shares from **`account_name`** (unchanged).
- Update `PortfolioService` (or equivalent) so that when computing `account_cash`, SELL proceeds are applied to the correct account as above.

### 5.4 Default in UI

- When the user is adding a SELL and has selected (or entered) a symbol:
  - **Source account:** Default to the **account that holds the most of that symbol**. If none hold it, do not default (or use first account); backend will reject with “insufficient holdings” if they submit.
  - **Cash destination:** Default to the **same account** as the source (so one field can drive both, or two fields with cash destination defaulting to source). User can change cash destination to any other valid account.

### 5.5 API for “Account Holding the Most”

- To default the source account (and thus cash destination), the frontend needs **per-account quantities for a given symbol**.
- **Option A:** New endpoint, e.g. `GET /portfolio/positions-by-symbol?symbol=AAPL`, returning e.g. `[{ "account_name": "Broker A", "quantity": 50 }, { "account_name": "Broker B", "quantity": 10 }]` (only accounts with quantity > 0), sorted by quantity descending.
- **Option B:** Extend `GET /portfolio` with a query like `?by_account=1` and return positions broken down by account (e.g. `positions_per_account: [{ "account_name": "A", "positions": [...] }, ...]`). Frontend then filters by symbol and picks the account with max quantity.

Either way, the backend must expose **per-account position quantities** for at least the symbols needed (e.g. one symbol for the “add sell” form). Option A is minimal and fits the “default account for sell” use case.

### 5.6 Schema and API Contract

- **Create transaction (POST):** Request body may include optional `cash_destination_account` (string, optional). For SELL, if omitted, backend sets it to `account_name` when persisting (or treats null as “same as account_name” in cash logic).
- **Edit transaction (PUT):** Same optional field when editing a SELL.
- **Response (transaction out):** Include `cash_destination_account` when present (e.g. for SELL), so the UI can show and edit it.

---

## 6. Implementation Checklist (for Engineers)

- [ ] **Symbol validation**
  - [ ] Integrate `QuoteService` (or equivalent) into transaction create/edit validation for BUY/SELL.
  - [ ] Define and implement “valid symbol” rule (price or display name from Yahoo).
  - [ ] Return 400 with clear message for invalid symbol.
  - [ ] (Optional) Add `GET /symbols/validate?symbol=...` and/or client-side validation on blur.

- [ ] **Sell validation**
  - [ ] Add a way to get “quantity of symbol S in account A” (extend `PortfolioService` or add helper used by `TransactionService`).
  - [ ] In `_validate_transaction_create` (and edit path for SELL), check that `account_name` has at least `quantity` of `symbol`; otherwise raise `ValidationError`.
  - [ ] Ensure validation runs on create and on edit when the result is a SELL with symbol/quantity/account.

- [ ] **Sell cash destination**
  - [ ] Add DB column `cash_destination_account` (nullable) and migration if applicable.
  - [ ] Update transaction create/edit schemas and persistence to accept and store `cash_destination_account`.
  - [ ] Update portfolio cash computation so SELL credits the correct account (cash_destination_account if set, else account_name).
  - [ ] Expose per-account quantities for a symbol (new endpoint or extended portfolio response).
  - [ ] Frontend: for SELL, add “Cash destination account” (default = source account); optionally default source account to “account with most shares” for the entered symbol.
  - [ ] API response: include `cash_destination_account` in transaction out where relevant.

---

## 7. Error Messages (Suggested)

| Case | Suggested message (backend) |
|------|-----------------------------|
| Invalid symbol | `"Invalid or unknown symbol: {symbol}"` |
| No position in account | `"You do not hold {symbol} in account {account_name}"` |
| Insufficient quantity | `"Insufficient shares of {symbol} in account {account_name}. You have {held}, tried to sell {quantity}"` |
| Invalid cash destination | `"Account not found: {cash_destination_account}"` (or reuse existing account validation) |

Frontend should display these (or a generic “Operation failed” with detail) so the user can correct the input.

---

## 8. Summary

| Feature | Backend | Frontend |
|--------|---------|----------|
| **Symbol validation** | Validate with Yahoo (QuoteService) on create/edit; reject invalid with 400 | Optional: validate on blur; always show API error on submit |
| **Sell validation** | Compute quantity held in source account; reject if no position or insufficient quantity | Show server error when create/edit returns 400 |
| **Sell cash destination** | New optional field; credit SELL proceeds to that account (or account_name); expose per-account quantities for symbol | Default source = account with most shares; default cash destination = source; allow user to change cash destination |

This design keeps validation and cash semantics on the server, and uses the existing Yahoo integration and portfolio engine; engineers can implement in the order above and adjust details (e.g. exact validity rule or endpoint shape) as needed.
