import Link from "next/link";
import type { ProductCard } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { ClaimedPrice } from "./ClaimedPrice";
import { TrackingBadge } from "./TrackingBadge";

export function PriceCard({ product }: { product: ProductCard }) {
  const soldOut = product.sizes_in_stock === 0;
  return (
    <Link
      href={`/products/${product.id}`}
      className="group flex flex-col overflow-hidden rounded-card border border-line bg-surface transition-colors hover:bg-surface-2"
    >
      <div className="relative aspect-[3/4] bg-surface-2">
        {product.image_url ? (
          // Hotlinked from the shop's CDN (PRODUCT.md); no copy is stored or optimised by us.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={product.image_url}
            alt={product.title}
            loading="lazy"
            className="h-full w-full object-cover"
          />
        ) : null}
        {soldOut ? (
          <span className="absolute left-2 top-2 rounded bg-bg/80 px-1.5 py-0.5 text-[11px]">
            Tükendi
          </span>
        ) : null}
      </div>
      <div className="flex flex-1 flex-col gap-1.5 p-3">
        <p className="text-[11px] uppercase tracking-wider text-muted">{product.brand_name}</p>
        <h2 className="line-clamp-2 text-sm leading-5">{product.title}</h2>
        <div className="mt-auto flex flex-wrap items-baseline gap-x-2">
          <span className="font-mono text-base tabular">
            {formatMoney(product.price_minor, product.currency)}
          </span>
          <ClaimedPrice
            price={product.price_minor}
            claimed={product.original_price_minor}
            currency={product.currency}
          />
        </div>
        <div className="flex items-center justify-between gap-2">
          <TrackingBadge since={product.first_seen_at} />
          <span className="font-mono text-[11px] text-muted tabular">
            {product.sizes_in_stock}/{product.sizes_total} beden
          </span>
        </div>
      </div>
    </Link>
  );
}
