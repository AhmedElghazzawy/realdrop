// Locales shared by server and client code (no server-only imports here).

export const LOCALES = ["en", "tr"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "en";

export function hasLocale(value: string): value is Locale {
  return (LOCALES as readonly string[]).includes(value);
}

// Formatting locale per UI language: en-GB gives "25 Oct 2026" and "₺1,299.99".
export const INTL_LOCALE: Record<Locale, string> = { en: "en-GB", tr: "tr-TR" };
