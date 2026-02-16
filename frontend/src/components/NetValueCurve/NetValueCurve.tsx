import { useMemo, useState } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import type { NetValueCurveResponse } from "../../types";

export type ZoomRange = "7d" | "30d" | "all";

export interface ChartPoint {
  index: number;
  date: string;
  displayDate: string;
  baseline: number;
  market_value: number;
  profit_loss: number;
  profit_loss_pct: number | null;
  is_trading_day: boolean;
  last_trading_date: string;
  /** For green fill: top of area when profit */
  profitTop: number;
  /** For red fill: bottom of area when loss */
  lossBottom: number;
}

export interface NetValueCurveProps {
  data: NetValueCurveResponse | null;
  loading: boolean;
  error: string | null;
  selectedAccountNames: Set<string>;
  includeCash: boolean;
  onIncludeCashChange: (include: boolean) => void;
  onRetry: () => void;
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

function formatShortDate(iso: string): string {
  const d = new Date(iso + "Z");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "2-digit" });
}

/** Build chart points from columnar API response and optional zoom (filter by last N days). */
export function buildChartData(
  response: NetValueCurveResponse,
  zoom: ZoomRange
): ChartPoint[] {
  const { dates, baseline, market_value, profit_loss, profit_loss_pct, is_trading_day, last_trading_date } =
    response;
  const n = dates.length;
  let startIdx = 0;
  if (zoom === "7d" && n > 7) startIdx = n - 7;
  else if (zoom === "30d" && n > 30) startIdx = n - 30;

  const points: ChartPoint[] = [];
  for (let i = startIdx; i < n; i++) {
    const b = baseline[i];
    const m = market_value[i];
    points.push({
      index: i - startIdx,
      date: dates[i],
      displayDate: formatShortDate(dates[i]),
      baseline: b,
      market_value: m,
      profit_loss: profit_loss[i],
      profit_loss_pct: profit_loss_pct[i],
      is_trading_day: is_trading_day[i],
      last_trading_date: last_trading_date[i],
      profitTop: m >= b ? m : b,
      lossBottom: m < b ? m : b,
    });
  }
  return points;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; payload: ChartPoint }>;
  label?: string;
  baselineLabel: string;
}

function CustomTooltip({ active, payload, baselineLabel }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload as ChartPoint;
  const plPct =
    p.profit_loss_pct != null
      ? `${(p.profit_loss_pct >= 0 ? "+" : "")}${p.profit_loss_pct.toFixed(2)}%`
      : "—";

  return (
    <div
      className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] px-3 py-2 shadow-lg"
      role="tooltip"
    >
      <p className="font-medium text-[var(--text-primary)]">{p.displayDate}</p>
      {!p.is_trading_day && (
        <p className="mt-0.5 text-xs text-[var(--text-muted)]">
          Last trading close: {formatShortDate(p.last_trading_date)}
        </p>
      )}
      <dl className="mt-1.5 space-y-0.5 text-sm">
        <div className="flex justify-between gap-4">
          <span className="text-[var(--text-muted)]">{baselineLabel}</span>
          <span className="tabular-nums text-[var(--text-primary)]">{formatCurrency(p.baseline)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-[var(--text-muted)]">Market Value (市值)</span>
          <span className="tabular-nums text-[var(--text-primary)]">
            {formatCurrency(p.market_value)}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-[var(--text-muted)]">P/L</span>
          <span
            className={`tabular-nums ${p.profit_loss >= 0 ? "text-[var(--success)]" : "text-red-500 dark:text-red-400"}`}
          >
            {formatSignedCurrency(p.profit_loss)}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-[var(--text-muted)]">P/L % (denom. baseline)</span>
          <span
            className={`tabular-nums ${p.profit_loss >= 0 ? "text-[var(--success)]" : "text-red-500 dark:text-red-400"}`}
          >
            {plPct}
          </span>
        </div>
      </dl>
    </div>
  );
}

const cardClass =
  "rounded-2xl border border-[var(--border-color)] bg-[var(--bg-card)] shadow-[var(--shadow-md)] pt-4 px-6 pb-6 md:pt-5 md:px-8 md:pb-8";
const titleClass = "text-xl font-bold tracking-tight text-[var(--text-primary)]";

