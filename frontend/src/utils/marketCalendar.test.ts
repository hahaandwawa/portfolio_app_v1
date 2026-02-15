import { describe, it, expect } from "vitest";
import {
  isWeekend,
  isUSMarketHoliday,
  isTradingDay,
  getTodayGainLossLabel,
} from "./marketCalendar";

describe("isWeekend", () => {
  it("returns true for Saturday", () => {
    // 2025-02-15 is Saturday
    expect(isWeekend(new Date(2025, 1, 15))).toBe(true);
  });

  it("returns true for Sunday", () => {
    // 2025-02-16 is Sunday
    expect(isWeekend(new Date(2025, 1, 16))).toBe(true);
  });

  it("returns false for Monday through Friday", () => {
    expect(isWeekend(new Date(2025, 1, 10))).toBe(false); // Mon
    expect(isWeekend(new Date(2025, 1, 11))).toBe(false); // Tue
    expect(isWeekend(new Date(2025, 1, 12))).toBe(false); // Wed
    expect(isWeekend(new Date(2025, 1, 13))).toBe(false); // Thu
    expect(isWeekend(new Date(2025, 1, 14))).toBe(false); // Fri
  });
});

describe("isUSMarketHoliday", () => {
  it("returns true for New Year (Jan 1)", () => {
    expect(isUSMarketHoliday(new Date(2025, 0, 1))).toBe(true);
  });

  it("returns true for Independence Day (July 4)", () => {
    expect(isUSMarketHoliday(new Date(2025, 6, 4))).toBe(true);
  });

  it("returns true for Christmas (Dec 25)", () => {
    expect(isUSMarketHoliday(new Date(2025, 11, 25))).toBe(true);
  });

  it("returns true for Juneteenth (June 19)", () => {
    expect(isUSMarketHoliday(new Date(2025, 5, 19))).toBe(true);
  });

  it("returns true for Thanksgiving (4th Thu Nov) - 2025 Nov 27", () => {
    expect(isUSMarketHoliday(new Date(2025, 10, 27))).toBe(true);
  });

  it("returns true for Memorial Day (last Mon May) - 2025 May 26", () => {
    expect(isUSMarketHoliday(new Date(2025, 4, 26))).toBe(true);
  });

  it("returns true for Labor Day (1st Mon Sep) - 2025 Sep 1", () => {
    expect(isUSMarketHoliday(new Date(2025, 8, 1))).toBe(true);
  });

  it("returns false for a regular weekday", () => {
    expect(isUSMarketHoliday(new Date(2025, 1, 12))).toBe(false); // Wed Feb 12
  });
});

describe("isTradingDay", () => {
  it("returns true for weekday that is not a holiday", () => {
    expect(isTradingDay(new Date(2025, 1, 12))).toBe(true); // Wed
  });

  it("returns false for Saturday", () => {
    expect(isTradingDay(new Date(2025, 1, 15))).toBe(false);
  });

  it("returns false for Sunday", () => {
    expect(isTradingDay(new Date(2025, 1, 16))).toBe(false);
  });

  it("returns false for New Year", () => {
    expect(isTradingDay(new Date(2025, 0, 1))).toBe(false);
  });
});

describe("getTodayGainLossLabel", () => {
  it('returns "今日" for a trading day', () => {
    expect(getTodayGainLossLabel(new Date(2025, 1, 12))).toBe("今日"); // Wed
  });

  it('returns "市场休市" for Saturday', () => {
    expect(getTodayGainLossLabel(new Date(2025, 1, 15))).toBe("市场休市");
  });

  it('returns "市场休市" for Sunday', () => {
    expect(getTodayGainLossLabel(new Date(2025, 1, 16))).toBe("市场休市");
  });

  it('returns "自上一收盘" for a holiday that is not weekend', () => {
    expect(getTodayGainLossLabel(new Date(2025, 0, 1))).toBe("自上一收盘"); // New Year Wed
  });
});
