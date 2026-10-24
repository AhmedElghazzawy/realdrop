"use client"; // Error boundaries must be Client Components

import { useParams } from "next/navigation";
import { DEFAULT_LOCALE, hasLocale } from "@/i18n/config";
import { en } from "@/i18n/en";
import { tr } from "@/i18n/tr";

export default function ErrorPage({ retry }: { error: unknown; retry: () => void }) {
  const { lang } = useParams<{ lang: string }>();
  const t = { en, tr }[hasLocale(lang) ? lang : DEFAULT_LOCALE].error;
  return (
    <div className="rounded-card border border-warn/40 p-8 text-center">
      <p className="mb-1 font-serif text-2xl">{t.title}</p>
      <p className="mb-4 text-sm text-muted">{t.body}</p>
      <button onClick={() => retry()} className="rounded-card bg-text px-4 py-2 text-sm text-bg">
        {t.retry}
      </button>
    </div>
  );
}
