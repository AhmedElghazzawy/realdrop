// Our categories, mirroring apps/api pipeline/categorize.py CATEGORIES (same keys, menu order).
// Labels are in i18n/en.ts and tr.ts.

export const CLOTHING = [
  "tshirts",
  "shirts",
  "knitwear",
  "sweatshirts",
  "jackets",
  "suits",
  "trousers",
  "jeans",
  "shorts",
  "tracksuits",
  "underwear",
  "swimwear",
] as const;

export const SHOES_ACCESSORIES = ["shoes", "bags", "accessories"] as const;

export const CATEGORIES = [...CLOTHING, ...SHOES_ACCESSORIES] as const;
export type CategoryKey = (typeof CATEGORIES)[number];

export function isCategory(value: string): value is CategoryKey {
  return (CATEGORIES as readonly string[]).includes(value);
}
