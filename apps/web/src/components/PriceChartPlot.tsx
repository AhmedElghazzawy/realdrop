"use client";

import { type KeyboardEvent, type PointerEvent, useEffect, useRef, useState } from "react";

export interface PlotPoint {
  day: string;
  price: number;
  priceLabel: string;
  claimed: number | null;
  claimedLabel: string | null;
}

const HEIGHT = 240;
const PAD = { top: 12, right: 12, bottom: 28, left: 76 };

// Step lines: a price holds until the next observation, so a slope between two days would show
// prices nobody saw. Hover or arrow keys move a crosshair; the tooltip reads both series.
export function PriceChartPlot({
  points,
  lo,
  hi,
  ticks,
  labels,
  aria,
}: {
  points: PlotPoint[];
  lo: number;
  hi: number;
  ticks: { value: number; label: string }[];
  labels: { paid: string; claimed: string };
  aria: string;
}) {
  const wrap = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);
  const [active, setActive] = useState<number | null>(null);

  // Draw in real pixels so text stays 11px at every width (a scaled viewBox shrinks it on phones).
  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(280, entry.contentRect.width)));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const n = points.length;
  const plotW = width - PAD.left - PAD.right;
  const x = (i: number) => (n === 1 ? PAD.left + plotW / 2 : PAD.left + (i / (n - 1)) * plotW);
  const y = (v: number) => PAD.top + ((hi - v) / (hi - lo)) * (HEIGHT - PAD.top - PAD.bottom);

  const step = (pick: (p: PlotPoint) => number | null) => {
    let d = "";
    let prev: number | null = null;
    points.forEach((p, i) => {
      const v = pick(p);
      if (v === null) {
        prev = null; // a gap: the shop showed no old price that day
        return;
      }
      d += prev === null ? `M${x(i)},${y(v)}` : `H${x(i)}V${y(v)}`;
      prev = v;
    });
    return d;
  };

  const nearest = (clientX: number) => {
    const rect = wrap.current?.getBoundingClientRect();
    if (!rect || n === 1) return 0;
    const i = Math.round(((clientX - rect.left - PAD.left) / plotW) * (n - 1));
    return Math.min(n - 1, Math.max(0, i));
  };

  const onKey = (e: KeyboardEvent) => {
    const keys: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1, Home: -n, End: n };
    if (!(e.key in keys)) return;
    e.preventDefault();
    setActive((i) => Math.min(n - 1, Math.max(0, (i ?? n - 1) + keys[e.key])));
  };

  const shown = active ?? null;
  const point = shown === null ? null : points[shown];
  const tipLeft = shown === null ? 0 : Math.min(Math.max(x(shown), PAD.left + 70), width - 90);

  return (
    <div ref={wrap} className="relative min-w-0 overflow-hidden">
      <svg
        width={width}
        height={HEIGHT}
        role="img"
        aria-label={aria}
        tabIndex={0}
        className="block touch-pan-y outline-offset-4"
        onPointerMove={(e: PointerEvent) => setActive(nearest(e.clientX))}
        onPointerLeave={() => setActive(null)}
        onFocus={() => setActive((i) => i ?? n - 1)}
        onBlur={() => setActive(null)}
        onKeyDown={onKey}
      >
        {ticks.map((tick) => (
          <g key={tick.value}>
            <line x1={PAD.left} x2={width - PAD.right} y1={y(tick.value)} y2={y(tick.value)} stroke="var(--line)" />
            <text x={PAD.left - 10} y={y(tick.value) + 4} textAnchor="end" className="fill-muted text-[11px] tabular">
              {tick.label}
            </text>
          </g>
        ))}
        <text x={PAD.left} y={HEIGHT - 8} className="fill-muted text-[11px]">
          {points[0].day}
        </text>
        {n > 1 ? (
          <text x={width - PAD.right} y={HEIGHT - 8} textAnchor="end" className="fill-muted text-[11px]">
            {points[n - 1].day}
          </text>
        ) : null}

        <path
          d={step((p) => p.claimed)}
          fill="none"
          stroke="var(--series-2)"
          strokeWidth={2}
          strokeDasharray="6 4"
          strokeLinejoin="round"
        />
        <path d={step((p) => p.price)} fill="none" stroke="var(--series-1)" strokeWidth={2} strokeLinejoin="round" />
        {/* The latest values get markers, so a single day still shows both series. */}
        {points[n - 1].claimed !== null ? (
          <circle cx={x(n - 1)} cy={y(points[n - 1].claimed ?? 0)} r={4} fill="var(--series-2)" stroke="var(--bg)" strokeWidth={2} />
        ) : null}
        <circle cx={x(n - 1)} cy={y(points[n - 1].price)} r={4} fill="var(--series-1)" stroke="var(--bg)" strokeWidth={2} />

        {point && shown !== null ? (
          <g aria-hidden>
            <line
              x1={x(shown)}
              x2={x(shown)}
              y1={PAD.top}
              y2={HEIGHT - PAD.bottom}
              stroke="var(--line-strong)"
            />
            {point.claimed !== null ? (
              <circle cx={x(shown)} cy={y(point.claimed)} r={4} fill="var(--series-2)" stroke="var(--bg)" strokeWidth={2} />
            ) : null}
            <circle cx={x(shown)} cy={y(point.price)} r={4.5} fill="var(--series-1)" stroke="var(--bg)" strokeWidth={2} />
          </g>
        ) : null}
      </svg>

      {point ? (
        <div
          role="status"
          className="pointer-events-none absolute top-0 -translate-x-1/2 border border-line bg-bg px-3 py-2 text-xs shadow-sm"
          style={{ left: tipLeft }}
        >
          <p className="mb-1 text-muted">{point.day}</p>
          <p className="flex items-center gap-2 tabular">
            <span aria-hidden className="inline-block h-0.5 w-3 bg-series-1" />
            <span className="text-muted">{labels.paid}</span>
            <span className="ml-auto pl-3 font-medium">{point.priceLabel}</span>
          </p>
          {point.claimedLabel ? (
            <p className="flex items-center gap-2 tabular">
              <span aria-hidden className="inline-block w-3 border-t-2 border-dashed border-series-2" />
              <span className="text-muted">{labels.claimed}</span>
              <span className="ml-auto pl-3 line-through">{point.claimedLabel}</span>
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
