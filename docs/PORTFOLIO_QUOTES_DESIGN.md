# Portfolio Quotes — Design Document (Yahoo Finance)

This document extends the **Portfolio Summary** feature by adding **live quote data** (current price and company name) for each stock in the portfolio, and defining the **computed fields** (市值, 浮动盈亏, 盈亏比例, 占比) so the holdings table can display a full “持仓明细” row per stock.

**Dependencies:** Assumes the base portfolio is implemented as in `PORTFOLIO_SUMMARY_DESIGN.md` and the frontend as in `PORTFOLIO_SUMMARY_FRONTEND.md`. This feature adds quote fetching and enriches the portfolio response (or a dedicated endpoint) with price, name, and derived metrics.

---

## 1. Overview

### 1.1 Goal

- For each **symbol** in the portfolio (from transactions), call a **Yahoo Finance** data source to retrieve:
  - **Current price** (最新价)
  - **Full company name** (名称), for display under the symbol in the “代码/名称” column.
- Using that data, **compute and expose** for each position:
  - 代码/名称 — symbol + name (from quote)
  - 最新价 — latest price (from quote)
  - 成本价 — average cost (from portfolio: `total_cost / quantity`)
  - 持仓数量 — quantity (from portfolio)
  - 市值 — market value = `quantity × latest_price`
  - 浮动盈亏 — unrealized P/L = `market_value - total_cost`
  - 盈亏比例 — P/L % = `(market_value - total_cost) / total_cost × 100`
  - 占比 — weight % = `market_value / total_portfolio_market_value × 100` (where total = sum of all positions’ market_value)

### 1.2 Data source: Yahoo Finance via yfinance

- **Yahoo** does not offer an official public API. The standard approach is the **yfinance** Python library, which fetches data from Yahoo Finance’s web endpoints.
- **Backend only:** Quote fetching is done on the server (Python). The frontend does not call Yahoo or any external quote API directly.
- **Legal / ToS:** yfinance is unofficial and not endorsed by Yahoo. Use for personal or internal tools; review Yahoo’s terms before commercial use.

---

## 2. Backend: Quote Data

### 2.1 Library and usage

- **Library:** `yfinance` (add to `requirements.txt`).
- **Usage:** For each symbol in the portfolio, obtain a `Ticker(symbol)` and read:
  - **Price:** Prefer `info.get("currentPrice")`. Fallback: `info.get("regularMarketPrice")` or `fast_info.get("lastPrice")` if available.
  - **Name:** Prefer `info.get("longName")`. Fallback: `info.get("shortName")` or `symbol` if missing.
- **Batch:** Use `yf.Tickers("SYM1 SYM2 ...")` to request multiple symbols in one go where possible, to reduce round-trips and rate-limit risk. Then for each symbol, read `tickers.tickers[symbol].info` (or equivalent) to get `currentPrice` and `longName`/`shortName`.

### 2.2 Quote service (backend)

- **New module:** e.g. `src/service/quote_service.py` (or `quote/yahoo_quote_service.py`).
- **Responsibilities:**
  - `get_quotes(symbols: list[str]) -> dict[str, QuoteResult]`
  - For each symbol, return a small structure, e.g. `{ "current_price": float | None, "display_name": str }`. `display_name` = longName or shortName or symbol.
  - Use in-memory **cache** with a short TTL (e.g. 60–300 seconds) keyed by symbol. So repeated portfolio loads within the TTL do not hit Yahoo again for the same symbol.
- **Errors:** If a symbol fails (timeout, not found, missing price), return `current_price: None` and `display_name: symbol` (or "—") so the rest of the portfolio still renders; the row for that symbol can show “—” for 最新价 and derived fields.

### 2.3 Caching

- **Why:** Avoid hitting Yahoo on every portfolio request; reduce rate-limit and latency.
- **What:** Cache per symbol: `current_price`, `display_name`.
- **TTL:** Configurable (e.g. 60–300 seconds). Default suggestion: **120 seconds**.
- **Scope:** In-process cache is enough for a single-instance app (e.g. dict + timestamp per symbol). For multiple workers, consider a shared cache (e.g. Redis) later.
- **Invalidation:** TTL-only is sufficient for v1; no manual invalidation required.

### 2.4 Rate limits and robustness

