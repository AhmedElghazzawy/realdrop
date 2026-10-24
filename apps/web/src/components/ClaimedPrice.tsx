import { getDictionary, getLocale } from "@/i18n";
import { claimedDiscount, formatMoney, formatPercent } from "@/lib/format";

// The shop's claimed old price and claimed discount, shown as a claim, never as a fact.
export async function ClaimedPrice({
  price,
  claimed,
  currency,
}: {
  price: number;
  claimed: number | null;
  currency: string;
}) {
  const discount = claimedDiscount(price, claimed);
  if (claimed === null || discount === null) return null;
  const [locale, t] = [await getLocale(), await getDictionary()];
  return (
    <span className="text-xs text-muted">
      <span className="line-through">{formatMoney(locale, claimed, currency)}</span>{" "}
      <span title={t.claim.title}>{t.claim.shopSays(formatPercent(locale, discount))}</span>
    </span>
  );
}
