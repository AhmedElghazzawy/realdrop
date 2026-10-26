import Link from "next/link";
import { getDictionary, getLocale } from "@/i18n";
import { CATEGORIES } from "@/lib/categories";
import { dealsQuery, shopHref } from "@/lib/links";

export async function SiteFooter() {
  const [locale, t] = [await getLocale(), await getDictionary()];
  return (
    <footer className="mt-20 border-t border-line bg-surface">
      <div className="mx-auto grid max-w-[90rem] gap-10 px-4 py-12 sm:grid-cols-2 lg:grid-cols-[2fr_3fr_1fr] lg:px-8">
        <div className="flex flex-col gap-3">
          <p className="text-lg font-semibold tracking-[0.18em]">
            REAL<span className="text-signal">DROP</span>
          </p>
          <p className="max-w-sm text-sm leading-6 text-muted">{t.footer.note}</p>
        </div>
        <div>
          <p className="eyebrow mb-3 text-muted">{t.footer.shop}</p>
          <ul className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
            {CATEGORIES.map((key) => (
              <li key={key}>
                <Link href={shopHref(locale, { category: key })} className="hover:underline">
                  {t.categories[key]}
                </Link>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="eyebrow mb-3 text-muted">{t.footer.about}</p>
          <ul className="flex flex-col gap-2 text-sm">
            <li>
              <Link href={shopHref(locale, dealsQuery)} className="hover:underline">
                {t.nav.deals}
              </Link>
            </li>
            <li>
              <Link href={`/${locale}/brands`} className="hover:underline">
                {t.nav.brands}
              </Link>
            </li>
            <li>
              <Link href={`/${locale}#how`} className="hover:underline">
                {t.nav.howItWorks}
              </Link>
            </li>
            <li>
              <Link href={`/${locale}/status`} className="hover:underline">
                {t.nav.status}
              </Link>
            </li>
          </ul>
        </div>
      </div>
    </footer>
  );
}
