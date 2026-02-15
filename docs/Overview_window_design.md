# Design: General Overview Window

This document describes the design and implementation plan for the **General Overview** feature: a horizontal block of three summary cards (Total Assets, Total Gain/Loss, Today's Gain/Loss) displayed below the header, consistent with the existing app style.

---

## 1. Feature Summary

| Card | Description | Data Source |
|------|-------------|-------------|
| **Total Assets** | Total portfolio value with breakdown: **Stocks** (sum of position market values) and **Cash** (aggregate cash balance). | Existing `GET /portfolio`: `positions[].market_value`, `cash_balance` |
| **Total Gain/Loss** | Stock-only unrealized P&L. Excludes cash add-ins; formula: sum of (market_value − total_cost) per position. | Existing `GET /portfolio`: `positions[].unrealized_pnl` (and optionally `total_cost` for %) |
| **Today's Gain/Loss** | Change in stock holdings since previous close. Formula: sum over positions of `(latest_price − previous_close) × quantity`. Requires **previous close** from quotes and **market-day logic** (weekend/holiday). | **New**: backend must expose `previous_close` per position; frontend computes today P&L and handles “market closed” labeling. |

---

## 2. UI Layout and Style

- **Placement**: One horizontal block directly under the **TopBar**, inside the same content container (`max-w-5xl`, `px-8 md:px-12`), and **above** Account Management and main content (Portfolio Block, Transaction Block).
- **Structure**: A single row of **3 cards** on desktop; on small screens, cards can stack vertically or remain in a scrollable row, depending on preference (recommend: responsive grid, e.g. 3 columns → 1 column).
- **Card style** (match existing blocks such as `PortfolioBlock`, `AccountManagementBlock`, `TransactionBlock`):
  - Container: `rounded-2xl border border-[var(--border-color)] bg-[var(--bg-card)] shadow-[var(--shadow-md)]`
  - Padding: `pt-4 px-6 pb-6 md:pt-5 md:px-8 md:pb-8` (or slightly tighter for compact cards)
  - Typography: title `text-xl font-bold tracking-tight text-[var(--text-primary)]`, secondary text `text-sm text-[var(--text-muted)]`, values use `text-[var(--text-primary)]`; for gain/loss use `text-[var(--success)]` for positive and `text-red-500 dark:text-red-400` for negative (align with existing `PortfolioBlock` mobile cards).
- **Section wrapper**: Use a `<section className="py-3">` (or similar) around the overview to keep spacing consistent with other sections.

---

## 3. Data Definitions

### 3.1 Total Assets (frontend-only computation)

- **Total assets** = `stocksValue + cashBalance`
  - `stocksValue` = sum of `position.market_value` for all positions (treat `null` as 0).
  - `cashBalance` = `portfolio.cash_balance` (already aggregated for selected accounts).
- **Breakdown**: Display two lines or sub-labels, e.g.:
  - 股票 (Stocks): $X,XXX.XX  
  - 现金 (Cash): $X,XXX.XX  

All from current `PortfolioSummary`; no API change.

### 3.2 Total Gain/Loss (frontend-only computation)

- **Total gain/loss (stocks only)** = sum of `position.unrealized_pnl` (treat `null` as 0).
- **Optional percentage**:  
  `totalGainLossPct = totalCost > 0 ? (totalGainLoss / totalCost) * 100 : null`,  
  where `totalCost` = sum of `position.total_cost`.
- Excludes cash deposits/withdrawals by definition (only position-level P&L).

No API change.

### 3.3 Today's Gain/Loss (backend + frontend)

- **Definition**: Change in value of stock holdings from **previous close** to **current price** (or latest quote).
  - **Formula**: `todayGainLoss = Σ (position.latest_price − position.previous_close) × position.quantity`  
  (only for positions where both `latest_price` and `previous_close` are non-null).
- **Previous close**: Not currently returned by the backend. Yahoo Finance (via yfinance) typically provides `previousClose` (or `regularMarketPreviousClose`) in `ticker.info`. The backend must expose this so the frontend can compute today’s P&L.
- **Market-day logic** (weekend / holiday):
  - **Option A (recommended, frontend-only):**  
    - If today is **weekend** (Saturday/Sunday) or a **known US market holiday**, show a subtitle such as “自上一收盘” / “Since last close” or “市场休市” / “Market closed”, and still use `previous_close` vs `latest_price` (change since last close).  
    - If today is a **trading day**, show “今日” / “Today”.  
    - Use a small, static list of US market holidays (e.g. New Year, Independence Day, Thanksgiving, Christmas) or a lightweight dependency; no backend calendar required for v1.
  - **Option B:** Backend exposes `is_trading_day` / `last_trading_date` (e.g. via exchange_calendar); frontend uses it for the same labeling.  
  For minimal scope, **Option A** is sufficient.
- **When previous close is missing**: If any symbol has no `previous_close`, either exclude it from the sum and show the partial total, or show “—” / “N/A” for Today’s Gain/Loss and a short tooltip (“部分行情缺失”).

---

## 4. Backend Changes

### 4.1 Quote service (`src/service/quote_service.py`)

- **Current**: Returns per symbol `current_price` and `display_name` (from yfinance `ticker.info`: `currentPrice` / `regularMarketPrice`, `longName` / `shortName`).
- **Change**: Also read **previous close** from `ticker.info`:
  - Prefer `previousClose` or `regularMarketPreviousClose` (depending on yfinance version).
  - Add to the returned dict, e.g. `previous_close: Optional[float]`.
- **Cache**: Same cache key (symbol); store and return `previous_close` with the same TTL as the existing quote so that “today’s” calculation is consistent.

### 4.2 Portfolio service (`src/service/portfolio_service.py`)

- In `_enrich_positions_with_quotes`, when attaching quote data to each position, set:
  - `position["previous_close"] = _round2(quote["previous_close"])` when present, else `None`.
- No change to cash or position aggregation logic.

### 4.3 API schema and router

- **Schema** (`src/app/api/schemas/portfolio.py`): Add optional field to `PortfolioPosition`:
  - `previous_close: Optional[float] = None`
- **Router**: No change; still `GET /portfolio` with optional `account` and `quotes`. When `quotes=true`, positions will include `previous_close` when available.

### 4.4 Frontend types and API client

- **Types** (`frontend/src/types/index.ts`): Add to `PortfolioPosition`:
  - `previous_close?: number | null;`
- **API client**: No change; already returns full `PortfolioSummary` from `getPortfolio()`.

---

## 5. Frontend Implementation

### 5.1 New component: `GeneralOverviewBlock`

- **Location**: e.g. `frontend/src/components/GeneralOverviewBlock/GeneralOverviewBlock.tsx`.
- **Props**:
  - `portfolio: PortfolioSummary | null`
  - `loading: boolean`
  - `error: string | null`
- **Behavior**:
  - If `error`: render a short error state (same pattern as `PortfolioBlock`: message in card-style container).
  - If `loading`: render skeleton or “加载中...” for the three cards.
  - Otherwise compute and display:
    - **Card 1 – Total Assets**: total assets, stocks breakdown, cash breakdown.
    - **Card 2 – Total Gain/Loss**: sum of `unrealized_pnl`, optional % (vs total cost); style positive/negative with existing success/red classes.
    - **Card 3 – Today’s Gain/Loss**: sum of `(latest_price - previous_close) * quantity` where both prices exist; subtitle “今日” vs “自上一收盘”/“市场休市” based on simple date/holiday check; handle missing `previous_close` (e.g. show “—” or partial).
- **Layout**: Use a grid, e.g. `grid grid-cols-1 md:grid-cols-3 gap-4` (or `gap-6`), so three equal-width cards on medium+ screens and stacked on small screens.
- **Accessibility**: Use semantic headings (e.g. `h2` or `h3` per card title) and ensure number formatting (e.g. `toLocaleString`) and +/- for gains/losses are clear.

### 5.2 Market-day / holiday helper (frontend)

- **Location**: e.g. `frontend/src/utils/marketCalendar.ts` (or inline in the component for v1).
- **Logic**:
  - `isWeekend(date: Date)`: `date.getDay() === 0 || date.getDay() === 6`.
  - `isUSMarketHoliday(date: Date)`: simple list of fixed and rule-based US holidays (e.g. Jan 1, July 4, Thanksgiving 4th Thu Nov, Dec 25; optionally Good Friday). No backend call.
  - `getTodayGainLossLabel(date: Date): string`: return “今日” when trading day, else “自上一收盘” or “市场休市”.
- **Timezone**: Use the user’s local date (or explicitly “America/New_York” for US market) so that “today” is consistent; document the choice (e.g. “US market calendar, local date”).

### 5.3 Integration in `App.tsx`

- **Data**: Reuse existing `portfolio` and `portfolioLoading` / `portfolioError` from the current `GET /portfolio` effect (same `selectedAccountNames` and `refreshKey`).
- **Placement**: Below `<TopBar />`, inside the same `max-w-5xl` content div, **above** `<AccountManagementBlock />`:

```tsx
<div className="mx-auto w-full max-w-5xl flex-1 px-8 md:px-12">
  <GeneralOverviewBlock
    portfolio={portfolio}
    loading={portfolioLoading}
    error={portfolioError}
  />
  <AccountManagementBlock ... />
  <main className="flex-1">
    ...
  </main>
</div>
```

- No new API calls; overview stays in sync with portfolio and account filter.

---

## 6. Edge Cases and Behavior

| Case | Behavior |
|------|----------|
| No positions, cash only | Total Assets = cash; Total Gain/Loss = $0; Today’s Gain/Loss = $0 or “—” |
| Positions but no quotes (`quotes=0` or quote failure) | `market_value` / `unrealized_pnl` may be null; show “—” or 0 for affected cards; Today’s P&L requires quotes and `previous_close`, so show “—” when missing |
| Partial quote failure | Total Assets / Total Gain/Loss: sum only positions with valid numbers. Today: sum only positions with both `latest_price` and `previous_close`; optionally note “部分行情缺失” |
| Weekend / holiday | Today’s card: show “自上一收盘” or “市场休市”, value = change since last close (same formula) |
| All accounts deselected | Same as today: portfolio may be empty; show zeros or empty state consistent with PortfolioBlock |

---

## 7. Implementation Order

1. **Backend**: Add `previous_close` to quote fetch and to portfolio position enrichment; add `previous_close` to `PortfolioPosition` schema; run existing tests and add a small test that `previous_close` is present when quote has it.
2. **Frontend types**: Extend `PortfolioPosition` with `previous_close`.
3. **Frontend – market calendar**: Implement `marketCalendar` (or equivalent) and `getTodayGainLossLabel`.
4. **Frontend – GeneralOverviewBlock**: Implement the three cards (Total Assets, Total Gain/Loss, Today’s Gain/Loss) with loading/error and responsive layout.
5. **App.tsx**: Insert `GeneralOverviewBlock` below header, pass `portfolio`, `portfolioLoading`, `portfolioError`.
6. **Polish**: Number formatting (currency, decimals), i18n if needed (e.g. 股票/现金/今日/自上一收盘), and any tooltip for “Today” vs “Since last close”.

---

## 8. File Checklist

| Layer | File | Change |
|-------|------|--------|
| Backend | `src/service/quote_service.py` | Return `previous_close` in quote dict |
| Backend | `src/service/portfolio_service.py` | Set `position["previous_close"]` in enrichment |
| Backend | `src/app/api/schemas/portfolio.py` | Add `previous_close: Optional[float]` to `PortfolioPosition` |
| Frontend | `frontend/src/types/index.ts` | Add `previous_close?: number \| null` to `PortfolioPosition` |
| Frontend | `frontend/src/utils/marketCalendar.ts` | New: weekend + US holiday check, label helper |
| Frontend | `frontend/src/components/GeneralOverviewBlock/GeneralOverviewBlock.tsx` | New: 3-card overview component |
| Frontend | `frontend/src/App.tsx` | Import and render `GeneralOverviewBlock` below TopBar |

---

This design keeps Total Assets and Total Gain/Loss fully derived from the existing API, and adds minimal backend surface (one optional field per position) to support Today’s Gain/Loss with clear market-day semantics and styling consistent with the rest of the app.
