import { Suspense } from "react";
import { getStats, type Run, type RunStatus } from "@/lib/api";
import { formatCount, formatDay, formatDayTime, formatDuration } from "@/lib/format";

const STATUS: Record<RunStatus, { label: string; className: string }> = {
  succeeded: { label: "başarılı", className: "text-signal border-signal/40" },
  partial: { label: "kısmi", className: "text-info border-info/40" },
  failed: { label: "başarısız", className: "text-warn border-warn/40" },
  running: { label: "sürüyor", className: "text-muted border-line" },
};

export default function StatusPage() {
  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="font-serif text-4xl">Veri toplama</h1>
        <p className="text-sm text-muted">
          Her gün 03:00 ve 15:00&apos;te (Türkiye) katalog ikiye bölünerek toplanır.
        </p>
      </header>
      <Suspense fallback={<div className="h-64 animate-pulse rounded-card bg-surface" />}>
        <Stats />
      </Suspense>
    </div>
  );
}

async function Stats() {
  const { brands, runs } = await getStats();
  return (
    <>
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {brands.flatMap((b) => [
          <Tile key={`${b.slug}-p`} label={`${b.name} · ürün`} value={formatCount(b.products)} />,
          <Tile key={`${b.slug}-v`} label="Beden (varyant)" value={formatCount(b.variants)} />,
          <Tile key={`${b.slug}-o`} label="Fiyat gözlemi" value={formatCount(b.observations)} />,
          <Tile
            key={`${b.slug}-s`}
            label="Takip başlangıcı"
            value={b.tracking_since ? formatDay(b.tracking_since) : "—"}
          />,
        ])}
      </section>

      <section className="overflow-x-auto rounded-card border border-line">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="bg-surface text-xs text-muted">
            <tr>
              <th className="px-3 py-2 font-normal">Başlangıç</th>
              <th className="px-3 py-2 font-normal">Marka</th>
              <th className="px-3 py-2 font-normal">Durum</th>
              <th className="px-3 py-2 text-right font-normal">Ürün</th>
              <th className="px-3 py-2 text-right font-normal">Hata</th>
              <th className="px-3 py-2 text-right font-normal">Süre</th>
              <th className="px-3 py-2 font-normal">Not</th>
            </tr>
          </thead>
          <tbody>
            {runs.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-muted">
                  Henüz toplama yapılmadı.
                </td>
              </tr>
            ) : (
              runs.map((run) => <RunRow key={run.id} run={run} />)
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

function RunRow({ run }: { run: Run }) {
  const status = STATUS[run.status];
  const firstNote = run.notes?.split("\n")[0] ?? "";
  return (
    <tr className="border-t border-line align-top">
      <td className="px-3 py-2 font-mono text-xs tabular">{formatDayTime(run.started_at)}</td>
      <td className="px-3 py-2">{run.brand_slug}</td>
      <td className="px-3 py-2">
        <span className={`rounded border px-1.5 py-0.5 text-xs ${status.className}`}>
          {status.label}
        </span>
      </td>
      <td className="px-3 py-2 text-right font-mono tabular">
        {formatCount(run.items_seen - run.items_failed)}
      </td>
      <td className="px-3 py-2 text-right font-mono tabular">{formatCount(run.items_failed)}</td>
      <td className="px-3 py-2 text-right font-mono text-xs tabular">
        {formatDuration(run.started_at, run.finished_at)}
      </td>
      <td className="max-w-xs truncate px-3 py-2 text-xs text-muted" title={run.notes ?? ""}>
        {firstNote}
      </td>
    </tr>
  );
}