- **Throttling:** If the portfolio has many symbols, consider batching (e.g. request up to N symbols at a time with a small delay between batches) to avoid 429s. yfinance may do some of this internally; document “best effort” and handle failures per symbol.
- **Timeouts:** Set a timeout (e.g. 5–10 s) for quote fetches so one slow symbol does not block the whole response. On timeout, treat that symbol as “no quote” (current_price None).
- **No API key:** yfinance does not require an API key; no secrets to manage.

---

## 3. Portfolio API Extension

### 3.1 Option A: Enrich GET /portfolio (recommended)

- **Same endpoint:** `GET /portfolio?account=...`
- **Response:** Extend each item in `positions[]` with quote and computed fields.

**Extended position shape:**

```json
{
  "symbol": "NVDA",
  "quantity": 37,
  "total_cost": 5069.00,
  "display_name": "NVIDIA CORP",
  "latest_price": 185.41,
  "cost_price": 137.00,
  "market_value": 6860.17,
  "unrealized_pnl": 1791.17,
  "unrealized_pnl_pct": 35.34,
  "weight_pct": 28.87
}
```

- **Backend computation:**
  - `cost_price` = `total_cost / quantity` (2 decimals).
  - After fetching quotes for all symbols in the portfolio:
    - `latest_price` = quote’s current price (or null if missing).
    - `market_value` = `quantity * latest_price` (null if no price).
    - `unrealized_pnl` = `market_value - total_cost` (null if no price).
    - `unrealized_pnl_pct` = `(market_value - total_cost) / total_cost * 100` (null if no price).
  - **Total portfolio market value** = sum of all positions’ `market_value` (only positions with non-null `market_value`).
  - `weight_pct` = for each position, `market_value / total_portfolio_market_value * 100` (null if no price or total is 0).

- **Optional query flag:** e.g. `GET /portfolio?account=...&quotes=0` to skip quote fetch and return only `symbol`, `quantity`, `total_cost` (and optionally `cost_price`) for lighter/faster responses or when quote service is down. Default: `quotes=1` (or omit) = include quotes and computed fields.

### 3.2 Option B: Separate quotes endpoint

- **Endpoint:** e.g. `GET /portfolio/quotes?symbols=AAPL,NVDA,...` returning only `{ symbol → { current_price, display_name } }`.
- **Frontend:** Calls GET /portfolio (positions only), then GET /portfolio/quotes for the list of symbols, then computes 市值, 浮动盈亏, 盈亏比例, 占比 on the client.
- **Trade-off:** More flexible (e.g. refresh quotes without recomputing portfolio) but two round-trips and more frontend logic. Option A is simpler for “one portfolio view” and keeps logic on the server.

**Recommendation:** Option A (enriched GET /portfolio) for a single, comprehensive portfolio response.

---

## 4. Field Definitions (Row Example)

| Column (中文) | API field | Formula / source |
|---------------|-----------|-------------------|
| 代码/名称 | `symbol`, `display_name` | From portfolio + quote. Display: symbol (bold), display_name below. |
| 最新价 | `latest_price` | From Yahoo (quote). |
| 成本价 | `cost_price` | `total_cost / quantity`. |
| 持仓数量 | `quantity` | From portfolio. |
| 市值 | `market_value` | `quantity × latest_price`. |
| 浮动盈亏 | `unrealized_pnl` | `market_value - total_cost`. |
| 盈亏比例 | `unrealized_pnl_pct` | `(market_value - total_cost) / total_cost × 100` (e.g. +35.34). |
| 占比 | `weight_pct` | `market_value / total_portfolio_market_value × 100` (e.g. 28.87). |

**Example row (NVDA):**

- 代码/名称: **NVDA** / NVIDIA CORP  
- 最新价: 185.41  
- 成本价: 137.00  
- 持仓数量: 37  
- 市值: $6,860.17 (or $6.86K)  
- 浮动盈亏: +$1,791.17 (green)  
- 盈亏比例: +35.34% (green)  
- 占比: 28.87% (e.g. progress bar)

**When quote is missing:** Show “—” or “N/A” for 最新价, 市值, 浮动盈亏, 盈亏比例, 占比; still show 代码 (symbol), 成本价, 持仓数量.

---

## 5. Backend Implementation Outline

