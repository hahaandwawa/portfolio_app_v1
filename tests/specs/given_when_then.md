# Given-When-Then Test Specification

## Investment Tracking App v1 - Test Matrix and Scenarios

This document defines the comprehensive test specification using Given-When-Then (GWT) format for the investment tracking application. Tests are designed to be deterministic with no network calls and fixed timestamps.

---

## Test Matrix

| Requirement ID | Scenario ID | Component | Test File | Status |
|----------------|-------------|-----------|-----------|--------|
| REQ-LED-001 | LED-001 | Ledger Service | `unit/test_ledger_service.py` | Pending |
| REQ-LED-002 | LED-002 | Ledger Service | `unit/test_ledger_service.py` | Pending |
| REQ-LED-003 | LED-003 | Ledger Service | `unit/test_ledger_service.py` | Pending |
| REQ-LED-004 | LED-004 | Ledger Service | `unit/test_ledger_service.py` | Pending |
| REQ-LED-005 | LED-005 | Ledger Service | `unit/test_ledger_service.py` | Pending |
| REQ-LED-006 | LED-006 | Ledger Service | `unit/test_ledger_service.py` | Pending |
| REQ-LED-007 | LED-007 | Ledger Service | `unit/test_ledger_service.py` | Pending |
| REQ-LED-008 | LED-008 | Ledger Service | `unit/test_ledger_service.py` | Pending |
| REQ-LED-009 | LED-009 | Ledger Service | `unit/test_ledger_service.py` | Pending |
| REQ-LED-010 | LED-010 | Ledger Service | `unit/test_ledger_service.py` | Pending |
| REQ-PFE-001 | PFE-001 | Portfolio Engine | `unit/test_portfolio_engine.py` | Pending |
| REQ-PFE-002 | PFE-002 | Portfolio Engine | `unit/test_portfolio_engine.py` | Pending |
| REQ-PFE-003 | PFE-003 | Portfolio Engine | `unit/test_portfolio_engine.py` | Pending |
| REQ-PFE-004 | PFE-004 | Portfolio Engine | `unit/test_portfolio_engine.py` | Pending |
| REQ-PFE-005 | PFE-005 | Portfolio Engine | `unit/test_portfolio_engine.py` | Pending |
| REQ-PFE-006 | PFE-006 | Portfolio Engine | `unit/test_portfolio_engine.py` | Pending |
| REQ-MKT-001 | MKT-001 | Market Data Service | `unit/test_market_data_service.py` | Pending |
| REQ-MKT-002 | MKT-002 | Market Data Service | `unit/test_market_data_service.py` | Pending |
| REQ-MKT-003 | MKT-003 | Market Data Service | `unit/test_market_data_service.py` | Pending |
| REQ-MKT-004 | MKT-004 | Market Data Service | `unit/test_market_data_service.py` | Pending |
| REQ-ANL-001 | ANL-001 | Analysis Service | `unit/test_analysis_service.py` | Pending |
| REQ-ANL-002 | ANL-002 | Analysis Service | `unit/test_analysis_service.py` | Pending |
| REQ-ANL-003 | ANL-003 | Analysis Service | `unit/test_analysis_service.py` | Pending |
| REQ-ANL-004 | ANL-004 | Analysis Service | `unit/test_analysis_service.py` | Pending |
| REQ-CSV-001 | CSV-001 | CSV Handling | `unit/test_csv.py` | Pending |
| REQ-CSV-002 | CSV-002 | CSV Handling | `unit/test_csv.py` | Pending |
| REQ-CSV-003 | CSV-003 | CSV Handling | `unit/test_csv.py` | Pending |
| REQ-CSV-004 | CSV-004 | CSV Handling | `unit/test_csv.py` | Pending |
| REQ-CSV-005 | CSV-005 | CSV Handling | `unit/test_csv.py` | Pending |
| REQ-API-001 | API-001 | API Endpoints | `api/test_accounts_api.py` | Pending |
| REQ-API-002 | API-002 | API Endpoints | `api/test_transactions_api.py` | Pending |
| REQ-API-003 | API-003 | API Endpoints | `api/test_analysis_api.py` | Pending |
| REQ-INT-001 | INT-001 | Integration | `integration/test_repositories_sqlite.py` | Pending |
| REQ-INT-002 | INT-002 | Integration | `integration/test_rebuild_triggers.py` | Pending |

