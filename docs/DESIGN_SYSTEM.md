# Design system

## Direction

**Light editorial store, with a dark mode.** (Redesign, 27 Oct 2026, owner decision.) The site looks
and is organised like the big international fashion shops (COS, Zara, SSENSE, Mr Porter): white
pages, large product photography, a thin black type system, a mega menu by category, and a shop
listing with filters. Price history is still the reason the site exists, so the product page gives
the chart its own full-width section and every discount is labelled as the shop's claim until our
history can judge it.

Principles: truth first (never decorate a number), organised before clever (every product sits in
one of our 15 categories), photography carries the colour, red is only for sale prices, square
corners, and motion only for hover feedback.

## Theme

Light by default. Dark follows the device setting, and the header switch (`ThemeToggle`) overrides it
and is remembered in `localStorage`. An inline script in `layout.tsx` sets `data-theme` on `<html>`
before the first paint, so there is no flash. Dark is its own set of values, not an inverted light.

## Tokens

CSS variables in `apps/web/src/app/globals.css`, mapped to Tailwind with `@theme inline`
(`bg-bg`, `text-muted`, `border-line`, `bg-sale`, …). No hex values in components.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#ffffff` | `#0c0c0d` | page |
| `--surface` | `#f4f4f2` | `#161618` | image wells, inputs, skeletons, footer |
| `--surface-2` | `#ebebe8` | `#1f1f22` | hover |
| `--line` / `--line-strong` | `#e3e3df` / `#c9c9c4` | `#2a2a2e` / `#3d3d42` | dividers / outlined controls |
| `--text` | `#111111` | `#f2f2ee` | text, filled buttons |
| `--on-text` | `#ffffff` | `#0c0c0d` | text on a `--text` or `--sale` fill |
| `--muted` | `#5f5f5c` | `#a1a1a6` | secondary text (AA on bg and surface) |
| `--sale` | `#c8102e` | `#ff6b6b` | the shop's sale price and its −% badge (a claim) |
| `--signal` | `#0f7a3d` | `#c6ff3d` | REAL drop only (verified by our history); logo accent |
| `--warn` | `#c2410c` | `#ff7a4d` | inflated claim; the note beside a claimed discount |
| `--info` | `#1d4ed8` | `#8ab4ff` | focus ring, prose links |
| `--series-1` / `--series-2` | `#2a78d6` / `#eb6834` | `#3987e5` / `#d95926` | chart: price paid / shop's claimed old price |

The chart series come from the dataviz reference palette and pass its validator in both modes
(lightness band, chroma, colour-blind separation, contrast): re-run it if you change them.
Corners are square (`--radius: 2px` at most). Colour is never the only carrier of meaning.

## Type

- **Display:** Instrument Serif, large and tight (`tracking-tight`, leading ~0.95-1.1), for page
  titles, section titles and product names only.
- **UI and numbers:** Geist, with `.tabular` (tabular figures) on every price, count and date column.
- **Eyebrows:** `.eyebrow` = 11 px, uppercase, 0.08em tracking (brand names, filter group titles).
- All three ship `latin-ext`; `ığüşöçİĞÜŞÖÇ` checked in each.

## Layout and navigation

- Page width `max-w-[90rem]`, gutter 16 px (phones) / 32 px (desktop). Pages pad themselves.
- **Header** (sticky): black announcement bar; logo; *Clothing* mega panel (clothing / shoes and
  accessories columns + a deals promo); *Deals* in `--sale`; *New in*; *Brands*; search; theme
  switch; EN / TR. Phones get a side drawer (`Drawer`, a `<dialog>`) and a search icon.
- **Categories** are ours (`products.category`, keyword rules in `pipeline/categorize.py`), listed in
  `lib/categories.ts`. The shop's own category is kept and shown on the product page.
