"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { LOCALES, type Locale } from "@/i18n/config";

// Same page, other language: swap the first path segment and keep the query (filters, sort).
export function LanguageSwitch({ current, label }: { current: Locale; label: string }) {
  const pathname = usePathname();
  const query = useSearchParams().toString();
  const rest = pathname.replace(/^\/(en|tr)(?=\/|$)/, "");
  return (
    <nav aria-label={label} className="flex items-center gap-1 text-xs">
      {LOCALES.map((locale, i) => (
        <span key={locale} className="flex items-center gap-1">
          {i > 0 ? <span className="text-line-strong">/</span> : null}
          <Link
            href={`/${locale}${rest}${query ? `?${query}` : ""}`}
            aria-current={locale === current ? "true" : undefined}
            lang={locale}
            className={`px-0.5 py-2 uppercase tracking-wider ${
              locale === current ? "font-semibold text-text" : "text-muted hover:text-text"
            }`}
          >
            {locale}
          </Link>
        </span>
      ))}
    </nav>
  );
}
