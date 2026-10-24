import type { Metadata } from "next";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import Link from "next/link";
import { Suspense } from "react";
import { LanguageSwitch } from "@/components/LanguageSwitch";
import { getDictionary, getLocale } from "@/i18n";
import { LOCALES } from "@/i18n/config";
import "../globals.css";

// latin-ext carries the Turkish letters (ğ ş ı İ). Checked: ığüşöçİĞÜŞÖÇ render in all three.
const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin", "latin-ext"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin", "latin-ext"] });
const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument-serif",
  subsets: ["latin", "latin-ext"],
  weight: "400",
});

export function generateStaticParams() {
  return LOCALES.map((lang) => ({ lang }));
}

export async function generateMetadata(): Promise<Metadata> {
  const t = await getDictionary();
  return { title: "RealDrop", description: t.meta.description };
}

export default async function RootLayout({ children }: LayoutProps<"/[lang]">) {
  const [locale, t] = [await getLocale(), await getDictionary()];
  return (
    <html
      lang={locale}
      className={`${geistSans.variable} ${geistMono.variable} ${instrumentSerif.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="border-b border-line">
          <nav className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
            <Link href={`/${locale}`} className="font-serif text-2xl tracking-tight">
              Real<span className="text-signal">Drop</span>
            </Link>
            <div className="ml-auto flex items-center gap-5 text-sm text-muted">
              <Link href={`/${locale}`} className="hover:text-text">
                {t.nav.products}
              </Link>
              <Link href={`/${locale}/status`} className="hover:text-text">
                {t.nav.status}
              </Link>
              {/* useSearchParams in the switch needs a Suspense boundary under Cache Components. */}
              <Suspense fallback={null}>
                <LanguageSwitch current={locale} label={t.nav.language} />
              </Suspense>
            </div>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>
        <footer className="border-t border-line px-4 py-4 text-center text-xs text-muted">
          {t.footer}
        </footer>
      </body>
    </html>
  );
}
