import type { PortfolioPosition } from "../../types";

export type SortKey =
  | "symbol"
  | "cost"
  | "quantity"
  | "latest_price"
  | "market_value"
  | "unrealized_pnl"
  | "unrealized_pnl_pct"
  | "weight_pct";
export type SortDir = "asc" | "desc" | null;

interface PortfolioTableProps {
  positions: PortfolioPosition[];
  sortKey: SortKey;
  sortDir: SortDir;
  onSort: (key: SortKey) => void;
}

function formatCost(pos: PortfolioPosition): string {
  const cost = pos.cost_price ?? (pos.quantity ? pos.total_cost / pos.quantity : 0);
  if (cost === 0 && !pos.quantity) return "—";
  return cost.toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatQuantity(qty: number): string {
  return qty.toLocaleString("zh-CN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 4,
  });
}

function formatMoney(value: number | null | undefined): string {
  if (value == null) return "—";
  return value.toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function SortIcon({ dir }: { dir: SortDir }) {
  if (dir === "asc") return <span className="text-[var(--accent)]">↑</span>;
  if (dir === "desc") return <span className="text-[var(--accent)]">↓</span>;
  return <span className="text-[var(--text-muted)]">↕</span>;
}

function PnLAmount({ value }: { value: number | null | undefined }) {
  if (value == null) return <td className="px-2 py-2 text-right text-[var(--text-secondary)] tabular-nums">—</td>;
  const isProfit = value >= 0;
  const cls = isProfit ? "text-[var(--success)]" : "text-red-500 dark:text-red-400";
  return (
    <td className={`px-2 py-2 text-right tabular-nums ${cls}`}>
      {value >= 0 ? "+" : ""}${formatMoney(value)}
    </td>
  );
}

function PnLPct({ value }: { value: number | null | undefined }) {
  if (value == null) return <td className="px-2 py-2 text-right text-[var(--text-secondary)] tabular-nums">—</td>;
  const isProfit = value >= 0;
  const cls = isProfit ? "text-[var(--success)]" : "text-red-500 dark:text-red-400";
  return (
    <td className={`px-2 py-2 text-right tabular-nums ${cls}`}>
      {value >= 0 ? "+" : ""}{value.toFixed(2)}%
    </td>
  );
}

export function PortfolioTable({
  positions,
  sortKey,
  sortDir,
  onSort,
}: PortfolioTableProps) {
  return (
    <div className="w-full overflow-hidden">
      <table className="w-full table-fixed border-collapse text-sm">
        <colgroup>
          <col style={{ width: "14%" }} />
          <col style={{ width: "10%" }} />
          <col style={{ width: "9%" }} />
          <col style={{ width: "9%" }} />
          <col style={{ width: "11%" }} />
          <col style={{ width: "14%" }} />
          <col style={{ width: "11%" }} />
          <col style={{ width: "14%" }} />
        </colgroup>
        <thead>
          <tr className="border-b border-[var(--border-color)] bg-[var(--bg-elevated)]">
            <th
              className="cursor-pointer select-none px-2 py-2 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] transition hover:text-[var(--text-primary)]"
              onClick={() => onSort("symbol")}
            >
              <span className="inline-flex items-center gap-0.5">
                代码/名称
                <SortIcon dir={sortKey === "symbol" ? sortDir : null} />
              </span>
            </th>
            <th
              className="cursor-pointer select-none px-2 py-2 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] transition hover:text-[var(--text-primary)]"
              onClick={() => onSort("latest_price")}
            >
              <span className="inline-flex items-center gap-0.5 justify-end w-full">
                最新价
                <SortIcon dir={sortKey === "latest_price" ? sortDir : null} />
              </span>
            </th>
            <th
              className="cursor-pointer select-none px-2 py-2 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] transition hover:text-[var(--text-primary)]"
              onClick={() => onSort("cost")}
            >
              <span className="inline-flex items-center gap-0.5 justify-end w-full">
                成本价
                <SortIcon dir={sortKey === "cost" ? sortDir : null} />
              </span>
            </th>
            <th
              className="cursor-pointer select-none px-2 py-2 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] transition hover:text-[var(--text-primary)]"
              onClick={() => onSort("quantity")}
            >
              <span className="inline-flex items-center gap-0.5 justify-end w-full">
                数量
                <SortIcon dir={sortKey === "quantity" ? sortDir : null} />
              </span>
            </th>
            <th
              className="cursor-pointer select-none px-2 py-2 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] transition hover:text-[var(--text-primary)]"
              onClick={() => onSort("market_value")}
            >
              <span className="inline-flex items-center gap-0.5 justify-end w-full">
                市值
                <SortIcon dir={sortKey === "market_value" ? sortDir : null} />
              </span>
            </th>
            <th
              className="cursor-pointer select-none px-2 py-2 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] transition hover:text-[var(--text-primary)]"
              onClick={() => onSort("unrealized_pnl")}
            >
              <span className="inline-flex items-center gap-0.5 justify-end w-full">
                浮动盈亏
                <SortIcon dir={sortKey === "unrealized_pnl" ? sortDir : null} />
              </span>
            </th>
            <th
              className="cursor-pointer select-none px-2 py-2 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] transition hover:text-[var(--text-primary)]"
              onClick={() => onSort("unrealized_pnl_pct")}
            >
              <span className="inline-flex items-center gap-0.5 justify-end w-full">
                盈亏%
                <SortIcon dir={sortKey === "unrealized_pnl_pct" ? sortDir : null} />
              </span>
            </th>
            <th
              className="cursor-pointer select-none px-2 py-2 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] transition hover:text-[var(--text-primary)]"
              onClick={() => onSort("weight_pct")}
            >
              <span className="inline-flex items-center gap-0.5 justify-end w-full">
                占比
                <SortIcon dir={sortKey === "weight_pct" ? sortDir : null} />
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          {positions.map((pos) => (
            <tr
              key={pos.symbol}
              className="border-b border-[var(--border-subtle)] transition hover:bg-[var(--accent-soft)]/50"
            >
              <td className="px-2 py-2 text-[var(--text-primary)]">
                <div className="font-semibold truncate">{pos.symbol}</div>
                <div className="text-xs text-[var(--text-secondary)] truncate">
                  {pos.display_name ?? "—"}
                </div>
              </td>
              <td className="px-2 py-2 text-right text-[var(--text-primary)] tabular-nums">
                {pos.latest_price != null ? `$${formatMoney(pos.latest_price)}` : "—"}
              </td>
              <td className="px-2 py-2 text-right text-[var(--text-primary)] tabular-nums">
                ${formatCost(pos)}
              </td>
              <td className="px-2 py-2 text-right text-[var(--text-primary)] tabular-nums">
                {formatQuantity(pos.quantity)}
              </td>
              <td className="px-2 py-2 text-right text-[var(--text-primary)] tabular-nums">
                {pos.market_value != null ? `$${formatMoney(pos.market_value)}` : "—"}
              </td>
              <PnLAmount value={pos.unrealized_pnl} />
              <PnLPct value={pos.unrealized_pnl_pct} />
              <td className="px-2 py-2 text-right">
                {pos.weight_pct != null ? (
                  <div className="flex items-center justify-end gap-1.5">
                    <div className="h-1.5 min-w-[24px] flex-1 max-w-[48px] rounded-full bg-[var(--border-subtle)] overflow-hidden">
                      <div
                        className="h-full rounded-full bg-[var(--accent)]"
                        style={{ width: `${Math.min(100, pos.weight_pct)}%` }}
                      />
                    </div>
                    <span className="tabular-nums text-[var(--text-primary)] w-10 text-right">
                      {pos.weight_pct.toFixed(1)}%
                    </span>
                  </div>
                ) : (
                  <span className="text-[var(--text-secondary)]">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
