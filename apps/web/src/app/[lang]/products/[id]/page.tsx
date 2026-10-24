import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ClaimedPrice } from "@/components/ClaimedPrice";
import { PriceChart } from "@/components/PriceChart";
import { TrackingBadge } from "@/components/TrackingBadge";
import { getDictionary, getLocale } from "@/i18n";
import { getProduct, NotFoundError, type ProductDetail } from "@/lib/api";
import { formatDayTime, formatMoney } from "@/lib/format";

export default async function ProductPage(props: PageProps<"/[lang]/products/[id]">) {
  const [locale, t] = [await getLocale(), await getDictionary()];
  return (
    <div className="flex flex-col gap-4">
      <Link href={`/${locale}`} className="text-sm text-muted hover:text-text">
        {t.product.back}
      </Link>
      <Suspense fallback={<div className="h-96 animate-pulse rounded-card bg-surface" />}>
        <Product params={props.params} />
      </Suspense>
    </div>
  );
}

async function load(id: string): Promise<ProductDetail> {
  try {
    return await getProduct(id);
  } catch (error) {
    if (error instanceof NotFoundError) notFound();
    throw error;
  }
}

async function Product({ params }: { params: Promise<{ id: string }> }) {
  const p = await load((await params).id);
  const [locale, t] = [await getLocale(), (await getDictionary()).product];
  return (
    <article className="grid gap-6 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <div className="flex gap-2 overflow-x-auto md:flex-col">
        {p.image_urls.slice(0, 4).map((src, i) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={src}
            src={src}
            alt={i === 0 ? p.title : ""}
            className="aspect-[3/4] w-3/4 shrink-0 rounded-card bg-surface object-cover md:w-full"
          />
        ))}
      </div>

      <div className="flex flex-col gap-5">
        <header className="flex flex-col gap-2">
          <p className="text-xs uppercase tracking-wider text-muted">
            {p.brand_name} · {p.category}
          </p>
          <h1 className="font-serif text-3xl leading-tight" lang="tr">
            {p.title}
          </h1>
          <div className="flex flex-wrap items-baseline gap-3">
            <span className="font-mono text-3xl tabular">
              {formatMoney(locale, p.price_minor, p.currency)}
            </span>
            <ClaimedPrice price={p.price_minor} claimed={p.original_price_minor} currency={p.currency} />
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
            <TrackingBadge since={p.first_seen_at} />
            <span>{t.lastChecked(formatDayTime(locale, p.observed_at))}</span>
          </div>
        </header>

        <section className="rounded-card border border-line bg-surface p-4">
          <h2 className="mb-3 text-sm font-medium">{t.history}</h2>
          <PriceChart history={p.history} currency={p.currency} />
          {p.history.length < 14 ? (
            <p className="mt-3 text-xs text-muted">{t.notEnoughHistory(p.history.length)}</p>
          ) : null}
        </section>

        <section>
          <h2 className="mb-2 text-sm font-medium">{t.sizes}</h2>
          <ul className="flex flex-wrap gap-2">
            {p.variants.map((v, i) => (
              <li
                key={`${v.size_label}-${i}`}
                className={`min-w-11 rounded border px-2.5 py-1.5 text-center font-mono text-xs ${
                  v.in_stock ? "border-line" : "border-line/50 text-muted line-through"
                }`}
                title={v.in_stock ? t.inStock : t.soldOut}
              >
                {v.size_label ?? "—"}
              </li>
            ))}
          </ul>
        </section>

        <a
          href={p.url}
          target="_blank"
          rel="noopener noreferrer"
          className="self-start rounded-card bg-text px-4 py-2.5 text-sm font-medium text-bg"
        >
          {t.viewAt(p.brand_name)}
        </a>
      </div>
    </article>
  );
}
