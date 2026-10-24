# Colin's (`colins`)

**Recommendation: go, brand 2 (after checking per-size stock).** Owner decision: _pending_

- Base URL: `https://www.colins.com.tr`
- Checked: 24 Oct 2026

## robots.txt

Disallows checkout/account pages, `/urunler/`, `/kampanyalar/`, `/markalar/`, and any URL containing
`*search*`, `*price*`, `*orderby*`, `*term*`. Product pages at `/p/<seo-name>-<id>` are **allowed**.
We must never request a URL with "price" or "search" in it.

## Terms

The "Gizlilik ve Güvenlik" page has no clause on bots or crawling, and there is no separate
terms-of-use link on product pages. Policies page: `/t/politikalarimiz`.

## Data source

- Product URLs: `/SitemapProducts`, **5,757 products**.
- Product page HTML: schema.org `Product` JSON-LD (price, currency, availability) and size buttons
  (`size-name`, `size-id`). No sold-out marker found on the size buttons of the sampled product, so
  **per-size stock is unclear**. Next step: find the endpoint the size picker calls, or confirm a
  sold-out class on a product that has a sold-out size.
- Price seen as `1999.90` in JSON-LD and `1999.9000` in embedded data.
