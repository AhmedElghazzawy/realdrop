import Form from "next/form";
import Link from "next/link";
import { Suspense } from "react";
import { SearchIcon } from "@/components/icons";
import { CardSkeleton, PriceCard } from "@/components/PriceCard";
import { getDictionary, getLocale } from "@/i18n";
import { type Filters, getFacets, getProducts, type SortOrder } from "@/lib/api";
import { CATEGORIES, type CategoryKey, isCategory } from "@/lib/categories";
import { formatCount } from "@/lib/format";
import { dealsQuery, shopHref } from "@/lib/links";
import { STYLES, type StyleKey } from "@/lib/styles";

// Men only for now (owner decision, 25 Oct 2026); a men/women choice comes later.
const MEN: Filters = { audience: "men" };

export default async function Home() {
  const [locale, t] = [await getLocale(), await getDictionary()];
  const h = t.home;
  return (
    <div className="flex flex-col gap-20 pb-10 lg:gap-28">
      <section className="mx-auto w-full max-w-[90rem] px-4 pt-10 lg:px-8 lg:pt-16">
        <div className="grid gap-10 lg:grid-cols-[1.25fr_1fr] lg:items-stretch">
          <div className="flex flex-col justify-center gap-7">
            <p className="flex w-fit items-center gap-2 rounded-full bg-surface px-3 py-1.5 text-xs font-medium">
              <span className="size-1.5 rounded-full bg-signal" aria-hidden />
              {h.kicker}
            </p>
            <h1 className="font-display text-5xl font-semibold leading-[0.95] tracking-tighter sm:text-7xl lg:text-[5.5rem]">
              {h.title}
              <br />
              <span className="text-signal">{h.titleAccent}</span>
            </h1>
            <p className="max-w-lg text-base leading-7 text-muted sm:text-lg">{h.intro}</p>
            <Form
              action={`/${locale}/shop`}
              role="search"
              className="flex h-14 max-w-lg items-center rounded-full bg-surface p-1.5 pl-5"
            >
              <label htmlFor="home-q" className="sr-only">
                {t.search.label}
              </label>
              <SearchIcon className="size-[18px] shrink-0 text-muted" />
              <input
                id="home-q"
                name="q"
                type="search"
                placeholder={t.search.placeholder}
                className="h-full min-w-0 flex-1 bg-transparent px-3 text-[15px] outline-none placeholder:text-muted"
              />
              <button className="h-full rounded-full bg-text px-6 text-sm font-medium text-on-text">
                {t.search.button}
              </button>
            </Form>
            <ul className="flex max-w-xl flex-wrap gap-2">
              {STYLES.slice(0, 6).map((key) => (
                <li key={key}>
                  <Link
                    href={shopHref(locale, { style: [key] })}
                    className="block rounded-full border border-line-strong px-4 py-2 text-sm font-medium transition-colors hover:border-text hover:bg-text hover:text-on-text"
                  >
                    {t.styles[key]}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div className="flex min-h-80 flex-col justify-between gap-6 rounded-[28px] bg-text p-7 text-on-text lg:p-9">
            <span className="w-fit rounded-full bg-signal px-3 py-1 text-xs font-semibold text-on-text">
              {h.soon}
            </span>
            <div className="grid flex-1 place-items-center rounded-[20px] border border-dashed border-on-text/30 p-6">
              <svg viewBox="0 0 24 24" className="size-12 opacity-80" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
                <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
                <circle cx="12" cy="13" r="3.5" />
              </svg>
            </div>
            <div className="flex flex-col gap-2">
              <h2 className="font-display text-3xl font-semibold tracking-tight">{h.lookSoon}</h2>
              <p className="max-w-sm text-sm leading-6 opacity-70">{h.lookSoonNote}</p>
            </div>
          </div>
        </div>
      </section>

      <Section title={h.stylesTitle} note={h.stylesNote}>
        <Suspense fallback={<TilesSkeleton />}>
          <StyleTiles />
        </Suspense>
      </Section>

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

      <section id="how" className="mx-4 scroll-mt-28 rounded-[28px] bg-surface lg:mx-8">
        <div className="mx-auto max-w-[90rem] px-4 py-16 lg:px-8 lg:py-24">
          <h2 className="mb-12 max-w-xl font-display font-semibold text-4xl leading-tight tracking-tight sm:text-5xl">
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
          <h2 className="font-display text-3xl font-semibold leading-none tracking-tight sm:text-4xl">{title}</h2>
          {note ? <p className="text-sm text-muted">{note}</p> : null}
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

// The picture for a style tile comes from the category that says the style best, so a tile shows
// clothes rather than whatever accessory was tagged last.
const STYLE_COVER: Record<StyleKey, CategoryKey> = {
  old_money: "knitwear",
  streetwear: "sweatshirts",
  minimal: "tshirts",
  smart_casual: "shirts",
  classic_tailoring: "suits",
  sporty: "tracksuits",
  workwear: "jackets",
  preppy: "knitwear",
  techwear: "jackets",
  y2k: "jeans",
};

/** One tile per style, with the newest in-stock piece of that style as the picture. */
async function StyleTiles() {
  const [locale, t] = [await getLocale(), await getDictionary()];
  const keys = STYLES.slice(0, 6);
  const [facets, ...firsts] = await Promise.all([
    getFacets(MEN),
    ...keys.map((key) => getProducts({ ...MEN, styles: [key], category: STYLE_COVER[key], inStock: true }, { sort: "recent", limit: 1 })),
  ]);
  const counts = new Map(facets.styles.map((s) => [s.key, s.count]));
  return (
    <ul className="rail -mx-4 flex gap-3 overflow-x-auto px-4 sm:mx-0 sm:grid sm:grid-cols-3 sm:overflow-visible sm:px-0 lg:grid-cols-6 lg:gap-4">
      {keys.map((key, i) => {
        const image = firsts[i].items[0]?.image_url;
        return (
          <li key={key} className="w-[42vw] shrink-0 sm:w-auto">
            <Link
              href={shopHref(locale, { style: [key] })}
              className="group relative block aspect-[3/4] overflow-hidden rounded-card bg-surface"
            >
              {image ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={image}
                  alt=""
                  loading="lazy"
                  className="h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-[1.04]"
                />
              ) : null}
              <div className="absolute inset-x-0 bottom-0 flex flex-col gap-0.5 bg-gradient-to-t from-black/70 to-transparent p-4 pt-16 text-white">
                <span className="font-display text-xl font-semibold tracking-tight">{t.styles[key]}</span>
                <span className="text-xs opacity-80 tabular">{t.home.pieces(formatCount(locale, counts.get(key) ?? 0))}</span>
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
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
            <div className="aspect-[4/5] overflow-hidden rounded-card bg-surface">
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
    <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {facets.brands.map((b) => (
        <li key={b.slug}>
          <Link
            href={shopHref(locale, { brand: [b.slug] })}
            className="flex h-24 flex-col items-center justify-center gap-1 rounded-card bg-surface px-3 text-center transition-colors hover:bg-surface-2"
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
        <li key={i} className="aspect-[4/5] w-[38vw] shrink-0 animate-pulse rounded-card bg-surface sm:w-auto" />
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
