import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { api } from "./client";
import type { NetValueCurveResponse } from "../types";

describe("api.getNetValueCurve", () => {
  const mockResponse: NetValueCurveResponse = {
    baseline_label: "Holdings Cost (avg)",
    price_type: "close",
    includes_cash: true,
    dates: ["2024-01-01", "2024-01-02"],
    baseline: [10000, 10000],
    market_value: [10100, 10200],
    profit_loss: [100, 200],
    profit_loss_pct: [1, 2],
    is_trading_day: [true, true],
    last_trading_date: ["2024-01-01", "2024-01-02"],
  };

  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("calls GET /api/net-value-curve with include_cash true by default", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    } as Response);

    const result = await api.getNetValueCurve({});

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/net-value-curve"),
      expect.any(Object)
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/include_cash=true/),
      expect.any(Object)
    );
    expect(result).toEqual(mockResponse);
  });

  it("appends account names as repeated account query params", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    } as Response);

    await api.getNetValueCurve({ account: ["Broker", "IRA"] });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/account=Broker&account=IRA|account=IRA&account=Broker/),
      expect.any(Object)
    );
  });

  it("sends include_cash false when specified", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ ...mockResponse, includes_cash: false }),
    } as Response);

    await api.getNetValueCurve({ include_cash: false });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/include_cash=false/),
      expect.any(Object)
    );
  });

  it("sends start_date and end_date when provided", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    } as Response);

    await api.getNetValueCurve({
      start_date: "2024-01-01",
      end_date: "2024-01-31",
    });

    const url = (fetchMock.mock.calls[0][0] as string);
    expect(url).toContain("start_date=2024-01-01");
    expect(url).toContain("end_date=2024-01-31");
  });

  it("sends refresh=true when refresh is true", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    } as Response);

    await api.getNetValueCurve({ refresh: true });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/refresh=true/),
      expect.any(Object)
    );
  });

  it("throws when response is not ok", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ detail: "Server error" }),
    } as Response);

    await expect(api.getNetValueCurve({})).rejects.toThrow("Server error");
  });
});
