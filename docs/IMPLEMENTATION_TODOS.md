# Implementation TODOs

This document lists all functions and features that are stubbed or incomplete, along with detailed implementation requirements for engineers.

---

## Priority Legend

| Priority | Description |
|----------|-------------|
| **P0** | Critical - Core functionality, should be implemented first |
| **P1** | High - Important for correctness and data integrity |
| **P2** | Medium - Useful feature, can be deferred |
| **P3** | Low - Nice to have, optional |

---

## 1. Undo Last Action (P0)

**File:** `src/app/services/ledger_service.py`  
**Method:** `LedgerService.undo_last_action(account_id: str) -> None`

### Current State
- Raises `NotImplementedError`
- Fetches latest revision but doesn't restore state

### What It Should Do
Restore the previous state of a transaction based on the last revision action. This enables users to undo accidental edits, deletes, or additions.

### Implementation Requirements

```python
def undo_last_action(self, account_id: str) -> None:
```

**Logic by revision action type:**

| Action | Undo Behavior |
|--------|---------------|
| `CREATE` | Soft-delete the transaction (mark `is_deleted=True`) |
| `UPDATE` | Restore `before_json` state to the transaction |
| `SOFT_DELETE` | Restore the transaction (mark `is_deleted=False`) |
| `RESTORE` | Re-delete the transaction (mark `is_deleted=True`) |

**Implementation Steps:**

1. Get the latest revision for the account:
   ```python
   latest_revision = self._transaction_repo.get_latest_revision(account_id)
   if not latest_revision:
       raise ValidationError("No actions to undo for this account")
   ```

2. Load the transaction being undone:
   ```python
   transaction = self._transaction_repo.get_by_id(latest_revision.txn_id)
   if not transaction:
       raise NotFoundError("Transaction", latest_revision.txn_id)
   ```

3. Apply undo logic based on action type:
   ```python
   if latest_revision.action == RevisionAction.CREATE:
       # Undo create = soft delete
       self.soft_delete_transaction(latest_revision.txn_id)
   
   elif latest_revision.action == RevisionAction.UPDATE:
       # Undo update = restore before_json state
       before_state = json.loads(latest_revision.before_json)
       # Convert JSON back to Transaction fields and update
       patch = TransactionUpdate(
           txn_time_est=datetime.fromisoformat(before_state['txn_time_est']),
           symbol=before_state.get('symbol'),
           quantity=Decimal(before_state['quantity']) if before_state.get('quantity') else None,
           price=Decimal(before_state['price']) if before_state.get('price') else None,
           cash_amount=Decimal(before_state['cash_amount']) if before_state.get('cash_amount') else None,
           fees=Decimal(before_state.get('fees', '0')),
           note=before_state.get('note'),
       )
       self.edit_transaction(latest_revision.txn_id, patch)
   
   elif latest_revision.action == RevisionAction.SOFT_DELETE:
       # Undo delete = restore
       transaction.is_deleted = False
       transaction.updated_at_est = now_eastern()
       self._transaction_repo.update(transaction)
       self._create_revision(transaction, RevisionAction.RESTORE, before=self._to_json(transaction))
   
   elif latest_revision.action == RevisionAction.RESTORE:
       # Undo restore = re-delete
       self.soft_delete_transaction(latest_revision.txn_id)
   ```

4. After any undo, the caller (API/UI) should rebuild the portfolio:
   ```python
   # In the calling code:
   portfolio_engine.rebuild_account(account_id)
   ```

