# Koton (`koton`)

**Recommendation: maybe, brand 3 (needs a DevTools look first).** Owner decision: _pending_

- Base URL: `https://www.koton.com`
- Checked: 24 Oct 2026

## robots.txt

Disallows `/list/*`, `/shopping-page/*`, basket/order/account pages, and `?category_ids=` /
`?search_text=`. Product pages at `/<seo-name>-<id>/` are **allowed**.

## Terms

`/uyelik-sozlesmesi/` returns 200 but the text is rendered client-side, so the agreement could not be
read with a plain request. **Not verified.** The owner should read it in a browser before a go.

## Data source

- Product URLs: `sitemap-products-1.xml.gz` (on S3), **15,000 URLs** in the first file (more files
  may follow). Some URLs end in `-1`; what that suffix means is not yet checked.
- Product page HTML: schema.org `Product` JSON-LD with one offer (price, TRY, availability) and a
  barcode (`gtin13`). Only the selected size is in the page, so other sizes' stock comes from an XHR
  call that still has to be found (browser DevTools -> Network).
