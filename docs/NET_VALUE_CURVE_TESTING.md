# Net Value Curve Feature - Comprehensive Testing Guide

## Overview

This document describes the comprehensive testing strategy for the Net Value Curve feature, including edge cases, performance tests, and integration scenarios.

## Test Files

### 1. `test_net_value_service.py` (Core Tests)
**Purpose:** Basic functionality and regression tests
- Empty data handling
- Average cost mechanics (BUY/SELL)
- Cash inclusion/exclusion
- Response shape validation
- Transaction date handling
- **Cash deposit regression tests** (catches the include_cash bug)

**Key Tests:**
- `test_cash_deposit_does_not_create_fake_profit` - Main regression test
- `test_sell_stock_into_cash_does_not_change_equity` - Verifies P/L consistency

### 2. `test_net_value_edge_cases.py` (Edge Cases)
**Purpose:** Boundary conditions and unusual scenarios

**Test Categories:**

#### Empty Data (`TestEdgeCasesEmptyData`)
- No transactions
- Single transaction on single day
- Transactions before/after date range

#### Multiple Accounts (`TestEdgeCasesMultipleAccounts`)
- Separate account transactions
- Nonexistent account queries
- Account filtering

#### Date Boundaries (`TestEdgeCasesDateBoundaries`)
- Same start/end date
- Year boundary crossing
- Leap year (Feb 29)

#### Average Cost Mechanics (`TestEdgeCasesAvgCostMechanics`)
- Multiple buys same symbol same day
- Zero quantity handling
- Sell validation

#### Cash Flow (`TestEdgeCasesCashFlow`)
- Negative cash balance
- Withdraw more than available
- Multiple cash transactions same day

#### Price Data (`TestEdgeCasesPriceData`)
- Symbol with no price data
- Price changes during period

#### P/L Percentages (`TestEdgeCasesPercents`)
- Baseline zero → P/L% null
- Very small baseline calculations

#### Include Cash (`TestEdgeCasesIncludeCash`)
- Toggle consistency
- Baseline label changes

### 3. `test_net_value_performance.py` (Performance/Stress Tests)
**Purpose:** Scalability and performance with large datasets

**Test Categories:**

#### Large Datasets (`TestPerformanceLargeDatasets`)
- **Many transactions single symbol:** 100 transactions over a year
- **Many symbols:** 50 symbols with transactions
- **Long date range:** 5 years of data
- **Daily transactions:** Trading day transactions for a year
- **Multiple accounts:** 5 accounts with 50 transactions each

#### Memory Usage (`TestPerformanceMemoryUsage`)
- Large response size validation
- Data type consistency
- Array length matching

#### Concurrent Scenarios (`TestPerformanceConcurrentScenarios`)
- Realistic portfolio simulation

**Performance Targets:**
- 100 transactions: < 5 seconds
- 50 symbols: < 3 seconds
- 5 years of data: < 10 seconds
- Daily transactions (year): < 10 seconds

### 4. `test_net_value_integration.py` (Integration Tests)
**Purpose:** Realistic scenarios and data integrity

**Test Categories:**

#### Realistic Scenarios (`TestIntegrationRealisticScenarios`)
- **DCA Strategy:** Dollar Cost Averaging over 12 months
- **Rebalancing:** Quarterly portfolio rebalancing
- **Tax Loss Harvesting:** Sell losers, buy similar positions

#### Data Integrity (`TestIntegrationDataIntegrity`)
- **P/L = MV - Baseline:** Verifies formula consistency
- **P/L% calculation:** Validates percentage math
- **Baseline monotonicity:** Baseline increases with buys
- **Cash consistency:** Cash difference between include_cash modes

#### Complex Scenarios (`TestIntegrationComplexScenarios`)
- **Full trading year:** Complete year simulation with deposits, buys, sells, rebalancing

## Running Tests

### Run All Net Value Tests
```bash
pytest src/tests/test_net_value*.py -v
```

### Run Specific Test Categories
```bash
# Edge cases only
pytest src/tests/test_net_value_edge_cases.py -v

# Performance tests
pytest src/tests/test_net_value_performance.py -v

# Integration tests
pytest src/tests/test_net_value_integration.py -v

# Regression tests
pytest src/tests/test_net_value_service.py::TestNetValueCurveCashDepositRegression -v
```

