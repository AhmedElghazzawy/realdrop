# Design system

## Direction

**Terminal x editorial.** Clothes are treated like tickers: a dark, dense, data-first interface where
price history is the hero, with editorial fashion typography so it still feels like fashion and not a
trading app. The "real discount" badge reads like a market signal. Mobile first (most Turkish
shoppers are on phones); desktop gets density, not decoration.

Principles: truth first (never decorate a number), density with air, one accent color used only for
real signals, motion that explains change (a price ticking down) and never just decorates.

## Tokens

Define as CSS variables in `apps/web/src/app/globals.css` and mirror them in the Tailwind theme.

```css
:root {
  --bg: #0a0a0b;          /* page */
  --surface: #111113;     /* cards */
  --surface-2: #17171a;   /* raised, hover */
  --line: #26262b;        /* borders, grid */
  --text: #ecece8;        /* primary text */
  --muted: #8b8b92;       /* secondary text */
  --signal: #c6ff3d;      /* REAL drop (the one accent) */
  --warn: #ff5a36;        /* inflated claim */
  --info: #7aa7ff;        /* neutral info, links */
  --radius: 10px;
}
```

Contrast: body text on `--bg` must meet WCAG AA (4.5:1); check `--muted` on `--surface` before use for
small text. Colour is never the only carrier of meaning (every badge has text and an icon).

## Type

- **Display / headlines:** an editorial serif (candidate: Instrument Serif). Use sparingly, large.
- **UI text:** a clean sans (candidate: Geist or Inter).
- **Numerals / prices / tickers:** a mono (candidate: Geist Mono or JetBrains Mono), tabular figures.
- **Turkish glyph check (do this first):** render `ığüşöçİĞÜŞÖÇ` in every chosen font at every weight
  before committing. A font that lacks them or ships a bad dotted/dotless I is rejected.
- Scale (px / line-height): 12/16, 14/20, 16/24, 20/28, 28/34, 40/44 display.

## Number and date formatting

Always through `lib/format.ts`, which uses `Intl` in the page language: `en-GB` (`₺1,299.90`, `24%`,
`24 Nov 2026`, the default) or `tr-TR` (`₺1.299,90`, `%24`, `24 Kas 2026`). Never concatenate strings by
hand; UI text lives in `src/i18n/en.ts` and `tr.ts`. Shop text (titles, categories) stays Turkish and
gets `lang="tr"`. Prices in the API are kurus; convert at the edge.

## Core components

| Component | Notes |
|---|---|
| `PriceCard` | image, brand, title, current price (mono), sparkline (30 d), badge, sizes in stock |
| `Sparkline` | 30-day line; end-point dot in `--signal` only when status is `real_drop` |
| `RealDiscountBadge` | states below |
| `PriceChart` | 30 / 90 day toggle, claimed-price line dashed in `--warn`, reference (median) line, hover tooltip, tracked-since marker |
| `SizePicker` | shows stock per size; selecting sets the alert target size |
| `SearchBar` + `FilterChips` | parsed filters shown as removable chips; edit-in-place |
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
- Layout: 375 px is the design baseline; check 375, 768 and 1280 for every screen.

## Pages

Home (search + real best deals), Search results, Product (chart, sizes, alert), Black Friday
(real deals vs inflated claims), Alerts, Assistant, Profile and Privacy.
