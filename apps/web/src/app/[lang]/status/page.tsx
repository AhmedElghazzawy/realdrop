import { Suspense } from "react";
import { getDictionary, getLocale } from "@/i18n";
import type { Locale } from "@/i18n/config";
import type { Dictionary } from "@/i18n/en";
import { getStats, type Run, type RunStatus } from "@/lib/api";
import { formatCount, formatDay, formatDayTime, minutesBetween } from "@/lib/format";

const STATUS_CLASS: Record<RunStatus, string> = {
  succeeded: "text-signal border-signal/40",
  partial: "text-info border-info/40",
  failed: "text-warn border-warn/40",
  running: "text-muted border-line",
};

type StatusText = Dictionary["status"];

export default async function StatusPage() {
  const t = (await getDictionary()).status;
  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="font-serif text-4xl">{t.title}</h1>
        <p className="text-sm text-muted">{t.intro}</p>
      </header>
      <Suspense fallback={<div className="h-64 animate-pulse rounded-card bg-surface" />}>
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
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {brands.flatMap((b) => [
          <Tile key={`${b.slug}-p`} label={t.products(b.name)} value={count(b.products)} />,
          <Tile key={`${b.slug}-v`} label={t.variants} value={count(b.variants)} />,
          <Tile key={`${b.slug}-o`} label={t.observations} value={count(b.observations)} />,
          <Tile
            key={`${b.slug}-s`}
            label={t.since}
            value={b.tracking_since ? formatDay(locale, b.tracking_since) : "—"}
          />,
        ])}
      </section>

      <section className="overflow-x-auto rounded-card border border-line">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="bg-surface text-xs text-muted">
            <tr>
              <th className="px-3 py-2 font-normal">{t.columns.started}</th>
              <th className="px-3 py-2 font-normal">{t.columns.brand}</th>
              <th className="px-3 py-2 font-normal">{t.columns.status}</th>
              <th className="px-3 py-2 text-right font-normal">{t.columns.products}</th>
              <th className="px-3 py-2 text-right font-normal">{t.columns.failed}</th>
              <th className="px-3 py-2 text-right font-normal">{t.columns.duration}</th>
              <th className="px-3 py-2 font-normal">{t.columns.notes}</th>
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

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-card border border-line bg-surface p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="font-mono text-2xl tabular">{value}</p>
    </div>
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
    <tr className="border-t border-line align-top">
      <td className="px-3 py-2 font-mono text-xs tabular">{formatDayTime(locale, run.started_at)}</td>
      <td className="px-3 py-2">{run.brand_slug}</td>
      <td className="px-3 py-2">
        <span className={`rounded border px-1.5 py-0.5 text-xs ${STATUS_CLASS[run.status]}`}>
          {t.states[run.status]}
        </span>
      </td>
      <td className="px-3 py-2 text-right font-mono tabular">
        {count(run.items_seen - run.items_failed)}
      </td>
      <td className="px-3 py-2 text-right font-mono tabular">{count(run.items_failed)}</td>
      <td className="px-3 py-2 text-right font-mono text-xs tabular">
        {duration(t, run.started_at, run.finished_at)}
      </td>
      <td className="max-w-xs truncate px-3 py-2 text-xs text-muted" title={run.notes ?? ""}>
        {firstNote}
      </td>
    </tr>
  );
}
