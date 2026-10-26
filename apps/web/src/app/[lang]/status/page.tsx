import { Suspense } from "react";
import { getDictionary, getLocale } from "@/i18n";
import type { Locale } from "@/i18n/config";
import type { Dictionary } from "@/i18n/en";
import { getStats, type Run, type RunStatus } from "@/lib/api";
import { formatCount, formatDay, formatDayTime, minutesBetween } from "@/lib/format";

const STATUS_CLASS: Record<RunStatus, string> = {
  succeeded: "text-signal",
  partial: "text-info",
  failed: "text-sale",
  running: "text-muted",
};

type StatusText = Dictionary["status"];

export default async function StatusPage() {
  const t = (await getDictionary()).status;
  return (
    <div className="mx-auto flex max-w-[90rem] flex-col gap-10 px-4 pb-10 pt-10 lg:px-8 lg:pt-14">
      <header className="flex flex-col gap-3 border-b border-line pb-8">
        <h1 className="font-serif text-4xl leading-none tracking-tight sm:text-5xl">{t.title}</h1>
        <p className="max-w-xl text-sm leading-6 text-muted">{t.intro}</p>
      </header>
      <Suspense fallback={<div className="h-64 animate-pulse bg-surface" />}>
        <Stats />
      </Suspense>
    </div>
  );
}

async function Stats() {
  const [locale, t] = [await getLocale(), (await getDictionary()).status];
  const count = (n: number) => formatCount(locale, n);
  const { brands, runs } = await getStats();
  return (
    <>
      <section className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead className="eyebrow text-muted">
            <tr className="border-b border-text">
              <th className="py-3 pr-3 font-normal">{t.columns.brand}</th>
              <th className="px-3 py-3 text-right font-normal">{t.columns.products}</th>
              <th className="px-3 py-3 text-right font-normal">{t.variants}</th>
              <th className="px-3 py-3 text-right font-normal">{t.observations}</th>
              <th className="py-3 pl-3 text-right font-normal">{t.since}</th>
            </tr>
          </thead>
          <tbody className="tabular">
            {brands.map((b) => (
              <tr key={b.slug} className="border-b border-line">
                <td className="py-3 pr-3 font-medium">{b.name}</td>
                <td className="px-3 py-3 text-right">{count(b.products)}</td>
                <td className="px-3 py-3 text-right">{count(b.variants)}</td>
                <td className="px-3 py-3 text-right">{count(b.observations)}</td>
                <td className="py-3 pl-3 text-right text-muted">
                  {b.tracking_since ? formatDay(locale, b.tracking_since) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="eyebrow text-muted">
            <tr className="border-b border-text">
              <th className="px-3 py-3 font-normal">{t.columns.started}</th>
              <th className="px-3 py-3 font-normal">{t.columns.brand}</th>
              <th className="px-3 py-3 font-normal">{t.columns.status}</th>
              <th className="px-3 py-3 text-right font-normal">{t.columns.products}</th>
              <th className="px-3 py-3 text-right font-normal">{t.columns.failed}</th>
              <th className="px-3 py-3 text-right font-normal">{t.columns.duration}</th>
              <th className="px-3 py-3 font-normal">{t.columns.notes}</th>
            </tr>
          </thead>
          <tbody>
            {runs.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-muted">
                  {t.noRuns}
                </td>
              </tr>
            ) : (
              runs.map((run) => <RunRow key={run.id} run={run} locale={locale} t={t} />)
            )}
          </tbody>
        </table>
      </section>
    </>
  );
}

function duration(t: StatusText, start: string, end: string | null): string {
  if (end === null) return t.running;
  const minutes = minutesBetween(start, end);
  return minutes < 60 ? t.minutes(minutes) : t.hours(Math.floor(minutes / 60), minutes % 60);
}

function RunRow({ run, locale, t }: { run: Run; locale: Locale; t: StatusText }) {
  const count = (n: number) => formatCount(locale, n);
  const firstNote = run.notes?.split("\n")[0] ?? "";
  return (
    <tr className="border-b border-line align-top">
      <td className="px-3 py-2 text-xs tabular">{formatDayTime(locale, run.started_at)}</td>
      <td className="px-3 py-2">{run.brand_slug}</td>
      <td className="px-3 py-2">
        <span className={`text-xs font-medium ${STATUS_CLASS[run.status]}`}>
          {t.states[run.status]}
        </span>
      </td>
      <td className="px-3 py-2 text-right tabular">
        {count(run.items_seen - run.items_failed)}
      </td>
      <td className="px-3 py-2 text-right tabular">{count(run.items_failed)}</td>
      <td className="px-3 py-2 text-right text-xs tabular">
        {duration(t, run.started_at, run.finished_at)}
      </td>
      <td className="max-w-xs truncate px-3 py-2 text-xs text-muted" title={run.notes ?? ""}>
        {firstNote}
      </td>
    </tr>
  );
}
