# Portfolio Summary — Design Document

## 1. Overview

**Goal:** Show the user a **current portfolio summary** derived purely from transactions: what stocks they hold (and in what quantity), and how much cash they have. No new database tables; the portfolio is computed on demand from existing transaction data.

**Scope:**

- **Per-account semantics:** Portfolio can be shown for one account, multiple accounts, or all accounts. The same **account filter** already used for the transaction list (TopBar → “选择要显示的账户”) drives which account(s) are included. When multiple accounts are selected, their positions are **merged** (e.g. AAPL from Account A + AAPL from Account B → one row “AAPL” with combined quantity and cash).
- **Cash:** Net cash balance from CASH_DEPOSIT, CASH_WITHDRAW, and the cash impact of BUY/SELL (money out for buys + fees, money in from sells minus fees).
- **Stocks:** For each symbol, net share quantity (sum of BUY quantities minus sum of SELL quantities). Optionally show cost basis (total cost from buys, minus proceeds from sells, or average cost).
- **No persistence:** Nothing is stored in the database for “portfolio”; every view is computed from transactions.

This document is intended for the engineer implementing the feature.

---

## 2. Computation Rules

### 2.1 Cash balance

Cash is affected by all four transaction types. For the selected account(s), process all transactions (chronological order is not required for a simple sum):

| Transaction type   | Effect on cash |
|--------------------|----------------|
| CASH_DEPOSIT       | + `cash_amount` |
| CASH_WITHDRAW      | - `cash_amount` |
| BUY                | - `amount` (quantity × price) - `fees` |
| SELL               | + `amount` (quantity × price) - `fees` |

**Formula:**  
`cash_balance = Σ(CASH_DEPOSIT.cash_amount) - Σ(CASH_WITHDRAW.cash_amount) - Σ(BUY.amount + BUY.fees) + Σ(SELL.amount - SELL.fees)`

- Use `amount` when present; otherwise compute from `quantity * price` for BUY/SELL.
- Round to a consistent precision (e.g. 2 decimal places) for display.

### 2.2 Stock positions

- **Symbol:** Only BUY and SELL transactions have a `symbol`. Group by `symbol` (normalize: strip, uppercase; empty/null excluded).
- **Quantity:** For each symbol,  
  `quantity_held = Σ(BUY.quantity) - Σ(SELL.quantity)`  
  over the selected account(s).
- **Filter out zero/negative:** Do not show symbols with `quantity_held ≤ 0` (zero or negative would indicate data error or short selling, which is out of scope).
- **Cost basis (optional for v1):**  
  - **Simple option:** Total cost = Σ(BUY.quantity × BUY.price + BUY.fees) for that symbol; total proceeds = Σ(SELL.quantity × SELL.price - SELL.fees). Unrealized cost = total cost - (proportional) cost of sold shares. For a minimal v1, “total cost” (sum of all buy cost) and “total proceeds” (sum of all sell proceeds) are enough; “cost basis” for remaining shares can be approximated (e.g. average cost per share = total_buy_cost / total_bought_qty, then cost_basis = quantity_held × avg_cost).  
  - Design decision: in the first version, at least show **quantity** and **total cost** (sum of (quantity × price + fees) for BUYs for that symbol, minus allocated cost of sold shares if desired, or simply “total spent on buys” and “total received from sells” for transparency). Exact FIFO/LIFO cost basis can be a later enhancement.

### 2.3 Account filter and merging

- **Input:** Same as transaction list: a set of selected account names. If the user has not selected any accounts, treat as “all accounts” (same as existing behavior: empty selection ⇒ all).
- **Filter:** Include only transactions whose `account_name` is in the selected set (or all transactions when the set is “all”).
- **Merge:** When multiple accounts are selected, aggregate after filtering:
  - **Cash:** Single total = sum of cash from each account (since we’re summing transactions, one pass over filtered transactions gives one cash total).
  - **Stocks:** One row per symbol; quantity and cost/proceeds are sums across all selected accounts for that symbol.

---

## 3. API

### 3.1 Endpoint

| Method | Endpoint   | Purpose |
|--------|------------|--------|
| GET    | `/portfolio` | Return portfolio summary for given account(s). |

**Query parameters:**

- `account` (optional, repeatable): Account names to include. If omitted or empty, include **all** accounts (same semantics as transaction list).

**Response (JSON):**

```json
{
  "cash_balance": 12345.67,
  "account_cash": [
    { "account_name": "Account A", "cash_balance": 5000.00 },
    { "account_name": "Account B", "cash_balance": 7345.67 }
  ],
  "positions": [
    {
      "symbol": "AAPL",
      "quantity": 10.5,
      "total_cost": 1500.25
    }
  ]
}
```

