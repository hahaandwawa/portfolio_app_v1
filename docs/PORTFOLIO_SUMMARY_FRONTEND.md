# Portfolio Summary — Frontend Design

This document specifies the frontend implementation for the Portfolio Summary feature. It assumes the backend implements `GET /portfolio` as described in `PORTFOLIO_SUMMARY_DESIGN.md`, with one extension: the response must include **per-account cash** so the Accounts block can show a cash badge on each account. See §1.2 and §4.

---

## 1. Design Goals and Constraints

### 1.1 Portfolio section (holdings table)

- **Reference:** “持仓明细” style: one row per stock, columns for code/name, cost, quantity, and (when data exists) market value, P/L, proportion. See the provided reference image.
- **Critical constraint:** All columns must be visible in a **single row without horizontal scrolling**. The table must fit within the same content width as the rest of the app (e.g. the existing `max-w-5xl` container). Do **not** use a fixed large `min-width` on the table that forces horizontal scroll.
- **One row per stock:** Each position is exactly one table row.
- **No cash in this section:** Do not display cash balance in the portfolio (holdings) section. Cash is shown only in the Accounts block (see §2).

### 1.2 Cash in Accounts block

- **Placement:** In the **Accounts block** (账户管理), each account row must show a **badge** with that account’s **current cash balance**.
- **Data source:** Backend must supply per-account cash. The frontend will use this to render the badge next to (or under) each account name. See §4 for the required API shape.

---

## 2. Accounts Block — Cash Badge

### 2.1 Where to show

- **Component:** `AccountListItem` (or equivalent account row in 账户管理).
- **Current row content:** Account icon, account name, badge “{n} 笔交易”, edit/delete buttons.
- **Addition:** A second badge (or inline text) showing **cash balance** for that account, e.g. “现金 ¥12,345.67” or “¥12,345.67” with a small “现金” label. Style consistently with the existing “{n} 笔交易” badge (e.g. same padding, rounded corners, different color or neutral so the two badges are distinguishable).

### 2.2 Data flow

- **Source:** Per-account cash comes from the portfolio API response (see §4). The App (or a parent) fetches portfolio data (including `account_cash`) when accounts are loaded or when `refreshKey` / selected accounts change.
- **Passing to AccountListItem:** Either:
  - **Option A:** App holds a map `accountName → cashBalance` (from latest portfolio response for **all** accounts). Pass `cashBalance: number | undefined` into `AccountManagementBlock`, which passes it to each `AccountListItem`. When portfolio has not been fetched for that account set, show “—” or hide the badge until data is available.
  - **Option B:** Fetch portfolio once with no account filter (all accounts); response includes `account_cash` for every account. App stores that map and passes cash per account into the Accounts block. When user has selected accounts, the portfolio table still uses the filtered API call for positions; the account_cash for badges can come from the same “all accounts” portfolio call or from the filtered call — if filtered, only selected accounts have cash data; then badges for non-selected accounts would need a separate “all accounts” portfolio fetch for badge data, or we only show badges for accounts that appear in the current portfolio response. **Recommended:** Backend returns `account_cash` for **all** accounts whenever the portfolio is fetched (or we have a dedicated lightweight endpoint for “cash per account”). Simplest for frontend: one `GET /portfolio` (no account filter) that returns `positions` for all accounts merged and `account_cash` for every account. Then the same data drives both the portfolio table (when “all” selected) and all account badges. When user filters to specific accounts, call `GET /portfolio?account=A&account=B`; backend returns merged positions plus `account_cash` for A and B only — so badges for A and B are correct; badges for other accounts could show previous value or “—” until we have a source. To keep badges always correct, backend can **always** include `account_cash` for **all** accounts in the system in every portfolio response (so one call with account filter still returns positions for selected accounts but cash for every account). That way one portfolio call gives positions (filtered) + cash for all accounts (for badges). Document this in §4.

### 2.3 Badge behavior

- **Loading:** If portfolio data is loading, show “—” or a subtle loading state for the cash badge.
- **Format:** Format cash as currency (e.g. 2 decimals, locale-aware). Example: `12,345.67` or `¥12,345.67` depending on product preference.
- **Zero:** Show “0.00” or “¥0.00”; do not hide the badge.

---

## 3. Portfolio Section — Holdings Table

### 3.1 Section structure

- **Title:** “持仓明细” (Holdings detail). Optional subtitle: “{n} 只股票” (n stocks) when there are positions.
- **Placement:** Above the “交易记录” block. Same account filter as the rest of the app: only selected account(s) are included; when multiple are selected, positions are merged (one row per symbol).
- **No cash row:** Do not render any cash balance in this section.

### 3.2 Table layout — no horizontal scroll

