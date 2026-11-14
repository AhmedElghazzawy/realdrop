# Brand feasibility

One file per candidate brand (`<slug>.md`), written during the feasibility step of the
add-brand-collector skill. The owner makes the go / no-go call and records it in the file.

Checked 24 Oct 2026 with our own User-Agent (`RealDropBot/0.1`), a handful of requests per site,
2 s apart.

| Brand | robots.txt | Terms | Data | Per-size stock | Recommendation |
|---|---|---|---|---|---|
| [DeFacto](defacto.md) | Listings and product pages allowed | No public terms page found | Card JSON in men's listing pages (since 30 Oct) | Sizes in stock only | **Go: brand 1** (owner: go, 24 Oct) |
| [Colin's](colins.md) | Product pages allowed (`*price*` URLs disallowed) | No anti-bot clause found | JSON-LD + HTML | Yes, per size in page | **Go: brand 2** (owner: go, 25 Oct) |
| [Koton](koton.md) | Product pages and `/erkek/` listing allowed | No anti-bot clause found (26 Oct) | **Akinon JSON** (see below) | Yes, per size in the JSON | **Go: Akinon group** (27 Oct) |
| Mudo | Product pages and `/erkek-giyim/` allowed | No anti-bot clause found (26 Oct) | Akinon JSON | Yes | **Go: Akinon group** (27 Oct) |
| GAP | Product pages and `/erkek-giyim/` allowed | No anti-bot clause found (26 Oct) | Akinon JSON | Yes | **Go: Akinon group** (27 Oct) |
| Marks & Spencer | Product pages allowed; men's URLs from the sitemap (`/erkek-...`) | No anti-bot clause found (26 Oct) | Akinon JSON | Yes | **Go: Akinon group** (27 Oct) |
| Damat Tween | Product pages allowed; sitemap (menswear only) | No anti-bot clause found (26 Oct) | Akinon JSON | Yes | **Go: Akinon group** (27 Oct) |
| Les Benjamins | `/products.json` allowed | No anti-bot clause found (26 Oct) | Shopify catalog JSON | Yes (`available` per variant) | **Go: Shopify group** (27 Oct) |
| Lufian, TommyLife, Hatemoğlu | Product pages and `/xml/sitemap/product.xml` allowed | No anti-bot clause in the membership agreement (27 Oct) | T-Soft page: variant buttons (`data-price` without VAT, `data-vat`, `data-instock`) | Yes | **Go: T-Soft group** (27 Oct) |
| Süvari | Allowed | **Membership agreement bans "multiple queries with automated programs"** | Ticimax | - | No-go |
| Sarar, AVVA, Bad Bear, Loft | Allowed | Terms page not found (JS footer; standard paths 404) | - | - | **Owner to read the terms in a browser** |
| Ramsey, Giesto | `/products.json` allowed | Ramsey (Gürmen group): no anti-bot clause | Shopify catalog JSON | Yes | **Wait:** 429 `local_rate_limited` after 1-3 identified requests; retry later, never work around |
| [LC Waikiki](lc-waikiki.md) | Allows everything | **Forbids robots, crawling, data mining** | JSON-LD | Not in page | No-go |
| [Mavi](mavi.md) | Product pages allowed | Not checked | Not reached | Not reached | No-go (Cloudflare challenge) |
| [H&M Turkey](hm-turkey.md) | **403 on robots.txt** | Not checked | Not reached | Not reached | No-go (blocked) |

## Wide scan, 26-27 Oct 2026

The owner asked for every big brand with stores in Turkey plus local brands. Method: one robots.txt
request per site, then (open sites only) sitemap -> one product URL -> our own robots matcher ->
that product page, 2 s apart, with the RealDrop User-Agent. Terms of use are **not** checked yet;
that happens per brand before its collector is built (add-brand-collector skill).

**Blocked (no-go, rule 8: never work around a block).** A legitimate later route for some is an
official affiliate product feed (Awin, Admitad, CJ); that needs a live site and an application by
the owner.

| Brand | Answer to a polite request |
|---|---|
| Zara, Bershka, Pull&Bear, Stradivarius, Massimo Dutti (Inditex) | 403 + bot challenge, even on robots.txt |
| H&M | 403 on robots.txt (24 Oct) |
| Mango | 429 on the first request |
| adidas, Cacharel | 403 |
| New Balance, İpekyol | 418 (bot block) |
| Kip, Kiğılı (Shopify) | 429 on the first product page: retry later at a slower rate before deciding |
| Calvin Klein, Superdry | No answer (timeout / connection reset): retry later |

**Open, grouped by shop platform** (one collector per platform covers the group):

| Platform | Brands | Data |
|---|---|---|
| Akinon | Koton, Lacoste, U.S. Polo Assn., Pierre Cardin, Mudo, GAP, Marks & Spencer, Damat Tween | Product URL with `Accept: application/json` returns full JSON: per-size `price`, `retail_price`, `stock`, `in_stock`, `basket_offers`, `attributes_kwargs.filterable_gender` |
| T-Soft | Lufian, Sarar, Hatemoğlu, TommyLife | JSON-LD Product + page stock words |
| Ticimax | AVVA, Süvari, Bad Bear | JSON-LD with variants |
| Shopify | Les Benjamins, Giesto (+ Ramsey; Kip, Kiğılı see above) | JSON-LD; Shopify product JSON to check against robots.txt |
| Colin's platform | Loft (`/p/...`, `/SitemapProducts`) | Likely the Colin's parser as is |
| Own platform | Network, Altınyıldız Classics, Yargıcı, Twist, Beymen, Tommy Hilfiger, The North Face, Columbia, Puma, Skechers, Benetton, Vakko, Jack & Jones (TR) | Mostly JSON-LD Product; one collector each |

Notes:
- Koton's basket offer on the sampled page was a coupon ("KTN20 KODU İLE %20 İNDİRİM"): not what
  everyone pays, so it is ignored, like any conditional offer (DeFacto rule).
- Akinon: one product page = one colour; size options can point at other colours' products, so only
  options whose product has the page's colour count as its sizes. When the page's colour is sold
  out, every size option may point elsewhere; the page itself is then its only (sold-out) size.
- Akinon collector (`collectors/akinon/`, 27 Oct): one parser and one collector for the classic
  storefront; each brand is a small subclass in `akinon/brands.py` (listing path or sitemap, default
  audience). Men's products only (owner, 26 Oct). Lacoste is Akinon too but its terms forbid robots
  and spiders: no-go. U.S. Polo Assn. and Pierre Cardin run the newer Akinon front end (no JSON
  answer): a separate parser, later.
- Shopify collector (`collectors/shopify/`, 27 Oct): the whole catalog from `/products.json`, 250
  products per request (Les Benjamins: 1,626 men's products in ~10 requests, 20 s). The JSON has no
  currency and Shopify can convert prices for visitors abroad (our runners are in the US), so each
  run first checks `Shopify.currency.active` on the home page and stops unless it is TRY.
- T-Soft collector (`collectors/tsoft/`, 27 Oct): product sitemap, then each page. Prices come from
  the variant buttons (price without VAT * (1 + VAT), checked on every page against the page's own
  VAT-included figure), never from JSON-LD: Hatemoğlu's JSON-LD price includes a "Sepette EKSTRA"
  basket offer (conditional, ignored).
- Shopify keeps `/policies/` out of robots.txt; read terms pages through a search engine or a
  browser, not with the collector's User-Agent.
- Not found yet: Ata Studio, Sabotage, Spasso (no shop site found; owner to send links). "Flaws" is
  probably Flaw Wear (flaw.com.tr exists but has no sitemap; to check).
- Not usable: levi.com.tr (a company WordPress site, not the Levi's shop), nike.com (global), Buratti
  (redirects to a different brand).

