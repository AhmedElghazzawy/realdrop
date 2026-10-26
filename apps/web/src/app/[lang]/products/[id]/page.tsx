import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ExternalIcon } from "@/components/icons";
import { CardSkeleton, PriceCard } from "@/components/PriceCard";
import { PriceChart } from "@/components/PriceChart";
import { getDictionary, getLocale } from "@/i18n";
import { type Filters, getProduct, getProducts, NotFoundError, type ProductDetail } from "@/lib/api";
import { isCategory } from "@/lib/categories";
import { claimedDiscount, formatDay, formatDayTime, formatMoney, formatPercent } from "@/lib/format";
import { shopHref } from "@/lib/links";

export default function ProductPage(props: PageProps<"/[lang]/products/[id]">) {
  return (
    <Suspense fallback={<ProductSkeleton />}>
      <Product params={props.params} />
    </Suspense>
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
  const [locale, dict] = [await getLocale(), await getDictionary()];
  const t = dict.product;
  const category = p.category !== null && isCategory(p.category) ? p.category : null;
  const discount = claimedDiscount(p.price_minor, p.original_price_minor);
  const pct = discount === null ? null : formatPercent(locale, discount);
  const inStock = p.variants.filter((v) => v.in_stock).length;

  return (
    <div className="mx-auto flex max-w-[90rem] flex-col gap-16 px-4 pb-10 pt-5 lg:gap-24 lg:px-8">
      <article className="flex flex-col gap-5">
        <nav aria-label="Breadcrumb" className="text-xs text-muted">
          <ol className="flex flex-wrap items-center gap-1.5">
            <li>
              <Link href={`/${locale}`} className="hover:text-text">
                {dict.shop.breadcrumbHome}
              </Link>
            </li>
            {category ? (
              <li className="flex items-center gap-1.5">
                <span aria-hidden>/</span>
                <Link href={shopHref(locale, { category })} className="hover:text-text">
                  {dict.categories[category]}
                </Link>
              </li>
            ) : null}
            <li className="flex items-center gap-1.5">
              <span aria-hidden>/</span>
              <Link href={shopHref(locale, { brand: [p.brand_slug] })} className="hover:text-text">
                {p.brand_name}
              </Link>
            </li>
          </ol>
        </nav>

        <div className="grid gap-8 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-12">
          <Gallery images={p.image_urls} title={p.title} label={t.image} />

          <div className="flex flex-col gap-7 lg:sticky lg:top-32 lg:self-start">
            <header className="flex flex-col gap-3">
              <Link
                href={shopHref(locale, { brand: [p.brand_slug] })}
                className="eyebrow self-start text-text hover:underline"
              >
                {p.brand_name}
              </Link>
              <h1 className="font-serif text-3xl leading-tight tracking-tight sm:text-4xl" lang="tr">
                {p.title}
              </h1>
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 tabular">
                <span className={`text-2xl font-medium ${pct ? "text-sale" : ""}`}>
                  {formatMoney(locale, p.price_minor, p.currency)}
                </span>
                {pct && p.original_price_minor !== null ? (
                  <>
                    <s className="text-base text-muted">
                      {formatMoney(locale, p.original_price_minor, p.currency)}
                    </s>
                    <span
                      title={dict.claim.title}
                      className="bg-sale px-1.5 py-0.5 text-xs font-semibold text-on-text"
                    >
                      {dict.claim.shopSays(pct)}
                    </span>
                  </>
                ) : null}
              </div>
              {pct ? (
                <p className="border-l-2 border-warn pl-3 text-xs leading-5 text-muted">{t.claimNote(pct)}</p>
              ) : null}
            </header>

            <section className="flex flex-col gap-3">
              <div className="flex items-baseline justify-between">
                <h2 className="eyebrow">{t.sizes}</h2>
                <span className="text-xs text-muted">{t.sizesNote(inStock, p.variants.length)}</span>
              </div>
              <ul className="grid grid-cols-4 gap-2 sm:grid-cols-6">
                {p.variants.map((v, i) => (
                  <li
                    key={`${v.size_label}-${i}`}
                    className={`flex h-11 items-center justify-center border text-xs tabular ${
                      v.in_stock ? "border-line-strong" : "border-line text-muted line-through"
                    }`}
                  >
                    <span className="sr-only">{v.in_stock ? t.inStock : t.soldOut}: </span>
                    {v.size_label ?? "—"}
                  </li>
                ))}
              </ul>
            </section>

            <div className="flex flex-col gap-2">
              <a
                href={p.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex h-13 items-center justify-center gap-2 bg-text px-6 text-sm font-medium text-on-text transition-opacity hover:opacity-85"
              >
                {t.buyAt(p.brand_name)} <ExternalIcon className="size-4" />
              </a>
              <p className="text-center text-xs text-muted">{t.buyNote}</p>
            </div>

            <dl className="border-t border-line text-sm">
              <Row label={t.brand}>{p.brand_name}</Row>
              {p.category_raw ? (
                <Row label={t.shopCategory}>
                  <span lang="tr">{p.category_raw}</span>
                </Row>
              ) : null}
              <Row label={t.since}>{formatDay(locale, p.first_seen_at)}</Row>
            </dl>
            <p className="-mt-4 text-xs text-muted">{t.lastChecked(formatDayTime(locale, p.observed_at))}</p>
          </div>
        </div>
      </article>

      <section className="grid grid-cols-[minmax(0,1fr)] gap-6 border-t border-line pt-10 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:gap-12">
        <div className="flex flex-col gap-3">
          <h2 className="font-serif text-3xl leading-none tracking-tight sm:text-4xl">{t.history}</h2>
          {p.history.length < 14 ? (
            <p className="max-w-sm text-sm leading-6 text-muted">{t.notEnoughHistory(p.history.length)}</p>
          ) : null}
        </div>
        <PriceChart history={p.history} currency={p.currency} />
      </section>

      {category ? (
        <Suspense fallback={<RailSkeleton />}>
          <MoreRail
            title={t.moreIn(dict.categories[category])}
            href={shopHref(locale, { category })}
            filters={{ audience: "men", category, inStock: true }}
            exclude={p.id}
            viewAll={dict.home.viewAll}
          />
        </Suspense>
      ) : null}
      <Suspense fallback={<RailSkeleton />}>
        <MoreRail
          title={t.moreFrom(p.brand_name)}
          href={shopHref(locale, { brand: [p.brand_slug] })}
          filters={{ audience: "men", brands: [p.brand_slug], inStock: true }}
          exclude={p.id}
          viewAll={dict.home.viewAll}
        />
      </Suspense>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-6 border-b border-line py-3">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right tabular">{children}</dd>
    </div>
  );
}

// Phones: a swipeable row of full images. Desktop: the two-column image grid fashion sites use.
function Gallery({
  images,
  title,
  label,
}: {
  images: string[];
  title: string;
  label: (n: number, of: number) => string;
}) {
  const shown = images.slice(0, 6);
  if (shown.length === 0) return <div className="aspect-[3/4] bg-surface" />;
  return (
    <ul className="rail -mx-4 flex gap-1 overflow-x-auto lg:mx-0 lg:grid lg:grid-cols-2 lg:gap-1 lg:overflow-visible">
      {shown.map((src, i) => (
        <li
          key={src}
          className={`w-[86vw] shrink-0 snap-start sm:w-[60vw] lg:w-auto ${
            i === 0 && shown.length % 2 === 1 ? "lg:col-span-2" : ""
          }`}
        >
          {/* Hotlinked from the shop's CDN; we store URLs, not images. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={src}
            alt={i === 0 ? title : label(i + 1, shown.length)}
            loading={i < 2 ? "eager" : "lazy"}
            className="aspect-[3/4] w-full bg-surface object-cover"
          />
        </li>
      ))}
    </ul>
  );
}

async function MoreRail({
  title,
  href,
  filters,
  exclude,
  viewAll,
}: {
  title: string;
  href: string;
  filters: Filters;
  exclude: string;
  viewAll: string;
}) {
  const data = await getProducts(filters, { sort: "recent", limit: 11 });
  const items = data.items.filter((item) => item.id !== exclude).slice(0, 10);
  if (items.length === 0) return null;
  return (
    <section className="flex flex-col gap-6">
      <div className="flex items-end justify-between gap-4">
        <h2 className="font-serif text-3xl leading-none tracking-tight sm:text-4xl">{title}</h2>
        <Link href={href} className="shrink-0 text-sm underline underline-offset-4">
          {viewAll}
        </Link>
      </div>
      <ul className="rail -mx-4 flex gap-3 overflow-x-auto px-4 lg:mx-0 lg:gap-4 lg:px-0">
        {items.map((product) => (
          <li key={product.id} className="w-[44vw] shrink-0 sm:w-[30vw] lg:w-[calc((100%-4rem)/5)]">
            <PriceCard product={product} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function RailSkeleton() {
  return (
    <ul className="flex gap-3 overflow-hidden lg:gap-4" aria-busy="true">
      {Array.from({ length: 5 }, (_, i) => (
        <li key={i} className="w-[44vw] shrink-0 sm:w-[30vw] lg:w-[calc((100%-4rem)/5)]">
          <CardSkeleton />
        </li>
      ))}
    </ul>
  );
}

function ProductSkeleton() {
  return (
    <div
      className="mx-auto grid max-w-[90rem] gap-8 px-4 pt-12 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-12 lg:px-8"
      aria-busy="true"
    >
      <div className="aspect-[3/4] animate-pulse bg-surface lg:aspect-[3/2]" />
      <div className="flex flex-col gap-4">
        <div className="h-3 w-24 animate-pulse bg-surface" />
        <div className="h-10 w-full animate-pulse bg-surface" />
        <div className="h-7 w-40 animate-pulse bg-surface" />
        <div className="mt-6 h-32 animate-pulse bg-surface" />
      </div>
    </div>
  );
}
