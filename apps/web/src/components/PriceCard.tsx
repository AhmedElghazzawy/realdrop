import Link from "next/link";
import { getDictionary, getLocale } from "@/i18n";
import type { ProductCard } from "@/lib/api";
import { claimedDiscount, formatMoney, formatPercent } from "@/lib/format";

// A product in a grid or rail: image first, then brand, name and price, like a shop's listing.
// A shop's claimed discount is shown the way shops show it (red price, struck old price), and the
// badge says it is the shop's claim; our own verdict needs 14 days of history (DESIGN_SYSTEM.md).
export async function PriceCard({ product, priority = false }: { product: ProductCard; priority?: boolean }) {
  const [locale, t] = [await getLocale(), await getDictionary()];
  const soldOut = product.sizes_in_stock === 0;
  const discount = claimedDiscount(product.price_minor, product.original_price_minor);
  return (
    <Link href={`/${locale}/products/${product.id}`} className="group flex flex-col gap-3">
      <div className="relative aspect-[3/4] overflow-hidden bg-surface">
        {product.image_url ? (
          // Hotlinked from the shop's CDN (PRODUCT.md); no copy is stored or optimised by us.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={product.image_url}
            alt={product.title}
            loading={priority ? "eager" : "lazy"}
            className={`h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-[1.03] ${
              soldOut ? "opacity-60" : ""
            }`}
          />
        ) : null}
        <div className="absolute left-0 top-0 flex flex-col items-start gap-1 p-2">
          {discount !== null && !soldOut ? (
            <span
              className="bg-sale px-1.5 py-0.5 text-[11px] font-semibold text-on-text tabular"
              title={t.claim.title}
            >
              {t.claim.shopSays(formatPercent(locale, discount))}
            </span>
          ) : null}
          {soldOut ? (
            <span className="bg-bg px-1.5 py-0.5 text-[11px] font-medium">{t.card.soldOut}</span>
          ) : null}
        </div>
      </div>
      <div className="flex flex-col gap-1 px-0.5">
        <p className="eyebrow font-medium">{product.brand_name}</p>
        <h3 className="line-clamp-2 text-[13px] leading-[18px] text-muted" lang="tr">
          {product.title}
        </h3>
        <p className="mt-0.5 flex flex-wrap items-baseline gap-x-2 text-sm tabular">
          <span className={discount !== null ? "font-semibold text-sale" : "font-semibold"}>
            {formatMoney(locale, product.price_minor, product.currency)}
          </span>
          {discount !== null && product.original_price_minor !== null ? (
            <span className="text-xs text-muted line-through" title={t.claim.title}>
              {formatMoney(locale, product.original_price_minor, product.currency)}
            </span>
          ) : null}
        </p>
        {!soldOut ? (
          <p className="text-[11px] text-muted">
            {t.card.sizes(product.sizes_in_stock, product.sizes_total)}
          </p>
        ) : null}
      </div>
    </Link>
  );
}

export function CardSkeleton() {
  return (
    <div className="flex flex-col gap-3" aria-hidden>
      <div className="aspect-[3/4] animate-pulse bg-surface" />
      <div className="h-3 w-1/3 animate-pulse bg-surface" />
      <div className="h-3 w-4/5 animate-pulse bg-surface" />
      <div className="h-3 w-1/4 animate-pulse bg-surface" />
    </div>
  );
}
