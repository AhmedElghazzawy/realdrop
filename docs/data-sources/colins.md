# Colin's (`colins`)

**Recommendation: go, brand 2.** Owner decision: **go** (25 Oct 2026). Per-size stock confirmed 25 Oct.

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
- Product URLs: 5,753 on 25 Oct 2026 (~3,240 men, ~2,500 women, no kids).
- Product page HTML (checked on 7 pages, 25 Oct 2026):
  - **Price paid:** JSON-LD `Product.offers.price` (`"999.99"`), same as `.product-detail-price`.
  - **Claimed old price:** `.product-detail-old-price` ("1399,90 TL"), only present when discounted;
    the site also shows `.discount-percentage` ("- 29%"). No basket-only price was seen.
  - **Per-size stock:** the size `<select>` has one `<option value="<variant id>" class="have-stock">`
    or `class="no-stock"` per size; sold-out text has " - STOĞA GELİNCE HABER VER" appended.
  - **Category:** a JS `Breadcrumb: "Erkek Pantolon<Erkek Giyim<Tüm Ürünler"` string (leaf first).
    Some products only sit under campaign categories ("Öğretmenler Günü Hediyesi<Tüm Ürünler"), so
    the audience comes from the title ("... Erkek ...", "... Kadın ...") as well.
  - Product id: the number at the end of the URL; `sku` in JSON-LD (`CL1083486_Q1.V1_DN45304`).
