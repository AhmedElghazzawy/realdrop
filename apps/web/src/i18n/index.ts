import { notFound } from "next/navigation";
import { lang } from "next/root-params";
import { type Locale, hasLocale } from "./config";
import { en } from "./en";
import { tr } from "./tr";

const DICTIONARIES = { en, tr } as const;

/** The current request's locale, from the `[lang]` root segment. Server Components only. */
export async function getLocale(): Promise<Locale> {
  const value = await lang();
  if (!hasLocale(value)) notFound();
  return value;
}

export async function getDictionary() {
  return DICTIONARIES[await getLocale()];
}

export function dictionaryFor(locale: Locale) {
  return DICTIONARIES[locale];
}
