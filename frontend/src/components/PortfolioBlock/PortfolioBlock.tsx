import { useMemo, useState } from "react";
import { PortfolioTable, type SortKey, type SortDir } from "./PortfolioTable";
import type { PortfolioPosition } from "../../types";

interface PortfolioBlockProps {
  positions: PortfolioPosition[];
  loading: boolean;
  error: string | null;
}

function sortPositions(
  positions: PortfolioPosition[],
  key: SortKey,
  dir: SortDir
): PortfolioPosition[] {
  if (!dir) return [...positions];
  const cmp = (a: PortfolioPosition, b: PortfolioPosition): number => {
    let v = 0;
    switch (key) {
      case "symbol":
        v = a.symbol.localeCompare(b.symbol);
        break;
      case "cost": {
        const ca = a.cost_price ?? (a.quantity ? a.total_cost / a.quantity : 0);
        const cb = b.cost_price ?? (b.quantity ? b.total_cost / b.quantity : 0);
        v = ca - cb;
        break;
      }
      case "quantity":
        v = a.quantity - b.quantity;
        break;
      case "latest_price":
        v = (a.latest_price ?? 0) - (b.latest_price ?? 0);
        break;
      case "market_value":
        v = (a.market_value ?? 0) - (b.market_value ?? 0);
        break;
      case "unrealized_pnl":
        v = (a.unrealized_pnl ?? 0) - (b.unrealized_pnl ?? 0);
        break;
      case "unrealized_pnl_pct":
        v = (a.unrealized_pnl_pct ?? 0) - (b.unrealized_pnl_pct ?? 0);
        break;
      case "weight_pct":
        v = (a.weight_pct ?? 0) - (b.weight_pct ?? 0);
        break;
      default:
        v = 0;
    }
    return dir === "asc" ? v : -v;
  };
  return [...positions].sort(cmp);
}

export function PortfolioBlock({
  positions,
  loading,
  error,
}: PortfolioBlockProps) {
  const [sortKey, setSortKey] = useState<SortKey>("symbol");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const cycleSort = (key: SortKey) => {
    if (key !== sortKey) {
      setSortKey(key);
      setSortDir("asc");
      return;
    }
    setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
  };

  const sortedPositions = useMemo(
    () => sortPositions(positions, sortKey, sortDir),
    [positions, sortKey, sortDir]
  );

  if (error) {
    return (
      <section className="py-6">
        <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--bg-card)] p-6 shadow-[var(--shadow-md)] md:p-8">
          <h2 className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
            持仓明细
          </h2>
          <p className="mt-3 text-center text-red-600 dark:text-red-400">
            加载失败 {error}
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="py-6">
      <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--bg-card)] p-6 shadow-[var(--shadow-md)] md:p-8">
        <div className="mb-4">
          <h2 className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
            持仓明细
          </h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            {loading
              ? "加载中..."
              : positions.length > 0
                ? `${positions.length} 只股票`
                : "所选账户暂无持仓."}
          </p>
        </div>
        {loading ? (
          <div className="flex min-h-[120px] items-center justify-center text-[var(--text-muted)]">
            加载中...
          </div>
        ) : positions.length === 0 ? (
          <p className="py-8 text-center text-sm text-[var(--text-secondary)]">
            所选账户暂无持仓.
          </p>
        ) : (
          <>
            <div className="hidden sm:block">
              <PortfolioTable
                positions={sortedPositions}
                sortKey={sortKey}
                sortDir={sortDir}
                onSort={cycleSort}
              />
            </div>
            <div className="sm:hidden space-y-3">
              {sortedPositions.map((pos) => {
                const costPrice = pos.cost_price ?? (pos.quantity ? pos.total_cost / pos.quantity : 0);
                const isProfit = (pos.unrealized_pnl ?? 0) >= 0;
                const pnlCls = isProfit ? "text-[var(--success)]" : "text-red-500 dark:text-red-400";
                return (
                  <div
                    key={pos.symbol}
                    className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-4 py-3 text-sm"
                  >
                    <div className="font-semibold text-[var(--text-primary)]">{pos.symbol}</div>
                    {pos.display_name && (
                      <div className="text-xs text-[var(--text-secondary)]">{pos.display_name}</div>
                    )}
                    <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[var(--text-secondary)]">
                      <span>成本价 ¥{costPrice.toFixed(2)}</span>
                      <span>数量 {pos.quantity.toLocaleString("zh-CN", { maximumFractionDigits: 4 })}</span>
                      {pos.latest_price != null && (
                        <>
                          <span>最新价 ¥{pos.latest_price.toFixed(2)}</span>
                          <span>市值 ¥{(pos.market_value ?? 0).toFixed(2)}</span>
                        </>
                      )}
                      {(pos.unrealized_pnl != null || pos.unrealized_pnl_pct != null) && (
                        <span className={`col-span-2 ${pnlCls}`}>
                          浮动盈亏 {pos.unrealized_pnl != null ? `¥${(pos.unrealized_pnl >= 0 ? "+" : "") + pos.unrealized_pnl.toFixed(2)}` : ""}
                          {pos.unrealized_pnl_pct != null && ` (${(pos.unrealized_pnl_pct >= 0 ? "+" : "") + pos.unrealized_pnl_pct.toFixed(2)}%)`}
                        </span>
                      )}
                      {pos.weight_pct != null && (
                        <span className="col-span-2">占比 {pos.weight_pct.toFixed(1)}%</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </section>
  );
}
