# DeFacto (`defacto`)

**Recommendation: go, brand 1.** Owner decision: **go** (24 Oct 2026). Collector: `collectors/defacto/`.

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

## How we read prices (decided while building)

On 10 sampled products `Price` and `DiscountedPrice` were always equal, and most products carry a
basket campaign: `CampaignBadge` with `CampaignDescription: "Sepette"`, shown on the page as
"Sepette Net %50 İndirim". It needs no coupon and no second item, so **everyone pays the campaign
price at checkout**. Therefore:

- `price_minor` = campaign `DiscountPrice` if the campaign is active now (its dates are Turkey local
  time), otherwise `DiscountedPrice`.
- `original_price_minor` = `max(Price, DiscountedPrice)` if it is higher than what you pay, else none.

This fits the existing columns; no data-model change. Several campaigns run from **14 Dec 2023 to
30 Nov 2026**: a "limited" discount almost three years long, exactly the kind of claim RealDrop
exists to check. The real-drop rule compares against the price people actually paid, so these
permanent campaigns will not count as real drops.

## Collector

- Sitemap index `sharedxml/tr-tr/sitemapindex.xml` -> every `product(-N).xml` -> product URLs
  (deduplicated; the index currently lists `product`, `product-3`, `-4`, `-5`).
- One GET per product page. Product id: the trailing number of the URL. Variant SKU: `MatrixId`.
  Sizes: `SizeName` as shown, except "Beden 30 - Boy 32" becomes `30/32`.
- Skipped as an item failure: 404, redirect away (discontinued), a URL robots.txt disallows.
- 20 product pages in a row without product data stops the run (challenge or maintenance page).
  The page includes a CAPTCHA script (probably for login); we never solve or work around one.
- About 14,600 product pages (sitemaps `product`, `-3`, `-4`, `-5`); collected in two shards a day.
- `product-5.xml` has stale text after `</urlset>`; the parser keeps the complete document before it.
- Dry run 24 Oct 2026: 20 products, 0 failures, 28 s.
- The site's firewall returns **403 for a User-Agent with the placeholder contact**
  (`you@example.com`) and 200 for ours with the repo URL. Keep a real contact in `COLLECTOR_USER_AGENT`.
- First stored run 24 Oct 2026: 20 products, 95 variants, 95 confirmed prices.

## What could break it

The data lives in inline scripts (`DataLayer:`, `CampaignBadge:`), not a documented API. A site
redesign that renames or moves them makes every page an item failure; the fixture tests and the
"pages without data" stop make that loud, not silent.