---

## GWT Scenarios

### A) Ledger / Transactions + Revisions + Undo

#### LED-001: Create Account Stores Cost Basis Method
```
GIVEN no accounts exist
WHEN I create an account named "Brokerage" with cost_basis_method="FIFO"
THEN the account is persisted with account_id, name="Brokerage", cost_basis_method=FIFO
AND created_at_est is set to current Eastern time
```

#### LED-002: Create Account with AVERAGE Cost Basis
```
GIVEN no accounts exist
WHEN I create an account named "IRA" with cost_basis_method="AVERAGE"
THEN the account is persisted with cost_basis_method=AVERAGE
```

#### LED-003: Duplicate Account Name Fails
```
GIVEN an account named "Brokerage" already exists
WHEN I attempt to create another account named "Brokerage"
THEN a ValidationError is raised with message containing "already exists"
```

#### LED-004: Add BUY Transaction Creates Revision
```
GIVEN an account exists with account_id
WHEN I add a BUY transaction for 10 shares of AAPL at $185.00
THEN the transaction is persisted with correct fields
AND a TransactionRevision with action=CREATE is created
AND before_json is None
AND after_json contains the transaction snapshot
```

#### LED-005: Add CASH_DEPOSIT Transaction
```
GIVEN an account exists with account_id
WHEN I add a CASH_DEPOSIT of $10,000.00
THEN the transaction is persisted with txn_type=CASH_DEPOSIT
AND cash_amount=10000.00
AND a CREATE revision is created
```

#### LED-006: BUY Requires Symbol
```
GIVEN an account exists
WHEN I attempt to add a BUY transaction without a symbol
THEN a ValidationError is raised with message "BUY requires a symbol"
```

#### LED-007: BUY Requires Positive Quantity
```
GIVEN an account exists
WHEN I attempt to add a BUY transaction with quantity=0 or quantity=-5
THEN a ValidationError is raised with message "BUY requires quantity > 0"
```

#### LED-008: Edit Transaction Creates UPDATE Revision
```
GIVEN an account exists with a BUY transaction for 10 AAPL @ $185.00
WHEN I edit the transaction to change price to $186.00
THEN the transaction is updated with price=$186.00
AND a TransactionRevision with action=UPDATE is created
AND before_json contains {"price": "185.00", ...}
AND after_json contains {"price": "186.00", ...}
```

#### LED-009: Soft Delete Transaction Sets is_deleted Flag
```
GIVEN an account exists with an active BUY transaction
WHEN I soft delete the transaction
THEN is_deleted is set to True
AND a SOFT_DELETE revision is created
AND before_json shows is_deleted=false
AND after_json shows is_deleted=true
```

#### LED-010: Cannot Edit Deleted Transaction
```
GIVEN a transaction that has been soft deleted (is_deleted=True)
WHEN I attempt to edit the transaction
THEN a ValidationError is raised with message "Cannot edit a deleted transaction"
```

#### LED-011: Undo SOFT_DELETE Restores Transaction
```
GIVEN a transaction that was soft deleted
WHEN I call undo_last_action for the account
THEN the transaction is_deleted is set to False
AND a RESTORE revision is created
```

#### LED-012: Undo UPDATE Restores Previous Values
```
GIVEN a transaction was edited from price $185 to $186
WHEN I call undo_last_action for the account
THEN the transaction price is restored to $185.00
AND an UPDATE revision is created reversing the change
```

---

### B) Portfolio Engine Rebuild + Aggregation

#### PFE-001: Rebuild Computes Correct Shares After BUY
```
GIVEN an account with no transactions
WHEN I add a BUY for 10 shares of AAPL and rebuild
THEN get_positions returns AAPL with shares=10
```

#### PFE-002: Rebuild After BUY Then Partial SELL
```
GIVEN an account with BUY 10 AAPL
WHEN I add a SELL for 3 shares of AAPL and rebuild
THEN get_positions returns AAPL with shares=7
```

#### PFE-003: Sell to Zero Removes Position
```
GIVEN an account with BUY 10 AAPL
WHEN I SELL all 10 shares and rebuild
THEN get_positions returns empty (position with shares=0 is not stored)
```

