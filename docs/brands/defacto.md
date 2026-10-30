# DeFacto (`defacto`)

**Recommendation: go, brand 1.** Owner decision: **go** (24 Oct 2026). Collector: `collectors/defacto/`.

- Base URL: `https://www.defacto.com.tr`
- Checked: 24 Oct 2026

## robots.txt

`User-agent: *` disallows `/product/`, `/tr-tr/`, `/shopping`, login/customer pages and many query
parameters (`*q=*`, `*name=*`, `*source=*`, `*sortorder*`, `*filtre=*`, ...). Product pages live at
`/<seo-name>-<7-digit id>` with no query string, which is **allowed**. Sitemaps are listed in robots.txt.
Category listings (`/erkek-giyim`, `?page=N`) are **allowed**; their AJAX variant (`*?ajx=*`) and
anything containing `catalog` are not, so we read the plain HTML pages (checked 30 Oct 2026).

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

## Collector (since 30 Oct 2026: men's listing pages)

**Why the change.** One GET per product page (~20,000 URLs in the sitemaps by Oct 2026) never
finished: from 25 to 29 Oct every run got 502s after about 650 pages, on different pages each time,
at 1 and at 0.5 request/s. That is the site saying "enough", so the same ~650 products were all we
ever refreshed. A listing card carries everything we store, so we now read listings instead.

- Listings (men only, owner decision 30 Oct 2026): `/erkek-giyim` (~5,225 products), `/erkek-ayakkabi`
  (~18), `/erkek-aksesuar` (~250). 24 cards a page, `?page=N`; about **230 requests a run** at
  0.5 request/s (~8 min).
- Each card (`<div data-index=N class=product-card data-type="" ... data-documents='{...}'>`) has
  the product page's `DataLayer` fields: `Name`, `SeoName`, `ProductVariantIndex` (the 7-digit id
  in the product URL, so products keep their ids), `Price`, `DiscountedPrice`,
  `CampaignDiscountedPrice`, `CampaignBadge` (with dates), `ColorName`, `CategoryName` (leaf only),
  `SubDivision` (`Man`), and `Sizes`. `window.productImageN=[...]` lists the card's images; they are
  served from `https://dfcdn.defacto.com.tr/7/<imagePath>`. `data-type=freeItem` is a promo tile.
- **Sizes on a card are only the sizes in stock**, keyed by `Barcode` (cards have no `MatrixId`).
  So a sold-out size just disappears; the catalog counts only sizes seen in the product's latest
  collection (`services/catalog.py`, `_current_variants`). Per-size history restarted on 30 Oct
  (new keys); the product-level chart, which combines sizes, did not.
- `category_raw` = listing root + card leaf, e.g. `Erkek > Giyim > Mont` (same shape as before).
- Paging: `id=totalCount` on page 1 gives the page count; the last page is short (5,225 = 217 × 24 +
  17). Past the end the site serves a page with no total and no cards, which ends the listing. A
  full last page means the listing grew during the run, so we read on while pages bring new products.
- Both shards read every listing page and keep their half of the products (by URL), like Shopify.
- A listing page that fails with 5xx after all retries is skipped; 3 in a row stop the run. A page
  without listing data inside the listing stops the run (challenge or maintenance page). We never
  solve or work around a CAPTCHA.
- The site's firewall returns **403 for a User-Agent with the placeholder contact**
  (`you@example.com`) and 200 for ours with the repo URL. Keep a real contact in `COLLECTOR_USER_AGENT`.
- `parse_product` (product pages) is still in `parser.py` with its fixtures, unused by the schedule.

History: first stored run 24 Oct 2026 (20 products, product pages); product pages until 29 Oct.

## What could break it

The data lives in HTML attributes and inline scripts (`data-documents`, `window.productImageN`,
`id=totalCount`), not a documented API. A redesign that renames them makes every card an item
failure or every page "without product data", which stops the run: loud, not silent. A new rule in
robots.txt for listings would stop the run too (`CollectorBlockedError`).
