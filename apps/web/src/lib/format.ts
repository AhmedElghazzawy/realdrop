// All number and date formatting goes through Intl with tr-TR (DESIGN_SYSTEM.md).
// The API sends money as integer kurus; it is converted here, at the edge, and nowhere else.

const moneyFormatters = new Map<string, Intl.NumberFormat>();

export function formatMoney(minor: number, currency = "TRY"): string {
  let formatter = moneyFormatters.get(currency);
  if (!formatter) {
    formatter = new Intl.NumberFormat("tr-TR", { style: "currency", currency });
    moneyFormatters.set(currency, formatter);
  }
  return formatter.format(minor / 100);
}

const percent = new Intl.NumberFormat("tr-TR", { style: "percent", maximumFractionDigits: 0 });

/** Discount the shop claims, as a fraction: (claimed - price) / claimed. */
export function claimedDiscount(price: number, claimed: number | null): number | null {
  if (claimed === null || claimed <= price) return null;
  return (claimed - price) / claimed;
}

export function formatPercent(fraction: number): string {
  return percent.format(fraction);
}

const day = new Intl.DateTimeFormat("tr-TR", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "Europe/Istanbul",
});
const dayTime = new Intl.DateTimeFormat("tr-TR", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Europe/Istanbul",
});

export function formatDay(iso: string): string {
  // A bare date ("2026-10-25") is an Istanbul calendar day already; pin it to noon so no
  // timezone shift can move it to another day.
  return day.format(new Date(iso.length === 10 ? `${iso}T12:00:00+03:00` : iso));
}

export function formatDayTime(iso: string): string {
  return dayTime.format(new Date(iso));
}

export function formatDuration(startIso: string, endIso: string | null): string {
  if (!endIso) return "sürüyor";
  const minutes = Math.round((Date.parse(endIso) - Date.parse(startIso)) / 60000);
  if (minutes < 60) return `${minutes} dk`;
  return `${Math.floor(minutes / 60)} sa ${minutes % 60} dk`;
}

const count = new Intl.NumberFormat("tr-TR");
export function formatCount(n: number): string {
  return count.format(n);
}