### Run with Coverage
```bash
pytest src/tests/test_net_value*.py --cov=src/service/net_value_service --cov=src/service/historical_price_service -v
```

## Test Data Simulation

### SimulatedPriceService
The integration tests use `SimulatedPriceService` which:
- Generates realistic price movements with volatility
- Applies daily trends
- Uses random walk model
- Prevents negative prices

**Usage:**
```python
price_svc = SimulatedPriceService(
    initial_prices={"AAPL": 150.0, "MSFT": 300.0},
    volatility=0.02,  # 2% daily volatility
    trend=0.0001     # 0.01% daily trend
)
```

## Key Test Scenarios

### 1. Cash Deposit Regression
**Scenario:** Deposit $100k, buy $8k stock, price unchanged
**Expected:** P/L = 0 (not +$100k)
**Test:** `test_cash_deposit_does_not_create_fake_profit`

### 2. DCA Strategy
**Scenario:** Regular monthly purchases
**Tests:** Average cost calculation, baseline growth

### 3. Rebalancing
**Scenario:** Quarterly buy/sell to maintain allocation
**Tests:** Baseline consistency, P/L accuracy

### 4. Tax Loss Harvesting
**Scenario:** Sell losers, buy similar positions
**Tests:** Baseline reset, position tracking

### 5. Long Date Range
**Scenario:** 5 years of transactions
**Tests:** Performance, memory usage, data integrity

## Acceptance Criteria

All tests verify these invariants:

1. **P/L Formula:** `profit_loss = market_value - baseline` (within 0.01 tolerance)
2. **P/L% Formula:** `profit_loss_pct = (profit_loss / baseline) * 100` when baseline > 0, else null
3. **Cash Consistency:** `baseline_with_cash - baseline_without_cash = cash_balance`
4. **Baseline Label:** Changes based on `include_cash` parameter
5. **Array Lengths:** All arrays have same length as `dates`
6. **Data Types:** Correct types (float, bool, str, Optional[float])
7. **Date Ordering:** Dates are in ascending order
8. **Non-Negative Values:** Baseline and market_value >= 0 (unless negative cash)

## Performance Benchmarks

| Scenario | Transactions | Days | Expected Time | Status |
|----------|-------------|------|---------------|--------|
| Many transactions | 100 | 365 | < 5s | ✅ |
| Many symbols | 50 | 30 | < 3s | ✅ |
| Long range | 3 | 1825 | < 10s | ✅ |
| Daily trading | ~250 | 366 | < 10s | ✅ |
| Multiple accounts | 250 | 50 | < 5s | ✅ |

## Edge Cases Covered

✅ Empty data (no transactions)
✅ Single transaction
✅ Date boundaries (same day, year crossing, leap year)
✅ Multiple accounts
✅ Negative cash balances
✅ Zero baseline (P/L% = null)
✅ Missing price data
✅ Price changes during period
✅ Multiple transactions same day
✅ Very small quantities/prices
✅ Transactions before/after date range

## Data Integrity Checks

✅ P/L always equals MV - Baseline
✅ P/L% calculated correctly
✅ Baseline monotonic with buys only
✅ Cash consistency between modes
✅ Array lengths match
✅ Data types correct
✅ Date ordering correct

## Regression Tests

The following tests would have caught the `include_cash` bug:

1. `test_cash_deposit_only_no_profit` - Depositing cash alone creates no profit
2. `test_cash_deposit_does_not_create_fake_profit` - Deposit + buy scenario
3. `test_sell_stock_into_cash_does_not_change_equity` - Sell doesn't create fake P/L

## Future Test Additions

Consider adding:
- [ ] Tests with actual yfinance API (with mocking/rate limiting)
- [ ] Tests with corporate actions (splits, dividends)
- [ ] Tests with very large numbers (precision)
- [ ] Tests with timezone edge cases
- [ ] Tests with concurrent API requests
- [ ] Tests with database corruption scenarios
- [ ] Tests with malformed transaction data

## Maintenance

When adding new features:
1. Add edge case tests for new functionality
2. Add performance tests if data volume increases
3. Add integration tests for new workflows
4. Update this document with new test scenarios
