import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { AutoSubmitForm } from "@/components/AutoSubmitForm";
import { Drawer } from "@/components/Drawer";
import { FilterIcon } from "@/components/icons";
import { CardSkeleton, PriceCard } from "@/components/PriceCard";
import { getDictionary, getLocale } from "@/i18n";
import type { Locale } from "@/i18n/config";
import { type Facets, type Filters, getFacets, getProducts, type SortOrder } from "@/lib/api";
import { CATEGORIES, type CategoryKey, isCategory } from "@/lib/categories";
import { formatCount } from "@/lib/format";
import { type ShopQuery, shopHref } from "@/lib/links";

const SORTS: SortOrder[] = ["recent", "claimed_discount", "price_asc", "price_desc"];
const PAGE_SIZE = 48;
// Men only for now (owner decision, 25 Oct 2026); a men/women choice comes later.
const AUDIENCE = "men";

type Raw = Record<string, string | string[] | undefined>;

/** The URL's query, cleaned: unknown values are dropped, never passed on to the API. */
function readQuery(raw: Raw): ShopQuery & { sort: SortOrder; page: number } {
  const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";
  const many = (v: string | string[] | undefined) => (Array.isArray(v) ? v : v ? [v] : []);
  const lira = (v: string) => (/^\d{1,7}$/.test(v) ? v : undefined);
  const sort = one(raw.sort) as SortOrder;
  const category = one(raw.category);
  return {
    q: one(raw.q).trim().slice(0, 100) || undefined,
    category: isCategory(category) ? category : undefined,
    brand: many(raw.brand)
      .filter((b) => /^[a-z0-9-]{1,64}$/.test(b))
      .slice(0, 20),
    min: lira(one(raw.min)),
    max: lira(one(raw.max)),
    sale: one(raw.sale) === "1",
    stock: one(raw.stock) === "1",
    sort: SORTS.includes(sort) ? sort : "recent",
    page: Math.max(1, Math.min(500, Number.parseInt(one(raw.page), 10) || 1)),
  };
}

function toFilters(query: ShopQuery): Filters {
  return {
    q: query.q,
    category: query.category,
    brands: query.brand,
    audience: AUDIENCE,
    // The shopper types whole lira; the API takes kurus.
    minPrice: query.min ? Number(query.min) * 100 : undefined,
    maxPrice: query.max ? Number(query.max) * 100 : undefined,
    onSale: query.sale,
    inStock: query.stock,
  };
}

export async function generateMetadata(props: PageProps<"/[lang]/shop">): Promise<Metadata> {
  const t = await getDictionary();
  const query = readQuery(await props.searchParams);
  return { title: query.category ? t.categories[query.category as CategoryKey] : t.shop.title };
}

export default function ShopPage(props: PageProps<"/[lang]/shop">) {
  return (
    <div className="mx-auto max-w-[90rem] px-4 pb-10 pt-6 lg:px-8">
      <Suspense fallback={<ShopSkeleton />}>
        <Shop searchParams={props.searchParams} />
      </Suspense>
    </div>
  );
}

