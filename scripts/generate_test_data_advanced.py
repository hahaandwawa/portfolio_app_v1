#!/usr/bin/env python3
"""
Advanced test data generator with more realistic scenarios.
Generates data for multiple accounts with different trading strategies.
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


def generate_advanced_test_data():
    """Generate advanced realistic trading data for multiple accounts."""
    
    # Initialize services
    account_service = AccountService()
    transaction_service = TransactionService()
    
    # Calculate date range (last 3 months from today)
    today = date.today()
    start_date = today - timedelta(days=90)
    
    # Limit total transactions to 100
    MAX_TRANSACTIONS = 100
    
    print("=" * 70)
    print("ADVANCED TEST DATA GENERATOR")
    print("=" * 70)
    print(f"Date range: {start_date} to {today}")
    print(f"Max transactions: {MAX_TRANSACTIONS}\n")
    
    # Stock universe with realistic prices
    stocks = {
        "AAPL": 180.0,
        "MSFT": 420.0,
        "GOOGL": 160.0,
        "AMZN": 150.0,
        "TSLA": 250.0,
        "NVDA": 500.0,
        "META": 350.0,
        "NFLX": 450.0,
        "JPM": 180.0,
        "V": 280.0,
        "JNJ": 160.0,
        "WMT": 170.0,
    }
    
    # Account 1: Conservative DCA Investor
    print("\n[Account 1] Conservative DCA Investor")
    print("-" * 70)
    account1 = "Retirement Account"
    try:
        account_service.create_account(AccountCreate(name=account1))
        print(f"✓ Created account: {account1}")
    except:
        print(f"✓ Account exists: {account1}")
    
    transactions = []
    cash1 = Decimal("100000")
    
    # Initial deposit
    transactions.append(TransactionCreate(
        account_name=account1,
        txn_type=TransactionType.CASH_DEPOSIT,
        cash_amount=cash1,
        txn_time_est=datetime.combine(start_date, datetime.min.time().replace(hour=9, minute=0)),
        txn_id=f"acc1_deposit_{start_date.isoformat()}",
        note="Retirement account initial funding"
    ))
    
    # Weekly DCA: $3000 per week - limit to ~10 weeks
    conservative_stocks = ["AAPL", "MSFT", "GOOGL", "JPM", "V", "JNJ"]
    week_start = start_date
    week_num = 0
    max_dca = 10  # Limit DCA purchases
    
    while week_start <= today and week_num < max_dca:
        days_until_monday = (7 - week_start.weekday()) % 7
        if days_until_monday == 0 and week_start.weekday() != 0:
            days_until_monday = 7
        monday = week_start + timedelta(days=days_until_monday)
        
        if monday <= today:
            symbol = conservative_stocks[week_num % len(conservative_stocks)]
            base_price = stocks[symbol]
            price = Decimal(str(round(base_price * random.uniform(0.95, 1.05), 2)))
            quantity = Decimal(str(round(3000 / float(price), 4)))
            
            if cash1 >= quantity * price + Decimal("1"):
                transactions.append(TransactionCreate(
                    account_name=account1,
                    txn_type=TransactionType.BUY,
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                    fees=Decimal("1.00"),
                    txn_time_est=datetime.combine(monday, datetime.min.time().replace(hour=10, minute=0)),
                    txn_id=f"acc1_dca_{symbol}_{monday.isoformat()}",
                    note=f"Weekly DCA - {symbol}"
                ))
                cash1 -= (quantity * price + Decimal("1.00"))
                week_num += 1
        
        week_start = monday + timedelta(days=7)
    
    print(f"  Generated {week_num} DCA purchases")
    
    # Account 2: Active Trader
    print("\n[Account 2] Active Trader")
    print("-" * 70)
    account2 = "Trading Account"
    try:
        account_service.create_account(AccountCreate(name=account2))
        print(f"✓ Created account: {account2}")
    except:
        print(f"✓ Account exists: {account2}")
    
    cash2 = Decimal("50000")
    
    # Initial deposit
    transactions.append(TransactionCreate(
        account_name=account2,
        txn_type=TransactionType.CASH_DEPOSIT,
        cash_amount=cash2,
        txn_time_est=datetime.combine(start_date, datetime.min.time().replace(hour=9, minute=0)),
        txn_id=f"acc2_deposit_{start_date.isoformat()}",
        note="Trading account funding"
    ))
    
    # More frequent, smaller trades - limit to ~25 trades
    trading_stocks = ["TSLA", "NVDA", "META", "NFLX", "AMZN"]
    positions2 = {s: Decimal("0") for s in trading_stocks}
    
    max_trades = min(25, MAX_TRANSACTIONS - len(transactions) - 20)  # Reserve for account 3
    trade_count = 0
    
    for i in range(max_trades * 2):  # Try more times to get valid trades
        if len(transactions) >= MAX_TRANSACTIONS - 20:
            break
        if trade_count >= max_trades:
            break
            
        txn_date = start_date + timedelta(days=random.randint(0, 90))
        if txn_date <= today and txn_date.weekday() < 5:
            symbol = random.choice(trading_stocks)
            base_price = stocks[symbol]
            
            # 60% buys, 40% sells
            if random.random() < 0.6 or positions2[symbol] == 0:
                # Buy
                price = Decimal(str(round(base_price * random.uniform(0.90, 1.10), 2)))
                quantity = Decimal(str(round(random.uniform(2, 15), 4)))
                
                if cash2 >= quantity * price + Decimal("1"):
                    transactions.append(TransactionCreate(
                        account_name=account2,
                        txn_type=TransactionType.BUY,
                        symbol=symbol,
                        quantity=quantity,
                        price=price,
                        fees=Decimal("1.00"),
                        txn_time_est=datetime.combine(txn_date, datetime.min.time().replace(
                            hour=random.randint(9, 15),
                            minute=0
                        )),
                        txn_id=f"acc2_trade_{symbol}_{txn_date.isoformat()}_{i}",
                        note="Active trading"
                    ))
                    cash2 -= (quantity * price + Decimal("1.00"))
                    positions2[symbol] += quantity
                    trade_count += 1
            else:
                # Sell
                price = Decimal(str(round(base_price * random.uniform(1.05, 1.25), 2)))
                sell_qty = positions2[symbol] * Decimal(str(random.uniform(0.2, 0.6)))
                quantity = Decimal(str(round(float(sell_qty), 4)))
                
                if quantity > Decimal("0.0001"):
                    transactions.append(TransactionCreate(
                        account_name=account2,
                        txn_type=TransactionType.SELL,
                        symbol=symbol,
                        quantity=quantity,
                        price=price,
                        fees=Decimal("1.00"),
                        txn_time_est=datetime.combine(txn_date, datetime.min.time().replace(
                            hour=random.randint(9, 15),
                            minute=0
                        )),
                        txn_id=f"acc2_sell_{symbol}_{txn_date.isoformat()}_{i}",
                        note="Take profit"
                    ))
                    cash2 += (quantity * price - Decimal("1.00"))
                    positions2[symbol] -= quantity
                    trade_count += 1
    
    print(f"  Generated {trade_count} active trades")
    
    # Account 3: Growth Investor (Tech Focus)
    print("\n[Account 3] Growth Investor")
    print("-" * 70)
    account3 = "Growth Portfolio"
    try:
        account_service.create_account(AccountCreate(name=account3))
        print(f"✓ Created account: {account3}")
    except:
        print(f"✓ Account exists: {account3}")
    
    cash3 = Decimal("75000")
    
    # Initial deposit
    transactions.append(TransactionCreate(
        account_name=account3,
        txn_type=TransactionType.CASH_DEPOSIT,
        cash_amount=cash3,
        txn_time_est=datetime.combine(start_date, datetime.min.time().replace(hour=9, minute=0)),
        txn_id=f"acc3_deposit_{start_date.isoformat()}",
        note="Growth portfolio funding"
    ))
    
    # Bi-weekly larger purchases focused on tech - limit to ~8 purchases
    growth_stocks = ["NVDA", "TSLA", "META", "AAPL", "MSFT"]
    
    biweekly_date = start_date
    purchase_count = 0
    max_purchases = min(8, MAX_TRANSACTIONS - len(transactions))
    
    while biweekly_date <= today and purchase_count < max_purchases:
        if biweekly_date.weekday() < 5:  # Weekday
            symbol = growth_stocks[purchase_count % len(growth_stocks)]
            base_price = stocks[symbol]
            price = Decimal(str(round(base_price * random.uniform(0.95, 1.05), 2)))
            quantity = Decimal(str(round(5000 / float(price), 4)))  # $5000 per purchase
            
            if cash3 >= quantity * price + Decimal("1"):
                transactions.append(TransactionCreate(
                    account_name=account3,
                    txn_type=TransactionType.BUY,
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                    fees=Decimal("1.00"),
                    txn_time_est=datetime.combine(biweekly_date, datetime.min.time().replace(hour=10, minute=0)),
                    txn_id=f"acc3_growth_{symbol}_{biweekly_date.isoformat()}",
                    note=f"Growth investment - {symbol}"
                ))
                cash3 -= (quantity * price + Decimal("1.00"))
                purchase_count += 1
        
        biweekly_date += timedelta(days=14)
    
    print(f"  Generated {purchase_count} growth investments")
    
    # Mid-period deposits for all accounts
    mid_date = start_date + timedelta(days=45)
    if mid_date <= today:
        transactions.append(TransactionCreate(
            account_name=account1,
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("20000"),
            txn_time_est=datetime.combine(mid_date, datetime.min.time().replace(hour=9, minute=0)),
            txn_id=f"acc1_mid_deposit",
            note="Additional retirement contribution"
        ))
        transactions.append(TransactionCreate(
            account_name=account2,
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("10000"),
            txn_time_est=datetime.combine(mid_date, datetime.min.time().replace(hour=9, minute=0)),
            txn_id=f"acc2_mid_deposit",
            note="Additional trading capital"
        ))
        print(f"\n✓ Added mid-period deposits")
    
    # Sort all transactions by date
    transactions.sort(key=lambda t: t.txn_time_est)
    
    # Ensure we don't exceed limit
    if len(transactions) > MAX_TRANSACTIONS:
        transactions = transactions[:MAX_TRANSACTIONS]
    
    # Create transactions in batch for better performance
    print(f"\n" + "=" * 70)
    print(f"Creating {len(transactions)} transactions...")
    print("=" * 70)
    
    created = 0
    failed = 0
    
    # Use batch create for better performance
    try:
        transaction_service.create_batch_transaction(transactions)
        created = len(transactions)
        print(f"✓ Batch created {created} transactions")
    except Exception as e:
        # Fallback to individual creates if batch fails
        print(f"Batch create failed, creating individually: {e}")
        for txn in transactions:
            try:
                transaction_service.create_transaction(txn)
                created += 1
                if created % 20 == 0:
                    print(f"  Created {created}/{len(transactions)}...")
            except Exception as err:
                failed += 1
                if failed <= 5:  # Only show first 5 errors
                    print(f"✗ Failed: {txn.txn_id} - {err}")
    
    # Summary
    print(f"\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✓ Successfully created: {created} transactions")
    if failed > 0:
        print(f"✗ Failed: {failed} transactions")
    
    # Breakdown by account and type
    by_account = {}
    by_type = {}
    
    for txn in transactions:
        acc = txn.account_name
        ttype = txn.txn_type.value
        
        by_account[acc] = by_account.get(acc, 0) + 1
        by_type[ttype] = by_type.get(ttype, 0) + 1
    
    print(f"\nBy Account:")
    for acc, count in sorted(by_account.items()):
        print(f"  {acc}: {count} transactions")
    
    print(f"\nBy Type:")
    for ttype, count in sorted(by_type.items()):
        print(f"  {ttype}: {count} transactions")
    
    print(f"\n✓ Advanced test data generation complete!")
    print(f"\nYou can now test:")
    print(f"  - Multiple accounts filtering")
    print(f"  - Net value curve with different strategies")
    print(f"  - Portfolio views per account")


if __name__ == "__main__":
    try:
        generate_advanced_test_data()
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
