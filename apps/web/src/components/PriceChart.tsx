import type { PricePoint } from "@/lib/api";
import { formatDay, formatMoney } from "@/lib/format";

// Server-rendered SVG: the price people paid each day (solid) and the shop's claimed old price
// (dashed, --warn). No chart library needed for one line; Phase 8 adds hover and 30/90-day ranges.
export function PriceChart({ history, currency }: { history: PricePoint[]; currency: string }) {
  if (history.length === 0) {
    return <p className="text-sm text-muted">Henüz onaylanmış fiyat yok.</p>;
  }
  const width = 640;
  const height = 220;
  const pad = { top: 16, right: 16, bottom: 28, left: 72 };
  const values = history.flatMap((p) =>
    p.original_price_minor === null ? [p.price_minor] : [p.price_minor, p.original_price_minor],
  );
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || max * 0.1 || 1;
  const lo = min - span * 0.15;
  const hi = max + span * 0.15;
  const x = (i: number) =>
    history.length === 1
      ? (pad.left + width - pad.right) / 2
      : pad.left + (i / (history.length - 1)) * (width - pad.left - pad.right);
  const y = (v: number) => pad.top + ((hi - v) / (hi - lo)) * (height - pad.top - pad.bottom);
  const line = (pick: (p: PricePoint) => number | null) =>
    history
      .map((p, i) => [i, pick(p)] as const)
      .filter((pair): pair is readonly [number, number] => pair[1] !== null)
      .map(([i, v], k) => `${k === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`)
      .join(" ");
  const last = history[history.length - 1];

  return (
    <figure>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        role="img"
        aria-label={`Fiyat geçmişi, ${history.length} gün. Son fiyat ${formatMoney(last.price_minor, currency)}.`}
      >
        {[hi, (hi + lo) / 2, lo].map((v) => (
          <g key={v}>
            <line x1={pad.left} x2={width - pad.right} y1={y(v)} y2={y(v)} stroke="var(--line)" />
            <text
              x={pad.left - 8}
              y={y(v) + 4}
              textAnchor="end"
              className="fill-[var(--muted)] font-mono text-[11px]"
            >
              {formatMoney(Math.round(v), currency)}
            </text>
          </g>
        ))}
        <path
          d={line((p) => p.original_price_minor)}
          fill="none"
          stroke="var(--warn)"
          strokeDasharray="5 5"
          strokeWidth={1.5}
        />
        <path d={line((p) => p.price_minor)} fill="none" stroke="var(--text)" strokeWidth={2} />
        {history.map((p, i) =>
          p.original_price_minor === null ? null : (
            <circle
              key={`claim-${p.day}`}
              cx={x(i)}
              cy={y(p.original_price_minor)}
              r={3.5}
              fill="var(--bg)"
              stroke="var(--warn)"
              strokeWidth={1.5}
            >
              <title>{`${formatDay(p.day)}: mağaza iddiası ${formatMoney(p.original_price_minor, currency)}`}</title>
            </circle>
          ),
        )}
        {history.map((p, i) => (
          <circle key={p.day} cx={x(i)} cy={y(p.price_minor)} r={3.5} fill="var(--text)">
            <title>{`${formatDay(p.day)}: ${formatMoney(p.price_minor, currency)}`}</title>
          </circle>
        ))}
        <text x={pad.left} y={height - 8} className="fill-[var(--muted)] text-[11px]">
          {formatDay(history[0].day)}
        </text>
        {history.length > 1 ? (
          <text
            x={width - pad.right}
            y={height - 8}
            textAnchor="end"
            className="fill-[var(--muted)] text-[11px]"
          >
            {formatDay(last.day)}
          </text>
        ) : null}
      </svg>
      <figcaption className="mt-2 flex flex-wrap gap-4 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4 bg-text" /> Ödenen fiyat (günlük en düşük)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-4 border-t border-dashed border-warn" /> Mağazanın
          &quot;eski fiyat&quot; iddiası
        </span>
      </figcaption>
    </figure>
  );
}
