#!/usr/bin/env python3
"""
Generate realistic test data for the last 3 months.
Simulates a real user's trading activity with deposits, buys, and sells.
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from decimal import Decimal
import random

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.service.account_service import AccountService, AccountCreate
from src.service.transaction_service import TransactionService, TransactionCreate
from src.service.enums import TransactionType


def generate_realistic_data():
    """Generate realistic trading data for the last 3 months."""
    
    # Initialize services
    account_service = AccountService()
    transaction_service = TransactionService()
    
    # Create account
    account_name = "Main Brokerage"
    print(f"Creating account: {account_name}")
    try:
        account_service.create_account(AccountCreate(name=account_name))
        print(f"✓ Account '{account_name}' created")
    except Exception as e:
        if "already taken" in str(e):
            print(f"✓ Account '{account_name}' already exists")
        else:
            raise
    
    # Calculate date range (last 3 months from today)
    today = date.today()
    start_date = today - timedelta(days=90)
    
    print(f"\nGenerating transactions from {start_date} to {today}")
    print("=" * 60)
    
    # Realistic stock symbols with approximate prices (as of late 2025)
    stocks = [
        ("AAPL", 180.0),   # Apple
        ("MSFT", 420.0),   # Microsoft
        ("GOOGL", 160.0),  # Google
        ("AMZN", 150.0),   # Amazon
        ("TSLA", 250.0),   # Tesla
        ("NVDA", 500.0),   # NVIDIA
        ("META", 350.0),   # Meta
        ("NFLX", 450.0),   # Netflix
    ]
    
    # Limit total transactions to 100
    MAX_TRANSACTIONS = 100
    
    transactions = []
    current_date = start_date
    cash_balance = Decimal("0")
    
    # Initial deposit
    initial_deposit = Decimal("50000")
    transactions.append(TransactionCreate(
        account_name=account_name,
        txn_type=TransactionType.CASH_DEPOSIT,
        cash_amount=initial_deposit,
        txn_time_est=datetime.combine(start_date, datetime.min.time().replace(hour=9, minute=0)),
        txn_id=f"deposit_initial_{start_date.isoformat()}",
        note="Initial account funding"
    ))
    cash_balance += initial_deposit
    print(f"✓ Initial deposit: ${initial_deposit:,.2f}")
    
    # Generate transactions over 3 months
    # Strategy: Regular DCA (Dollar Cost Averaging) with some opportunistic buys/sells
    
    # Track positions
    positions = {symbol: {"shares": Decimal("0"), "avg_cost": Decimal("0")} for symbol, _ in stocks}
    
    # Limit total transactions to 100 (including deposits)
    MAX_TRANSACTIONS = 100
    
    # Weekly DCA purchases (every Monday) - limit to ~12 weeks
    week_start = start_date
    dca_count = 0
    max_dca = min(12, (MAX_TRANSACTIONS - 10) // 2)  # Reserve space for other transactions
    
    while week_start <= today and dca_count < max_dca:
        # Find next Monday
        days_until_monday = (7 - week_start.weekday()) % 7
        if days_until_monday == 0 and week_start.weekday() != 0:
            days_until_monday = 7
        monday = week_start + timedelta(days=days_until_monday)
        
        if monday <= today:
            # DCA: Buy $2000 worth of a random stock
            symbol, base_price = random.choice(stocks)
            price_variation = random.uniform(0.95, 1.05)
            price = Decimal(str(round(base_price * price_variation, 2)))
            quantity = Decimal(str(round(2000 / float(price), 4)))
            
            if cash_balance >= quantity * price:
                transactions.append(TransactionCreate(
                    account_name=account_name,
                    txn_type=TransactionType.BUY,
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                    fees=Decimal("1.00"),
                    txn_time_est=datetime.combine(monday, datetime.min.time().replace(hour=10, minute=0)),
                    txn_id=f"dca_{symbol}_{monday.isoformat()}",
                    note=f"Weekly DCA purchase"
                ))
                cash_balance -= (quantity * price + Decimal("1.00"))
                positions[symbol]["shares"] += quantity
                dca_count += 1
                if len(transactions) % 10 == 0:
                    print(f"  Generated {len(transactions)} transactions...")
        
        week_start = monday + timedelta(days=7)
    
    # Add opportunistic buys - limit based on remaining transaction count
    remaining = MAX_TRANSACTIONS - len(transactions) - 5  # Reserve for sells and deposits
    opportunistic_buys = min(remaining // 2, 15)
    
    for i in range(opportunistic_buys):
        if len(transactions) >= MAX_TRANSACTIONS - 5:
            break
        txn_date = start_date + timedelta(days=random.randint(0, 90))
        if txn_date <= today and txn_date.weekday() < 5:
            symbol, base_price = random.choice(stocks)
            price_variation = random.uniform(0.90, 1.10)
            price = Decimal(str(round(base_price * price_variation, 2)))
            quantity = Decimal(str(round(random.uniform(5, 20), 4)))
            
            if cash_balance >= quantity * price:
                transactions.append(TransactionCreate(
                    account_name=account_name,
                    txn_type=TransactionType.BUY,
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                    fees=Decimal("1.00"),
                    txn_time_est=datetime.combine(txn_date, datetime.min.time().replace(
                        hour=random.randint(9, 15),
                        minute=0
                    )),
                    txn_id=f"buy_{symbol}_{txn_date.isoformat()}_{i}",
                    note="Opportunistic purchase"
                ))
                cash_balance -= (quantity * price + Decimal("1.00"))
                positions[symbol]["shares"] += quantity
    
    # Add some sells (take profits) - limit to ~8 sells
    max_sells = min(8, MAX_TRANSACTIONS - len(transactions))
    sell_count = 0
    
    for i in range(max_sells * 3):  # Try more times to get valid sells
        if len(transactions) >= MAX_TRANSACTIONS:
            break
        if sell_count >= max_sells:
            break
            
        txn_date = start_date + timedelta(days=random.randint(30, 90))
        if txn_date <= today and txn_date.weekday() < 5:
            available_symbols = [s for s, p in positions.items() if p["shares"] > 0]
            if available_symbols:
                symbol = random.choice(available_symbols)
                base_price = dict(stocks)[symbol]
                price_variation = random.uniform(1.05, 1.20)
                price = Decimal(str(round(base_price * price_variation, 2)))
                max_sell = positions[symbol]["shares"] * Decimal("0.5")
                quantity = Decimal(str(round(float(max_sell) * random.uniform(0.2, 0.5), 4)))
                
                if quantity > Decimal("0.0001"):
                    transactions.append(TransactionCreate(
                        account_name=account_name,
                        txn_type=TransactionType.SELL,
                        symbol=symbol,
                        quantity=quantity,
                        price=price,
                        fees=Decimal("1.00"),
                        txn_time_est=datetime.combine(txn_date, datetime.min.time().replace(
                            hour=random.randint(9, 15),
                            minute=0
                        )),
                        txn_id=f"sell_{symbol}_{txn_date.isoformat()}_{i}",
                        note="Take profit"
                    ))
                    cash_balance += (quantity * price - Decimal("1.00"))
                    positions[symbol]["shares"] -= quantity
                    sell_count += 1
    
    # Add a mid-period deposit
    mid_date = start_date + timedelta(days=45)
    if mid_date <= today:
        additional_deposit = Decimal("20000")
        transactions.append(TransactionCreate(
            account_name=account_name,
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=additional_deposit,
            txn_time_est=datetime.combine(mid_date, datetime.min.time().replace(hour=9, minute=0)),
            txn_id=f"deposit_mid_{mid_date.isoformat()}",
            note="Additional funding"
        ))
        cash_balance += additional_deposit
        print(f"✓ {mid_date.strftime('%Y-%m-%d')}: Deposit ${additional_deposit:,.2f}")
    
    # Sort transactions by date
    transactions.sort(key=lambda t: t.txn_time_est)
    
    # Ensure we don't exceed limit
    if len(transactions) > MAX_TRANSACTIONS:
        transactions = transactions[:MAX_TRANSACTIONS]
    
    # Create transactions in batch for better performance
    print(f"\nCreating {len(transactions)} transactions...")
    print("=" * 60)
    
    created_count = 0
    # Use batch create for better performance
    try:
        transaction_service.create_batch_transaction(transactions)
        created_count = len(transactions)
        print(f"✓ Batch created {created_count} transactions")
    except Exception as e:
        # Fallback to individual creates if batch fails
        print(f"Batch create failed, creating individually: {e}")
        for txn in transactions:
            try:
                transaction_service.create_transaction(txn)
                created_count += 1
                if created_count % 20 == 0:
                    print(f"  Created {created_count}/{len(transactions)}...")
            except Exception as err:
                print(f"✗ Failed to create transaction {txn.txn_id}: {err}")
    
    print(f"\n✓ Successfully created {created_count} transactions")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Account: {account_name}")
    print(f"Date range: {start_date} to {today}")
    print(f"Total transactions: {created_count}")
    
    # Count by type
    buy_count = sum(1 for t in transactions if t.txn_type == TransactionType.BUY)
    sell_count = sum(1 for t in transactions if t.txn_type == TransactionType.SELL)
    deposit_count = sum(1 for t in transactions if t.txn_type == TransactionType.CASH_DEPOSIT)
    
    print(f"\nTransaction breakdown:")
    print(f"  Deposits: {deposit_count}")
    print(f"  Buys: {buy_count}")
    print(f"  Sells: {sell_count}")
    
    # Current positions
    print(f"\nCurrent positions:")
    for symbol, pos in positions.items():
        if pos["shares"] > 0:
            print(f"  {symbol}: {pos['shares']:.4f} shares")
    
    print(f"\nEstimated cash balance: ${cash_balance:,.2f}")
    print("\n✓ Test data generation complete!")
    print("\nYou can now:")
    print("  - View transactions: GET /transactions")
    print("  - View portfolio: GET /portfolio")
    print("  - View net value curve: GET /net-value-curve")


if __name__ == "__main__":
    try:
        generate_realistic_data()
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
