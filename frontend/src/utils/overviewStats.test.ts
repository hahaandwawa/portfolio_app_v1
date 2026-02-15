import { describe, it, expect } from "vitest";
import { computeOverviewStats } from "./overviewStats";
import type { PortfolioSummary } from "../types";

describe("computeOverviewStats", () => {
  it("returns zeros and default label when portfolio is null", () => {
    const labelDate = new Date(2025, 1, 12); // Wed = trading day
    const stats = computeOverviewStats(null, labelDate);
    expect(stats.totalAssets).toBe(0);
    expect(stats.stocksValue).toBe(0);
    expect(stats.cashBalance).toBe(0);
    expect(stats.totalGainLoss).toBe(0);
    expect(stats.totalGainLossPct).toBeNull();
    expect(stats.todayGainLoss).toBeNull();
    expect(stats.todayGainLossPct).toBeNull();
    expect(stats.todayLabel).toBe("今日");
    expect(stats.hasPartialToday).toBe(false);
  });

  it("computes total assets = stocks + cash", () => {
    const portfolio: PortfolioSummary = {
      cash_balance: 1000,
      account_cash: [],
      positions: [
        { symbol: "AAPL", quantity: 10, total_cost: 1500, market_value: 1600 },
      ],
    };
    const stats = computeOverviewStats(portfolio);
    expect(stats.totalAssets).toBe(2600);
    expect(stats.stocksValue).toBe(1600);
    expect(stats.cashBalance).toBe(1000);
  });

  it("computes total gain/loss and percentage from unrealized_pnl", () => {
    const portfolio: PortfolioSummary = {
      cash_balance: 0,
      account_cash: [],
      positions: [
        { symbol: "AAPL", quantity: 10, total_cost: 1000, unrealized_pnl: 100 },
        { symbol: "MSFT", quantity: 5, total_cost: 2000, unrealized_pnl: -50 },
      ],
    };
    const stats = computeOverviewStats(portfolio);
    expect(stats.totalGainLoss).toBe(50);
    expect(stats.totalGainLossPct).toBeCloseTo(50 / 3000 * 100, 2); // 1.67%
  });

  it("returns totalGainLossPct null when total cost is 0", () => {
    const portfolio: PortfolioSummary = {
      cash_balance: 0,
      account_cash: [],
      positions: [],
    };
    const stats = computeOverviewStats(portfolio);
    expect(stats.totalGainLossPct).toBeNull();
  });

  it("computes today gain/loss from (latest_price - previous_close) * quantity", () => {
    const portfolio: PortfolioSummary = {
      cash_balance: 0,
      account_cash: [],
      positions: [
        {
          symbol: "AAPL",
          quantity: 10,
          total_cost: 1000,
          latest_price: 105,
          previous_close: 100,
        },
        {
          symbol: "MSFT",
          quantity: 5,
          total_cost: 2000,
          latest_price: 398,
          previous_close: 400,
        },
      ],
    };
    const stats = computeOverviewStats(portfolio);
    // AAPL: (105-100)*10 = 50, MSFT: (398-400)*5 = -10 => 40
    expect(stats.todayGainLoss).toBe(40);
    // value at previous close: 100*10 + 400*5 = 1000 + 2000 = 3000; pct = 40/3000 * 100
    expect(stats.todayGainLossPct).toBeCloseTo(40 / 3000 * 100, 2);
    expect(stats.hasPartialToday).toBe(false);
  });

  it("returns todayGainLoss null when no position has both latest_price and previous_close", () => {
    const portfolio: PortfolioSummary = {
      cash_balance: 0,
      account_cash: [],
      positions: [
        { symbol: "AAPL", quantity: 10, total_cost: 1000, latest_price: 105 },
        { symbol: "MSFT", quantity: 5, total_cost: 2000, previous_close: 400 },
      ],
    };
    const stats = computeOverviewStats(portfolio);
    expect(stats.todayGainLoss).toBeNull();
    expect(stats.todayGainLossPct).toBeNull();
    expect(stats.hasPartialToday).toBe(true);
  });

  it("computes negative today PnL when latest_price < previous_close (e.g. weekend data quirk)", () => {
    const portfolio: PortfolioSummary = {
      cash_balance: 0,
      account_cash: [],
      positions: [
        {
          symbol: "AAPL",
          quantity: 10,
          total_cost: 1000,
          latest_price: 147.5,
          previous_close: 148,
        },
        {
          symbol: "MSFT",
          quantity: 10,
          total_cost: 3500,
          latest_price: 398,
          previous_close: 398.5,
        },
      ],
    };
    const stats = computeOverviewStats(portfolio);
    // (147.5-148)*10 + (398-398.5)*10 = -5 + -5 = -10
    expect(stats.todayGainLoss).toBe(-10);
    expect(stats.hasPartialToday).toBe(false);
  });

  it("computes partial today when some positions have missing quote data", () => {
    const portfolio: PortfolioSummary = {
      cash_balance: 0,
      account_cash: [],
      positions: [
        {
          symbol: "AAPL",
          quantity: 10,
          total_cost: 1000,
          latest_price: 105,
          previous_close: 100,
        },
        { symbol: "MSFT", quantity: 5, total_cost: 2000 },
      ],
    };
    const stats = computeOverviewStats(portfolio);
    expect(stats.todayGainLoss).toBe(50); // only AAPL contributes
    expect(stats.todayGainLossPct).toBeCloseTo(50 / 1000 * 100, 2); // 5%
    expect(stats.hasPartialToday).toBe(true);
  });

  it("uses labelDate for todayLabel", () => {
    const portfolio: PortfolioSummary = {
      cash_balance: 0,
      account_cash: [],
      positions: [],
    };
    const sat = new Date(2025, 1, 15);
    const stats = computeOverviewStats(portfolio, sat);
    expect(stats.todayLabel).toBe("市场休市");
  });
});
