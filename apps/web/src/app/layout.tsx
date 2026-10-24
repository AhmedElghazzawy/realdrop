import type { Metadata } from "next";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import Link from "next/link";
import "./globals.css";

// latin-ext carries the Turkish letters (ğ ş ı İ). Checked: ığüşöçİĞÜŞÖÇ render in all three.
const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin", "latin-ext"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin", "latin-ext"] });
const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument-serif",
  subsets: ["latin", "latin-ext"],
  weight: "400",
});

export const metadata: Metadata = {
  title: "RealDrop",
  description: "Moda indirimlerinin gerçeği: gerçek fiyat geçmişi ve gerçek indirimler.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="tr"
      className={`${geistSans.variable} ${geistMono.variable} ${instrumentSerif.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="border-b border-line">
          <nav className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
            <Link href="/" className="font-serif text-2xl tracking-tight">
              Real<span className="text-signal">Drop</span>
            </Link>
            <div className="ml-auto flex gap-5 text-sm text-muted">
              <Link href="/" className="hover:text-text">
                Ürünler
              </Link>
              <Link href="/status" className="hover:text-text">
                Veri toplama
              </Link>
            </div>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>
        <footer className="border-t border-line px-4 py-4 text-center text-xs text-muted">
          Fiyatlar mağaza sitelerinden günlük olarak toplanır. Her iddia, gözlemlediğimiz fiyatlara
          dayanır.
        </footer>
      </body>
    </html>
  );
}
