"""One collector for every classic Akinon storefront; brands.py configures it per brand.

Product URLs come from either
- the brand's men's category listing, requested as JSON page by page (`?page=N`), which lets us
  fetch only men's products (owner decision 27 Oct 2026: new brands store men only), or
- the sitemap, optionally filtered by a URL pattern, for brands without such a listing.
Each product URL is then requested once with `Accept: application/json` (parser.py).

Like the other collectors: 404s, robots-disallowed URLs and pages that keep failing with 5xx are
skipped as ItemFailures; many non-product answers in a row, or a few broken pages in a row, stop
the run. Skipped quietly: pages for a colour already collected in this run, and products not for
`only_audience`.
"""

import re
from collections.abc import AsyncIterator
from typing import Any, ClassVar

import httpx

from realdrop.collectors.akinon.parser import parse_product
from realdrop.collectors.base import (
    Audience,
    BrandCollector,
    ItemFailure,
    RawProduct,
    Shard,
    in_flight,
)
from realdrop.collectors.http import (
    CollectorBlockedError,
    CollectorServerError,
    PoliteClient,
    RobotsDisallowedError,
)
from realdrop.collectors.sitemap import sitemap_locs

JSON = {"Accept": "application/json"}
MAX_PAGES_WITHOUT_DATA = 20
MAX_BROKEN_PAGES_IN_A_ROW = 3
PAGES_IN_FLIGHT = 3
MAX_LISTING_PAGES = 1000  # a safety stop, far above any real catalog (Koton men: ~300 pages)


class AkinonCollector(BrandCollector):
    """Subclass per brand and set the ClassVars below (see brands.py)."""

    # Either listing_paths (preferred) or sitemap_index must be set.
    listing_paths: ClassVar[tuple[str, ...]] = ()
    sitemap_index: ClassVar[str | None] = None
    url_pattern: ClassVar[str | None] = None  # sitemap URLs must match this (re.search)
    # For brands whose products carry no gender attribute (a men's-only brand).
    default_audience: ClassVar[Audience | None] = None
    # Products for anyone else are dropped (owner decision 27 Oct 2026: new brands store men only,
    # to fit Neon's free 0.5 GB). None keeps everything.
    only_audience: ClassVar[Audience | None] = "men"

    def __init__(self, client: PoliteClient, *, shard: Shard | None = None) -> None:
        super().__init__(client, shard=shard)
        self._pages_without_data = 0
        self._broken_in_a_row = 0
        self._seen: set[str] = set()

    async def fetch_catalog(self) -> AsyncIterator[RawProduct | ItemFailure]:
        urls = await (self._listing_urls() if self.listing_paths else self._sitemap_urls())
        urls = [u for u in dict.fromkeys(urls) if self.shard.contains(u)]
        async for item in in_flight(urls, self._fetch_product, PAGES_IN_FLIGHT):
            if item is not None:
                yield item

    async def _listing_urls(self) -> list[str]:
        urls: list[str] = []
        for path in self.listing_paths:
            page, last = 1, 1
            while page <= min(last, MAX_LISTING_PAGES):
                response = await self.client.get(
                    f"{self.base_url}{path}", params={"page": page}, headers=JSON
                )
                data: dict[str, Any] = response.json()
                last = int(data["pagination"]["num_pages"])
                urls += [f"{self.base_url}{p['absolute_url']}" for p in data["products"]]
                page += 1
        return urls

    async def _sitemap_urls(self) -> list[str]:
        if self.sitemap_index is None:
            raise ValueError(f"{self.slug}: set listing_paths or sitemap_index")
        index = await self.client.get(self.sitemap_index)
        sitemaps = [u for u in sitemap_locs(index.text) if "product" in u]
        pattern = re.compile(self.url_pattern) if self.url_pattern else None
        urls: list[str] = []
        for sitemap_url in sitemaps:
            sitemap = await self.client.get(sitemap_url)
            urls += [u for u in sitemap_locs(sitemap.text) if pattern is None or pattern.search(u)]
        return urls

    async def _fetch_product(self, url: str) -> RawProduct | ItemFailure | None:
        try:
            response = await self.client.get(url, headers=JSON)
        except RobotsDisallowedError:
            return ItemFailure(source=url, reason="robots.txt disallows this URL")
        except CollectorServerError as exc:
            self._broken_in_a_row += 1
            if self._broken_in_a_row >= MAX_BROKEN_PAGES_IN_A_ROW:
                raise
            return ItemFailure(source=url, reason=str(exc))
        except httpx.HTTPStatusError as exc:
            return ItemFailure(source=url, reason=f"HTTP {exc.response.status_code}")
        self._broken_in_a_row = 0  # the site answered, so it is not down

        try:
            data = response.json()
            has_product = isinstance(data, dict) and isinstance(data.get("product"), dict)
        except ValueError:  # an HTML page: maintenance, challenge, or no JSON support
            has_product = False
        if not has_product:
            self._pages_without_data += 1
            if self._pages_without_data >= MAX_PAGES_WITHOUT_DATA:
                raise CollectorBlockedError(
                    f"{self._pages_without_data} product pages in a row without product JSON "
                    f"(challenge or maintenance page?); last: {url}"
                )
            return ItemFailure(source=url, reason="no product JSON")
        self._pages_without_data = 0

        try:
            product = parse_product(data, url)
        except (KeyError, TypeError, ValueError) as exc:
            return ItemFailure(source=url, reason=f"{type(exc).__name__}: {exc}"[:500])
        if product.external_id in self._seen:
            return None  # another listing entry of a colour already collected
        self._seen.add(product.external_id)
        if product.audience is None and self.default_audience is not None:
            product = product.model_copy(update={"audience": self.default_audience})
        if self.only_audience is not None and product.audience != self.only_audience:
            return None  # e.g. a boys' item listed under men's, or a women's page in the sitemap
        return product