#### PFE-004: Rebuild Ignores Deleted Transactions
```
GIVEN an account with BUY 10 AAPL, then the transaction is soft deleted
WHEN I rebuild the account
THEN get_positions returns empty (no AAPL position)
```

#### PFE-005: Cash Balance After Deposit and Withdrawal
```
GIVEN an account with no transactions
WHEN I add CASH_DEPOSIT $10,000 then CASH_WITHDRAW $2,500 and rebuild
THEN get_cash_balance returns $7,500
```

#### PFE-006: Cash Balance Affected by BUY (Cash Impact)
```
GIVEN an account with CASH_DEPOSIT $10,000
WHEN I add BUY 10 AAPL @ $185.00 with $5 fees and rebuild
THEN cash_balance = 10000 - (10 * 185) - 5 = $8,145.00
```

#### PFE-007: Aggregate Positions Across Multiple Accounts
```
GIVEN Account A has 10 AAPL, Account B has 5 AAPL and 20 MSFT
WHEN I call aggregate_positions([A.id, B.id])
THEN result contains AAPL=15, MSFT=20
```

#### PFE-008: Aggregate Cash Across Multiple Accounts
```
GIVEN Account A has $5,000 cash, Account B has $3,000 cash
WHEN I call aggregate_cash([A.id, B.id])
THEN result is $8,000
```

#### PFE-009: Validate Sell - Sufficient Shares
```
GIVEN an account with 10 AAPL shares
WHEN I call validate_sell(account_id, "AAPL", 5)
THEN returns True
```

#### PFE-010: Validate Sell - Insufficient Shares
```
GIVEN an account with 10 AAPL shares
WHEN I call validate_sell(account_id, "AAPL", 15)
THEN returns False
```

#### PFE-011: Validate Withdrawal - Sufficient Cash
```
GIVEN an account with $10,000 cash
WHEN I call validate_withdrawal(account_id, $5000, enforce=True)
THEN returns True
```

#### PFE-012: Validate Withdrawal - Insufficient Cash
```
GIVEN an account with $1,000 cash
WHEN I call validate_withdrawal(account_id, $5000, enforce=True)
THEN returns False
```

---

### C) Market Data Service

#### MKT-001: Get Quotes Returns Quote Data
```
GIVEN a market data provider with AAPL quote (last=$185.50, prev=$184.25)
WHEN I call get_quotes(["AAPL"])
THEN result contains Quote(symbol="AAPL", last_price=185.50, prev_close=184.25, as_of=...)
```

#### MKT-002: Caching - Second Call Uses Cache
```
GIVEN cache TTL is 60 seconds
WHEN I call get_quotes(["AAPL"]) twice within 60 seconds
THEN the provider is called only once (first call)
AND second call returns cached data
```

#### MKT-003: Cache Expiry - Calls Provider After TTL
```
GIVEN cache TTL is 1 second
WHEN I call get_quotes(["AAPL"]), wait 2 seconds, call again
THEN the provider is called twice
```

#### MKT-004: Fallback to Cache on Provider Failure
```
GIVEN AAPL quote is cached from previous successful call
AND the provider is now failing
WHEN I call get_quotes(["AAPL"])
THEN returns the cached quote (graceful degradation)
```

#### MKT-005: Empty Symbols Returns Empty Dict
```
GIVEN any provider
WHEN I call get_quotes([])
THEN result is empty dict {}
```

#### MKT-006: Unknown Symbol Not in Result
```
GIVEN provider only knows AAPL, GOOGL
WHEN I call get_quotes(["AAPL", "UNKNOWN"])
THEN result contains AAPL but not UNKNOWN
```

---

### D) Analysis Service

#### ANL-001: Today PnL Calculation - Single Position
```
GIVEN an account with 10 shares of AAPL
AND quote: AAPL last=$185.50, prev=$184.25
WHEN I call today_pnl([account_id])
THEN pnl_dollars = 10 * (185.50 - 184.25) = $12.50
AND pnl_percent = (12.50 / (10 * 184.25)) * 100 = 0.68%
```

#### ANL-002: Today PnL - Multiple Positions
```
GIVEN an account with 10 AAPL and 5 TSLA
AND quotes: AAPL last=185.50/prev=184.25, TSLA last=248.75/prev=250.10
WHEN I call today_pnl([account_id])
THEN AAPL_pnl = 10 * 1.25 = $12.50
AND TSLA_pnl = 5 * (-1.35) = -$6.75
AND total_pnl = $12.50 - $6.75 = $5.75
```

