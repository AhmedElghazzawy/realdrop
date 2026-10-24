// English is the default language (owner decision, 25 Oct 2026). Every other dictionary must have
// exactly this shape: `Dictionary` is derived from this file and the compiler checks the rest.
// Product titles and categories come from the shops and are not translated (yet).

export const en = {
  meta: {
    description: "The truth about fashion discounts: real price history and real price drops.",
  },
  nav: { products: "Products", status: "Data collection", language: "Language" },
  footer: "Prices are collected daily from the shops' own websites. Every claim is based on prices we observed.",
  home: {
    title: "Is that discount real?",
    titleAccent: "Let the price history tell.",
    intro:
      "We record shop prices every day. Once 14 days of history build up, each product gets a real-discount check; until then we show the shop's claim next to the price we actually observed.",
    audienceNote: "Showing men's clothing.",
    searchLabel: "Search products",
    searchPlaceholder: "Search: coat, jeans, shirt…",
    sortLabel: "Sort by",
    sorts: {
      recent: "Recently seen",
      claimed_discount: "Shop's claimed discount",
      price_asc: "Price: low to high",
      price_desc: "Price: high to low",
    },
    searchButton: "Search",
    count: (n: string) => `${n} products`,
    noMatch: "No products match this search.",
    empty: "No products collected yet. The next collection runs at 03:00 Turkey time.",
    previous: "← Previous",
    next: "Next →",
    pages: "Pages",
  },
  card: {
    soldOut: "Sold out",
    sizes: (inStock: number, total: number) => `${inStock}/${total} sizes`,
  },
  claim: {
    shopSays: (pct: string) => `shop says −${pct}`,
    title: "The discount the shop claims",
  },
  tracking: (date: string) => `Tracking since ${date}`,
  product: {
    back: "← Products",
    lastChecked: (time: string) => `Last checked: ${time}`,
    history: "Price history",
    notEnoughHistory: (days: number) =>
      `${days} ${days === 1 ? "day" : "days"} of data so far. A real-discount verdict needs at least 14 days; until then we make no discount claims.`,
    sizes: "Sizes",
    inStock: "In stock",
    soldOut: "Sold out",
    viewAt: (brand: string) => `View at ${brand} ↗`,
  },
  chart: {
    noData: "No confirmed prices yet.",
    paid: "Price paid (lowest of the day)",
    claimed: "Shop's claimed \"old price\"",
    claimedPoint: (day: string, price: string) => `${day}: shop claims ${price}`,
    aria: (days: number, last: string) => `Price history, ${days} days. Latest price ${last}.`,
  },
  status: {
    title: "Data collection",
    intro: "The catalog is collected in two halves every day, at 03:00 and 15:00 Turkey time.",
    products: (brand: string) => `${brand} · products`,
    variants: "Sizes (variants)",
    observations: "Price observations",
    since: "Tracking since",
    columns: {
      started: "Started",
      brand: "Brand",
      status: "Status",
      products: "Products",
      failed: "Failed",
      duration: "Duration",
      notes: "Notes",
    },
    noRuns: "No collection runs yet.",
    states: { succeeded: "succeeded", partial: "partial", failed: "failed", running: "running" },
    running: "running",
    minutes: (m: number) => `${m} min`,
    hours: (h: number, m: number) => `${h} h ${m} min`,
  },
  error: {
    title: "We couldn't reach the data.",
    body: "The API may be down. Please try again in a moment.",
    retry: "Try again",
  },
};

export type Dictionary = typeof en;