1. **requirements.txt:** Add `yfinance` (pin a recent version, e.g. `yfinance>=0.2.40`).
2. **Quote service:** `src/service/quote_service.py` (or under a `quotes` package):
   - In-memory cache: `dict[symbol, (current_price, display_name, cached_at)]` with TTL.
   - `get_quotes(symbols: list[str]) -> dict[str, { "current_price": float | None, "display_name": str }]`.
   - Use `yf.Tickers(" ".join(symbols))` then for each symbol read `info["currentPrice"]`, `info.get("longName") or info.get("shortName") or symbol`. Catch exceptions per symbol; on failure put `current_price: None`, `display_name: symbol`.
3. **Portfolio service:** After computing positions (symbol, quantity, total_cost):
   - Collect unique symbols from positions.
   - Call quote service `get_quotes(symbols)`.
   - For each position, attach `display_name`, `latest_price`, then compute `cost_price`, `market_value`, `unrealized_pnl`, `unrealized_pnl_pct`. Sum `market_value` for total, then set `weight_pct` per position.
4. **Schema:** Extend Pydantic model for position, e.g. `PortfolioPositionEnriched` with optional fields `display_name`, `latest_price`, `cost_price`, `market_value`, `unrealized_pnl`, `unrealized_pnl_pct`, `weight_pct`. All computed/numeric fields nullable for “quote missing” case.
5. **Router:** Keep `GET /portfolio`. If `quotes=0`, return positions without quote enrichment; otherwise (default) return enriched positions.
6. **Tests:** Unit tests for quote service (mock yfinance): cache TTL, missing symbol, timeout. Unit tests for portfolio service: given mock quote data, assert computed fields (market_value, pnl, weight_pct).

---

## 6. Frontend Updates

- **Types:** Extend `PortfolioPosition` (or introduce `PortfolioPositionEnriched`) with optional `display_name`, `latest_price`, `cost_price`, `market_value`, `unrealized_pnl`, `unrealized_pnl_pct`, `weight_pct`. See `PORTFOLIO_SUMMARY_FRONTEND.md` §3.3 for the table columns that already anticipate these.
- **Table:** Render all eight columns. For 代码/名称: symbol (bold) + `display_name` on second line (or “—” if no name). Format 市值/浮动盈亏 as currency (e.g. $6.86K); 盈亏比例 with “+” and “%”; 占比 as percentage + optional progress bar. Profit in green, loss in red.
- **Missing quote:** Show “—” for 最新价, 市值, 浮动盈亏, 盈亏比例, 占比; still show 代码, 成本价, 持仓数量 (cost_price can be computed from total_cost/quantity even without quote).
- **Layout:** Keep “single row, no horizontal scroll” (flexible column widths, compact headers). If needed, abbreviate headers (e.g. 盈亏%, 占比) to fit.

No change to account filter, cash badges, or account_cash; only the positions array is enriched.

---

## 7. Edge Cases

- **Symbol not on Yahoo:** e.g. private or non-US ticker. Quote service returns `current_price: None`, `display_name: symbol`. Row shows symbol + cost + quantity; rest “—”.
- **Market closed:** yfinance usually still returns last close as “current” price; no special handling required.
- **Quote service down / timeout:** Either return portfolio without quotes (all quote fields null) or fail the request with 503. Recommendation: **degrade gracefully** — return positions with null quote fields so the user still sees holdings and cost/quantity.
- **Very large portfolio (many symbols):** Batch quote requests and/or cap symbols (e.g. first 50) to avoid long response times; document limit. Optionally add pagination later.
- **Rounding:** 成本价, 最新价, 市值: 2 decimals. 盈亏比例, 占比: 2 decimals (e.g. 35.34%). 持仓数量: match existing portfolio precision (e.g. 2–4 decimals).

---

## 8. Summary

| Item | Decision |
|------|----------|
| Data source | Yahoo Finance via **yfinance** (Python), backend only. |
| Fields from quote | **Current price**, **company name** (longName/shortName). |
| Caching | In-memory, per-symbol, configurable TTL (e.g. 120 s). |
| API | Enrich **GET /portfolio** with quote + computed fields (Option A). Optional `?quotes=0` to skip quotes. |
| Computed fields | cost_price, market_value, unrealized_pnl, unrealized_pnl_pct, weight_pct. |
| Missing quote | Return nulls; frontend shows “—” for price-derived columns, keeps symbol/cost/quantity. |
| Robustness | Per-symbol errors and timeouts; degrade gracefully (no quote for that symbol). |

This design makes the portfolio “持仓明细” table comprehensive: 代码/名称, 最新价, 成本价, 持仓数量, 市值, 浮动盈亏, 盈亏比例, 占比, with minimal new surface (one library, one service, extended response).
