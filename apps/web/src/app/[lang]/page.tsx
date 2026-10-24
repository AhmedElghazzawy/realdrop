import Link from "next/link";
import { Suspense } from "react";
import { PriceCard } from "@/components/PriceCard";
import { getDictionary, getLocale } from "@/i18n";
import { getProducts, type SortOrder } from "@/lib/api";
import { formatCount } from "@/lib/format";

const SORTS: SortOrder[] = ["recent", "claimed_discount", "price_asc", "price_desc"];
const PAGE_SIZE = 48;
// Men only for now (owner decision, 25 Oct 2026); a men/women choice comes later.
const AUDIENCE = "men";

type Search = { q?: string; sort?: string; page?: string };

function readSearch(raw: Record<string, string | string[] | undefined>): Required<Search> {
  const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";
  const sort = one(raw.sort);
  return {
    q: one(raw.q).slice(0, 100),
    sort: SORTS.includes(sort as SortOrder) ? sort : "recent",
    page: String(Math.max(1, Number.parseInt(one(raw.page), 10) || 1)),
  };
}

export default async function Home(props: PageProps<"/[lang]">) {
  const t = (await getDictionary()).home;
  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-2">
        <h1 className="font-serif text-4xl leading-tight sm:text-5xl">
          {t.title} <span className="text-muted">{t.titleAccent}</span>
        </h1>
        <p className="max-w-2xl text-sm text-muted">{t.intro}</p>
      </section>
      <Suspense fallback={<GridSkeleton />}>
        <Results searchParams={props.searchParams} />
      </Suspense>
    </div>
  );
}

async function Results({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [locale, t] = [await getLocale(), (await getDictionary()).home];
  const { q, sort, page } = readSearch(await searchParams);
  const pageNumber = Number(page);
  const data = await getProducts({
    q: q || undefined,
    audience: AUDIENCE,
    sort: sort as SortOrder,
    limit: PAGE_SIZE,
    offset: (pageNumber - 1) * PAGE_SIZE,
  });
  const lastPage = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
  const link = (p: number) => `/${locale}?${new URLSearchParams({ q, sort, page: String(p) })}`;

  return (
    <div className="flex flex-col gap-4">
      <form className="flex flex-col gap-2 sm:flex-row" action={`/${locale}`} role="search">
        <label htmlFor="q" className="sr-only">
          {t.searchLabel}
        </label>
        <input
          id="q"
          name="q"
          defaultValue={q}
          placeholder={t.searchPlaceholder}
          className="h-11 w-full rounded-card sm:flex-1 border border-line bg-surface px-3 text-sm placeholder:text-muted"
        />
        <label htmlFor="sort" className="sr-only">
          {t.sortLabel}
        </label>
        <select
          id="sort"
          name="sort"
          defaultValue={sort}
          className="h-11 rounded-card border border-line bg-surface px-3 text-sm"
        >
          {SORTS.map((s) => (
            <option key={s} value={s}>
              {t.sorts[s]}
            </option>
          ))}
        </select>
        <button className="h-11 rounded-card bg-text px-5 text-sm font-medium text-bg">
          {t.searchButton}
        </button>
      </form>

      <p className="font-mono text-xs text-muted tabular">
        {t.audienceNote} {t.count(formatCount(locale, data.total))}
        {q ? ` · “${q}”` : ""}
      </p>

      {data.items.length === 0 ? (
        <div className="rounded-card border border-dashed border-line p-10 text-center text-sm text-muted">
          {q ? t.noMatch : t.empty}
        </div>
      ) : (
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {data.items.map((product) => (
            <li key={product.id}>
              <PriceCard product={product} />
            </li>
          ))}
        </ul>
      )}

      {lastPage > 1 ? (
        <nav className="flex items-center justify-center gap-4 text-sm" aria-label={t.pages}>
          {pageNumber > 1 ? <Link href={link(pageNumber - 1)}>{t.previous}</Link> : null}
          <span className="font-mono text-muted tabular">
            {pageNumber} / {lastPage}
          </span>
          {pageNumber < lastPage ? <Link href={link(pageNumber + 1)}>{t.next}</Link> : null}
        </nav>
      ) : null}
    </div>
  );
}

function GridSkeleton() {
  return (
    <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4" aria-busy="true">
      {Array.from({ length: 8 }, (_, i) => (
        <li key={i} className="aspect-[3/5] animate-pulse rounded-card bg-surface" />
      ))}
    </ul>
  );
}