async function Shop({ searchParams }: { searchParams: Promise<Raw> }) {
  const [locale, t] = [await getLocale(), await getDictionary()];
  const query = readQuery(await searchParams);
  const filters = toFilters(query);
  const [data, facets] = await Promise.all([
    getProducts(filters, {
      sort: query.sort,
      limit: PAGE_SIZE,
      offset: (query.page - 1) * PAGE_SIZE,
    }),
    getFacets(filters),
  ]);
  const lastPage = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
  const brandNames = new Map(facets.brands.map((b) => [b.slug, b.name]));
  const isDeals = query.sale && query.sort === "claimed_discount" && !query.category;
  const title = query.category
    ? t.categories[query.category as CategoryKey]
    : query.q
      ? t.shop.searchTitle(query.q)
      : isDeals
        ? t.shop.dealsTitle
        : t.shop.title;

  // Active filters as removable chips.
  const chips: { label: string; href: string }[] = [];
  if (query.q) chips.push({ label: `“${query.q}”`, href: shopHref(locale, { ...query, q: undefined, page: 1 }) });
  if (query.category)
    chips.push({
      label: t.categories[query.category as CategoryKey],
      href: shopHref(locale, { ...query, category: undefined, page: 1 }),
    });
  for (const slug of query.brand ?? [])
    chips.push({
      label: brandNames.get(slug) ?? slug,
      href: shopHref(locale, { ...query, brand: query.brand?.filter((b) => b !== slug), page: 1 }),
    });
  if (query.min || query.max)
    chips.push({
      label: `₺${query.min ?? "0"} – ${query.max ? `₺${query.max}` : "∞"}`,
      href: shopHref(locale, { ...query, min: undefined, max: undefined, page: 1 }),
    });
  if (query.sale) chips.push({ label: t.shop.onSale, href: shopHref(locale, { ...query, sale: false, page: 1 }) });
  if (query.stock) chips.push({ label: t.shop.inStock, href: shopHref(locale, { ...query, stock: false, page: 1 }) });

  const filterPanel = <FilterPanel locale={locale} query={query} facets={facets} />;

  return (
    <div className="flex flex-col gap-6">
      <nav aria-label="Breadcrumb" className="text-xs text-muted">
        <ol className="flex flex-wrap items-center gap-1.5">
          <li>
            <Link href={`/${locale}`} className="hover:text-text">
              {t.shop.breadcrumbHome}
            </Link>
          </li>
          <li aria-hidden>/</li>
          <li>
            <Link href={shopHref(locale)} className="hover:text-text">
              {t.nav.men}
            </Link>
          </li>
          {query.category ? (
            <>
              <li aria-hidden>/</li>
              <li aria-current="page" className="text-text">
                {t.categories[query.category as CategoryKey]}
              </li>
            </>
          ) : null}
        </ol>
      </nav>

      <header className="flex flex-col gap-1">
        <h1 className="font-serif text-4xl leading-none tracking-tight sm:text-5xl">{title}</h1>
        <p className="text-sm text-muted tabular">{t.shop.count(formatCount(locale, data.total))}</p>
      </header>

      <CategoryStrip locale={locale} query={query} facets={facets} />

      <div className="flex flex-wrap items-center gap-2 border-y border-line py-3">
        <Suspense fallback={null}>
          <Drawer
            label={t.shop.filters}
            closeLabel={t.nav.close}
            trigger={
              <span className="flex items-center gap-2 text-sm font-medium">
                <FilterIcon className="size-[18px]" />
                {t.shop.filters}
                {chips.length ? <span className="bg-text px-1.5 text-[11px] text-on-text">{chips.length}</span> : null}
              </span>
            }
            triggerClassName="h-10 border border-line-strong px-3 lg:hidden"
          >
            {filterPanel}
          </Drawer>
        </Suspense>

        <ul className="flex flex-wrap items-center gap-2">
          {chips.map((chip) => (
            <li key={chip.href}>
              <Link
                href={chip.href}
                aria-label={t.shop.remove(chip.label)}
                className="flex h-8 items-center gap-2 bg-surface px-3 text-xs hover:bg-surface-2"
              >
                {chip.label} <span aria-hidden>✕</span>
              </Link>
            </li>
          ))}
          {chips.length > 1 ? (
            <li>
              <Link href={shopHref(locale, { sort: query.sort })} className="px-1 text-xs underline underline-offset-4">
                {t.shop.clearAll}
              </Link>
            </li>
          ) : null}
        </ul>

        <AutoSubmitForm action={`/${locale}/shop`} className="ml-auto flex items-center gap-2">
          <HiddenFields query={query} except={["sort", "page"]} />
          <label htmlFor="sort" className="text-xs text-muted">
            {t.shop.sortLabel}
          </label>
          <select
            id="sort"
            name="sort"
            defaultValue={query.sort}
            className="h-10 border border-line-strong bg-bg px-2 text-sm"
          >
            {SORTS.map((s) => (
              <option key={s} value={s}>
                {t.shop.sorts[s]}
              </option>
            ))}
          </select>
          <noscript>
            <button className="h-10 border border-line-strong px-3 text-sm">{t.shop.apply}</button>
          </noscript>
        </AutoSubmitForm>
      </div>

      <div className="grid gap-8 lg:grid-cols-[15rem_minmax(0,1fr)] lg:gap-10">
        <aside className="hidden lg:block" aria-label={t.shop.filters}>
          <div className="sticky top-28">{filterPanel}</div>
        </aside>

        <section aria-label={title}>
          {data.items.length === 0 ? (
            <div className="flex flex-col items-center gap-3 border border-dashed border-line-strong px-6 py-20 text-center">
              <p className="font-serif text-2xl">{chips.length ? t.shop.noMatch : t.shop.empty}</p>
              {chips.length ? (
                <>
                  <p className="text-sm text-muted">{t.shop.noMatchHint}</p>
                  <Link href={shopHref(locale)} className="mt-2 bg-text px-5 py-2.5 text-sm font-medium text-on-text">
                    {t.shop.clearAll}
                  </Link>
                </>
              ) : null}
            </div>
          ) : (
            <ul className="grid grid-cols-2 gap-x-3 gap-y-10 sm:grid-cols-3 sm:gap-x-4 xl:grid-cols-4">
              {data.items.map((product, i) => (
                <li key={product.id}>
                  <PriceCard product={product} priority={i < 4} />
                </li>
              ))}
            </ul>
          )}

          {lastPage > 1 ? <Pagination locale={locale} query={query} lastPage={lastPage} /> : null}
        </section>
      </div>
    </div>
  );
}

