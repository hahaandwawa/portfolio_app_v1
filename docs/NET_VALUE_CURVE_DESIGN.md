# Net Value Curve Feature — Design Document

## 1. Overview

**Goal:** Display a historical equity curve showing a **baseline** (see §1.1) and **market value** over time, with clear visualization of profit/loss and interactive hover details.

**Key Requirements:**
- Two lines: Baseline (see definition below) and Market Value (市值)
- Visual profit/loss indication (green for profit, red for loss)
- Shadow/fill between lines to show profit/loss area
- Hover tooltip showing daily baseline, market value, P/L and P/L% (with denominator explicit)
- **Include/exclude cash** — default and toggle (see §1.2)
- Efficient data fetching (minimize API calls)
- Handle transaction edits/deletes gracefully (recompute only; no price cache invalidation)
- Market holidays: forward-fill prices; tooltip shows “Last trading close” on non-trading days
- Zoom options: Last 7 days, 30 days, or all time

**V1 constraint — Currency:** V1 supports **USD-denominated assets only**. No FX conversion or multi-currency cash. If you later support non-USD holdings or cash, add currency fields and an FX service; until then, state explicitly: “V1 supports USD only; FX deferred.”

### 1.1 Baseline Definition (Product/Finance Correctness)

**Do not** use “cost basis” to mean “sum of buy costs minus sell proceeds” — that is neither standard cost basis nor a good baseline for the chart (it can go negative or tiny after selling winners, making P/L% misleading).

| Option | Name in UI | Definition | When it changes |
|--------|------------|------------|------------------|
| **A** (deferred) | Net Invested / Net Contributions | Deposits − withdrawals; requires crisp cash-flow model (transfers, FX, fees). | — |
| **B** (v1) | **Holdings Cost** | Sum over open positions of (avg cost × current shares). | When you buy (adds), sell (reduces), or change cost via edits. |

- **V1 scope:** Use **Option B (Holdings Cost)** only. Lock to this in API and UX. Option A (Net Invested) requires a crisp cash-flow model (deposits/withdrawals, transfers, FX, fees, “allocated to stocks”); defer until that model exists.
- **Holdings Cost vs tax-lot cost basis:** Baseline B uses **weighted average cost** (your existing model). This is not the same as FIFO/LIFO/specific-lot cost basis. Many apps show “cost basis” as average cost (especially outside US tax contexts). If you later add lot tracking, the baseline definition may change; document the choice in the UI (e.g. “Holdings cost (avg)”).
- **Tooltip and axis labels** must use the same term (e.g. “Holdings Cost (avg)”) and the same definition as the baseline.

#### 1.1.1 Cost Basis Mechanics (Average Cost) — Enforce in Code

Baseline = avg_cost × shares **only** if avg_cost is updated correctly. A naive implementation that recomputes “average cost” using sells is wrong: on SELL, **avg_cost must not change**; only shares change (and realized P/L can be tracked separately).

**Per-symbol state:** `shares`, `avg_cost` (and optionally `realized_pnl`).

- **BUY:**  
  - `avg_cost = (prev_shares * prev_avg_cost + buy_qty * buy_price + fees) / (prev_shares + buy_qty)`  
  - `shares += buy_qty`
- **SELL:**  
  - `shares -= sell_qty`  
  - **avg_cost unchanged**  
  - (Optional: `realized_pnl += sell_qty * (sell_price - avg_cost) - fees` or similar.)
- **When shares == 0:** reset `avg_cost = 0` (or null) so the next BUY starts fresh.

Implement this in the day-by-day holdings loop (and in any existing portfolio summary logic) so the baseline curve is stable and does not drift on sells.

### 1.2 Cash: Include vs Exclude

**Problem:** If you exclude cash, the curve drops after a sell (proceeds go to cash but are not counted). Many users interpret the chart as “my account value”, so that feels wrong.

**Recommendation:**
- **Default:** Include cash — curve = **portfolio equity** (stocks + cash). This is what most apps show.
- **Toggle:** “Include cash” / “Exclude cash”. When excluded, label clearly: e.g. “Stock holdings value” or “Equity excluding cash” so users don’t confuse it with total account value.

