// All number and date formatting goes through Intl (DESIGN_SYSTEM.md), in the UI language.
// The API sends money as integer kurus; it is converted here, at the edge, and nowhere else.

import { INTL_LOCALE, type Locale } from "@/i18n/config";

const cache = new Map<string, Intl.NumberFormat | Intl.DateTimeFormat>();

function cached<T extends Intl.NumberFormat | Intl.DateTimeFormat>(key: string, make: () => T): T {
  let formatter = cache.get(key) as T | undefined;
  if (!formatter) {
    formatter = make();
    cache.set(key, formatter);
  }
  return formatter;
}

export function formatMoney(locale: Locale, minor: number, currency = "TRY"): string {
  const formatter = cached(
    `money:${locale}:${currency}`,
    // narrowSymbol: "₺" in every language (plain "symbol" is "TRY" in English).
    () =>
      new Intl.NumberFormat(INTL_LOCALE[locale], {
        style: "currency",
        currency,
        currencyDisplay: "narrowSymbol",
      }),
  );
  return formatter.format(minor / 100);
}

/** Discount the shop claims, as a fraction: (claimed - price) / claimed. */
export function claimedDiscount(price: number, claimed: number | null): number | null {
  if (claimed === null || claimed <= price) return null;
  return (claimed - price) / claimed;
}

export function formatPercent(locale: Locale, fraction: number): string {
  return cached(
    `pct:${locale}`,
    () =>
      new Intl.NumberFormat(INTL_LOCALE[locale], { style: "percent", maximumFractionDigits: 0 }),
  ).format(fraction);
}

export function formatDay(locale: Locale, iso: string): string {
  const formatter = cached(
    `day:${locale}`,
    () =>
      new Intl.DateTimeFormat(INTL_LOCALE[locale], {
        day: "numeric",
        month: "short",
        year: "numeric",
        timeZone: "Europe/Istanbul",
      }),
  );
  // A bare date ("2026-10-25") is an Istanbul calendar day already; pin it to noon so no
  // timezone shift can move it to another day.
  return formatter.format(new Date(iso.length === 10 ? `${iso}T12:00:00+03:00` : iso));
}

export function formatDayTime(locale: Locale, iso: string): string {
  return cached(
    `daytime:${locale}`,
    () =>
      new Intl.DateTimeFormat(INTL_LOCALE[locale], {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "Europe/Istanbul",
      }),
  ).format(new Date(iso));
}

export function formatCount(locale: Locale, n: number): string {
  return cached(`count:${locale}`, () => new Intl.NumberFormat(INTL_LOCALE[locale])).format(n);
}

export function minutesBetween(startIso: string, endIso: string): number {
  return Math.round((Date.parse(endIso) - Date.parse(startIso)) / 60000);
}