- `cash_balance`: number, two decimal places (merged over requested accounts).
- `account_cash`: array of `{ account_name, cash_balance }` for per-account cash. When `account` query is present, include entries for those accounts only; when omitted (all accounts), include all accounts. Used by the frontend to show a cash badge on each account in the Accounts block (see `PORTFOLIO_SUMMARY_FRONTEND.md`).
- `positions`: array of `{ symbol, quantity, total_cost }`. Only symbols with `quantity > 0`. Sorted by `symbol` (e.g. A–Z).  
  - `total_cost` is the total cost of current holdings (e.g. sum of (quantity × price + fees) for BUYs minus a simple proportional cost of sold shares, or v1: “average cost × quantity_held” using total buy cost / total buy quantity for that symbol). If the team prefers “total buy cost” and “total sell proceeds” as separate fields for v1, that is acceptable.

**Status codes:**

- `200`: Success.
- `400`/`500`: As per existing API conventions (e.g. invalid request or server error).

No new database tables; the handler loads transactions (via existing `TransactionService.list_transactions(account_names=...)`) and computes the aggregates in memory.

---

## 4. Backend Implementation Notes

- **New module or router:** Add a portfolio endpoint, e.g. in `src/app/api/routers/portfolio.py` or under the existing transactions router as `GET /transactions/portfolio` or a dedicated `GET /portfolio` under the app. Recommendation: **`GET /portfolio`** in a small `portfolio` router for clarity.
- **Service layer:** Either:
  - A thin **portfolio service** (e.g. `src/service/portfolio_service.py`) that takes `account_names: Optional[List[str]]`, calls `TransactionService.list_transactions(account_names=account_names)`, then computes cash and positions; or
  - The same logic inline in the router. Prefer a small **PortfolioService** so logic is testable and reusable.
- **Computation:** One pass over the list of transactions: update cash (by txn_type and amount/fees), and update per-symbol quantity and (if implemented) cost/proceeds. Then build `positions` for symbols with `quantity > 0`, sort by symbol.
- **Schemas:** Pydantic models for response, e.g. `PortfolioPosition(symbol, quantity, total_cost)`, `PortfolioSummary(cash_balance, positions)`.
- **Tests:** Unit tests for PortfolioService (or equivalent): e.g. only CASH_DEPOSIT/CASH_WITHDRAW → cash only; BUY/SELL only → positions only; mixed; multiple accounts → merged result; empty selection ⇒ all accounts.

---

## 5. Frontend

### 5.1 Placement and behavior

- **Section:** A dedicated **“Portfolio Summary”** (or “当前持仓” / “资产概览”) section visible on the main screen. Placement: e.g. **above** the “交易记录” (TransactionBlock) so the user sees portfolio first, then transactions. Alternatively, a collapsible section or a tab; the important part is that it is clearly a summary of **current** holdings and cash.
- **Account scope:** The portfolio section must use the **same** account selection as the rest of the app. That is, `selectedAccountNames` from App state (same as TopBar and TransactionBlock): when the user changes the account filter, both the transaction list and the portfolio summary update. No separate account selector for portfolio.
- **Data flow:** When `selectedAccountNames` (or “all”) and `refreshKey` change, the frontend calls `GET /portfolio?account=...` with the selected account name(s) (or no param if “all”) and renders the result. After add/edit/delete transaction, `onRefresh` already triggers a refresh; ensure the portfolio section also refetches (e.g. same `refreshKey` or a dedicated refetch when portfolio API is used).

### 5.2 UI content

- **Cash:** Not displayed in the portfolio section. Cash is shown as a **badge per account** in the Accounts block (账户管理), using `account_cash` from the API. See **`docs/PORTFOLIO_SUMMARY_FRONTEND.md`** for layout, data flow, and no-horizontal-scroll table design.
- **Positions:** Table: one row per stock; columns e.g. **代码/名称**, **成本价**, **持仓数量** (and later 最新价, 市值, 浮动盈亏, 盈亏比例, 占比 when market data exists). Only rows with quantity &gt; 0. Table must fit in one row without horizontal scrolling.
- **Empty state:** If there are no positions and cash is 0, show a short message like “No holdings for the selected account(s).” / “所选账户暂无持仓.”
- **Loading / error:** Show loading indicator while fetching; on API error, show a short error message (consistent with existing transaction block).

### 5.3 API client and types

