/**
 * US market calendar helpers for "Today's Gain/Loss" labeling.
 * Uses local date (user's timezone); for US market semantics consider America/New_York.
 */

/**
 * True if date is Saturday (6) or Sunday (0).
 */
export function isWeekend(date: Date): boolean {
  const day = date.getDay();
  return day === 0 || day === 6;
}

/** Fixed US market holidays: month 0-indexed, day 1-indexed. */
const FIXED_HOLIDAYS: { month: number; day: number }[] = [
  { month: 0, day: 1 },   // New Year
  { month: 6, day: 4 },   // Independence Day
  { month: 11, day: 25 }, // Christmas
];

/**
 * Nth weekday of month (e.g. 4th Thursday of November).
 * weekday: 0 = Sunday, 1 = Monday, ..., 6 = Saturday.
 */
function nthWeekdayOfMonth(year: number, month: number, weekday: number, n: number): Date {
  const first = new Date(year, month, 1);
  let count = 0;
  const d = new Date(first);
  while (d.getMonth() === month) {
    if (d.getDay() === weekday) {
      count++;
      if (count === n) return d;
    }
    d.setDate(d.getDate() + 1);
  }
  return first; // fallback
}

/**
 * Last Monday of month.
 */
function lastMondayOfMonth(year: number, month: number): Date {
  const last = new Date(year, month + 1, 0);
  const day = last.getDay();
  const diff = day === 0 ? 6 : day - 1; // days back to Monday
  const d = new Date(last);
  d.setDate(last.getDate() - diff);
  return d;
}

/**
 * True if date is a US market holiday (simplified list: New Year, July 4, Thanksgiving, Christmas,
 * plus Memorial Day, Labor Day, Juneteenth).
 */
export function isUSMarketHoliday(date: Date): boolean {
  const year = date.getFullYear();
  const month = date.getMonth();
  const day = date.getDate();

  for (const h of FIXED_HOLIDAYS) {
    if (month === h.month && day === h.day) return true;
  }

  // Thanksgiving: 4th Thursday of November
  const thanksgiving = nthWeekdayOfMonth(year, 10, 4, 4);
  if (month === 10 && day === thanksgiving.getDate()) return true;

  // Memorial Day: last Monday of May
  const memorial = lastMondayOfMonth(year, 4);
  if (month === 4 && day === memorial.getDate()) return true;

  // Labor Day: 1st Monday of September
  const labor = nthWeekdayOfMonth(year, 8, 1, 1);
  if (month === 8 && day === labor.getDate()) return true;

  // Juneteenth: June 19
  if (month === 5 && day === 19) return true;

  return false;
}

/**
 * Whether the given date is a US trading day (not weekend, not holiday).
 */
export function isTradingDay(date: Date): boolean {
  return !isWeekend(date) && !isUSMarketHoliday(date);
}

/**
 * Label for "Today's Gain/Loss" card:
 * - "今日" when today is a trading day,
 * - "自上一收盘" / "市场休市" when market is closed (weekend or holiday).
 */
export function getTodayGainLossLabel(date: Date): string {
  if (isTradingDay(date)) return "今日";
  if (isWeekend(date)) return "市场休市";
  return "自上一收盘";
}
