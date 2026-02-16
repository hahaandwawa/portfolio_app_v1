# Portfolio Management Application

A full-stack portfolio tracking application for managing investment transactions, accounts, and portfolio performance visualization.

## Features

- **Transaction Management**: Record BUY, SELL, CASH_DEPOSIT, and CASH_WITHDRAW transactions
- **Account Management**: Multiple account support with filtering
- **Portfolio Overview**: Real-time portfolio summary with positions and cash balances
- **Net Value Curve**: Historical equity curve visualization showing portfolio performance over time
- **CSV Import/Export**: Bulk transaction import and export functionality

---

## Net Value Curve — How It Works

### Overview

The **Net Value Curve** (净值曲线) is a powerful visualization tool that shows your portfolio's performance over time by comparing two key metrics:

1. **Baseline** — Your cost basis (what you've invested)
2. **Market Value** — Current market value (what your portfolio is worth now)

### How the Plot is Constructed

#### Data Calculation Process

The chart is built **day-by-day** from your transaction history:

1. **For each calendar day** (from start date to today):
   - All transactions occurring on that day are applied
   - Holdings (shares) and cash balance are calculated at end-of-day
   - Historical stock prices are fetched for that date
   - Baseline and market value are computed

2. **Baseline Calculation:**
   ```
   With cash included (default):
     Baseline = Cash Balance + Holdings Cost
     Holdings Cost = Σ(Average Cost × Current Shares) for each stock
   
   With cash excluded:
     Baseline = Holdings Cost only
   ```

3. **Market Value Calculation:**
   ```
   With cash included (default):
     Market Value = Cash Balance + Stock Market Value
     Stock Market Value = Σ(Current Price × Shares) for each stock
   
   With cash excluded:
     Market Value = Stock Market Value only
   ```

4. **Profit/Loss:**
   ```
   P/L = Market Value - Baseline
   P/L% = (P/L / Baseline) × 100  (when baseline > 0)
   ```

#### Visual Elements

The chart displays:

- **Two Lines:**
  - **Gray dashed line** = Baseline (Book Value / Holdings Cost)
  - **Blue solid line** = Market Value (市值)

- **Colored Fill Areas:**
  - **Green area** = Profit zone (market value above baseline)
  - **Red area** = Loss zone (market value below baseline)
  - The height of the colored area = your profit or loss amount

- **Axes:**
  - **X-Axis:** Dates (calendar days, including weekends/holidays)
  - **Y-Axis:** Dollar amounts (formatted as $X or $X.Xk)

- **Non-Trading Days:**
  - Prices are **forward-filled** from the last trading day
  - Tooltip shows: **"Last trading close: [date]"**

#### Technical Details

- **Average Cost Calculation:**
  - Uses **weighted average cost** (not FIFO/LIFO)
  - On BUY: `avg_cost = (prev_shares × prev_avg_cost + buy_qty × buy_price + fees) / (prev_shares + buy_qty)`
  - On SELL: `avg_cost` remains unchanged (only shares decrease)
  - When shares = 0: `avg_cost` resets to 0

- **Price Data:**
  - Uses **Close prices** (unadjusted) from Yahoo Finance
  - Cached in SQLite by (symbol, date) for performance
  - Forward-filled for weekends/holidays

- **Transaction Dates:**
  - Transactions applied by **US/Eastern trade date**
  - All transactions on date T are applied **before** computing T's closing value

---

## What to Look For in the Plot

### 1. **Overall Trend Direction**

**Question:** Is your portfolio growing over time?

**Look for:**
- ✅ **Upward-sloping market value line** = Portfolio is growing
- ✅ **Expanding green area** = Profits are increasing
- ✅ **Market value consistently above baseline** = You're profitable

**Warning signs:**
- ⚠️ **Declining market value** = Portfolio losing value
- ⚠️ **Growing red area** = Losses increasing
- ⚠️ **Market value below baseline** = You're at a loss

### 2. **Profit/Loss Magnitude**

**Question:** How much profit or loss do you have?

**How to read:**
- **Vertical distance** between lines = P/L in dollars
- **Green area height** = Profit amount
- **Red area height** = Loss amount
- **Hover over any point** to see exact P/L and P/L%

**Example:**
- Baseline = $50,000, Market Value = $55,000
- Profit = $5,000 (10% gain)

### 3. **Baseline Behavior**

**Question:** How is your cost basis changing?

**What affects baseline:**
- **Increases when:**
  - You buy stocks (adds to holdings cost)
  - You deposit cash (if "Include cash" is ON)
- **Decreases when:**
  - You sell stocks (reduces holdings cost)
  - You withdraw cash (if "Include cash" is ON)

**Important:** Selling stocks does **not** change your average cost per share—only the number of shares changes. This ensures accurate cost basis tracking.

### 4. **Cash Impact (Include/Exclude Toggle)**

**With cash included (default):**
- Shows **total portfolio equity** (stocks + cash)
- Baseline label: "Book Value (cash + holdings cost)"
- Best for: Seeing total account value

**With cash excluded:**
- Shows **stock holdings only**
- Baseline label: "Holdings Cost (avg)"
- Best for: Analyzing pure stock performance

**Key insight:** Toggling cash on/off changes the **level** of both lines, but the **P/L** (gap between lines) remains the same because cash cancels out in the calculation.

### 5. **Transaction Impact Visualization**

**Buying stocks:**
- Baseline ↑ (you paid for new shares)
- Market value ↑ (you own more shares)
- Small dip possible if buying at higher than current market price

**Selling stocks:**
- Baseline ↓ (reduces holdings cost)
- Market value ↓ (you own fewer shares)
- Cash increases (if cash included)

**Depositing cash:**
- Baseline ↑ (if cash included)
- Market value ↑ (if cash included)
- **P/L does NOT change** (cash deposit is not profit)

**Withdrawing cash:**
- Baseline ↓ (if cash included)
- Market value ↓ (if cash included)
- **P/L does NOT change** (cash withdrawal is not a loss)

### 6. **Performance Metrics**

**Hover tooltip shows:**
- Date (or "Last trading close: [date]" on weekends)
- Baseline value
- Market value
- Profit/Loss (absolute)
- Profit/Loss % (percentage)

**Key metrics:**
- **P/L%** — Your return percentage
- **Trend direction** — Is the gap widening (good) or narrowing (concerning)?

---

## Common Patterns

### Pattern 1: Consistent Growth ✅
- Both lines trending upward
- Green area consistently present and growing
- **Meaning:** Portfolio performing well, making profits

### Pattern 2: Volatile Performance 📊
- Lines crossing frequently
- Green and red areas alternating
- **Meaning:** High volatility, experiencing both gains and losses

### Pattern 3: Declining Value ⚠️
- Market value trending downward
- Red area appearing or growing
- **Meaning:** Portfolio losing value, review needed

### Pattern 4: Flat Performance ➡️
- Lines running parallel and close together
- Minimal colored area
- **Meaning:** Roughly break-even, little profit or loss

---

## Usage Tips

1. **Zoom Levels:**
   - **7 days:** Short-term movements
   - **30 days:** Monthly trends
   - **All time:** Overall trajectory

2. **Include Cash Toggle:**
   - **ON:** Total account value (recommended)
   - **OFF:** Pure stock performance analysis

3. **Account Filtering:**
   - Filter by specific accounts for individual performance
   - Or view all accounts for total portfolio

4. **Hover for Details:**
   - Move mouse over any point for exact values
   - Check "Last trading close" date on weekends/holidays

5. **Watch Patterns:**
   - Consistent upward trend = good performance
   - Frequent crossing = volatility
   - Declining trend = needs review

---

## Example Interpretation

**Scenario:**
- Baseline starts at $50,000
- Over 3 months, baseline increases to $70,000 (more purchases)
- Market value increases to $75,000 (stocks appreciated)
- Green area shows $5,000 profit
- P/L% = 7.14%

**What this means:**
- ✅ Portfolio is growing
- ✅ You're profitable (7.14% gain)
- ✅ Market value consistently above baseline
- ✅ Good overall performance

---

## Key Takeaways

1. **The gap between lines = your profit/loss**
   - Green area = profit
   - Red area = loss

2. **Baseline = your cost basis**
   - What you've invested (cash + holdings cost)
   - Reference point for measuring performance

3. **Market value = current worth**
   - What your portfolio is worth today
   - Includes cash (if toggle is ON)

4. **P/L% shows your return**
   - Calculated as (P/L / Baseline) × 100
   - Positive = profit, negative = loss

5. **Include cash toggle changes the level, not the P/L**
   - Both lines shift up/down together
   - The gap (P/L) remains the same

---

## Technical Documentation

For detailed technical documentation, see:
- [Design Document](./docs/NET_VALUE_CURVE_DESIGN.md) — Architecture and implementation details
- [Testing Guide](./docs/NET_VALUE_CURVE_TESTING.md) — Test coverage and scenarios
- [User Guide](./docs/NET_VALUE_CURVE_USER_GUIDE.md) — Comprehensive user guide

---

## Quick Start

### Generate Test Data

```bash
# Generate realistic test data for last 3 months
python scripts/generate_test_data.py

# Generate advanced multi-account data
python scripts/generate_test_data_advanced.py
```

### View the Curve

1. Start the backend server
2. Open the frontend application
3. Navigate to the Net Value Curve section
4. Select accounts and date range
5. Toggle "Include cash" to see different views

### API Endpoint

```
GET /net-value-curve?account=AccountName&start_date=2024-01-01&end_date=2024-12-31&include_cash=true
```

---

## Support

For issues or questions:
- Check the [User Guide](./docs/NET_VALUE_CURVE_USER_GUIDE.md)
- Review the [Design Document](./docs/NET_VALUE_CURVE_DESIGN.md)
- Run tests: `pytest src/tests/test_net_value*.py -v`