- **Types (e.g. `frontend/src/types/index.ts`):**  
  `PortfolioPosition { symbol: string; quantity: number; total_cost: number }`  
  `AccountCash { account_name: string; cash_balance: number }`  
  `PortfolioSummary { cash_balance: number; account_cash: AccountCash[]; positions: PortfolioPosition[] }`
- **Client (e.g. `frontend/src/api/client.ts`):**  
  `getPortfolio(params?: { account?: string[] }): Promise<PortfolioSummary>`  
  - If `params.account` is a non-empty array, pass each as `account=...` in the query string; otherwise omit the param (backend treats as “all accounts”).

### 5.4 Files to add or change

| File | Change |
|------|--------|
| **New** `frontend/src/components/PortfolioBlock/PortfolioBlock.tsx` (or similar) | Section "持仓明细" that accepts `selectedAccountNames`, `refreshKey`, fetches portfolio, displays **positions table only** (no cash) and empty/loading/error states. Table must fit in one row without horizontal scroll. See `PORTFOLIO_SUMMARY_FRONTEND.md`. |
| `frontend/src/App.tsx` | Render the new portfolio section (e.g. above `TransactionBlock`), pass `selectedAccountNames`, `refreshKey`, and optionally `onRefresh` if needed. |
| `frontend/src/api/client.ts` | Add `getPortfolio(params?)`. |
| `frontend/src/types/index.ts` | Add `PortfolioPosition`, `PortfolioSummary`. |

Reuse existing styling (e.g. card, border, theme variables) so the section matches the rest of the app.

---

## 6. Edge Cases and Rules

- **No accounts / empty selection:** Backend treats “no account filter” as “all accounts”. Frontend already uses “all accounts” when none selected; pass no `account` query param in that case.
- **Selected accounts with no transactions:** Portfolio returns `cash_balance: 0`, `positions: []`.
- **Symbol with net zero or negative quantity:** Do not include in `positions` (or show 0 and clarify in product; recommendation: hide 0/negative).
- **Fees:** Always include in cash and in cost (e.g. BUY: cost = quantity×price + fees; SELL: proceeds = quantity×price - fees).
- **Rounding:** Use a consistent precision (e.g. 2 decimals) for cash and total_cost; quantity can be 2–4 decimals depending on existing transaction data.

---

## 7. Out of Scope / Future

- **Market value / current price:** Showing “current value” of positions would require external data (e.g. quote API). Implemented via Portfolio Quotes (Yahoo Finance). See docs/PORTFOLIO_QUOTES_DESIGN.md for current price, company name, and computed fields (市值, 浮动盈亏, 盈亏比例, 占比).
- **Historical portfolio / snapshots:** Only “current” state derived from all transactions up to now. No time-travel or stored snapshots.
- **Short selling / negative quantity:** Treated as data error or excluded from positions for now.

---

## 8. Implementation Order (Suggested)

1. **Backend:** Portfolio response schema and service (compute cash + positions from `list_transactions`), then `GET /portfolio` endpoint and tests.
2. **Frontend:** Types and `getPortfolio` client; add `PortfolioBlock` and integrate in `App.tsx` with `selectedAccountNames` and `refreshKey`.
3. **Polish:** Empty state, loading, error handling, and copy (see §9).

---

## 9. Copy (for UX)

- Section title: **“Portfolio”** / **“当前持仓”** or **“资产概览”**.
- Cash row label: **“Cash”** / **“现金”**.
- Table headers: **代码/名称**, **成本价**, **持仓数量** (and later: 最新价, 市值, 浮动盈亏, 盈亏比例, 占比). Cash: shown as badge in Accounts block, not in portfolio table.
- Empty: **“No holdings for the selected account(s).”** / **“所选账户暂无持仓.”**
- Error: Use existing pattern (e.g. “加载失败” + backend hint).

---

## 10. Summary

| Item | Decision |
|------|----------|
| Data source | Transactions only; no new DB storage. |
| Account scope | Same as transaction list filter; merge when multiple selected. |
| Cash | CASH_DEPOSIT − CASH_WITHDRAW − BUY (amount+fees) + SELL (amount−fees). |
| Positions | Per symbol: quantity = Σ(BUY qty) − Σ(SELL qty); show only &gt; 0. Optionally total_cost (cost basis). |
| API | GET `/portfolio?account=...` → `{ cash_balance, positions[] }`. |
| Frontend | New section (e.g. above transactions), same account filter, refetch on filter/refresh. |

This gives the engineer a complete specification to implement the portfolio summary feature end-to-end.
