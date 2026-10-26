import Form from "next/form";
import Link from "next/link";
import { Suspense } from "react";
import { ArrowRight, SearchIcon } from "@/components/icons";
import { CardSkeleton, PriceCard } from "@/components/PriceCard";
import { getDictionary, getLocale } from "@/i18n";
import { type Filters, getFacets, getProducts, type SortOrder } from "@/lib/api";
import { CATEGORIES, type CategoryKey, isCategory } from "@/lib/categories";
import { formatCount } from "@/lib/format";
import { dealsQuery, shopHref } from "@/lib/links";

// Men only for now (owner decision, 25 Oct 2026); a men/women choice comes later.
const MEN: Filters = { audience: "men" };

export default async function Home() {
  const [locale, t] = [await getLocale(), await getDictionary()];
  const h = t.home;
  return (
    <div className="flex flex-col gap-20 pb-10 lg:gap-28">
      <section className="border-b border-line">
        <div className="mx-auto grid max-w-[90rem] gap-10 px-4 py-14 lg:grid-cols-[1.2fr_1fr] lg:items-end lg:px-8 lg:py-24">
          <div className="flex flex-col gap-6">
            <p className="eyebrow text-muted">{h.kicker}</p>
            <h1 className="font-serif text-5xl leading-[0.95] tracking-tight sm:text-7xl lg:text-8xl">
              {h.title}
              <br />
              <span className="text-muted">{h.titleAccent}</span>
            </h1>
          </div>
          <div className="flex flex-col gap-6 lg:pb-3">
            <p className="max-w-md text-base leading-7 text-muted">{h.intro}</p>
            <Form action={`/${locale}/shop`} role="search" className="flex h-12 max-w-md items-center border border-text">
              <label htmlFor="home-q" className="sr-only">
                {t.search.label}
              </label>
              <SearchIcon className="ml-4 size-[18px] shrink-0 text-muted" />
              <input
                id="home-q"
                name="q"
                type="search"
                placeholder={t.search.placeholder}
                className="h-full min-w-0 flex-1 bg-transparent px-3 text-sm outline-none placeholder:text-muted"
              />
              <button className="h-full bg-text px-5 text-sm font-medium text-on-text">{t.search.button}</button>
            </Form>
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
              <Link
                href={shopHref(locale, dealsQuery)}
                className="flex items-center gap-1.5 font-medium underline underline-offset-4"
              >
                {h.ctaDeals} <ArrowRight className="size-4" />
              </Link>
              <Link href={shopHref(locale)} className="text-muted underline underline-offset-4 hover:text-text">
                {h.ctaAll}
              </Link>
            </div>
          </div>
        </div>
      </section>

      <Section title={h.categoriesTitle}>
        <Suspense fallback={<TilesSkeleton />}>
          <CategoryTiles />
        </Suspense>
      </Section>

      <Section
        title={h.dealsTitle}
        note={h.dealsNote}
        more={{ href: shopHref(locale, dealsQuery), label: h.viewAll }}
      >
        <Suspense fallback={<RailSkeleton />}>
          <Rail filters={{ ...MEN, onSale: true, inStock: true }} sort="claimed_discount" />
        </Suspense>
      </Section>

      <Section title={h.newTitle} more={{ href: shopHref(locale), label: h.viewAll }}>
        <Suspense fallback={<RailSkeleton />}>
          <Rail filters={{ ...MEN, inStock: true }} sort="recent" />
        </Suspense>
      </Section>

      <Section title={h.brandsTitle} more={{ href: `/${locale}/brands`, label: h.viewAll }}>
        <Suspense fallback={<div className="h-24 animate-pulse bg-surface" />}>
          <BrandStrip />
        </Suspense>
      </Section>

      <section id="how" className="scroll-mt-28 bg-surface">
        <div className="mx-auto max-w-[90rem] px-4 py-16 lg:px-8 lg:py-24">
          <h2 className="mb-12 max-w-xl font-serif text-4xl leading-tight tracking-tight sm:text-5xl">
            {h.how.title}
          </h2>
          <ol className="grid gap-10 md:grid-cols-3">
            {h.how.steps.map((step, i) => (
              <li key={step.title} className="flex flex-col gap-3 border-t border-text pt-5">
                <span className="text-xs text-muted tabular">0{i + 1}</span>
                <h3 className="text-lg font-medium">{step.title}</h3>
                <p className="max-w-sm text-sm leading-6 text-muted">{step.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>
    </div>
  );
}

function Section({
  title,
  note,
  more,
  children,
}: {
  title: string;
  note?: string;
  more?: { href: string; label: string };
  children: React.ReactNode;
}) {
  return (
    <section className="mx-auto w-full max-w-[90rem] px-4 lg:px-8">
      <div className="mb-6 flex items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="font-serif text-3xl leading-none tracking-tight sm:text-4xl">{title}</h2>
          {note ? <p className="text-xs text-muted">{note}</p> : null}
        </div>
        {more ? (
          <Link href={more.href} className="flex shrink-0 items-center gap-1 text-sm underline underline-offset-4">
            {more.label}
          </Link>
        ) : null}
      </div>
      {children}
    </section>
  );
}

async function CategoryTiles() {
  const [locale, t] = [await getLocale(), await getDictionary()];
  const facets = await getFacets(MEN);
  const byKey = new Map(facets.categories.filter((c) => isCategory(c.key)).map((c) => [c.key, c]));
  const tiles = CATEGORIES.flatMap((key) => {
    const c = byKey.get(key);
    return c && c.count > 0 ? [c] : [];
  });
  return (
    // Phones: one swipeable row (15 stacked tiles is a long scroll). Wider screens: a grid.
    <ul className="rail -mx-4 flex gap-3 overflow-x-auto px-4 sm:mx-0 sm:grid sm:grid-cols-3 sm:overflow-visible sm:px-0 lg:grid-cols-5 lg:gap-4">
      {tiles.map((c) => (
        <li key={c.key} className="w-[38vw] shrink-0 sm:w-auto">
          <Link href={shopHref(locale, { category: c.key })} className="group flex flex-col gap-2.5">
            <div className="aspect-[4/5] overflow-hidden bg-surface">
              {c.image_url ? (
                // Hotlinked from the shop's CDN, like product images.
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={c.image_url}
                  alt=""
                  loading="lazy"
                  className="h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-[1.03]"
                />
              ) : null}
            </div>
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-sm font-medium">{t.categories[c.key as CategoryKey]}</span>
              <span className="text-xs text-muted tabular">{formatCount(locale, c.count)}</span>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}

async function Rail({ filters, sort }: { filters: Filters; sort: SortOrder }) {
  const data = await getProducts(filters, { sort, limit: 12 });
  return (
    <ul className="rail -mx-4 flex gap-3 overflow-x-auto px-4 lg:mx-0 lg:gap-4 lg:px-0">
      {data.items.map((product) => (
        <li key={product.id} className="w-[44vw] shrink-0 sm:w-[30vw] lg:w-[calc((100%-4rem)/5)]">
          <PriceCard product={product} />
        </li>
      ))}
    </ul>
  );
}

async function BrandStrip() {
  const [locale, t] = [await getLocale(), await getDictionary()];
  const facets = await getFacets(MEN);
  return (
    <ul className="grid grid-cols-2 border-l border-t border-line sm:grid-cols-3 lg:grid-cols-6">
      {facets.brands.map((b) => (
        <li key={b.slug} className="border-b border-r border-line">
          <Link
            href={shopHref(locale, { brand: [b.slug] })}
            className="flex h-24 flex-col items-center justify-center gap-1 px-3 text-center hover:bg-surface"
          >
            <span className="text-sm font-semibold uppercase tracking-[0.14em]">{b.name}</span>
            <span className="text-[11px] text-muted tabular">{t.home.items(formatCount(locale, b.count))}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function TilesSkeleton() {
  return (
    <ul className="flex gap-3 overflow-hidden sm:grid sm:grid-cols-3 lg:grid-cols-5 lg:gap-4" aria-busy="true">
      {Array.from({ length: 10 }, (_, i) => (
        <li key={i} className="aspect-[4/5] w-[38vw] shrink-0 animate-pulse bg-surface sm:w-auto" />
      ))}
    </ul>
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
