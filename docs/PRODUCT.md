# Product

## One line

Turkish shoppers see "70% off!" everywhere on Black Friday, and many of those discounts are inflated.
fiyatgercek records real prices every day, tells you what the discount **really** is, alerts you when
your size really drops, and lets you search in plain Turkish or English.

## The problem

- Retailers raise "original" prices before sales, then show a big discount. Shoppers know it and
  distrust it, but cannot prove it.
- Existing price trackers are strong in electronics and weak in fashion, where size, color and
  stock decide whether a price matters.
- Fashion search is keyword-based. People think in descriptions: "black oversize winter coat under
  2000 TL", "a shirt for a wedding, not too formal".

## Users

1. **The deal skeptic** (mostly mobile, Turkish-speaking): wants to know if a sale is real.
2. **The busy shopper**: types what they want in one sentence and expects good results.
3. **The size-specific buyer**: only cares about a price if their size is in stock.

## Value propositions

1. **Honest price**: price history per product and variant, a computed *real discount*, and a flag
   when the retailer's claimed discount is inflated.
2. **Alerts that mean something**: per size, only on confirmed real drops, with caps against spam.
3. **Understands language**: Turkish, English and mixed queries, parsed into filters plus meaning.
4. **Learns your taste**: the more you save and dismiss, the better the ordering. Visible and deletable.
5. **Assistant**: ask "is this jacket actually cheap right now?" and get an answer from real data.

## Scope for 27 Nov 2026

| Priority | Item |
|---|---|
| Must | Daily (later every-few-hours) price collection from 5-6 brands, running on a server, not a laptop |
| Must | Product pages: price chart, size/stock, real-discount badge, link out to the retailer |
| Must | Search: query parser + hybrid retrieval + rerank, in Turkish and English |
| Must | Telegram alerts per size (target price or minimum real discount) |
| Must | Black Friday page: real best deals, inflated-claim examples |
| Must | KVKK basics: privacy notice, consent, delete-my-data |
| Should | Shopping assistant with tools and the number-grounding guard |
| Should | Taste profile, onboarding quiz, "for you" ordering |
| Should | Email alerts |
| Could | Web push, English UI |

## Explicit non-goals for this release

- Price **forecasting** ("will it drop more?"). It needs months of history; before that it would be a gimmick.
- A native mobile app. The site must work very well on a phone instead.
- Cross-brand "same item" matching.
- Checkout, payments, marketplace sellers (Trendyol-style multi-seller platforms).
- Back-filling old prices. We only claim what we observed, and we say since when.

## Honest limits to show in the product

- On launch day we will have about 34 days of history at most. Badges say "tracking since <date>" and
  a variant with fewer than 14 days of data gets no real-discount claim.
- Every claim is phrased as "based on prices we observed since <date>".

## Brand selection

Candidates (to be confirmed by a feasibility check; record the result in `docs/brands/<slug>.md`):
LC Waikiki, DeFacto, Koton, Mavi, Colin's, H&M Turkey.

A brand is in only if: robots.txt and terms do not forbid what we do, there is a feed or JSON
endpoint (HTML scraping only as a last resort), URLs and product IDs are stable, sizes and stock are
visible per variant, and the catalog is large enough to matter. Start with the easiest brand to get
data flowing, then add the others.

## Launch targets (targets, not promises)

- Collection success >= 90% of scheduled runs per brand over the last 14 days.
- Query parser exact-match >= 85% on the golden set; retrieval recall@10 >= 0.80.
- Assistant number-grounding = 100% (zero unverified prices in answers).
- Search p95 < 1.5 s including rerank.
- 100 users who create at least one alert in the first week (a goal to measure, not to promise).

## Money

No revenue is planned for this season. Treat Black Friday as getting users and proving the idea.
Affiliate programs usually need approval, so apply early. Always link out to the retailer.

## Legal and ethical notes

- Check each retailer's terms and robots.txt. Scraping rules are a gray area; the owner decides per
  brand and records the decision in `docs/brands/<slug>.md`. Prefer official feeds and affiliate data.
- Link to retailer product pages; do not copy images or descriptions into our own storage beyond
  what we need for search (hotlink images where allowed; confirm per brand).
- KVKK (Turkey's data protection law): collect the minimum, get consent, provide export and
  deletion, keep a retention policy, and explain taste profiling in plain language.
