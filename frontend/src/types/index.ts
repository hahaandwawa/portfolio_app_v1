export interface Account {
  name: string;
  transaction_count: number;
}

export type TransactionType = "BUY" | "SELL" | "CASH_DEPOSIT" | "CASH_WITHDRAW";

export interface Transaction {
  txn_id: string;
  account_name: string;
  txn_type: TransactionType;
  txn_time_est: string;
  symbol: string | null;
  quantity: number | null;
  price: number | null;
  cash_amount: number | null;
  amount: number | null;
  fees: number;
  note: string | null;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface TransactionCreatePayload {
  account_name: string;
  txn_type: TransactionType;
  txn_time_est: string;
  symbol?: string;
  quantity?: number;
  price?: number;
  cash_amount?: number;
  fees?: number;
  note?: string;
}

export interface TransactionEditPayload {
  account_name: string;
  txn_type: TransactionType;
  txn_time_est: string;
  symbol?: string;
  quantity?: number;
  price?: number;
  cash_amount?: number;
  fees?: number;
  note?: string;
}

export interface TransactionImportResult {
  imported: number;
  accounts_created: string[];
  errors: string[];
}