/** Category pills under the title: one tap to switch category, counts under the other filters. */
async function CategoryStrip({ locale, query, facets }: { locale: Locale; query: ShopQuery; facets: Facets }) {
  const t = await getDictionary();
  const counts = new Map(facets.categories.map((c) => [c.key, c.count]));
  const pill = (active: boolean) =>
    `flex h-9 shrink-0 items-center gap-1.5 whitespace-nowrap border px-3.5 text-[13px] ${
      active ? "border-text bg-text text-on-text" : "border-line-strong hover:border-text"
    }`;
  return (
    <nav aria-label={t.shop.category} className="rail -mx-4 flex gap-2 overflow-x-auto px-4 lg:hidden">
      <Link href={shopHref(locale, { ...query, category: undefined, page: 1 })} className={pill(!query.category)}>
        {t.nav.allProducts}
      </Link>
      {CATEGORIES.filter((key) => counts.get(key)).map((key) => (
        <Link
          key={key}
          href={shopHref(locale, { ...query, category: key, page: 1 })}
          aria-current={query.category === key ? "page" : undefined}
          className={pill(query.category === key)}
        >
          {t.categories[key]}
          <span className={query.category === key ? "opacity-70" : "text-muted"}>{counts.get(key)}</span>
        </Link>
      ))}
    </nav>
  );
}

/** Keeps the current filters in a form that changes only some of them. */
function HiddenFields({ query, except }: { query: ShopQuery; except: (keyof ShopQuery)[] }) {
  const skip = new Set(except);
  return (
    <>
      {query.q && !skip.has("q") ? <input type="hidden" name="q" value={query.q} /> : null}
      {query.category && !skip.has("category") ? (
        <input type="hidden" name="category" value={query.category} />
      ) : null}
      {!skip.has("brand") && query.brand?.map((b) => <input key={b} type="hidden" name="brand" value={b} />)}
      {query.min && !skip.has("min") ? <input type="hidden" name="min" value={query.min} /> : null}
      {query.max && !skip.has("max") ? <input type="hidden" name="max" value={query.max} /> : null}
      {query.sale && !skip.has("sale") ? <input type="hidden" name="sale" value="1" /> : null}
      {query.stock && !skip.has("stock") ? <input type="hidden" name="stock" value="1" /> : null}
      {query.sort && query.sort !== "recent" && !skip.has("sort") ? (
        <input type="hidden" name="sort" value={query.sort} />
      ) : null}
    </>
  );
}

