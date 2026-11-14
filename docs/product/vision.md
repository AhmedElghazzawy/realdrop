# Product vision

| | |
|---|---|
| **Status** | Current. Replaces the price-tracker spec of 24 Oct 2026 (see git history) |
| **Owner decision** | 14 Nov 2026: pivot to an AI fashion advisor ([ADR 0013](../architecture/decisions/0013-pivot-to-ai-fashion-advisor.md)) |
| **Launch** | Black Friday, Fri 27 Nov 2026 (MVP), then iterate |

## One line

**RealDrop is your AI fashion advisor.** Tell it your style, show it a look you love, and it builds
that outfit from real products across Turkish fashion brands, with honest prices.

## The problem

1. **Inspiration does not lead to purchase.** People save outfits on Instagram, Pinterest and TikTok,
   but turning a photo into "which jacket, which trousers, from which shop, in my size and budget"
   takes hours of searching across a dozen sites.
2. **Shopping is organised by store, not by style.** Every brand has its own site, its own filters
   and its own words. Nobody answers "old money look under 4,000 TL" across all of them.
3. **Discounts lie.** Retailers raise "original" prices before sales. Shoppers distrust every "70%
   off!" and cannot check it.

## Who it is for

| Persona | Need | What RealDrop gives them |
|---|---|---|
| **The style enthusiast** (18-30, mobile, follows fashion accounts) | Recreate looks they see online; build a recognisable personal style | Shop the look, outfit boards, a style profile that shapes everything |
| **The unsure dresser** | "What should I wear to a wedding / first day at work?" | A stylist they can ask in plain words, answering with complete outfits |
| **The smart shopper** | Not overpaying; buying when the price is really low | Real-discount labels on every recommendation, price history per product |

Men's clothing only at launch; a men/women choice comes later.

## Value propositions

1. **Shop the look.** Upload a screenshot; the AI identifies each piece and finds matching products
   from every brand we track, in your sizes and budget.
2. **A style profile that matters.** Pick your styles (old money, streetwear, minimal, smart casual,
   classic tailoring, techwear, workwear, preppy, ...), fits, colours and budget once. Every feed,
   match and outfit is ranked by it, with a visible "because you like ..." reason.
3. **Complete outfits, not single products.** Outfit boards (top, bottom, shoes, layer, accessory)
   with a total price, built around a piece you like or an occasion you describe.
4. **A stylist you can talk to** (if ready by launch): "old money outfit for a wedding under 4,000
   TL" returns boards from the real catalog.
5. **Honest prices, everywhere.** Every product shows its real discount based on prices we recorded
   ourselves, and flags inflated "original" prices. This is what no other style app can do.

## Scope for 27 Nov 2026

| Priority | Item | Use cases |
|---|---|---|
| Must | Price collection from 11+ brands on a server, twice a day (every 4 h before the sale) | UC-08 |
| Must | Catalog understanding: style tags and attributes on every product, search by meaning | enables all |
| Must | Style profile onboarding, stored on the device ([ADR 0014](../architecture/decisions/0014-style-profile-on-device.md)) | UC-01 |
| Must | Shop the look from a photo ([ADR 0015](../architecture/decisions/0015-shop-the-look-via-vision-model.md)) | UC-02 |
| Must | "For you" feed and outfit boards | UC-03, UC-04 |
| Must | Product page: price chart, real-discount badge, sizes, link out to the retailer | UC-06 |
| Must | Advisor-first redesign, mobile first, English + Turkish | all |
| Must | KVKK basics: privacy notice (incl. photo handling), consent, delete-my-data | all |
| Should | AI stylist chat and "Complete the look" | UC-05 |
| Should | Black Friday page: real best deals, inflated-claim examples | UC-07 |
| After launch | My wardrobe, optional login to sync, price alerts, image-similarity matching, women's clothing | UC-09, UC-10 |

## Non-goals for this release

- Virtual try-on or generating images of the user.
- A native mobile app: the site must work very well on a phone instead.
- Checkout, payments, marketplace sellers. We always link out to the retailer.
- Price forecasting ("will it drop more?"): it needs months of history.
- Storing users' photos. A photo is analysed and discarded.

## Honest limits shown in the product

- On launch day we have about 34 days of history at most. A variant with fewer than 14 days of data
  gets no real-discount claim; badges say "tracking since <date>".
- Shop-the-look results are "similar pieces", never claimed to be the exact item in the photo.
- Style tags are produced by rules and an AI model and can be wrong; users can say "not my style".

## Success measures (targets, not promises)

| Area | Measure | Launch target |
|---|---|---|
| Activation | Visitors who finish the style profile | >= 40% |
| Core value | Shop-the-look uploads that lead to at least one retailer click | >= 30% |
| Quality | Piece detection: correct category per piece on the eval set | >= 90% |
| Quality | Match relevance: at least one good match in the top 5 per piece | >= 80% |
| Trust | Unverified prices in AI answers (number-grounding guard) | 0 |
| Data | Collection success per brand over the last 14 days | >= 90% of scheduled runs |
| Speed | Shop-the-look end to end, p95 | < 8 s |

## Money

No revenue this season. Launch is about users and proving the idea. Affiliate programs need approval,
so apply early. Always link out to the retailer.

## Legal and ethical notes

- **Collection:** each retailer's robots.txt and terms are checked before we collect; the decision is
  recorded in [`../data-sources/`](../data-sources/README.md). Prefer official feeds and JSON endpoints.
- **Images:** product images are hotlinked from the retailer, not copied.
- **KVKK** (Turkey's data protection law): collect the minimum. The style profile stays on the
  device. Uploaded photos are sent to the analysis model and not stored; the privacy notice names the
  provider and whether it may use the data.
- **Personalisation is explained** in plain language and can be reset at any time.
