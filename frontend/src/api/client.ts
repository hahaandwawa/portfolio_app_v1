const API_BASE = "/api";

async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
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

export const api = {
  getAccounts: () =>
    fetchApi<{ name: string; transaction_count: number }[]>("/accounts"),
  postAccount: (name: string) =>
    fetchApi<{ name: string; transaction_count: number }>("/accounts", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  putAccount: (oldName: string, newName: string) =>
    fetchApi<{ name: string; transaction_count: number }>(
      `/accounts/${encodeURIComponent(oldName)}`,
      { method: "PUT", body: JSON.stringify({ name: newName }) }
    ),
  deleteAccount: (name: string) =>
    fetchApi<void>(`/accounts/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),
  getTransactions: (params: { account?: string[]; page?: number; page_size?: number }) => {
    const search = new URLSearchParams();
    if (params.account?.length) {
      params.account.forEach((a) => search.append("account", a));
    }
    if (params.page) search.set("page", String(params.page));
    if (params.page_size) search.set("page_size", String(params.page_size));
    const qs = search.toString();
    return fetchApi<{
      items: import("../types").Transaction[];
      total: number;
      page: number;
      page_size: number;
      total_pages: number;
    }>(`/transactions${qs ? `?${qs}` : ""}`);
  },
  postTransaction: (data: import("../types").TransactionCreatePayload) =>
    fetchApi<import("../types").Transaction>("/transactions", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  putTransaction: (txnId: string, data: import("../types").TransactionEditPayload) =>
    fetchApi<import("../types").Transaction>(`/transactions/${txnId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteTransaction: (txnId: string) =>
    fetchApi<void>(`/transactions/${txnId}`, { method: "DELETE" }),

  /** POST CSV file; returns import result. */
  async importTransactionsCsv(file: File): Promise<import("../types").TransactionImportResult> {
    const url = `${API_BASE}/transactions/import`;
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(url, {
      method: "POST",
      body: form,
      headers: {}, // do not set Content-Type; browser sets multipart boundary
    });
    if (!res.ok) {
      const msg = await getApiError(res);
      throw new Error(msg);
    }
    return res.json();
  },

  /** GET CSV blob and trigger download. Optional account filter. */
  async exportTransactionsCsv(params?: { account?: string[] }): Promise<Blob> {
    const search = new URLSearchParams();
    if (params?.account?.length) {
      params.account.forEach((a) => search.append("account", a));
    }
    const qs = search.toString();
    const url = `${API_BASE}/transactions/export${qs ? `?${qs}` : ""}`;
    const res = await fetch(url);
    if (!res.ok) {
      const msg = await getApiError(res);
      throw new Error(msg);
    }
    return res.blob();
  },

  /** GET template CSV and trigger download. */
  async downloadTransactionsTemplate(): Promise<Blob> {
    const url = `${API_BASE}/transactions/template`;
    const res = await fetch(url);
    if (!res.ok) {
      const msg = await getApiError(res);
      throw new Error(msg);
    }
    return res.blob();
  },
};