- **Container:** Table lives in the same max-width content area as the rest of the app. Do **not** use `min-width` on the table that would force the container to overflow (avoid the pattern used in `TransactionTable` with `min-w-[800px]` + `overflow-x-auto` for this portfolio table).
- **Strategy to fit one row:**
  - Use **full width** of the container: `w-full` with no `min-width`.
  - Use **flexible column widths**: e.g. `table-fixed` with percentage or fractional widths, or CSS Grid, so that columns share space and shrink proportionally. Ensure the “code/name” column has enough space for the longest symbol; numbers can be narrower.
  - **Compact headers:** Prefer short labels to keep the header row tight (e.g. “代码”, “成本价”, “数量”). Optional: two-line header “代码/名称” only if space allows without scroll.
  - **Font size:** Keep table text at `text-sm` (or one step smaller if needed) so that all columns fit on typical viewports (e.g. 1024px width).
  - **Padding:** Use modest horizontal padding (e.g. `px-3`) to save space.
- **Responsive fallback:** On very narrow viewports (e.g. &lt; 640px), if the table still cannot fit, either:
  - **Option A:** Switch to a **card layout**: one card per stock, each card showing the same fields stacked vertically (code, cost, quantity, etc.). No row-based table on small screens.
  - **Option B:** Allow horizontal scroll only as a last resort and document it; prefer that above the breakpoint the table never scrolls horizontally.

### 3.3 Columns (current data — no market data)

Backend currently provides per position: `symbol`, `quantity`, `total_cost`. No “latest price” or “market value” from the API yet.

| Column       | Header (中文) | Content | Sortable | Width / notes |
|-------------|----------------|---------|----------|----------------|
| Code/Name   | 代码/名称      | Symbol (bold). Optional second line: full name if backend provides it later. | Yes | Flexible; allow ~20% or more so symbols are readable. |
| Cost price  | 成本价         | Average cost = `total_cost / quantity`, formatted as currency (2 decimals). | Yes | Numeric, fixed or min width. |
| Quantity    | 持仓数量       | `quantity`, formatted (e.g. 2–4 decimals as appropriate). | Yes | Numeric. |

All columns should be **sortable** (click header to sort by that column, toggle ascending/descending). Default sort: e.g. by symbol A–Z.

**Quote-enabled columns (see `PORTFOLIO_QUOTES_DESIGN.md`):** 最新价, 市值, 浮动盈亏, 盈亏比例, 占比. Leave the table structure easy to extend (e.g. add columns when API provides these fields). The “single row, no horizontal scroll” rule applies when those columns are added: use proportional widths and compact styling so the row still fits.

### 3.4 Visual and UX details

- **Sorting:** Headers show sort direction (e.g. ↑↓ or caret). Click to cycle: unsorted → asc → desc (or asc ↔ desc).
- **Profit/loss (future):** When 浮动盈亏 / 盈亏比例 exist, show profit in green (e.g. `+$1.79K`, `+35.34%`) and loss in red, with a small trend icon (up/down) if desired.
- **Proportion (占比) (future):** When available, show a horizontal bar (e.g. blue) whose length is proportional to the position’s share of total portfolio value. Keep the bar thin so the row height stays minimal.
- **Empty state:** If there are no positions for the selected account(s), show a short message: “所选账户暂无持仓.” (No holdings for the selected account(s).)
- **Loading / error:** Show a loading indicator while fetching; on API error, show a short error message (e.g. “加载失败” + backend hint), consistent with the transaction block.

### 3.5 Styling

- Reuse existing theme variables: `--text-primary`, `--text-muted`, `--border-color`, `--bg-card`, `--accent`, etc.
- Match the card style of “账户管理” and “交易记录”: rounded border, same shadow and padding.
- Table: header row with subtle background (`--bg-elevated`), row borders, hover state on body rows (`hover:bg-[var(--accent-soft)]/50` or similar).

---

## 4. API Contract (Backend Extension for Frontend)

The frontend expects the portfolio API to return **per-account cash** so it can render the cash badge in the Accounts block.

### 4.1 Endpoint

- Same as main design: `GET /portfolio?account=...` (optional repeatable `account`; no param = all accounts).

### 4.2 Response shape

```json
{
  "cash_balance": 12345.67,
  "account_cash": [
    { "account_name": "Account A", "cash_balance": 5000.00 },
    { "account_name": "Account B", "cash_balance": 7345.67 }
  ],
  "positions": [
    { "symbol": "AAPL", "quantity": 10.5, "total_cost": 1500.25 }
  ]
}
```

- **`account_cash`** (required): Array of `{ account_name, cash_balance }`. Must include **every account** that exists in the system (or at least every account that was requested when `account` filter is used). Recommended: when `account` is present, return cash for those accounts only; when `account` is omitted (all accounts), return cash for **all** accounts. Frontend will then show a badge for each account; if an account is missing from `account_cash`, show “—” or 0 for that account.
- **`positions`**, **`cash_balance`**: As in main design (merged positions and merged cash for the requested account set).