**Requirement for historical cash:** To support `include_cash=true` correctly over time, the system must be able to reconstruct **cash balance at each date**. That requires a well-defined cash model.

**Cash model v1 (minimum viable):**
- **Transaction types:** CASH_DEPOSIT, CASH_WITHDRAW, and BUY/SELL with fees. (Optionally: FEE, DIVIDEND, INTEREST.)
- **Starting cash:** Per-account starting balance, or an initial CASH_DEPOSIT (or equivalent) so cash at “day 0” is defined.
- **BUY:** Reduces cash by `shares × price + fees`.
- **SELL:** Increases cash by `shares × price − fees`.
- **CASH_DEPOSIT / CASH_WITHDRAW:** Add/subtract amount by date.

If this is in place, `include_cash=true` is correct. If the cash ledger is **incomplete** (e.g. no deposits/withdrawals or no starting cash), apply a **hard gate**:
- **Option 1:** Default `include_cash=false` and disable the include_cash toggle (or hide it) until the cash model is complete.
- **Option 2:** Show the toggle but label **“Cash (partial)”** and add a tooltip/warning: “Historical cash may be incomplete; equity curve may not match broker statements.”

Prefer implementing the minimal cash model and then defaulting to `include_cash=true`; otherwise use Option 1 or 2 so users don’t distrust the curve.

---

## 2. Architecture Design

### 2.1 High-Level Flow

```
Frontend Request → Backend API → Historical Price Service → Cache/Storage → yfinance
                    ↓
              Portfolio Service (compute holdings at each date)
                    ↓
              Return time series data
```

### 2.2 Core Components

1. **HistoricalPriceService** (Backend)
   - Fetches historical prices for symbols
   - Implements caching strategy
   - Handles market holidays

2. **NetValueService** (Backend)
   - Computes portfolio holdings at each date (incremental; see §3.2)
   - Calculates baseline (Holdings Cost in v1) and market value; supports include/exclude cash
   - Returns time series data (columnar arrays only; see §3.3)

3. **NetValueCurve Component** (Frontend)
   - Chart visualization (using a charting library)
   - Zoom controls (7d, 30d, all)
   - Hover tooltips

---

## 3. Backend Design

### 3.1 Historical Price Service

**File:** `src/service/historical_price_service.py`

