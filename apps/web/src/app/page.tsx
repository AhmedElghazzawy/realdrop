import Link from "next/link";
import { Suspense } from "react";
import { PriceCard } from "@/components/PriceCard";
import { getProducts, type SortOrder } from "@/lib/api";
import { formatCount } from "@/lib/format";

const SORTS: { value: SortOrder; label: string }[] = [
  { value: "recent", label: "En son görülen" },
  { value: "claimed_discount", label: "Mağaza indirimi (iddia)" },
  { value: "price_asc", label: "Fiyat: düşükten" },
  { value: "price_desc", label: "Fiyat: yüksekten" },
];
const PAGE_SIZE = 48;

type Search = { q?: string; sort?: string; page?: string };

function readSearch(raw: Record<string, string | string[] | undefined>): Required<Search> {
  const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";
  const sort = one(raw.sort);
  return {
    q: one(raw.q).slice(0, 100),
    sort: SORTS.some((s) => s.value === sort) ? sort : "recent",
    page: String(Math.max(1, Number.parseInt(one(raw.page), 10) || 1)),
  };
}

export default function Home(props: PageProps<"/">) {
  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-2">
        <h1 className="font-serif text-4xl leading-tight sm:text-5xl">
          İndirim gerçek mi? <span className="text-muted">Fiyat geçmişi söylesin.</span>
        </h1>
        <p className="max-w-2xl text-sm text-muted">
          Her gün mağazaların fiyatlarını kaydediyoruz. 14 günlük geçmiş birikince her ürün için
          &quot;gerçek indirim&quot; hesabı açılacak; o zamana kadar mağazanın iddiasını ve
          gözlemlediğimiz fiyatı yan yana gösteriyoruz.
        </p>
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
  const { q, sort, page } = readSearch(await searchParams);
  const pageNumber = Number(page);
  const data = await getProducts({
    q: q || undefined,
    sort: sort as SortOrder,
    limit: PAGE_SIZE,
    offset: (pageNumber - 1) * PAGE_SIZE,
  });
  const lastPage = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
  const link = (p: number) => `/?${new URLSearchParams({ q, sort, page: String(p) })}`;

  return (
    <div className="flex flex-col gap-4">
      <form className="flex flex-col gap-2 sm:flex-row" action="/" role="search">
        <label htmlFor="q" className="sr-only">
          Ürün ara
        </label>
        <input
          id="q"
          name="q"
          defaultValue={q}
          placeholder="Ürün ara: kaban, jean, gömlek…"
          className="h-11 w-full rounded-card sm:flex-1 border border-line bg-surface px-3 text-sm placeholder:text-muted"
        />
        <label htmlFor="sort" className="sr-only">
          Sıralama
        </label>
        <select
          id="sort"
          name="sort"
          defaultValue={sort}
          className="h-11 rounded-card border border-line bg-surface px-3 text-sm"
        >
          {SORTS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <button className="h-11 rounded-card bg-text px-5 text-sm font-medium text-bg">Ara</button>
      </form>

      <p className="font-mono text-xs text-muted tabular">
        {formatCount(data.total)} ürün{q ? ` · “${q}”` : ""}
      </p>

      {data.items.length === 0 ? (
        <div className="rounded-card border border-dashed border-line p-10 text-center text-sm text-muted">
          {q ? "Bu aramaya uyan ürün yok." : "Henüz ürün toplanmadı. İlk toplama gece 03:00'te."}
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
        <nav className="flex items-center justify-center gap-4 text-sm" aria-label="Sayfalar">
          {pageNumber > 1 ? <Link href={link(pageNumber - 1)}>← Önceki</Link> : null}
          <span className="font-mono text-muted tabular">
            {pageNumber} / {lastPage}
          </span>
          {pageNumber < lastPage ? <Link href={link(pageNumber + 1)}>Sonraki →</Link> : null}
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
