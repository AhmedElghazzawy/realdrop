import Form from "next/form";
import Link from "next/link";
import { Suspense } from "react";
import { getDictionary, getLocale } from "@/i18n";
import { CLOTHING, SHOES_ACCESSORIES } from "@/lib/categories";
import { dealsQuery, shopHref } from "@/lib/links";
import { ChevronDown, SearchIcon } from "./icons";
import { LanguageSwitch } from "./LanguageSwitch";
import { MobileMenu } from "./MobileMenu";
import { ThemeToggle } from "./ThemeToggle";

// Store header: thin announcement bar, then logo, category menu (a full-width panel on hover or
// keyboard focus, no JS), search, theme and language. Phones get the same links in a drawer.
export async function SiteHeader() {
  const [locale, t] = [await getLocale(), await getDictionary()];
  const link = "py-2 text-[13px] font-medium tracking-wide hover:text-muted";

  const clothingPanel = (
    <div className="grid grid-cols-[1fr_1fr_14rem] gap-10 py-8">
      <div>
        <p className="eyebrow mb-4 text-muted">{t.nav.clothing}</p>
        <ul className="grid grid-cols-2 gap-x-8 gap-y-2.5 text-sm">
          {CLOTHING.map((key) => (
            <li key={key}>
              <Link href={shopHref(locale, { category: key })} className="hover:underline">
                {t.categories[key]}
              </Link>
            </li>
          ))}
          <li className="col-span-2 mt-2">
            <Link href={shopHref(locale)} className="font-medium underline underline-offset-4">
              {t.nav.allProducts}
            </Link>
          </li>
        </ul>
      </div>
      <div>
        <p className="eyebrow mb-4 text-muted">{t.nav.shoesAccessories}</p>
        <ul className="flex flex-col gap-2.5 text-sm">
          {SHOES_ACCESSORIES.map((key) => (
            <li key={key}>
              <Link href={shopHref(locale, { category: key })} className="hover:underline">
                {t.categories[key]}
              </Link>
            </li>
          ))}
        </ul>
      </div>
      <Link
        href={shopHref(locale, dealsQuery)}
        className="flex flex-col justify-end gap-2 bg-surface p-5 hover:bg-surface-2"
      >
        <span className="eyebrow text-sale">{t.nav.deals}</span>
        <span className="font-serif text-2xl leading-tight">{t.home.dealsTitle}</span>
      </Link>
    </div>
  );

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-bg/95 backdrop-blur">
      <p className="hidden bg-text px-4 py-1.5 text-center text-[11px] tracking-wide text-on-text sm:block">
        {t.announcement}
      </p>
      <div className="mx-auto flex h-14 max-w-[90rem] items-center gap-2 px-4 lg:h-16 lg:gap-8 lg:px-8">
        <Suspense fallback={<div className="size-10 lg:hidden" />}>
          <MobileMenu labels={{ open: t.nav.menu, close: t.nav.close }}>
            <MobileLinks />
          </MobileMenu>
        </Suspense>

        <Link
          href={`/${locale}`}
          className="text-lg font-semibold tracking-[0.18em] lg:text-xl"
          aria-label="RealDrop"
        >
          REAL<span className="text-signal">DROP</span>
        </Link>

        <nav aria-label={t.nav.shop} className="hidden h-full items-stretch gap-7 lg:flex">
          <div className="group flex items-center">
            <Link href={shopHref(locale)} className={`${link} flex items-center gap-1`}>
              {t.nav.clothing} <ChevronDown className="size-3.5" />
            </Link>
            <div className="invisible absolute inset-x-0 top-full border-b border-line bg-bg opacity-0 shadow-sm transition-opacity duration-150 group-focus-within:visible group-focus-within:opacity-100 group-hover:visible group-hover:opacity-100">
              <div className="mx-auto max-w-[90rem] px-8">{clothingPanel}</div>
            </div>
          </div>
          <Link href={shopHref(locale, dealsQuery)} className={`${link} flex items-center text-sale`}>
            {t.nav.deals}
          </Link>
          <Link href={shopHref(locale)} className={`${link} flex items-center`}>
            {t.nav.newIn}
          </Link>
          <Link href={`/${locale}/brands`} className={`${link} flex items-center`}>
            {t.nav.brands}
          </Link>
        </nav>

        <div className="ml-auto flex items-center gap-1 lg:gap-3">
          <Form
            action={`/${locale}/shop`}
            role="search"
            className="hidden items-center border-b border-line-strong md:flex"
          >
            <label htmlFor="header-q" className="sr-only">
              {t.search.label}
            </label>
            <input
              id="header-q"
              name="q"
              type="search"
              placeholder={t.search.placeholder}
              className="h-9 w-44 bg-transparent text-sm outline-none placeholder:text-muted lg:w-56"
            />
            <button type="submit" aria-label={t.search.button} className="grid size-9 place-items-center">
              <SearchIcon className="size-[18px]" />
            </button>
          </Form>
          <Link
            href={`/${locale}/shop`}
            aria-label={t.nav.search}
            className="grid size-10 place-items-center md:hidden"
          >
            <SearchIcon />
          </Link>
          <ThemeToggle labels={t.nav.theme} />
          {/* useSearchParams in the switch needs a Suspense boundary under Cache Components. */}
          <Suspense fallback={null}>
            <LanguageSwitch current={locale} label={t.nav.language} />
          </Suspense>
        </div>
      </div>
    </header>
  );
}

async function MobileLinks() {
  const [locale, t] = [await getLocale(), await getDictionary()];
  const item = "block py-2.5 text-[15px]";
  return (
    <div className="flex flex-col gap-6">
      <Form action={`/${locale}/shop`} role="search" className="flex items-center border-b border-line-strong">
        <label htmlFor="menu-q" className="sr-only">
          {t.search.label}
        </label>
        <input
          id="menu-q"
          name="q"
          type="search"
          placeholder={t.search.placeholder}
          className="h-11 flex-1 bg-transparent text-base outline-none placeholder:text-muted"
        />
        <button type="submit" aria-label={t.search.button} className="grid size-11 place-items-center">
          <SearchIcon />
        </button>
      </Form>
      <div className="flex flex-col">
        <Link href={shopHref(locale, dealsQuery)} className={`${item} font-medium text-sale`}>
          {t.nav.deals}
        </Link>
        <Link href={shopHref(locale)} className={item}>
          {t.nav.newIn}
        </Link>
        <Link href={`/${locale}/brands`} className={item}>
          {t.nav.brands}
        </Link>
      </div>
      <div>
        <p className="eyebrow mb-1 text-muted">{t.nav.clothing}</p>
        <ul>
          {CLOTHING.map((key) => (
            <li key={key}>
              <Link href={shopHref(locale, { category: key })} className={item}>
                {t.categories[key]}
              </Link>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <p className="eyebrow mb-1 text-muted">{t.nav.shoesAccessories}</p>
        <ul>
          {SHOES_ACCESSORIES.map((key) => (
            <li key={key}>
              <Link href={shopHref(locale, { category: key })} className={item}>
                {t.categories[key]}
              </Link>
            </li>
          ))}
        </ul>
      </div>
      <Link href={`/${locale}/status`} className="text-sm text-muted">
        {t.nav.status}
      </Link>
    </div>
  );
}
