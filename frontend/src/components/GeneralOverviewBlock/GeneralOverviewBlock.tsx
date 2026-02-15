import { useMemo } from "react";
import { computeOverviewStats } from "../../utils/overviewStats";
import type { PortfolioSummary } from "../../types";

interface GeneralOverviewBlockProps {
  portfolio: PortfolioSummary | null;
  loading: boolean;
  error: string | null;
}

function formatCurrency(value: number): string {
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatSignedCurrency(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return sign + formatCurrency(value);
}

export function GeneralOverviewBlock({
  portfolio,
  loading,
  error,
}: GeneralOverviewBlockProps) {
  const { totalAssets, stocksValue, cashBalance, totalGainLoss, totalGainLossPct, todayGainLoss, todayGainLossPct, todayLabel, hasPartialToday } = useMemo(
    () => computeOverviewStats(portfolio),
    [portfolio]
  );

  const cardClass =
    "rounded-2xl border border-[var(--border-color)] bg-[var(--bg-card)] shadow-[var(--shadow-md)] pt-4 px-6 pb-6 md:pt-5 md:px-8 md:pb-8";
  const titleClass = "text-xl font-bold tracking-tight text-[var(--text-primary)]";
  const mutedClass = "text-sm text-[var(--text-muted)]";

  if (error) {
    return (
      <section className="py-3">
        <div className={cardClass}>
          <h2 className={titleClass}>总览</h2>
          <p className="mt-3 text-center text-red-600 dark:text-red-400">加载失败 {error}</p>
        </div>
      </section>
    );
  }

  if (loading) {
    return (
      <section className="py-3">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3 md:gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className={cardClass}>
              <div className="h-6 w-24 animate-pulse rounded bg-[var(--border-subtle)]" />
              <div className="mt-3 h-8 w-32 animate-pulse rounded bg-[var(--border-subtle)]" />
              <div className="mt-2 h-4 w-full animate-pulse rounded bg-[var(--border-subtle)]" />
            </div>
          ))}
        </div>
      </section>
    );
  }

  const totalGainLossCls =
    totalGainLoss >= 0 ? "text-[var(--success)]" : "text-red-500 dark:text-red-400";
  const todayGainLossCls =
    todayGainLoss != null
      ? todayGainLoss >= 0
        ? "text-[var(--success)]"
        : "text-red-500 dark:text-red-400"
      : "text-[var(--text-primary)]";

  return (
    <section className="py-3">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3 md:gap-6">
        {/* Card 1: Total Assets */}
        <article className={cardClass}>
          <h2 className={titleClass}>总资产</h2>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-[var(--text-primary)]">
            {formatCurrency(totalAssets)}
          </p>
          <div className="mt-2 space-y-1">
            <p className={mutedClass}>股票: {formatCurrency(stocksValue)}</p>
            <p className={mutedClass}>现金: {formatCurrency(cashBalance)}</p>
          </div>
        </article>

        {/* Card 2: Total Gain/Loss */}
        <article className={cardClass}>
          <h2 className={titleClass}>总盈亏</h2>
          <p className={`mt-2 text-2xl font-semibold tabular-nums ${totalGainLossCls}`}>
            {formatSignedCurrency(totalGainLoss)}
          </p>
          {totalGainLossPct != null && (
            <p className={`mt-1 text-sm tabular-nums ${totalGainLossCls}`}>
              ({totalGainLossPct >= 0 ? "+" : ""}
              {totalGainLossPct.toFixed(2)}%)
            </p>
          )}
        </article>

        {/* Card 3: Today's Gain/Loss */}
        <article className={cardClass}>
          <h2 className={titleClass}>
            当日盈亏
            <span className="ml-2 text-sm font-normal text-[var(--text-muted)]">
              {todayLabel}
            </span>
          </h2>
          <p className={`mt-2 text-2xl font-semibold tabular-nums ${todayGainLossCls}`}>
            {todayGainLoss != null
              ? formatSignedCurrency(todayGainLoss)
              : "—"}
          </p>
          {todayGainLossPct != null && (
            <p className={`mt-1 text-sm tabular-nums ${todayGainLossCls}`}>
              ({todayGainLossPct >= 0 ? "+" : ""}
              {todayGainLossPct.toFixed(2)}%)
            </p>
          )}
          {hasPartialToday && (
            <p className="mt-1 text-xs text-[var(--text-muted)]" title="部分行情缺失">
              部分行情缺失
            </p>
          )}
        </article>
      </div>
    </section>
  );
}
