"use client"; // Error boundaries must be Client Components

import { useParams } from "next/navigation";
import { DEFAULT_LOCALE, hasLocale } from "@/i18n/config";
import { en } from "@/i18n/en";
import { tr } from "@/i18n/tr";

export default function ErrorPage({ retry }: { error: unknown; retry: () => void }) {
  const { lang } = useParams<{ lang: string }>();
  const t = { en, tr }[hasLocale(lang) ? lang : DEFAULT_LOCALE].error;
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center gap-3 px-4 py-24 text-center">
      <p className="font-serif text-4xl leading-tight tracking-tight">{t.title}</p>
      <p className="text-sm text-muted">{t.body}</p>
      <button onClick={() => retry()} className="mt-3 h-11 bg-text px-6 text-sm font-medium text-on-text">
        {t.retry}
      </button>
    </div>
  );
}