#### ANL-003: Today PnL - Multi-Account Aggregation
```
GIVEN Account A has 10 AAPL, Account B has 5 AAPL
AND quote: AAPL last=$185.50, prev=$184.25
WHEN I call today_pnl([A.id, B.id])
THEN pnl_dollars = 15 * 1.25 = $18.75
```

#### ANL-004: Today PnL - Empty Account
```
GIVEN an account with no positions
WHEN I call today_pnl([account_id])
THEN pnl_dollars = $0.00
AND pnl_percent = None
```

#### ANL-005: Allocation Breakdown
```
GIVEN an account with 10 AAPL (value=$1855) and 5 MSFT (value=$1891.25)
AND quotes: AAPL=$185.50, MSFT=$378.25
WHEN I call allocation([account_id])
THEN items include:
  - AAPL: market_value=$1855.00, percentage=49.52%
  - MSFT: market_value=$1891.25, percentage=50.48%
AND total_value = $3746.25
```

#### ANL-006: Allocation Percentages Sum to 100%
```
GIVEN any account with multiple positions
WHEN I call allocation([account_id])
THEN sum of all item.percentage equals 100.00 (within 0.01 tolerance)
```

---

### E) CSV Template / Import / Export

#### CSV-001: Template Has Required Headers
```
GIVEN CsvTemplateGenerator
WHEN I call generate_template(path)
THEN the file contains headers: account_name, txn_time_est, type, symbol, quantity, price, cash_amount, fees, note
```

#### CSV-002: Import Valid Rows
```
GIVEN a CSV file with 3 valid transaction rows
WHEN I call import_csv(path)
THEN summary.imported_count = 3
AND summary.error_count = 0
AND all 3 transactions are persisted
```

#### CSV-003: Import Invalid Type Row Captured in Errors
```
GIVEN a CSV with one row having type="INVALID_TYPE"
WHEN I call import_csv(path)
THEN summary.error_count >= 1
AND summary.errors contains "Row N: Invalid transaction type: INVALID_TYPE"
```

#### CSV-004: Import Invalid Decimal Value
```
GIVEN a CSV with one row having quantity="not_a_number"
WHEN I call import_csv(path)
THEN summary.error_count >= 1
AND summary.errors contains "Invalid decimal value"
```

#### CSV-005: Export Only Non-Deleted Transactions
```
GIVEN an account with 3 transactions, 1 of which is soft deleted
WHEN I call export_csv(path)
THEN the exported file contains 2 data rows (excludes deleted)
```

#### CSV-006: Round-Trip Export Then Import
```
GIVEN an account with 5 transactions
WHEN I export to CSV and import into a new account
THEN the new account has 5 transactions matching the original (ignoring IDs)
```

#### CSV-007: Import Creates Account if Not Exists
```
GIVEN no account named "NewAccount" exists
WHEN I import a CSV with rows for "NewAccount"
THEN an account named "NewAccount" is created
AND transactions are added to that account
```

---

### F) API Contract Tests

#### API-001: Create Account - Success
```
GIVEN no accounts exist
WHEN I POST /accounts with {"name": "Brokerage", "cost_basis_method": "FIFO"}
THEN response status is 201
AND response body contains account_id, name="Brokerage", cost_basis_method="FIFO"
```

#### API-002: Create Account - Duplicate Name Returns 400
```
GIVEN an account named "Brokerage" exists
WHEN I POST /accounts with {"name": "Brokerage"}
THEN response status is 400
AND response body contains error message
```

#### API-003: List Accounts
```
GIVEN 2 accounts exist
WHEN I GET /accounts
THEN response status is 200
AND response body contains accounts array with 2 items
AND count = 2
```

#### API-004: Add Transaction - Success
```
GIVEN an account exists with account_id
WHEN I POST /transactions with valid BUY data
THEN response status is 201
AND response body contains txn_id, txn_type="BUY", symbol, quantity, price
```

#### API-005: Add Transaction - Validation Error Returns 400
```
GIVEN an account exists
WHEN I POST /transactions with BUY but missing symbol
THEN response status is 400
AND response body contains "BUY requires a symbol"
```

