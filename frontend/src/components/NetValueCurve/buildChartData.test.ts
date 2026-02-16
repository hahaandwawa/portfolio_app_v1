import { describe, it, expect } from "vitest";
import { buildChartData } from "./NetValueCurve";
import type { NetValueCurveResponse } from "../../types";

function makeResponse(overrides: Partial<NetValueCurveResponse> & { dates: string[] }): NetValueCurveResponse {
  const { dates, ...rest } = overrides;
  const n = dates.length;
  return {
    baseline_label: "Holdings Cost (avg)",
    price_type: "close",
    includes_cash: true,
    dates,
    baseline: rest.baseline ?? Array.from({ length: n }, (_, i) => 10000 + i * 0),
    market_value: rest.market_value ?? Array.from({ length: n }, (_, i) => 10000 + i * 10),
    profit_loss: rest.profit_loss ?? Array.from({ length: n }, (_, i) => i * 10),
    profit_loss_pct: rest.profit_loss_pct ?? Array.from({ length: n }, (_, i) => (i * 10 / 10000) * 100),
    is_trading_day: rest.is_trading_day ?? Array.from({ length: n }, () => true),
    last_trading_date: rest.last_trading_date ?? dates,
    ...rest,
  };
}

describe("buildChartData", () => {
  it("returns all points when zoom is all and data has 5 points", () => {
    const dates = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"];
    const res = makeResponse({ dates });
    const points = buildChartData(res, "all");
    expect(points).toHaveLength(5);
    expect(points[0].index).toBe(0);
    expect(points[0].date).toBe("2024-01-01");
    expect(points[0].baseline).toBe(10000);
    expect(points[0].market_value).toBe(10000);
    expect(points[0].profitTop).toBe(10000);
    expect(points[0].lossBottom).toBe(10000);
    expect(points[4].index).toBe(4);
  });

  it("slices last 7 points when zoom is 7d and data has 10 points", () => {
    const dates = Array.from({ length: 10 }, (_, i) => `2024-01-${String(i + 1).padStart(2, "0")}`);
    const res = makeResponse({ dates });
    const points = buildChartData(res, "7d");
    expect(points).toHaveLength(7);
    expect(points[0].date).toBe("2024-01-04");
    expect(points[0].index).toBe(0);
    expect(points[6].date).toBe("2024-01-10");
    expect(points[6].index).toBe(6);
  });

  it("slices last 30 points when zoom is 30d and data has 40 points", () => {
    const dates: string[] = [];
    for (let i = 0; i < 40; i++) {
      const d = new Date("2024-01-01");
      d.setDate(d.getDate() + i);
      dates.push(d.toISOString().slice(0, 10));
    }
    const res = makeResponse({ dates });
    const points = buildChartData(res, "30d");
    expect(points).toHaveLength(30);
    expect(points[0].date).toBe(dates[10]);
    expect(points[29].date).toBe(dates[39]);
  });

  it("returns all points when zoom is 7d but data has only 5 points", () => {
    const dates = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"];
    const res = makeResponse({ dates });
    const points = buildChartData(res, "7d");
    expect(points).toHaveLength(5);
  });

  it("computes profitTop and lossBottom correctly for profit and loss", () => {
    const dates = ["2024-01-01", "2024-01-02"];
    const res = makeResponse({
      dates,
      baseline: [10000, 10000],
      market_value: [10500, 9500],
      profit_loss: [500, -500],
      profit_loss_pct: [5, -5],
    });
    const points = buildChartData(res, "all");
    expect(points[0].profitTop).toBe(10500);
    expect(points[0].lossBottom).toBe(10000);
    expect(points[1].profitTop).toBe(10000);
    expect(points[1].lossBottom).toBe(9500);
  });

  it("includes is_trading_day and last_trading_date from response", () => {
    const dates = ["2024-01-01", "2024-01-02"];
    const res = makeResponse({
      dates,
      is_trading_day: [true, false],
      last_trading_date: ["2024-01-01", "2024-01-01"],
    });
    const points = buildChartData(res, "all");
    expect(points[0].is_trading_day).toBe(true);
    expect(points[0].last_trading_date).toBe("2024-01-01");
    expect(points[1].is_trading_day).toBe(false);
    expect(points[1].last_trading_date).toBe("2024-01-01");
  });
});
