"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { LOCALES, type Locale } from "@/i18n/config";

// Same page, other language: swap the first path segment and keep the query (search, sort).
export function LanguageSwitch({ current, label }: { current: Locale; label: string }) {
  const pathname = usePathname();
  const query = useSearchParams().toString();
  const rest = pathname.replace(/^\/(en|tr)(?=\/|$)/, "");
  return (
    <nav aria-label={label} className="flex gap-1 font-mono text-xs">
      {LOCALES.map((locale) => (
        <Link
          key={locale}
          href={`/${locale}${rest}${query ? `?${query}` : ""}`}
          aria-current={locale === current ? "true" : undefined}
          lang={locale}
          className={`rounded px-1.5 py-0.5 uppercase ${
            locale === current ? "bg-text text-bg" : "text-muted hover:text-text"
          }`}
        >
          {locale}
        </Link>
      ))}
    </nav>
  );
}
