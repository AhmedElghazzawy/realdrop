// URLs for the shop pages, so every menu, chip and card links the same way.

import type { Locale } from "@/i18n/config";

export type ShopQuery = {
  q?: string;
  category?: string;
  brand?: string[];
  min?: string;
  max?: string;
  sale?: boolean;
  stock?: boolean;
  sort?: string;
  page?: number;
};

export function shopHref(locale: Locale, query: ShopQuery = {}): string {
  const search = new URLSearchParams();
  if (query.q) search.set("q", query.q);
  if (query.category) search.set("category", query.category);
  for (const brand of query.brand ?? []) search.append("brand", brand);
  if (query.min) search.set("min", query.min);
  if (query.max) search.set("max", query.max);
  if (query.sale) search.set("sale", "1");
  if (query.stock) search.set("stock", "1");
  if (query.sort && query.sort !== "recent") search.set("sort", query.sort);
  if (query.page && query.page > 1) search.set("page", String(query.page));
  const text = search.toString();
  return `/${locale}/shop${text ? `?${text}` : ""}`;
}

export const dealsQuery: ShopQuery = { sale: true, stock: true, sort: "claimed_discount" };
