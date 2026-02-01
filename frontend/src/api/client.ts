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
};
