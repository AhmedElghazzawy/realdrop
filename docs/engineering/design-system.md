# Design system

## Direction

**Warm, soft and modern: an AI style advisor, not a discount table.** (Redesign, 14 Nov 2026, after
the owner rejected both the white editorial store and a dark "editorial × data" concept.) Warm
off-white pages, one deep-green accent, rounded photo cards, pill controls, and a characterful
grotesque for headlines. The home page leads with styles (pick a style, we find the pieces); price
honesty stays as a feature: every discount is labelled as the shop's claim until our history can
judge it.

Principles: truth first (never decorate a number), photography carries the colour, one accent
(green = the advisor and real drops), red only for sale prices, soft corners, motion only for hover
feedback.

## Theme

Light by default. Dark follows the device setting, and the header switch (`ThemeToggle`) overrides it
and is remembered in `localStorage`. An inline script in `layout.tsx` sets `data-theme` on `<html>`
before the first paint, so there is no flash. Dark is its own set of values, not an inverted light.

## Tokens

CSS variables in `apps/web/src/app/globals.css`, mapped to Tailwind with `@theme inline`
(`bg-bg`, `text-muted`, `border-line`, `bg-sale`, …). No hex values in components.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#f6f3ee` | `#12110f` | page (warm off-white / warm near-black) |
| `--surface` | `#ece7df` | `#1c1a17` | image wells, inputs, skeletons, cards |
| `--surface-2` | `#e3ddd3` | `#25221e` | hover |
| `--line` / `--line-strong` | `#e2dcd2` / `#c9c1b5` | `#2c2925` / `#403b35` | dividers / outlined controls |
| `--text` | `#1b1814` | `#f2eee7` | text, filled buttons |
| `--on-text` | `#f6f3ee` | `#12110f` | text on a `--text` or `--signal` fill |
| `--muted` | `#6a635a` | `#a69f94` | secondary text (AA on bg and surface) |
| `--sale` | `#b3261e` | `#ff7b6e` | the shop's sale price and its −% badge (a claim) |
| `--signal` | `#1f6b4a` | `#7fd6a4` | the one accent: advisor voice, REAL drop, logo |
| `--warn` | `#b4501a` | `#ff9466` | inflated claim; the note beside a claimed discount |
| `--info` | `#2b59c3` | `#8eb0ff` | focus ring, prose links |
| `--series-1` / `--series-2` | `#2a78d6` / `#eb6834` | `#3987e5` / `#d95926` | chart: price paid / shop's claimed old price |

The chart series come from the dataviz reference palette and pass its validator in both modes
(lightness band, chroma, colour-blind separation, contrast): re-run it if you change them.
Cards and photos use `rounded-card` (`--radius: 14px`); buttons, chips and search are pills. Colour is never the only carrier of meaning.

## Type

- **Display:** Bricolage Grotesque (`font-display font-semibold`, `tracking-tight`/`tighter`,
  leading ~0.95-1.1), for page titles, section titles and product names only.
- **UI and numbers:** Geist, with `.tabular` (tabular figures) on every price, count and date column.
- **Eyebrows:** `.eyebrow` = 11 px, uppercase, 0.08em tracking (brand names, filter group titles).
- All fonts ship `latin-ext`; `ığüşöçİĞÜŞÖÇ` checked in each.

## Layout and navigation

- Page width `max-w-[90rem]`, gutter 16 px (phones) / 32 px (desktop). Pages pad themselves.
- **Header** (sticky): green announcement bar; lowercase `realdrop` logo; *Clothing* mega panel (clothing / shoes and
  accessories columns + a deals promo); *Deals* in `--sale`; *New in*; *Brands*; search; theme
  switch; EN / TR. Phones get a side drawer (`Drawer`, a `<dialog>`) and a search icon.
- **Categories** are ours (`products.category`, keyword rules in `pipeline/categorize.py`), listed in
  `lib/categories.ts`. The shop's own category is kept and shown on the product page.
- **Shop listing** (`/[lang]/shop`): all filters live in the URL (`q`, `category`, `brand` (repeatable),
  `style` (repeatable, max 3), `min`/`max` in lira, `sale=1`, `stock=1`, `sort`, `page`), so every view is linkable. Desktop: a
  sidebar with category counts, brand checkboxes (2+ brands), price, availability. Phones: a category
  pill rail and a Filters drawer. Removable chips and "Clear all" above a 2/3/4-column grid,
  48 per page, numbered pagination. Counts come from `/products/facets`, each dimension counted
  without its own filter.
- **Shop by style** (home): six tiles; photo and count come from `/products/facets` (`styles[].image_url`: the newest in-stock garment, preferring a fitting category per style).
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
