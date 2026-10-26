import { getDictionary, getLocale } from "@/i18n";
import type { PricePoint } from "@/lib/api";
import { formatDay, formatMoney } from "@/lib/format";
import { type PlotPoint, PriceChartPlot } from "./PriceChartPlot";

// Server half of the price chart: every label is formatted here (dictionary entries are functions,
// which cannot cross into a client component), the client half only draws and handles hover.
// Series colours are the validated dataviz palette (--series-1 paid, --series-2 the shop's claim).
export async function PriceChart({ history, currency }: { history: PricePoint[]; currency: string }) {
  const [locale, t] = [await getLocale(), await getDictionary()];
  if (history.length === 0) {
    return <p className="text-sm text-muted">{t.chart.noData}</p>;
  }
  const money = (minor: number) => formatMoney(locale, minor, currency);
  const points: PlotPoint[] = history.map((p) => ({
    day: formatDay(locale, p.day),
    price: p.price_minor,
    priceLabel: money(p.price_minor),
    claimed: p.original_price_minor,
    claimedLabel: p.original_price_minor === null ? null : money(p.original_price_minor),
  }));

  const values = history.flatMap((p) =>
    p.original_price_minor === null ? [p.price_minor] : [p.price_minor, p.original_price_minor],
  );
  const [min, max] = [Math.min(...values), Math.max(...values)];
  const span = max - min || max * 0.1 || 1;
  const lo = Math.max(0, min - span * 0.2);
  const hi = max + span * 0.2;
  const ticks = [hi, (hi + lo) / 2, lo].map((v) => ({ value: v, label: money(Math.round(v)) }));
  const hasClaim = points.some((p) => p.claimed !== null);
  const last = points[points.length - 1];

  return (
    <figure className="flex flex-col gap-4">
      {/* Two series: a legend always, so identity never rests on colour alone. */}
      <figcaption className="flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-muted">
        <span className="flex items-center gap-2">
          <span aria-hidden className="inline-block h-0.5 w-5 bg-series-1" /> {t.chart.paid}
        </span>
        {hasClaim ? (
          <span className="flex items-center gap-2">
            <span aria-hidden className="inline-block w-5 border-t-2 border-dashed border-series-2" />{" "}
            {t.chart.claimed}
          </span>
        ) : null}
      </figcaption>
      <PriceChartPlot
        points={points}
        lo={lo}
        hi={hi}
        ticks={ticks}
        labels={{ paid: t.chart.price, claimed: t.chart.shopClaim }}
        aria={t.chart.aria(points.length, last.priceLabel)}
      />
      <details className="group text-sm">
        <summary className="cursor-pointer text-xs text-muted underline underline-offset-4 hover:text-text">
          {t.chart.table}
        </summary>
        <div className="mt-3 max-h-72 overflow-auto border-t border-line">
          <table className="w-full text-left text-xs tabular">
            <thead className="sticky top-0 bg-bg text-muted">
              <tr>
                <th className="py-2 font-normal">{t.chart.day}</th>
                <th className="py-2 text-right font-normal">{t.chart.price}</th>
                {hasClaim ? <th className="py-2 text-right font-normal">{t.chart.shopClaim}</th> : null}
              </tr>
            </thead>
            <tbody>
              {points
                .map((p, i) => (
                  <tr key={history[i].day} className="border-t border-line">
                    <td className="py-1.5">{p.day}</td>
                    <td className="py-1.5 text-right">{p.priceLabel}</td>
                    {hasClaim ? <td className="py-1.5 text-right text-muted">{p.claimedLabel ?? "—"}</td> : null}
                  </tr>
                ))
                .reverse()}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