async function FilterPanel({ locale, query, facets }: { locale: Locale; query: ShopQuery; facets: Facets }) {
  const t = await getDictionary();
  const counts = new Map(facets.categories.map((c) => [c.key, c.count]));
  const heading = "eyebrow mb-3 font-medium";
  const check = "size-4 accent-[var(--text)]";
  return (
    <div className="flex flex-col gap-8">
      <section>
        <h2 className={heading}>{t.shop.category}</h2>
        <ul className="flex flex-col gap-1.5 text-sm">
          <li>
            <Link
              href={shopHref(locale, { ...query, category: undefined, page: 1 })}
              className={!query.category ? "font-semibold" : "text-muted hover:text-text"}
            >
              {t.nav.allProducts}
            </Link>
          </li>
          {CATEGORIES.filter((key) => counts.get(key)).map((key) => (
            <li key={key}>
              <Link
                href={shopHref(locale, { ...query, category: key, page: 1 })}
                className={`flex justify-between gap-2 ${
                  query.category === key ? "font-semibold" : "text-muted hover:text-text"
                }`}
              >
                <span>{t.categories[key]}</span>
                <span className="tabular">{counts.get(key)}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <AutoSubmitForm action={`/${locale}/shop`} className="flex flex-col gap-8">
        <HiddenFields query={query} except={["brand", "min", "max", "sale", "stock", "page"]} />

        {facets.brands.length > 1 || query.brand?.length ? (
          <fieldset>
            <legend className={heading}>{t.shop.brand}</legend>
            <ul className="flex max-h-72 flex-col gap-2 overflow-y-auto text-sm">
              {facets.brands.map((b) => (
                <li key={b.slug}>
                  <label className="flex cursor-pointer items-center gap-2.5">
                    <input
                      type="checkbox"
                      name="brand"
                      value={b.slug}
                      defaultChecked={query.brand?.includes(b.slug)}
                      className={check}
                    />
                    <span className="flex-1">{b.name}</span>
                    <span className="text-muted tabular">{b.count}</span>
                  </label>
                </li>
              ))}
            </ul>
          </fieldset>
        ) : null}

        <fieldset>
          <legend className={heading}>{t.shop.price}</legend>
          <div className="flex items-end gap-2">
            <label className="flex flex-1 flex-col gap-1 text-xs text-muted">
              {t.shop.min}
              <input
                name="min"
                inputMode="numeric"
                pattern="[0-9]*"
                defaultValue={query.min}
                placeholder={facets.min_price_minor ? String(Math.floor(facets.min_price_minor / 100)) : "0"}
                className="h-10 w-full border border-line-strong bg-bg px-2 text-sm text-text"
              />
            </label>
            <label className="flex flex-1 flex-col gap-1 text-xs text-muted">
              {t.shop.max}
              <input
                name="max"
                inputMode="numeric"
                pattern="[0-9]*"
                defaultValue={query.max}
                placeholder={facets.max_price_minor ? String(Math.ceil(facets.max_price_minor / 100)) : ""}
                className="h-10 w-full border border-line-strong bg-bg px-2 text-sm text-text"
              />
            </label>
            <button className="h-10 border border-text px-3 text-xs font-medium hover:bg-text hover:text-on-text">
              {t.shop.apply}
            </button>
          </div>
        </fieldset>

        <fieldset>
          <legend className={heading}>{t.shop.availability}</legend>
          <div className="flex flex-col gap-2 text-sm">
            <label className="flex cursor-pointer items-center gap-2.5">
              <input type="checkbox" name="sale" value="1" defaultChecked={query.sale} className={check} />
              {t.shop.onSale}
            </label>
            <label className="flex cursor-pointer items-center gap-2.5">
              <input type="checkbox" name="stock" value="1" defaultChecked={query.stock} className={check} />
              {t.shop.inStock}
            </label>
          </div>
        </fieldset>
      </AutoSubmitForm>
    </div>
  );
}

async function Pagination({
  locale,
  query,
  lastPage,
}: {
  locale: Locale;
  query: ShopQuery & { page: number };
  lastPage: number;
}) {
  const t = await getDictionary();
  const current = query.page;
  // First, last, and two either side of the current page, with gaps marked.
  const pages = [...new Set([1, current - 2, current - 1, current, current + 1, current + 2, lastPage])]
    .filter((p) => p >= 1 && p <= lastPage)
    .sort((a, b) => a - b);
  const cell = "grid h-10 min-w-10 place-items-center px-2 text-sm tabular";
  return (
    <nav aria-label={t.shop.pages} className="mt-14 flex items-center justify-center gap-1">
      {current > 1 ? (
        <Link href={shopHref(locale, { ...query, page: current - 1 })} className={`${cell} hover:underline`}>
          ← <span className="sr-only sm:not-sr-only sm:ml-1">{t.shop.previous}</span>
        </Link>
      ) : null}
      {pages.map((p, i) => (
        <span key={p} className="flex items-center gap-1">
          {i > 0 && p - pages[i - 1] > 1 ? <span className="px-1 text-muted">…</span> : null}
          <Link
            href={shopHref(locale, { ...query, page: p })}
            aria-current={p === current ? "page" : undefined}
            aria-label={t.shop.page(p, lastPage)}
            className={`${cell} ${p === current ? "bg-text text-on-text" : "hover:bg-surface"}`}
          >
            {p}
          </Link>
        </span>
      ))}
      {current < lastPage ? (
        <Link href={shopHref(locale, { ...query, page: current + 1 })} className={`${cell} hover:underline`}>
          <span className="sr-only sm:not-sr-only sm:mr-1">{t.shop.next}</span> →
        </Link>
      ) : null}
    </nav>
  );
}

function ShopSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-busy="true">
      <div className="h-3 w-40 animate-pulse bg-surface" />
      <div className="h-12 w-72 animate-pulse bg-surface" />
      <div className="h-10 w-full animate-pulse bg-surface" />
      <div className="grid gap-10 lg:grid-cols-[15rem_minmax(0,1fr)]">
        <div className="hidden h-96 animate-pulse bg-surface lg:block" />
        <ul className="grid grid-cols-2 gap-x-3 gap-y-10 sm:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }, (_, i) => (
            <li key={i}>
              <CardSkeleton />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