**Responsibilities:**
- Fetch historical prices from yfinance
- Cache historical data efficiently
- Handle market holidays (use previous trading day's price)

**Key Methods:**

```python
class HistoricalPriceService:
    def get_historical_prices(
        self,
        symbols: list[str],
        start_date: datetime,
        end_date: datetime
    ) -> dict[str, list[dict]]:
        """
        Returns: {symbol: [{"date": "2024-01-01", "close": 150.0}, ...]}
        """
        
    def get_price_on_date(
        self,
        symbol: str,
        target_date: datetime
    ) -> Optional[float]:
        """
        Get price for a symbol on a specific date.
        If market holiday, returns previous trading day's price.
        """
```

**Caching Strategy:**

1. **SQLite (persistent, source of truth)**
   - Store by **(symbol, date)** only. Schema records **which price** the curve uses (see §3.1.1). V1 uses **close** (unadjusted) for market value:
     ```sql
     CREATE TABLE historical_prices (
         symbol TEXT NOT NULL,
         date TEXT NOT NULL,
         close_price REAL NOT NULL,
         adj_close_price REAL,
         price_type TEXT NOT NULL DEFAULT 'close',
         updated_at TEXT NOT NULL,
         PRIMARY KEY (symbol, date)
     )
     ```
     - Curve uses `close_price` when `price_type = 'close'`. Optionally store `adj_close_price` for future return/indexed views.
   - Lookup: for a requested range, query `WHERE symbol IN (...) AND date BETWEEN ? AND ?`.
   - **Do not** invalidate this cache on transaction create/edit/delete. Transaction changes do not change historical market prices; they only change holdings and baseline. Invalidating would cause unnecessary yfinance refetches.

2. **In-Memory (optional speed-up)**
   - **Do not** cache by `(symbol, start_date, end_date)` — different zoom ranges would yield different keys and low hit rates.
   - Prefer: per-symbol **LRU of (date → price)** or “latest fetched span” per symbol, so any request that needs that symbol’s dates can hit memory first.
   - Alternatively: cache the **API response payload** (net value curve) by `(account_filter, start_date, end_date, include_cash)` with short TTL, and never cache raw prices by range in memory.

3. **Fetch Strategy (defensive batching):**
   - yfinance multi-ticker download (e.g. `yf.download([...])`) returns multi-indexed data and can **fail partially** (some tickers missing; different exchanges/timezones). Do not assume one call returns all symbols.
   - **Approach:** Try batch download for the requested symbols and date range. Detect which symbols (or date ranges) are missing or invalid. **Retry failed tickers individually**, then persist per-ticker results into SQLite by (symbol, date).
   - Forward-fill: for weekends/holidays use previous trading day’s price (see §5).

4. **Corporate actions and price type (see §3.1.1):** For “Market Value (市值)” the curve must be **shares × price**. Using Adjusted Close with **unchanged** (unadjusted) shares can be wrong: adj_close is split-adjusted, so shares × adj_close is inconsistent for past dates unless shares are also split-adjusted. **V1 recommendation:** use **Close** (unadjusted) for market value; store and document `price_type: 'close'`.

### 3.1.1 Corporate Actions and Symbol Events

Splits, dividends, ticker changes, and delistings affect the curve unless handled.

**Fix A — Use Close for market value (recommended for portfolio “value”):**
- **Store** `close_price` (unadjusted). Compute **market_value = Σ(shares_today × close_today)**.
- You are correct for “what it would be worth at close” given today’s share counts.
- Splits: if transactions after a split use **post-split** shares (as most brokers and imports do), your share counts are already correct and close is correct for that date. No need to adjust historical shares when using close.
- **API/UI:** Label as “Market Value (市值)”; no disclaimer needed for broker match on value.

**Fix B — Use Adj Close but relabel (for “return curve” only):**
- If you ever add a **return/indexed** curve, use Adjusted Close and **rename** the series to e.g. “Split/dividend-adjusted value (proxy)” or “Indexed value”. Document: “This curve is adjusted for corporate actions; it may not match broker statement value exactly.” Do **not** label it “Market Value (市值)” so users don’t expect Fix A.

**V1 decision:** Use **Fix A**. Store `close_price`; set `price_type = 'close'` in schema. Optionally store `adj_close_price` for future return/indexed views. Response includes `price_type: "close"` so the frontend can label correctly.

### 3.2 Net Value Service

**File:** `src/service/net_value_service.py`

**Responsibilities:**
- Compute portfolio holdings at each date (incremental; see algorithm below)
- Calculate **baseline** (Holdings Cost **or** Net Invested, per product choice in §1.1) and market value
- Support **include_cash** (default true): when true, add cash balance at each date to market value so the curve is portfolio equity
- Generate time series as **columnar arrays only** (no duplicate `daily_data` list)

**Key Method:**

```python
class NetValueService:
    def __init__(
        self,
        transaction_service: TransactionService,
        historical_price_service: HistoricalPriceService,
    ):
        self._txn_svc = transaction_service
        self._price_svc = historical_price_service
        # v1: baseline is always Holdings Cost

    def get_net_value_curve(
        self,
        account_names: Optional[list[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_cash: bool = True,
    ) -> dict:
        """
        Returns columnar arrays only (no daily_data list):
        {
            "dates": ["2024-01-01", "2024-01-02", ...],
            "baseline": [10000.0, 10000.0, 10500.0, ...],
            "market_value": [10000.0, 10100.0, 10600.0, ...],
            "profit_loss": [0.0, 100.0, 100.0, ...],
            "profit_loss_pct": [0.0, 1.0, 0.95, ...],
            "is_trading_day": [true, true, false, ...],
        }
        - baseline: Holdings Cost (v1).
        - profit_loss = market_value - baseline.
        - profit_loss_pct = (profit_loss / baseline) * 100 when baseline > 0; else null or omit (frontend shows "—").
        - is_trading_day: false for weekends/holidays.
        - last_trading_date: actual last trading date whose close was used (for tooltip "Last trading close: {date}").
        - baseline_label, price_type, includes_cash: see response schema (§3.3).
        """
```

**Transaction date rule (timezone / intraday):** Pick **one** consistent rule and document it. Do not leave “optionally apply at EOD” ambiguous.

- **Trade date:** All transactions are applied by **US/Eastern trade date**. Convert `txn_time_est` to US/Eastern and take the **calendar date**. For imports: determine trade date in US/Eastern; **ignore time-of-day for v1**.
- **When to apply vs close:** **All transactions on trade date T are applied before computing that date’s close value.** So the value at T uses positions and cash **after** applying every transaction on T. This matches “trades during the day affect that day’s closing snapshot.” (Alternative “applied after close” is less common and would value T’s close without that day’s trades; do not use for v1 unless explicitly chosen.)

**Algorithm (explicit; biggest compute cost is holdings-by-day):**

1. **Pre-index transactions by date**
   - Get all transactions (filtered by account_names), sort by `txn_time_est` ascending.
   - Normalize each transaction’s date using the rule above (US/Eastern trade date).
   - Build a map: `date → list of transactions on that date`.

2. **Build the list of calendar days** from `start_date` to `end_date` (inclusive). Forward-fill will apply to prices and to holdings (holdings only change on transaction dates).

3. **Iterate day-by-day:**
   - **Holdings:** Start with empty holdings and cash. For each day:
     - Apply all transactions with that date (BUY/SELL/CASH_DEPOSIT/CASH_WITHDRAW) to update holdings and cash.
     - Holdings and cash are otherwise **constant** (forward-filled) until the next transaction date.
   - **Baseline (v1):** Holdings Cost only = sum over symbols of (avg cost × current shares). Use **avg-cost mechanics** from §1.1.1: BUY updates avg_cost; SELL leaves avg_cost unchanged; when shares==0 reset avg_cost.
   - **Market value:** For that day, get price per symbol (from HistoricalPriceService; forward-filled for non-trading days). Then `market_value = dot(holdings, prices_on_day)`. If `include_cash`, add cash balance at end of that day.

4. **Vectorize where possible:** e.g. request all needed (symbol, date) prices in one or few batch calls; compute market_value as dot product per day.

**Symbol set for price fetch:** Do not fetch only “currently held” symbols — holdings change over time, so you would miss symbols held earlier in the window and market value would be wrong in the past.

- **Definition:** `symbols_in_range = { symbol | position shares ≠ 0 on any date in [start_date, end_date] }`.
- **Implementation:** While iterating day-by-day, track every symbol that ever has nonzero shares in the range; or precompute from the transaction list: all symbols that appear in any BUY/SELL in the date range (safe superset). Fetch prices from HistoricalPriceService only for this set (and use it for `refresh` overwrite scope).

**Performance:**
- Batch fetch all historical prices for `symbols_in_range × dates` upfront; use SQLite (and optional in-memory LRU per symbol).
- No price cache invalidation on transaction changes; only recompute net value when transactions change.

### 3.3 API Endpoint

**File:** `src/app/api/routers/net_value.py` (new)

**Endpoint:** `GET /net-value-curve`

**Query Parameters:**
- `account`: Optional list of account names (same as portfolio endpoint)
- `start_date`: Optional ISO date string (default: first transaction date)
- `end_date`: Optional ISO date string (default: today)
- `include_cash`: Optional boolean (default: true) — when true, market value = equity (stocks + cash)
- `refresh`: Optional (default: false). **Contract:** When `refresh=1` (or `true`), the server **overwrites** cached price rows in the requested `[start_date, end_date]` for **symbols_in_range** (see §3.2). Fetches from yfinance and writes back to SQLite for those (symbol, date) pairs. No transaction-based invalidation. Optional: `refresh=recent` could mean “overwrite only last N days.”

**Response Schema (columnar; tooltips reconstruct from index). Include metadata so frontend labels stay in sync with backend:**

```python
class NetValueCurveResponse(BaseModel):
    # Metadata (prevent UI/backend drift)
    baseline_label: str = "Holdings Cost (avg)"
    price_type: str = "close"           # "close" | "adj_close"
    includes_cash: bool = True           # echo of request

    dates: list[str]                    # ISO date strings
    baseline: list[float]
    market_value: list[float]
    profit_loss: list[float]
    profit_loss_pct: list[Optional[float]]
    is_trading_day: list[bool]
    last_trading_date: list[str]        # ISO date of last trading day used for price (for tooltip)
```

- **last_trading_date:** Same length as `dates`. For calendar date `dates[i]`, if `is_trading_day[i]` is false (weekend/holiday), `last_trading_date[i]` is the **actual** last trading date whose close was used (e.g. for Sunday 2026-02-15, might be `"2026-02-13"`). Tooltip: **“Last trading close: {last_trading_date[i]}”** so users see the real date, not the calendar date.

**P/L % definition:** `profit_loss_pct[i] = (profit_loss[i] / baseline[i]) * 100` when `baseline[i] > 0`; otherwise `null`. Frontend shows "—" when baseline is 0.

---

## 4. Frontend Design

### 4.1 Chart Library Selection

**Recommendation:** Use **Recharts** (React charting library)

**Reasons:**
- React-native, works well with TypeScript
- Good performance
- Supports area charts, tooltips, zoom
- Easy to customize colors (green/red for profit/loss)
- Lightweight

**Alternative:** Chart.js with react-chartjs-2 (more features but heavier)

**Installation:**
```bash
npm install recharts
```

### 4.2 NetValueCurve Component

**File:** `frontend/src/components/NetValueCurve/NetValueCurve.tsx`

**Features:**
- Area chart with two lines: **baseline** (Holdings Cost or Net Invested — label must match API) and **market value**
- Fill between lines (green when profit, red when loss)
- **Include cash** toggle (default on); when off, label chart e.g. "Stock holdings value" / "Equity excluding cash"
- Hover tooltip showing:
  - Date
  - On non-trading days: e.g. "Last trading close: &lt;date&gt;" so users don’t think the market traded
  - Baseline (same label as axis, e.g. "Holdings Cost")
  - Market value
  - Profit/loss (absolute)
  - Profit/loss % (with denominator = baseline; show "—" when baseline is 0)
- Zoom controls: 7 days, 30 days, all time
- Loading state
- Error handling

**Data:** Consume columnar response including **`baseline_label`**, **`price_type`**, **`includes_cash`** (use for axis/toggle labels so UI never drifts from backend), and **`last_trading_date`** for non-trading-day tooltips. Build chart series from index (e.g. `data[i] = { date: dates[i], baseline: baseline[i], last_trading_date: last_trading_date[i], ... }`).

**Component Structure:**

```typescript
interface NetValueCurveResponse {
  baseline_label: string;      // e.g. "Holdings Cost (avg)"
  price_type: string;          // "close" | "adj_close"
  includes_cash: boolean;

  dates: string[];
  baseline: number[];
  market_value: number[];
  profit_loss: number[];
  profit_loss_pct: (number | null)[];
  is_trading_day: boolean[];
  last_trading_date: string[];  // actual last trading date per point (for tooltip)
}
```

**Visual Design:**
- Baseline line: Gray/dashed; **label = `baseline_label`** from API (e.g. "Holdings Cost (avg)").
- Market value line: Blue/solid (Market Value / 市值).
- Fill area: Green when market_value > baseline, red when market_value < baseline.
- Tooltip: Date; when `!is_trading_day`, show **"Last trading close: {last_trading_date[i]}"**; baseline, market value, P/L, P/L% (or "—" if baseline is 0). Use `baseline_label` for the baseline name in the tooltip.

### 4.3 API Client Method

**File:** `frontend/src/api/client.ts`

**Add method:**

```typescript
async getNetValueCurve(
  accountNames?: string[],
  startDate?: string,
  endDate?: string,
  includeCash: boolean = true,
  refresh?: boolean
): Promise<NetValueCurveResponse> {
  const params = new URLSearchParams();
  if (accountNames?.length) accountNames.forEach(acc => params.append('account', acc));
  if (startDate) params.set('start_date', startDate);
  if (endDate) params.set('end_date', endDate);
  params.set('include_cash', includeCash ? 'true' : 'false');
  if (refresh) params.set('refresh', 'true');
  const response = await fetch(`/api/net-value-curve?${params}`);
  if (!response.ok) throw new Error('Failed to fetch net value curve');
  return response.json();
}
```

### 4.4 Integration into App

**Location:** Add below `GeneralOverviewBlock` or above `PortfolioBlock`

**State Management:**
- Fetch when `selectedAccountNames` changes
- Refetch when transactions are added/edited/deleted (via `refreshKey`)

---

## 5. Market Holidays / Non-Trading Days

### 5.1 Approach: Forward-Fill (Explicit)

- **Prices:** Use previous trading day’s close for weekends/holidays (forward-fill). yfinance returns no row or NaN for non-trading days; we fill from last known close.
- **Holdings:** Holdings (and cash) only change on **transaction dates**. On non-trading days we do not apply any new transactions, so holdings are implicitly forward-filled (same as previous calendar day).
- **Date range:** Generate **calendar days** from start to end. Each day has a value (price and holdings forward-filled). Curve is continuous; no gaps.

### 5.2 Tooltip on Non-Trading Days

- Backend returns `is_trading_day: list[bool]` and **`last_trading_date: list[str]`** (same length as `dates`).
- When `is_trading_day[i] === false`, tooltip must show the **actual** last trading date, e.g. **"Last trading close: {last_trading_date[i]}"** (e.g. `2026-02-13` for a Sunday 2026-02-15 point). Do not show the calendar date as if it were the trading date; use `last_trading_date[i]` so users see which close was used.

---

## 6. Performance Considerations

### 6.1 Data Fetching Optimization

**Problem:** Fetching historical prices for many symbols over long periods is slow.

**Solutions:**

1. **Batch Fetching:**
   - Fetch all symbols for date range in one yfinance call
   - yfinance supports: `ticker.history(start=start, end=end)`

2. **Incremental Cache Updates:**
   - Only fetch missing dates from yfinance
   - Use cached data for existing dates

3. **Lazy Loading:**
   - Frontend requests data only for visible date range
   - When zooming, fetch additional data if needed

4. **Pagination/Chunking:**
   - For very long date ranges, fetch in chunks
   - Frontend can request specific ranges

### 6.2 Computation Optimization (Holdings-by-Day)

**The main compute cost is holdings-by-day, not price fetches.**

1. **Pre-index transactions by date:** Build `date → [transactions]` once.
2. **Single day-by-day pass:** For each calendar day, apply only transactions on that date; otherwise holdings and cash stay unchanged (forward-filled).
3. **Market value per day:** `market_value = dot(holdings, prices_on_day)`. Batch all (symbol, date) price lookups; vectorize by symbol/date where possible.
4. **No price cache invalidation on transaction changes** — only recompute net value when the user (or UI) refetches after add/edit/delete.

### 6.3 Frontend Optimization

1. **Debounce Zoom Changes:**
   - Don't refetch immediately on zoom
   - Wait for user to settle on a zoom level

2. **Virtual Scrolling (if needed):**
   - For very long date ranges, render only visible points

3. **Data Sampling (correctness-preserving):**
   - Naive sampling (e.g. every Nth day) can drop large drawdowns/spikes and misstate P/L around transaction-heavy periods.
   - **Rule:** Use **daily** for range ≤ 1 year; **weekly** (e.g. week-end points) for > 1 year; **monthly** (month-end) for > 5 years (or similar thresholds). **Always keep** a data point on every **transaction date** and at **period endpoints** (start_date, end_date). So when downsampling, merge: required points (txn dates + endpoints) ∪ sampled points (e.g. weekly or monthly). This preserves correctness at trade dates and avoids missing big moves.

---

## 7. Implementation Plan

### Phase 1: Backend Core (Week 1)

1. **Create HistoricalPriceService**
   - Implement SQLite (symbol, date) cache for **close_price** (v1 curve uses close); optional adj_close_price; price_type = 'close'
   - Optional in-memory: LRU per symbol (date→price) or latest span
   - Implement price fetching with forward-fill; return **last_trading_date** per point when forward-filled; do not invalidate on transaction changes

2. **Create NetValueService**
   - Pre-index transactions by date; day-by-day incremental holdings using **avg-cost mechanics** (§1.1.1); baseline + market value (include_cash option)
   - **symbols_in_range** for price fetch/refresh; transactions on T applied before T’s close
   - Return columnar arrays + baseline_label, price_type, includes_cash, last_trading_date; P/L% (null when baseline=0)

3. **Create API Endpoint**
   - Add `/net-value-curve` route
   - Add request/response schemas
   - Add error handling

4. **Tests**
   - Unit tests for services
   - Integration tests for API

### Phase 2: Frontend Core (Week 2)

1. **Install Dependencies**
   - Add recharts to package.json

2. **Create NetValueCurve Component**
   - Chart: baseline + market value; use **baseline_label**, **price_type**, **includes_cash** from API for axis/toggle labels
   - Include-cash toggle (respect gate if cash model incomplete); when off, label "Stock holdings value"
   - Fill area (green/red)
   - Tooltip: date; when `!is_trading_day` show "Last trading close: {last_trading_date[i]}"; baseline, market value, P/L, P/L% (or "—" when baseline=0)

3. **Add API Client Method**
   - Implement `getNetValueCurve()`

4. **Integrate into App**
   - Add component to App.tsx
   - Connect to account filter
   - Add loading/error states

### Phase 3: Enhancements (Week 3)

1. **Zoom Controls**
   - Add 7d/30d/all buttons
   - Implement date range filtering

2. **Polish**
   - Improve tooltip design
   - Add animations
   - Responsive design

3. **Performance Tuning**
   - Optimize data fetching (defensive batch + per-ticker retry)
   - Add loading indicators
   - Implement sampling rule: daily ≤1y, weekly >1y, monthly >5y; keep txn dates + endpoints (§6.3)

---

## 8. Database Schema Changes

### New Table: `historical_prices`

Store the price type used for the curve (see §3.1.1). **V1 uses Close (unadjusted)** for market value.

```sql
CREATE TABLE IF NOT EXISTS historical_prices (
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    close_price REAL NOT NULL,
    adj_close_price REAL,
    price_type TEXT NOT NULL DEFAULT 'close',
    updated_at TEXT NOT NULL,
    PRIMARY KEY (symbol, date)
);

CREATE INDEX idx_historical_prices_symbol_date ON historical_prices(symbol, date);
```

- For v1: populate `close_price` from yfinance; curve uses it (`price_type = 'close'`). Optionally store `adj_close_price` for future return/indexed views.
- **Migration:** Add migration script to create table on first run. No data migration needed (empty initially).

---

## 9. Error Handling

### Backend Errors

1. **yfinance API Failures:**
   - Return partial data (available symbols)
   - Log errors
   - Return error message in response

2. **Missing Historical Data:**
   - For symbols without historical data, use current price for all dates
   - Or exclude from calculation

3. **Invalid Date Ranges:**
   - Validate start_date < end_date
   - Return 400 error

### Frontend Errors

1. **API Failures:**
   - Show error message
   - Allow retry

2. **Empty Data:**
   - Show message: "No data available"
   - Suggest checking date range

3. **Loading States:**
   - Show spinner while fetching
   - Disable zoom controls during load

---

## 10. Testing Strategy

### Backend Tests

1. **HistoricalPriceService:**
   - Test SQLite (symbol, date) lookup and fill from yfinance
   - Test forward-fill for weekends/holidays; test `last_trading_date` for non-trading days
   - Test that curve uses close (price_type = 'close')
   - Test defensive fetch: partial batch failure → retry failed tickers individually
   - No tests for “invalidate on transaction change” (we do not do that)

2. **NetValueService:**
   - Test incremental holdings by date
   - Test **avg-cost mechanics:** BUY updates avg_cost; SELL leaves avg_cost unchanged, only shares decrease; shares==0 ⇒ avg_cost reset (§1.1.1)
   - Test baseline (Holdings Cost) and market value (with/without cash)
   - Test P/L% when baseline > 0 and when baseline = 0
   - Test transaction date: US/Eastern trade date; transactions on T applied **before** T’s close value
   - Test symbols_in_range: price fetch includes every symbol with nonzero shares on any date in range

3. **API Tests:**
   - Test endpoint with various parameters (account, include_cash, start_date, end_date)
   - Test response includes baseline_label, price_type, includes_cash, last_trading_date
   - Test refresh=1: overwrites cached rows in [start, end] for symbols_in_range
   - Test error cases

### Frontend Tests

1. **Component Tests:**
   - Test chart rendering
   - Test zoom functionality
   - Test tooltip display

2. **Integration Tests:**
   - Test data flow from API to chart
   - Test account filter integration

---

## 11. Future Enhancements

1. **Export Chart:**
   - Export as PNG/SVG
   - Export data as CSV

2. **Comparison:**
   - Compare against benchmark (e.g., S&P 500)

3. **Multiple Timeframes:**
   - Daily, weekly, monthly views

4. **Annotations:**
   - Mark transaction dates on chart

5. **Performance Metrics:**
   - Show CAGR, Sharpe ratio, etc.

---

## 12. Summary

| Component | Technology | Key Features |
|-----------|-----------|--------------|
| Backend Service | Python | Historical price (symbol, date) cache; net value recomputed on demand |
| API Endpoint | FastAPI | `/net-value-curve` with account filter and include_cash |
| Frontend Chart | Recharts | Baseline + market value; include-cash toggle; tooltip “Last trading close” when not trading day |
| Cache | SQLite | (symbol, date) → close; in-memory LRU per symbol optional; **no** invalidation on transaction changes |

**Key Design Decisions:**
1. **Baseline (v1):** Holdings Cost (avg) only; **avg-cost mechanics** enforced: BUY updates avg_cost; SELL leaves avg_cost unchanged; shares==0 ⇒ reset avg_cost (§1.1.1). Option A deferred. API returns `baseline_label: "Holdings Cost (avg)"`.
2. **Cash:** Minimal cash model (CASH_DEPOSIT, CASH_WITHDRAW, BUY/SELL+fees; starting cash or initial deposit). If incomplete: gate — default include_cash=false or label “Cash (partial)” with tooltip.
3. **Market value:** Use **Close** (unadjusted) for “Market Value (市值)” so shares × close is correct; store `price_type: 'close'`. Adj close reserved for future return curve. API returns `price_type`, `includes_cash`.
4. **P/L%:** Denominator = baseline; show “—” when baseline = 0.
5. **Prices:** Cache by (symbol, date); never invalidate on transaction changes. **symbols_in_range** = symbols with nonzero shares on any date in [start,end]; fetch and refresh only that set. Defensive batch fetch: retry failed tickers individually.
6. **refresh:** refresh=1 overwrites cached rows in [start, end] for symbols_in_range.
7. **Transaction date:** US/Eastern trade date; ignore time for v1. **Rule:** Transactions on date T are applied **before** computing T’s close value.
8. **Response:** Columnar arrays + `baseline_label`, `price_type`, `includes_cash`, `last_trading_date` (actual last trading date per point for tooltip “Last trading close: {date}”).
9. **Sampling:** Daily ≤1y, weekly >1y, monthly >5y; always keep points on transaction dates + period endpoints.
10. **Currency:** V1 USD only; FX deferred.
11. Forward-fill prices and holdings on non-trading days (continuous curve).