#### API-006: Add Transaction - Account Not Found Returns 404
```
GIVEN no account with id "nonexistent"
WHEN I POST /transactions with account_id="nonexistent"
THEN response status is 404
```

#### API-007: Edit Transaction - Success
```
GIVEN a transaction exists
WHEN I PATCH /transactions/{txn_id} with {"price": 190.00}
THEN response status is 200
AND response body shows updated price
```

#### API-008: Delete Transaction - Success
```
GIVEN a transaction exists
WHEN I DELETE /transactions/{txn_id}
THEN response status is 204
AND subsequent GET shows is_deleted=true (if include_deleted=true)
```

#### API-009: Get Today PnL
```
GIVEN an account with positions
WHEN I GET /analysis/pnl?account_ids={id}
THEN response status is 200
AND response body contains pnl_dollars, pnl_percent, as_of
```

#### API-010: Get Allocation
```
GIVEN an account with positions
WHEN I GET /analysis/allocation?account_ids={id}
THEN response status is 200
AND response body contains items array, total_value
```

#### API-011: Get Quotes
```
WHEN I GET /analysis/quotes?symbols=AAPL,MSFT
THEN response status is 200
AND response body is array of quote objects with symbol, last_price, prev_close, as_of
```

#### API-012: Invalid Request Body Returns 422 (Pydantic Validation)
```
WHEN I POST /accounts with {"name": ""} (empty name)
THEN response status is 422
AND response body contains validation error details
```

---

### G) Integration Tests

#### INT-001: Repository SQLite Persistence
```
GIVEN an in-memory SQLite database
WHEN I create an account and transaction via repositories
THEN data can be retrieved by ID
AND data persists across multiple queries in same session
```

#### INT-002: Rebuild Triggered After Ledger Changes
```
GIVEN an account with existing positions
WHEN I add a new transaction via LedgerService
AND I call rebuild_account
THEN positions reflect the new transaction
```

#### INT-003: Full Transaction Lifecycle
```
GIVEN a fresh database
WHEN I:
  1. Create account
  2. Add CASH_DEPOSIT $10,000
  3. Add BUY 10 AAPL @ $185
  4. Edit to change price to $186
  5. Add SELL 5 AAPL @ $190
  6. Soft delete the SELL
THEN:
  - 4 revisions exist (CREATE, CREATE, UPDATE, CREATE, SOFT_DELETE)
  - Positions show 10 AAPL (sell is deleted)
  - Cash reflects deposit and buy only
```

---

## Edge Cases to Test

| Scenario | Expected Behavior |
|----------|-------------------|
| Zero quantity BUY | ValidationError: quantity > 0 required |
| Negative price | ValidationError: price >= 0 required |
| Negative fees | ValidationError: fees cannot be negative |
| Empty symbol (BUY) | ValidationError: symbol required |
| CASH_DEPOSIT with 0 amount | ValidationError: cash_amount > 0 required |
| Sell more than owned | InsufficientSharesError (if validated) |
| Withdraw more than cash balance | InsufficientCashError (if enforce=True) |
| Edit deleted transaction | ValidationError |
| Undo with no actions | ValidationError: No actions to undo |
| Import missing column | ValidationError: Missing required columns |
| Import empty file | ImportSummary with 0 counts |
| Aggregation with empty account list | Empty results |
| Quotes for empty symbol list | Empty dict |

---

## Determinism Requirements

All tests MUST be deterministic:

1. **No Network Calls**: Use stub/mock providers
2. **Fixed Timestamps**: Use `eastern_datetime()` helper or fixtures
3. **Fixed Market Data**: Use `DeterministicMarketProvider` with known prices
4. **In-Memory Database**: Use SQLite `:memory:` with StaticPool
5. **Seeded Random**: If random needed, use fixed seed (e.g., `seed=42`)

---

## Test Coverage Goals

| Component | Target Coverage |
|-----------|-----------------|
| LedgerService | 90%+ |
| PortfolioEngine | 90%+ |
| MarketDataService | 85%+ |
| AnalysisService | 85%+ |
| CSV handling | 80%+ |
| API endpoints | 80%+ |
| Repositories | 75%+ |

---

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_ledger_service.py

# Run tests matching pattern
pytest -k "test_buy"

# Run with verbose output
pytest -v
```
