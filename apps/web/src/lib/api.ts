// Typed client for the RealDrop API (apps/api, schemas/catalog.py). Server-side only: pages fetch
// in Server Components, so the API address never reaches the browser.

const API_URL = process.env.API_URL ?? "http://localhost:8010";

export type RunStatus = "running" | "succeeded" | "partial" | "failed";
export type SortOrder = "recent" | "price_asc" | "price_desc" | "claimed_discount";

export interface BrandStats {
  slug: string;
  name: string;
  products: number;
  variants: number;
  observations: number;
  tracking_since: string | null;
}

export interface Run {
  id: string;
  brand_slug: string;
  started_at: string;
  finished_at: string | null;
  status: RunStatus;
  items_seen: number;
  items_failed: number;
  notes: string | null;
}

export interface Stats {
  brands: BrandStats[];
  runs: Run[];
}

export interface ProductCard {
  id: string;
  brand_slug: string;
  brand_name: string;
  title: string;
  url: string;
  image_url: string | null;
  category: string | null; // ours: lib/categories.ts
  category_raw: string | null; // the shop's own wording
  price_minor: number;
  original_price_minor: number | null;
  currency: string;
  sizes_in_stock: number;
  sizes_total: number;
  first_seen_at: string;
  observed_at: string;
}

export interface ProductList {
  items: ProductCard[];
  total: number;
}

export interface PricePoint {
  day: string;
  price_minor: number;
  original_price_minor: number | null;
}

export interface ProductDetail extends ProductCard {
  image_urls: string[];
  variants: {
    size_label: string | null;
    in_stock: boolean;
    price_minor: number;
    original_price_minor: number | null;
  }[];
  history: PricePoint[];
}

export class NotFoundError extends Error {}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (response.status === 404) throw new NotFoundError(path);
  if (!response.ok) throw new Error(`API ${response.status} for ${path}`);
  return (await response.json()) as T;
}

export function getStats(): Promise<Stats> {
  return get("/stats");
}

export type Audience = "men" | "women";

export interface Filters {
  q?: string;
  brands?: string[];
  category?: string;
  audience?: Audience;
  minPrice?: number; // kurus
  maxPrice?: number; // kurus
  onSale?: boolean;
  inStock?: boolean;
}

export interface Facets {
  total: number;
  categories: { key: string; count: number; image_url: string | null }[];
  brands: { slug: string; name: string; count: number }[];
  min_price_minor: number | null;
  max_price_minor: number | null;
}

function filterParams(filters: Filters): URLSearchParams {
  const search = new URLSearchParams();
  if (filters.q) search.set("q", filters.q);
  for (const brand of filters.brands ?? []) search.append("brand", brand);
  if (filters.category) search.set("category", filters.category);
  if (filters.audience) search.set("audience", filters.audience);
  if (filters.minPrice !== undefined) search.set("min_price", String(filters.minPrice));
  if (filters.maxPrice !== undefined) search.set("max_price", String(filters.maxPrice));
  if (filters.onSale) search.set("on_sale", "true");
  if (filters.inStock) search.set("in_stock", "true");
  return search;
}

export function getProducts(
  filters: Filters,
  page: { sort?: SortOrder; limit?: number; offset?: number } = {},
): Promise<ProductList> {
  const search = filterParams(filters);
  if (page.sort) search.set("sort", page.sort);
  search.set("limit", String(page.limit ?? 48));
  search.set("offset", String(page.offset ?? 0));
  return get(`/products?${search}`);
}

export function getFacets(filters: Filters): Promise<Facets> {
  return get(`/products/facets?${filterParams(filters)}`);
}

export function getProduct(id: string): Promise<ProductDetail> {
  return get(`/products/${encodeURIComponent(id)}`);
}
