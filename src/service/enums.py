from enum import Enum


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    CASH_DEPOSIT = "CASH_DEPOSIT"
    CASH_WITHDRAW = "CASH_WITHDRAW"