- **Shop listing** (`/[lang]/shop`): all filters live in the URL (`q`, `category`, `brand` (repeatable),
  `min`/`max` in lira, `sale=1`, `stock=1`, `sort`, `page`), so every view is linkable. Desktop: a
  sidebar with category counts, brand checkboxes (2+ brands), price, availability. Phones: a category
  pill rail and a Filters drawer. Removable chips and "Clear all" above a 2/3/4-column grid,
  48 per page, numbered pagination. Counts come from `/products/facets`, each dimension counted
  without its own filter.
- **Rails** (home and product page): horizontal scroll-snap rows that bleed to the screen edge on
  phones and show 5 cards on desktop.

## Number and date formatting

Always through `lib/format.ts`, which uses `Intl` in the page language: `en-GB` (`₺1,299.90`, `24%`,
`24 Nov 2026`, the default) or `tr-TR` (`₺1.299,90`, `%24`, `24 Kas 2026`). Never concatenate strings by
hand; UI text lives in `src/i18n/en.ts` and `tr.ts`. Shop text (titles, categories) stays Turkish and
gets `lang="tr"`. Prices in the API are kurus; convert at the edge.

## Core components

| Component | Notes |
|---|---|
| `PriceCard` | 3:4 image, no box; −% badge (`--sale`, shop's claim) or "Sold out"; brand eyebrow; 2-line title; price in `--sale` when discounted with the claimed price struck; sizes in stock. `CardSkeleton` for loading |
| `PriceChart` | server half formats labels; `PriceChartPlot` (client) draws step lines in real pixels: price paid `--series-1` solid, claimed old price `--series-2` dashed; legend always; crosshair + tooltip on hover and arrow keys; latest values marked; "Show as table" view. Later: 30/90-day toggle, median reference line |
| `SiteHeader` / `SiteFooter` / `Drawer` | see Layout and navigation |
| `AutoSubmitForm` | GET form that applies itself when a checkbox, radio or select changes |
| `ThemeToggle` | reads the theme with `useSyncExternalStore` (it lives on `<html>`, outside React) |
| `RealDiscountBadge` | Phase 4+; states below |
| `SizePicker` | shows stock per size; selecting sets the alert target size |
| `AlertSheet` | bottom sheet on mobile: target price or "any real drop of N%", channel picker |
| `AssistantPanel` | streaming answer, tool-call chips ("checked 30-day history"), product cards inline |
| `TastePanel` | what we learned, in plain words, with reset and delete |

### RealDiscountBadge states

| State | Look | Text (tr) |
|---|---|---|
| `real_drop` | `--signal` outline + arrow icon | "GERÇEK İNDİRİM %24" |
| `claim_inflated` (with real_drop) | `--warn` strike on the claim, shown beside | "Mağaza %50 diyor, gerçek %12" |
| `claim_inflated` (no real drop) | `--warn` | "Şişirilmiş indirim: gerçek %4" |
| `normal` / `small_drop` | muted | "Fiyat normal" / "Küçük düşüş %6" |
| `insufficient_history` | muted dotted | "Takip: 12 Kas'tan beri" |
| `price_up` | muted up arrow | "Fiyat arttı" |

## States, accessibility, motion

- Every component implements loading (skeleton), empty, error and populated states.
- Keyboard navigable, visible focus ring, 44 px minimum touch targets, labelled inputs, alt text.
- `prefers-reduced-motion` respected: no ticking animations, no parallax.
- Motion: 150-250 ms ease-out; price changes tick once; list items fade/slide in with a short stagger.
- Layout: 375 px is the design baseline; check 375, 768 and 1280 for every screen, light and dark.
  Headless Chrome on macOS will not go below 500 px wide: load the page in a 375 px iframe instead.

## Pages

Built: Home (hero + search, category tiles, biggest-discount and just-checked rails, brands, how it
works), Shop (listing with filters; Deals is the shop with `sale=1&stock=1&sort=claimed_discount`),
Product (gallery, sticky info panel, price history, more-in-category and more-from-brand rails),
Brands (A–Z), Data collection. Later: Black Friday (real deals vs inflated claims), Alerts,
Assistant, Profile and Privacy.