Backend implementation: when computing portfolio, compute cash per account in the same pass; include `account_cash` for the filtered account list (or for all accounts if no filter) in the response.

---

## 5. Data Flow Summary

1. **App** holds `accounts`, `selectedAccountNames`, `refreshKey`, and optionally a **portfolio state**: `portfolio: { positions, account_cash } | null` and `portfolioLoading` / `portfolioError`.
2. **Portfolio fetch:** When `selectedAccountNames` or `refreshKey` changes, call `getPortfolio({ account: selectedAccountNames.size > 0 ? Array.from(selectedAccountNames) : undefined })`. Store `positions` for the portfolio table and `account_cash` for the account badges. To always have cash for every account, either:
   - Call portfolio once with no filter when loading accounts and use `account_cash` for all badges; and call again when filter changes for the positions table (and optionally merge `account_cash` from both so badges stay full), or
   - Ensure backend returns `account_cash` for all accounts in every response (e.g. when no filter, return all; when filter present, return cash for filtered accounts only — then badges for non-selected accounts need another source or show “—”).
3. **Portfolio section:** Reads `positions` (and loading/error) from App state, renders the holdings table. No cash in this section.
4. **Accounts block:** Receives `accountCashMap: Record<string, number>` (from App, derived from `account_cash`). Each `AccountListItem` receives `cashBalance: number | undefined` for its account and shows the cash badge.

---

## 6. Types and API Client

### 6.1 Types (`frontend/src/types/index.ts`)

```ts
export interface PortfolioPosition {
  symbol: string;
  quantity: number;
  total_cost: number;
}

export interface AccountCash {
  account_name: string;
  cash_balance: number;
}

export interface PortfolioSummary {
  cash_balance: number;
  account_cash: AccountCash[];
  positions: PortfolioPosition[];
}
```

### 6.2 Client (`frontend/src/api/client.ts`)

- `getPortfolio(params?: { account?: string[] }): Promise<PortfolioSummary>`
  - If `params?.account` is non-empty, append each as `account=...` in the query string; otherwise omit `account` (all accounts).

---

## 7. Files to Add or Change

| File | Change |
|------|--------|
| **New** `frontend/src/components/PortfolioBlock/PortfolioBlock.tsx` | Section “持仓明细”, fetches portfolio (or receives from App), renders holdings table only (no cash). Sortable columns; full-width table with no horizontal scroll. Empty/loading/error states. |
| **New** (optional) `frontend/src/components/PortfolioBlock/PortfolioTable.tsx` | Table presentational component: receives sorted positions, column definitions, onSort. Ensures single-row layout (flexible widths, compact padding). |
| `frontend/src/components/AccountManagementBlock/AccountListItem.tsx` | Add a **cash badge**: accept `cashBalance: number \| undefined`, display next to “{n} 笔交易” (e.g. “现金 ¥12,345.67” or “¥12,345.67”). |
| `frontend/src/components/AccountManagementBlock/AccountManagementBlock.tsx` | Accept optional `accountCashMap: Record<string, number>`. Pass `cashBalance={accountCashMap?.[account.name]}` to each `AccountListItem`. |
| `frontend/src/App.tsx` | Fetch portfolio when `selectedAccountNames` / `refreshKey` (and optionally on mount for all accounts). Store `portfolio`, `portfolioLoading`, `portfolioError`. Render `PortfolioBlock` above `TransactionBlock` with positions + loading/error. Pass `accountCashMap` (from `portfolio.account_cash`) to `AccountManagementBlock`. |
| `frontend/src/api/client.ts` | Add `getPortfolio(params?)` returning `PortfolioSummary`. |
| `frontend/src/types/index.ts` | Add `PortfolioPosition`, `AccountCash`, `PortfolioSummary`. |

---

## 8. Copy (UX)

- Portfolio section title: **持仓明细**
- Subtitle (when positions exist): **{n} 只股票**
- Table headers: **代码/名称**, **成本价**, **持仓数量** (and later: 最新价, 市值, 浮动盈亏, 盈亏比例, 占比)
- Empty state: **所选账户暂无持仓.**
- Account cash badge: **现金 ¥{amount}** or **¥{amount}** (consistent with existing currency formatting)
- Error: **加载失败** + backend hint (same as transaction block)

---

## 9. Summary for the Engineer

- **Portfolio section:** “持仓明细” table, one row per stock. **No cash** in this section. All columns must fit in **one row without horizontal scrolling** (flexible widths, compact layout, optional card layout on very small screens).
- **Accounts block:** Add a **cash badge** on each account row; data from portfolio API’s `account_cash`.
- **API:** Backend must add `account_cash: { account_name, cash_balance }[]` to `GET /portfolio` response.
- **Data flow:** App fetches portfolio (with current account filter), stores positions + `account_cash`; portfolio section shows positions only; Accounts block receives a cash map and shows a badge per account.
