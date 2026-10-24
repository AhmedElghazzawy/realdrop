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
  category: string | null;
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

export function getProducts(params: {
  q?: string;
  sort?: SortOrder;
  limit?: number;
  offset?: number;
}): Promise<ProductList> {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.sort) search.set("sort", params.sort);
  search.set("limit", String(params.limit ?? 48));
  search.set("offset", String(params.offset ?? 0));
  return get(`/products?${search}`);
}

export function getProduct(id: string): Promise<ProductDetail> {
  return get(`/products/${encodeURIComponent(id)}`);
}