export function NetValueCurve({
  data,
  loading,
  error,
  selectedAccountNames,
  includeCash,
  onIncludeCashChange,
  onRetry,
}: NetValueCurveProps) {
  const [zoom, setZoom] = useState<ZoomRange>("30d");

  const chartData = useMemo(() => (data ? buildChartData(data, zoom) : []), [data, zoom]);

  /** Per-point baseline path for Area fill (green: baseline → market_value). Recharts baseLine expects numeric x. */
  const baseLinePath = useMemo(
    () => chartData.map((p) => ({ x: p.index, y: p.baseline })),
    [chartData]
  );
  /** Per-point bottom path for red fill (market_value → baseline when in loss). */
  const redBaseLinePath = useMemo(
    () => chartData.map((p) => ({ x: p.index, y: p.lossBottom })),
    [chartData]
  );

  const baselineLabel = data?.baseline_label ?? "Holdings Cost (avg)";
  const chartSubtitle = data?.includes_cash
    ? "Portfolio equity (stocks + cash)"
    : "Stock holdings value (excluding cash)";

  const hasAccounts = selectedAccountNames.size > 0;

  if (error) {
    return (
      <section className="py-3">
        <div className={cardClass}>
          <h2 className={titleClass}>净值曲线</h2>
          <p className="mt-3 text-center text-red-600 dark:text-red-400">{error}</p>
          <div className="mt-3 flex justify-center">
            <button
              type="button"
              onClick={onRetry}
              className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
            >
              重试
            </button>
          </div>
        </div>
      </section>
    );
  }

  if (!hasAccounts) {
    return (
      <section className="py-3">
        <div className={cardClass}>
          <h2 className={titleClass}>净值曲线</h2>
          <p className="mt-3 text-center text-sm text-[var(--text-muted)]">
            请先选择账户以查看净值曲线
          </p>
        </div>
      </section>
    );
  }

  if (loading) {
    return (
      <section className="py-3">
        <div className={cardClass}>
          <h2 className={titleClass}>净值曲线</h2>
          <div className="mt-4 flex h-64 items-center justify-center rounded-xl bg-[var(--bg-elevated)]">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--border-color)] border-t-[var(--accent)]" />
          </div>
        </div>
      </section>
    );
  }

  if (!data || chartData.length === 0) {
    return (
      <section className="py-3">
        <div className={cardClass}>
          <h2 className={titleClass}>净值曲线</h2>
          <p className="mt-3 text-center text-sm text-[var(--text-muted)]">
            暂无数据，请确认所选账户有交易记录
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="py-3">
      <div className={cardClass}>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className={titleClass}>净值曲线</h2>
            <p className="mt-0.5 text-sm text-[var(--text-muted)]">{chartSubtitle}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-[var(--text-muted)]">Include cash</span>
            <button
              type="button"
              role="switch"
              aria-checked={includeCash}
              onClick={() => onIncludeCashChange(!includeCash)}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:ring-offset-2 ${
                includeCash ? "bg-[var(--success)]" : "bg-[var(--border-color)]"
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition ${includeCash ? "translate-x-5" : "translate-x-0.5"}`}
              />
            </button>
            <div className="ml-2 flex rounded-lg border border-[var(--border-color)] p-0.5">
              {(["7d", "30d", "all"] as const).map((z) => (
                <button
                  key={z}
                  type="button"
                  onClick={() => setZoom(z)}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
                    zoom === z
                      ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                      : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                  }`}
                >
                  {z === "all" ? "All" : z.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="h-72 w-full md:h-80">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={chartData}
              margin={{ top: 8, right: 8, left: 8, bottom: 8 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
              <XAxis
                dataKey="index"
                tickFormatter={(_, i) => chartData[i]?.displayDate ?? ""}
                tick={{ fontSize: 12, fill: "var(--text-muted)" }}
                tickLine={false}
                axisLine={{ stroke: "var(--border-color)" }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: "var(--text-muted)" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `$${v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v}`}
                width={48}
              />
              <Tooltip
                content={<CustomTooltip baselineLabel={baselineLabel} />}
                cursor={{ stroke: "var(--border-color)", strokeWidth: 1 }}
              />
              <Legend
                wrapperStyle={{ fontSize: 12 }}
                formatter={(value) => (
                  <span className="text-[var(--text-secondary)]">{value}</span>
                )}
              />
              {/* Red fill: from market_value up to baseline when in loss */}
              <Area
                type="monotone"
                dataKey="baseline"
                baseLine={redBaseLinePath}
                fill="#ef4444"
                fillOpacity={0.35}
                stroke="none"
                isAnimationActive={true}
                hide
              />
              {/* Green fill: from baseline up to market_value when in profit */}
              <Area
                type="monotone"
                dataKey="profitTop"
                baseLine={baseLinePath}
                fill="var(--success)"
                fillOpacity={0.35}
                stroke="none"
                isAnimationActive={true}
                hide
              />
              <Line
                type="monotone"
                dataKey="baseline"
                name={baselineLabel}
                stroke="#9ca3af"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                isAnimationActive={true}
              />
              <Line
                type="monotone"
                dataKey="market_value"
                name="Market Value (市值)"
                stroke="var(--accent)"
                strokeWidth={2}
                dot={false}
                isAnimationActive={true}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}
