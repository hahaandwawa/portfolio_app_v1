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
  cash_destination_account?: string | null;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface TransactionPayload {
  account_name: string;
  txn_type: TransactionType;
  txn_time_est: string;
  symbol?: string;
  quantity?: number;
  price?: number;
  cash_amount?: number;
  fees?: number;
  note?: string;
  cash_destination_account?: string | null;
}


export interface TransactionImportResult {
  imported: number;
  accounts_created: string[];
  errors: string[];
}

// Portfolio (from GET /portfolio; optional fields when quotes enabled)
export interface PortfolioPosition {
  symbol: string;
  quantity: number;
  total_cost: number;
  display_name?: string | null;
  latest_price?: number | null;
  cost_price?: number | null;
  market_value?: number | null;
  unrealized_pnl?: number | null;
  unrealized_pnl_pct?: number | null;
  weight_pct?: number | null;
  previous_close?: number | null;
}

export interface AccountCash {
  account_name: string;
  cash_balance: number;
}

export interface PortfolioSummary {
  cash_balance: number;
  account_cash: AccountCash[];
  positions: PortfolioPosition[];
}

/** Per-account position for a symbol (GET /portfolio/positions-by-symbol). */
export interface PositionByAccount {
  account_name: string;
  quantity: number;
}

export interface PositionsBySymbolResponse {
  symbol: string;
  positions: PositionByAccount[];
}

/** Net value curve API response (GET /net-value-curve). Columnar arrays; tooltips use index i. */
export interface NetValueCurveResponse {
  baseline_label: string;
  price_type: string;
  includes_cash: boolean;
  dates: string[];
  baseline: number[];
  market_value: number[];
  profit_loss: number[];
  profit_loss_pct: (number | null)[];
  is_trading_day: boolean[];
  last_trading_date: string[];
}
