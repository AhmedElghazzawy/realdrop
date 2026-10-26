"""One collector for every T-Soft storefront; brands.py configures it per brand.

Product URLs come from the shop's product sitemap (`/xml/sitemap/product.xml` on T-Soft); each
page is requested once and parsed from its HTML (parser.py). The sitemap mixes men's and women's
products and the page is the only place that says which, so other audiences are fetched and then
dropped.

Like the other collectors: 404s, robots-disallowed URLs and pages that keep failing with 5xx are
skipped as ItemFailures; many pages without product data in a row, or a few broken pages in a
row, stop the run.
"""

from collections.abc import AsyncIterator
from typing import ClassVar

import httpx

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
from realdrop.collectors.tsoft.parser import has_product_data, parse_product

MAX_PAGES_WITHOUT_DATA = 20
MAX_BROKEN_PAGES_IN_A_ROW = 3
PAGES_IN_FLIGHT = 3


class TsoftCollector(BrandCollector):
    """Subclass per brand and set the ClassVars below (see brands.py)."""

    product_sitemap: ClassVar[str]
    # For a brand whose categories do not start with "Erkek" / "Kadın" (a men's-only brand).
    default_audience: ClassVar[Audience | None] = None
    # Owner decision 27 Oct 2026: new brands store men only. None keeps everything.
    only_audience: ClassVar[Audience | None] = "men"

    def __init__(self, client: PoliteClient, *, shard: Shard | None = None) -> None:
        super().__init__(client, shard=shard)
        self._pages_without_data = 0
        self._broken_in_a_row = 0

    async def fetch_catalog(self) -> AsyncIterator[RawProduct | ItemFailure]:
        sitemap = await self.client.get(self.product_sitemap)
        urls = [u for u in dict.fromkeys(sitemap_locs(sitemap.text)) if self.shard.contains(u)]
        async for item in in_flight(urls, self._fetch_product, PAGES_IN_FLIGHT):
            if item is not None:
                yield item

    async def _fetch_product(self, url: str) -> RawProduct | ItemFailure | None:
        try:
            response = await self.client.get(url)
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

        if not has_product_data(response.text):
            self._pages_without_data += 1
            if self._pages_without_data >= MAX_PAGES_WITHOUT_DATA:
                raise CollectorBlockedError(
                    f"{self._pages_without_data} product pages in a row without product data "
                    f"(challenge or maintenance page?); last: {url}"
                )
            return ItemFailure(source=url, reason="no product data")
        self._pages_without_data = 0

        try:
            product = parse_product(response.text, url)
        except (KeyError, TypeError, ValueError) as exc:
            return ItemFailure(source=url, reason=f"{type(exc).__name__}: {exc}"[:500])
        if product.audience is None and self.default_audience is not None:
            product = product.model_copy(update={"audience": self.default_audience})
        if self.only_audience is not None and product.audience != self.only_audience:
            return None
        return product
