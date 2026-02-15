import type { TransactionType } from "../types";

/** Transaction type options for form selects. */
export const TXN_TYPES: { value: TransactionType; label: string }[] = [
  { value: "BUY", label: "买入" },
  { value: "SELL", label: "卖出" },
  { value: "CASH_DEPOSIT", label: "现金存入" },
  { value: "CASH_WITHDRAW", label: "现金取出" },
];

/** Transaction type display labels for tables. */
export const TXN_TYPE_LABELS: Record<string, string> = Object.fromEntries(
  TXN_TYPES.map((t) => [t.value, t.label])
);

/** Format a Date to a `datetime-local` input value string. */
export function toLocalDatetime(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Parse an ISO string to a `datetime-local` input value string. */
export function isoToLocalDatetime(iso: string): string {
  try {
    return toLocalDatetime(new Date(iso));
  } catch {
    return "";
  }
}
