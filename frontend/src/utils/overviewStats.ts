import { getTodayGainLossLabel } from "./marketCalendar";
import type { PortfolioSummary } from "../types";

export interface OverviewStats {
  totalAssets: number;
  stocksValue: number;
  cashBalance: number;
  totalGainLoss: number;
  totalGainLossPct: number | null;
  todayGainLoss: number | null;
  todayGainLossPct: number | null;
  todayLabel: string;
  hasPartialToday: boolean;
}

/**
 * Compute overview block stats from portfolio summary.
 * @param portfolio - from GET /portfolio (or null for empty state)
 * @param labelDate - date used for today label (default: new Date())
 */
export function computeOverviewStats(
  portfolio: PortfolioSummary | null,
  labelDate: Date = new Date()
): OverviewStats {
  if (!portfolio) {
    return {
      totalAssets: 0,
      stocksValue: 0,
      cashBalance: 0,
      totalGainLoss: 0,
      totalGainLossPct: null,
      todayGainLoss: null,
      todayGainLossPct: null,
      todayLabel: getTodayGainLossLabel(labelDate),
      hasPartialToday: false,
    };
  }
  const cash = portfolio.cash_balance ?? 0;
  const positions = portfolio.positions ?? [];
  const stocks = positions.reduce((sum, p) => sum + (p.market_value ?? 0), 0);
  const total = stocks + cash;

  const totalCost = positions.reduce((sum, p) => sum + (p.total_cost ?? 0), 0);
  const totalPnl = positions.reduce((sum, p) => sum + (p.unrealized_pnl ?? 0), 0);
  const pct = totalCost > 0 ? (totalPnl / totalCost) * 100 : null;

  let todayPnlSum = 0;
  let valueAtPreviousClose = 0;
  let hasAnyValid = false;
  let anyMissing = false;
  for (const p of positions) {
    const lp = p.latest_price;
    const pc = p.previous_close;
    const qty = p.quantity ?? 0;
    if (lp != null && pc != null) {
      todayPnlSum += (lp - pc) * qty;
      valueAtPreviousClose += pc * qty;
      hasAnyValid = true;
    } else if (qty > 0) {
      anyMissing = true;
    }
  }
  const todayPnl =
    positions.length === 0 || !hasAnyValid
      ? null
      : Math.round(todayPnlSum * 100) / 100;
  const todayPct =
    todayPnl != null && valueAtPreviousClose > 0
      ? (todayPnlSum / valueAtPreviousClose) * 100
      : null;

  return {
    totalAssets: total,
    stocksValue: stocks,
    cashBalance: cash,
    totalGainLoss: totalPnl,
    totalGainLossPct: pct,
    todayGainLoss: todayPnl,
    todayGainLossPct: todayPct,
    todayLabel: getTodayGainLossLabel(labelDate),
    hasPartialToday: anyMissing,
  };
}