**Edge Cases to Handle:**
- Transaction was hard-deleted (shouldn't happen, but check)
- `before_json` is malformed or missing
- Multiple consecutive undos (each creates a new revision)

**Testing:**
- Create a transaction, undo → transaction should be soft-deleted
- Edit a transaction, undo → transaction should have original values
- Soft-delete a transaction, undo → transaction should be restored
- Chain: create → edit → delete → undo → undo → undo

---

## 2. SELL Validation - Insufficient Shares Check (P1)

**File:** `src/app/services/ledger_service.py`  
**Method:** `LedgerService._validate_transaction_create()`

### Current State
- TODO comment at line 245
- No validation that user has enough shares to sell

### What It Should Do
Prevent users from selling more shares of a symbol than they currently own in that account.

### Implementation Requirements

**Location:** Inside `_validate_transaction_create()`, after basic field validation for SELL.

**Dependencies Required:**
- Need access to `PortfolioEngine` to check current position
- Either inject `PortfolioEngine` into `LedgerService` or access via a callback

**Option A: Inject PortfolioEngine (Recommended)**

1. Update `LedgerService.__init__`:
   ```python
   def __init__(
       self,
       account_repo: AccountRepository,
       transaction_repo: TransactionRepository,
       portfolio_engine: Optional['PortfolioEngine'] = None,  # Optional for backward compat
   ):
       self._account_repo = account_repo
       self._transaction_repo = transaction_repo
       self._portfolio_engine = portfolio_engine
   ```

2. Add validation in `_validate_transaction_create()`:
   ```python
   if data.txn_type == TransactionType.SELL:
       if self._portfolio_engine:
           if not self._portfolio_engine.validate_sell(
               account_id=data.account_id,
               symbol=data.symbol,
               quantity=data.quantity,
           ):
               # Get current shares for error message
               position = self._portfolio_engine._cache_repo.get_position(
                   data.account_id, data.symbol
               )
               current_shares = position.shares if position else Decimal("0")
               raise InsufficientSharesError(
                   symbol=data.symbol,
                   requested=str(data.quantity),
                   available=str(current_shares),
               )
   ```

3. Update dependency injection in `api/deps.py` and `app_context.py` to pass portfolio_engine.

**Option B: Validation Callback (Alternative)**
Pass a validation callback that can check shares without tight coupling.

**Note:** The `PortfolioEngine.validate_sell()` method already exists and works correctly.

---

## 3. CASH_WITHDRAW Validation - Insufficient Cash Check (P1)

**File:** `src/app/services/ledger_service.py`  
**Method:** `LedgerService._validate_transaction_create()`

### Current State
- TODO comment at line 251
- No validation that user has enough cash to withdraw

### What It Should Do
When `enforce_cash_balance` setting is enabled, prevent users from withdrawing more cash than available in the account.

### Implementation Requirements

**Location:** Inside `_validate_transaction_create()`, after basic field validation for CASH_WITHDRAW.

**Implementation:**

```python
if data.txn_type == TransactionType.CASH_WITHDRAW:
    if data.cash_amount is None or data.cash_amount <= 0:
        raise ValidationError("CASH_WITHDRAW requires cash_amount > 0")
    
    # Check if enforcement is enabled
    settings = get_settings()
    if settings.enforce_cash_balance and self._portfolio_engine:
        if not self._portfolio_engine.validate_withdrawal(
            account_id=data.account_id,
            amount=data.cash_amount,
            enforce=True,
        ):
            # Get current cash for error message
            cash = self._portfolio_engine.get_cash_balance(data.account_id)
            raise InsufficientCashError(
                requested=str(data.cash_amount),
                available=str(cash),
            )
```

**Note:** The `PortfolioEngine.validate_withdrawal()` method already exists and works correctly.

**Configuration:**
- `enforce_cash_balance` is already in `Settings` (default: `False`)
- When `False`, withdrawals are allowed even if they result in negative cash

---

## 4. Get All Account IDs in Analysis Endpoint (P2)

**File:** `src/app/api/routers/analysis.py`  
**Function:** `get_positions()`

### Current State
- When no `account_ids` parameter is provided, returns empty list
- TODO comment at line 38

### What It Should Do
When no account IDs are specified, include positions from ALL accounts (aggregated view).

### Implementation Requirements

```python
@router.get("/positions", response_model=PositionsResponse)
def get_positions(
    account_ids: Optional[str] = Query(None, description="Comma-separated account IDs (all if empty)"),
    portfolio: PortfolioEngine = Depends(get_portfolio_engine),
    analysis: AnalysisService = Depends(get_analysis_service),
    ledger: LedgerService = Depends(get_ledger_service),  # Add this dependency
) -> PositionsResponse:
    # Parse account IDs
    if account_ids:
        account_id_list = account_ids.split(",")
    else:
        # Get all account IDs
        accounts = ledger.list_accounts()
        account_id_list = [a.account_id for a in accounts]
    
    # Rest of the function remains the same...
```

**Also update:**
- `get_cash_balance()` endpoint
- `get_today_pnl()` endpoint
- `get_allocation()` endpoint

---

## 5. Real Market Data Provider (P2)

**File:** `src/app/providers/stub_provider.py` (or new file)

### Current State
- `StubMarketDataProvider` returns hardcoded/random prices
- Works offline but not useful for real tracking

### What It Should Do
Fetch real-time stock quotes from a market data API.

### Implementation Requirements

**Create:** `src/app/providers/yahoo_provider.py` (or other API)

```python
"""Yahoo Finance market data provider."""

import yfinance as yf
from decimal import Decimal
from datetime import datetime
from typing import Dict, List

from app.domain.views import Quote
from app.core.timezone import now_eastern, EASTERN_TZ


class YahooFinanceProvider:
    """
    Real market data provider using Yahoo Finance.
    
    Free tier with reasonable rate limits.
    """
    
    def __init__(self):
        self._cache: Dict[str, Quote] = {}
        self._cache_time: datetime = None
        self._cache_ttl_seconds: int = 15  # Yahoo has ~15s delay anyway
    
    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Fetch real-time quotes from Yahoo Finance."""
        if not symbols:
            return {}
        
        result = {}
        as_of = now_eastern()
        
        try:
            # Batch fetch
            tickers = yf.Tickers(" ".join(symbols))
            
            for symbol in symbols:
                upper_symbol = symbol.upper()
                try:
                    ticker = tickers.tickers.get(upper_symbol)
                    if ticker:
                        info = ticker.info
                        # Get current price and previous close
                        last_price = Decimal(str(info.get('regularMarketPrice', 0)))
                        prev_close = Decimal(str(info.get('regularMarketPreviousClose', 0)))
                        
                        if last_price > 0:
                            result[upper_symbol] = Quote(
                                symbol=upper_symbol,
                                last_price=last_price,
                                prev_close=prev_close,
                                as_of=as_of,
                            )
                except Exception:
                    # Skip symbols that fail
                    continue
                    
        except Exception as e:
            # Network error - return empty, let caller use cache
            pass
        
        return result
    
    def is_trading_day(self) -> bool:
        """Check if US markets are open today."""
        # Use pandas_market_calendars or hardcoded logic
        # See market calendar section below
        pass
    
    def previous_trading_day(self) -> str:
        """Get the previous trading day."""
        # See market calendar section below
        pass
```

**Dependencies to add:**
```toml
# pyproject.toml
"yfinance>=0.2.0",
```

**Alternative APIs:**
- Alpha Vantage (free tier: 5 calls/min)
- Polygon.io (free tier available)
- IEX Cloud (free tier: 50k calls/month)

---

## 6. Market Calendar (P3)

**File:** `src/app/providers/stub_provider.py`

### Current State
- `is_trading_day()` always returns `True`
- `previous_trading_day()` returns yesterday (ignores weekends/holidays)

### What It Should Do
Correctly identify US market trading days and non-trading days.

### Implementation Requirements

**Option A: Use `pandas_market_calendars` library**

```python
import pandas_market_calendars as mcal
from datetime import date, timedelta

class MarketCalendar:
    """US market calendar utilities."""
    
    def __init__(self):
        self._nyse = mcal.get_calendar('NYSE')
    
    def is_trading_day(self, check_date: date = None) -> bool:
        """Check if a date is a trading day."""
        if check_date is None:
            check_date = date.today()
        
        schedule = self._nyse.schedule(
            start_date=check_date,
            end_date=check_date
        )
        return len(schedule) > 0
    
    def previous_trading_day(self, from_date: date = None) -> date:
        """Get the most recent trading day before from_date."""
        if from_date is None:
            from_date = date.today()
        
        # Look back up to 10 days (handles long weekends)
        start = from_date - timedelta(days=10)
        schedule = self._nyse.schedule(start_date=start, end_date=from_date - timedelta(days=1))
        
        if len(schedule) > 0:
            return schedule.index[-1].date()
        return from_date - timedelta(days=1)  # Fallback
```

**Option B: Hardcoded holidays (simpler, no extra dependency)**

```python
US_MARKET_HOLIDAYS_2024 = {
    date(2024, 1, 1),   # New Year's Day
    date(2024, 1, 15),  # MLK Day
    date(2024, 2, 19),  # Presidents Day
    date(2024, 3, 29),  # Good Friday
    date(2024, 5, 27),  # Memorial Day
    date(2024, 6, 19),  # Juneteenth
    date(2024, 7, 4),   # Independence Day
    date(2024, 9, 2),   # Labor Day
    date(2024, 11, 28), # Thanksgiving
    date(2024, 12, 25), # Christmas
}

def is_trading_day(check_date: date = None) -> bool:
    if check_date is None:
        check_date = date.today()
    
    # Weekend check
    if check_date.weekday() >= 5:
        return False
    
    # Holiday check
    if check_date in US_MARKET_HOLIDAYS_2024:
        return False
    
    return True
```

---

## Summary Table

| # | Feature | Priority | Complexity | Dependencies |
|---|---------|----------|------------|--------------|
| 1 | Undo Last Action | P0 | Medium | JSON parsing, revision logic |
| 2 | SELL Validation | P1 | Low | PortfolioEngine injection |
| 3 | CASH_WITHDRAW Validation | P1 | Low | PortfolioEngine injection |
| 4 | Get All Account IDs | P2 | Low | Add LedgerService dependency |
| 5 | Real Market Data Provider | P2 | Medium | External API (yfinance) |
| 6 | Market Calendar | P3 | Low | Optional: pandas_market_calendars |

---

## Implementation Order Recommendation

1. **Items 2 & 3** (SELL/WITHDRAW validation) - Low effort, high impact on data integrity
2. **Item 1** (Undo) - Core feature, enables user recovery from mistakes
3. **Item 4** (All accounts default) - Small UX improvement
4. **Items 5 & 6** (Real market data) - Only needed when moving beyond testing

---

## Testing Checklist

For each implementation, ensure tests cover:

- [ ] Happy path (normal operation)
- [ ] Edge cases (zero values, empty states)
- [ ] Error conditions (validation failures, not found)
- [ ] Integration with existing features
- [ ] UI reflects changes correctly (desktop app)
- [ ] API returns correct status codes
