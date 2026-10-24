import { claimedDiscount, formatMoney, formatPercent } from "@/lib/format";

// The shop's claimed old price and claimed discount, shown as a claim, never as a fact.
export function ClaimedPrice({
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
  return (
    <span className="text-xs text-muted">
      <span className="line-through">{formatMoney(claimed, currency)}</span>{" "}
      <span title="Mağazanın iddia ettiği indirim">mağaza: −{formatPercent(discount)}</span>
    </span>
  );
}
