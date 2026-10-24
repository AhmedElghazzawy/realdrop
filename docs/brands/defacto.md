# DeFacto (`defacto`)

**Recommendation: go, brand 1.** Owner decision: _pending_

- Base URL: `https://www.defacto.com.tr`
- Checked: 24 Oct 2026

## robots.txt

`User-agent: *` disallows `/product/`, `/tr-tr/`, `/shopping`, login/customer pages and many query
parameters (`*q=*`, `*name=*`, `*source=*`, `*sortorder*`, `*filtre=*`, ...). Product pages live at
`/<seo-name>-<7-digit id>` with no query string, which is **allowed**. Sitemaps are listed in robots.txt.

## Terms

No public terms-of-use page in `sharedxml/tr-tr/static.xml`; `/statik/kullanim-kosullari` and
`/statik/uyelik-sozlesmesi` return 404. The privacy policy has no clause on bots or crawling. The
membership agreement is probably only shown at sign-up; we never log in.

## Data source

- Product URLs: `sharedxml/tr-tr/product.xml` (4,545) + `product-3.xml` (4,545); `product-2.xml` is
  empty. About **9,100 products** (each URL is one product in one colour). At 1 request/s a full
  pass takes about 2.5 h.
- Product page HTML (200, no challenge for our User-Agent) contains:
  - schema.org `Product` JSON-LD: name, images, sizes, `offers.price`, `priceCurrency` TRY.
  - `PRODUCT_DETAIL_SIZE_DATA=[...]`: one entry per size with `ProductVariantMatrixId` (stable id),
    `Size`, `Length`, `StockQuantity`. **Per-size stock: yes.**
  - `DataLayer`: `Price`, `DiscountedPrice`, `CampaignDiscountedPrice`, `ColorName`, `LongCode`.
  - `CampaignBadge`: basket campaigns, e.g. "Sepette" (-50 TL off at checkout), with start and end dates.
- Stable ids: the 7-digit number in the URL (`ProductVariantIndex`) for the product, and
  `ProductVariantMatrixId` for each size.

## Things to decide while building

- Which field is the shelf price and which is the claimed "old" price (`Price` vs `DiscountedPrice`
  on a product that is on sale; sample a discounted product).
- Basket campaigns ("Sepette ... TL indirim") are not the shelf price. The example seen ran from
  **14 Dec 2023 to 30 Nov 2026**, a "campaign" that is almost three years old, which is exactly the
  kind of claim RealDrop exists to check. Storing them needs a data-model change (ask the owner
  first); for v1 we store the shelf price only.
- The page includes a CAPTCHA script (probably for login). If a challenge page is ever served, the
  collector stops (no evasion).
