# Net Value Curve — User Guide

## Overview

The **Net Value Curve** (净值曲线) displays your portfolio's performance over time by comparing two key metrics:
1. **Baseline** — Your cost basis (what you paid)
2. **Market Value** — Current market value (what it's worth now)

The visual gap between these two lines shows your **profit or loss** at any point in time.

---

## How the Plot is Constructed

### Data Calculation

The chart is built day-by-day from your transaction history:

1. **For each calendar day** from the start date to today:
   - The system applies all transactions that occurred on that day
   - Calculates your **holdings** (shares held) and **cash balance** at the end of that day
   - Looks up historical stock prices for that date
   - Computes baseline and market value

2. **Baseline Calculation:**
   - **With cash included** (default): `Baseline = Cash Balance + Holdings Cost`
     - Holdings Cost = Sum of (Average Cost × Shares) for each stock you own
   - **With cash excluded**: `Baseline = Holdings Cost only`
   - Uses **weighted average cost** per stock (not FIFO/LIFO)

3. **Market Value Calculation:**
   - **With cash included** (default): `Market Value = Cash Balance + Stock Market Value`
     - Stock Market Value = Sum of (Current Price × Shares) for each stock
   - **With cash excluded**: `Market Value = Stock Market Value only`

4. **Profit/Loss:**
   - `P/L = Market Value - Baseline`
   - `P/L% = (P/L / Baseline) × 100` (when baseline > 0)

### Visual Elements

The chart displays:

- **Two Lines:**
  - **Gray dashed line** = Baseline (Book Value / Holdings Cost)
  - **Blue solid line** = Market Value (市值)

- **Colored Fill Areas:**
  - **Green area** = Profit zone (market value above baseline)
  - **Red area** = Loss zone (market value below baseline)
  - The height of the colored area = your profit or loss amount

- **X-Axis:** Dates (calendar days)
- **Y-Axis:** Dollar amounts (formatted as $X or $X.Xk for thousands)

### Non-Trading Days

- **Weekends and holidays** are included in the chart
- Prices are **forward-filled** from the last trading day
- Hover tooltip shows: **"Last trading close: [date]"** so you know which price was used

---

## What to Look For

### 1. **Overall Trend**

**Question:** Is your portfolio growing over time?

**What to check:**
- Is the **blue line (Market Value)** trending upward?
- Is the **green area** getting larger over time?
- Are you consistently above the baseline?

**Good signs:**
- ✅ Upward-sloping market value line
- ✅ Green area expanding
- ✅ Market value consistently above baseline

**Warning signs:**
- ⚠️ Market value declining
- ⚠️ Red area appearing or growing
- ⚠️ Market value falling below baseline

### 2. **Profit/Loss Magnitude**

**Question:** How much profit or loss do you have?

**What to check:**
- **Vertical distance** between the two lines = your P/L in dollars
- **Green area height** = profit amount
- **Red area height** = loss amount
- Hover over any point to see exact P/L and P/L%

**Example:**
- If baseline = $50,000 and market value = $55,000
- Your profit = $5,000 (10% gain)

### 3. **Baseline Behavior**

**Question:** Is your baseline increasing or decreasing?

**What to check:**
- **Baseline increases** when you:
  - Buy more stocks (adds to holdings cost)
  - Deposit cash (if "Include cash" is ON)
- **Baseline decreases** when you:
  - Sell stocks (reduces holdings cost)
  - Withdraw cash (if "Include cash" is ON)

**Important:** Selling stocks does **not** change your average cost per share—only the number of shares changes. This ensures the baseline accurately reflects your cost basis.

### 4. **Cash Impact**

**Toggle:** "Include cash" checkbox

**With cash included (default):**
- Shows **total portfolio equity** (stocks + cash)
- Baseline = "Book Value (cash + holdings cost)"
- This is what most users expect—your total account value

**With cash excluded:**
- Shows **stock holdings only**
- Baseline = "Holdings Cost (avg)"
- Useful for analyzing stock performance separately from cash

**When to use each:**
- **Include cash:** When you want to see total account value (recommended for most users)
- **Exclude cash:** When analyzing pure stock performance, or if cash data is incomplete

### 5. **Transaction Impact**

**Question:** How do your trades affect the curve?

**What happens:**
- **Buying stocks:**
  - Baseline increases (you paid for new shares)
  - Market value increases (you own more shares)
  - The curve may show a small dip if you bought at a higher price than current market

- **Selling stocks:**
  - Baseline decreases (you sold shares, reducing holdings cost)
  - Market value decreases (you own fewer shares)
  - If you sold at a profit, you'll see cash increase (if cash is included)

- **Depositing cash:**
  - Baseline increases (if cash included)
  - Market value increases (if cash included)
  - **P/L does NOT change** (cash deposit is not profit)

- **Withdrawing cash:**
  - Baseline decreases (if cash included)
  - Market value decreases (if cash included)
  - **P/L does NOT change** (cash withdrawal is not a loss)

### 6. **Performance Metrics**

**Hover tooltip shows:**
- **Date** (or "Last trading close: [date]" on weekends/holidays)
- **Baseline** (your cost/book value)
- **Market Value** (current worth)
- **Profit/Loss** (absolute dollar amount)
- **Profit/Loss %** (percentage gain/loss)

**Key metrics to watch:**
- **P/L%** — Your return percentage (positive = profit, negative = loss)
- **Trend direction** — Is the gap between lines widening (good) or narrowing (concerning)?

---

## Common Scenarios

### Scenario 1: Consistent Growth
**What you see:**
- Both lines trending upward
- Green area consistently present and growing
- Market value line stays above baseline

**What it means:**
- Your portfolio is performing well
- You're making profits on your investments
- Consider: Are you beating your baseline growth rate?

### Scenario 2: Volatile Performance
**What you see:**
- Lines crossing frequently
- Green and red areas alternating
- Market value fluctuating around baseline

**What it means:**
- Your portfolio is volatile
- You're experiencing both gains and losses
- Consider: Is this volatility acceptable for your risk tolerance?

### Scenario 3: Declining Value
**What you see:**
- Market value line trending downward
- Red area appearing or growing
- Market value falling below baseline

**What it means:**
- Your portfolio is losing value
- You may be in a drawdown period
- Consider: Review your positions and strategy

### Scenario 4: Flat Performance
**What you see:**
- Lines running parallel and close together
- Minimal green or red area
- Market value ≈ baseline

**What it means:**
- Your portfolio is roughly break-even
- Little profit or loss
- Consider: Are you achieving your investment goals?

---

## Understanding the Baseline

### What is "Holdings Cost"?
- Sum of (Average Cost × Current Shares) for all stocks you own
- Uses **weighted average cost** (not FIFO/LIFO)
- Example: If you bought 10 shares @ $100, then 10 more @ $120:
  - Average cost = ($100×10 + $120×10) / 20 = $110/share
  - Holdings cost = $110 × 20 = $2,200

### What is "Book Value"?
- **Book Value = Cash + Holdings Cost**
- This is your total "cost basis" including cash
- Represents what you've put into the portfolio

### Why Baseline Matters
- **Baseline is your reference point** for measuring performance
- If market value > baseline → you're profitable
- If market value < baseline → you're at a loss
- The **percentage gain/loss** is calculated relative to baseline

---

## Tips for Interpretation

1. **Zoom Levels:**
   - **7 days:** See recent short-term movements
   - **30 days:** See monthly trends
   - **All time:** See overall portfolio trajectory

2. **Include Cash Toggle:**
   - **ON (default):** Best for seeing total account value
   - **OFF:** Best for analyzing pure stock performance

3. **Account Filtering:**
   - Filter by specific accounts to see individual account performance
   - Or view all accounts combined for total portfolio view

4. **Hover for Details:**
   - Move your mouse over any point to see exact values
   - Check "Last trading close" date on weekends/holidays

5. **Watch for Patterns:**
   - Consistent upward trend = good
   - Frequent crossing = volatility
   - Declining trend = review needed

---

## Important Notes

### Currency
- **V1 supports USD only**
- All values are in US dollars
- Multi-currency support is planned for future versions

### Price Data
- Uses **Close prices** (unadjusted) from Yahoo Finance
- Prices are cached to minimize API calls
- Non-trading days use previous trading day's close (forward-filled)

### Transaction Dates
- Transactions are applied by **US/Eastern trade date**
- All transactions on date T are applied **before** computing that day's closing value
- This matches how brokers typically show end-of-day positions

### Accuracy
- The curve reflects your transaction history
- Ensure all transactions are recorded accurately
- Cash deposits/withdrawals must be recorded for accurate "include cash" mode

---

## Troubleshooting

### "No data available"
- **Cause:** No transactions in the selected date range or accounts
- **Solution:** Check that you have transactions recorded, and verify account filter

### Curve looks wrong after a transaction
- **Cause:** Transaction may not be recorded correctly
- **Solution:** Verify the transaction details (date, quantity, price, fees)

### Baseline seems incorrect
- **Cause:** May be using wrong "include cash" mode, or cash transactions missing
- **Solution:** Toggle "Include cash" to see the difference, verify all cash deposits/withdrawals are recorded

### Prices seem outdated
- **Cause:** Price cache may be stale
- **Solution:** Use the "Refresh" option (if available) to fetch latest prices

---

## Example Interpretation

**Example chart showing:**
- Baseline starts at $50,000 (initial deposit + first purchases)
- Market value starts at $50,000 (same, no price change yet)
- Over 3 months:
  - Baseline increases to $70,000 (more purchases + deposits)
  - Market value increases to $75,000 (stocks appreciated)
  - Green area shows $5,000 profit
  - P/L% = ($5,000 / $70,000) × 100 = 7.14%

**What this tells you:**
- ✅ Portfolio is growing
- ✅ You're profitable (7.14% gain)
- ✅ Market value is above baseline consistently
- ✅ Good performance overall

---

## Summary

The Net Value Curve helps you:
- **Track performance** over time
- **Visualize profit/loss** clearly
- **Understand the impact** of your trades
- **Monitor trends** in your portfolio

**Key takeaway:** The gap between the blue line (market value) and gray line (baseline) represents your profit or loss. A growing green area means you're making money. A red area means you're at a loss relative to your cost basis.
