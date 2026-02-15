import type {
  Account,
  Transaction,
  TransactionListResponse,
  TransactionPayload,
  TransactionImportResult,
  PortfolioSummary,
  PositionsBySymbolResponse,
} from "../types";

const API_BASE = "/api";

async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const headers: HeadersInit = { ...options?.headers };
  // Only set Content-Type for requests that carry a body
  if (options?.body) {
    (headers as Record<string, string>)["Content-Type"] ??= "application/json";
  }
  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

async function getApiError(res: Response): Promise<string> {
  const text = await res.text();
  try {
    const j = JSON.parse(text) as { detail?: string | string[] };
    const d = j.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.join("; ");
    return text || res.statusText;
  } catch {
    return text || res.statusText;
  }
}

/** Build URLSearchParams with optional account filter. */
function accountSearchParams(accounts?: string[]): URLSearchParams {
  const search = new URLSearchParams();
  if (accounts?.length) {
    accounts.forEach((a) => search.append("account", a));
  }
  return search;
}

/** Append query string to path if non-empty. */
function withQuery(path: string, search: URLSearchParams): string {
  const qs = search.toString();
  return qs ? `${path}?${qs}` : path;
}

export const api = {
  getAccounts: () => fetchApi<Account[]>("/accounts"),

  postAccount: (name: string) =>
    fetchApi<Account>("/accounts", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),

  putAccount: (oldName: string, newName: string) =>
    fetchApi<Account>(`/accounts/${encodeURIComponent(oldName)}`, {
      method: "PUT",
      body: JSON.stringify({ name: newName }),
    }),

  deleteAccount: (name: string) =>
    fetchApi<void>(`/accounts/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),

  getTransactions(params: { account?: string[]; page?: number; page_size?: number }) {
    const search = accountSearchParams(params.account);
    if (params.page) search.set("page", String(params.page));
    if (params.page_size) search.set("page_size", String(params.page_size));
    return fetchApi<TransactionListResponse>(withQuery("/transactions", search));
  },

  postTransaction: (data: TransactionPayload) =>
    fetchApi<Transaction>("/transactions", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  putTransaction: (txnId: string, data: TransactionPayload) =>
    fetchApi<Transaction>(`/transactions/${txnId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteTransaction: (txnId: string) =>
    fetchApi<void>(`/transactions/${txnId}`, { method: "DELETE" }),

  /** POST CSV file; returns import result. */
  async importTransactionsCsv(file: File): Promise<TransactionImportResult> {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/transactions/import`, {
      method: "POST",
      body: form,
      // Do not set Content-Type; browser sets multipart boundary automatically
    });
    if (!res.ok) throw new Error(await getApiError(res));
    return res.json();
  },

  /** GET CSV blob and trigger download. Optional account filter. */
  async exportTransactionsCsv(params?: { account?: string[] }): Promise<Blob> {
    const search = accountSearchParams(params?.account);
    const res = await fetch(withQuery(`${API_BASE}/transactions/export`, search));
    if (!res.ok) throw new Error(await getApiError(res));
    return res.blob();
  },

  /** GET template CSV and trigger download. */
  async downloadTransactionsTemplate(): Promise<Blob> {
    const res = await fetch(`${API_BASE}/transactions/template`);
    if (!res.ok) throw new Error(await getApiError(res));
    return res.blob();
  },

  /** GET portfolio summary (positions + per-account cash). Optional account filter. */
  getPortfolio(params?: { account?: string[] }): Promise<PortfolioSummary> {
    const search = accountSearchParams(params?.account);
    return fetchApi<PortfolioSummary>(withQuery("/portfolio", search));
  },

  /** GET per-account quantities for a symbol (for SELL default account / cash destination). */
  getPositionsBySymbol(symbol: string): Promise<PositionsBySymbolResponse> {
    const trimmed = symbol?.trim().toUpperCase() ?? "";
    if (!trimmed) return Promise.resolve({ symbol: trimmed, positions: [] });
    const search = new URLSearchParams({ symbol: trimmed });
    return fetchApi<PositionsBySymbolResponse>(`/portfolio/positions-by-symbol?${search}`);
  },
};
