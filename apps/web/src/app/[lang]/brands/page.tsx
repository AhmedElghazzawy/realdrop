import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { getDictionary, getLocale } from "@/i18n";
import { getFacets } from "@/lib/api";
import { formatCount } from "@/lib/format";
import { shopHref } from "@/lib/links";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getDictionary()).brandsPage.title };
}

export default async function BrandsPage() {
  const t = (await getDictionary()).brandsPage;
  return (
    <div className="mx-auto max-w-[90rem] px-4 pb-10 pt-10 lg:px-8">
      <header className="mb-10 flex flex-col gap-2 border-b border-line pb-8">
        <h1 className="font-serif text-5xl leading-none tracking-tight sm:text-6xl">{t.title}</h1>
        <p className="text-sm text-muted">{t.intro}</p>
      </header>
      <Suspense fallback={<div className="h-64 animate-pulse bg-surface" />}>
        <BrandList />
      </Suspense>
    </div>
  );
}

async function BrandList() {
  const [locale, t] = [await getLocale(), await getDictionary()];
  const { brands } = await getFacets({ audience: "men" });
  // Grouped by first letter, like a shop's brand index.
  const groups = new Map<string, typeof brands>();
  for (const brand of [...brands].sort((a, b) => a.name.localeCompare(b.name, locale))) {
    const letter = brand.name.charAt(0).toLocaleUpperCase(locale);
    groups.set(letter, [...(groups.get(letter) ?? []), brand]);
  }
  return (
    <div className="grid gap-x-10 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
      {[...groups].map(([letter, group]) => (
        <section key={letter}>
          <h2 className="mb-3 font-serif text-3xl">{letter}</h2>
          <ul className="flex flex-col gap-2">
            {group.map((b) => (
              <li key={b.slug}>
                <Link
                  href={shopHref(locale, { brand: [b.slug] })}
                  className="flex items-baseline justify-between gap-3 border-b border-line py-2 hover:border-text"
                >
                  <span className="text-sm font-medium uppercase tracking-[0.12em]">{b.name}</span>
                  <span className="text-xs text-muted tabular">{t.brandsPage.items(formatCount(locale, b.count))}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
