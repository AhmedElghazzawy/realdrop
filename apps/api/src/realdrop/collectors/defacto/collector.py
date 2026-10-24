"""DeFacto collector: product URLs from the sitemaps, one polite GET per product page.

About 9,000 product pages; at 1 request/s a full pass takes about 2.5 hours. A product page that
404s, redirects away (discontinued) or is disallowed by robots.txt is skipped as an ItemFailure.
Many pages in a row without product data means something is wrong (a challenge or maintenance page
served with 200), so the run stops instead of hammering the site.
"""

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime

import httpx

from realdrop.collectors.base import BrandCollector, ItemFailure, RawProduct
from realdrop.collectors.defacto.parser import (
    BASE_URL,
    has_product_data,
    parse_product,
    product_sitemaps,
    sitemap_locs,
)
from realdrop.collectors.http import CollectorBlockedError, PoliteClient, RobotsDisallowedError

SITEMAP_INDEX = f"{BASE_URL}/sharedxml/tr-tr/sitemapindex.xml"
MAX_PAGES_WITHOUT_DATA = 20


class DefactoCollector(BrandCollector):
    slug = "defacto"
    name = "DeFacto"
    base_url = BASE_URL
    rate_limit_rps = 1.0

    def __init__(
        self, client: PoliteClient, *, now: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        super().__init__(client)
        self._now = now
        self._pages_without_data = 0

    async def fetch_catalog(self) -> AsyncIterator[RawProduct | ItemFailure]:
        index = await self.client.get(SITEMAP_INDEX)
        seen: set[str] = set()
        for sitemap_url in product_sitemaps(index.text):
            sitemap = await self.client.get(sitemap_url)
            for url in sitemap_locs(sitemap.text):
                if url in seen:
                    continue
                seen.add(url)
                yield await self._fetch_product(url)

    async def _fetch_product(self, url: str) -> RawProduct | ItemFailure:
        try:
            response = await self.client.get(url)
        except RobotsDisallowedError:
            return ItemFailure(source=url, reason="robots.txt disallows this URL")
        except httpx.HTTPStatusError as exc:
            return ItemFailure(source=url, reason=f"HTTP {exc.response.status_code}")

        if str(response.url).rstrip("/") != url.rstrip("/"):
            return ItemFailure(source=url, reason=f"redirected to {response.url} (discontinued?)")
        if not has_product_data(response.text):
            self._pages_without_data += 1
            if self._pages_without_data >= MAX_PAGES_WITHOUT_DATA:
                raise CollectorBlockedError(
                    f"{self._pages_without_data} product pages in a row without product data "
                    f"(challenge or maintenance page?); last: {url}"
                )
            return ItemFailure(source=url, reason="no product data on page")
        self._pages_without_data = 0

        try:
            return parse_product(response.text, url, self._now())
        except (KeyError, TypeError, ValueError) as exc:
            return ItemFailure(source=url, reason=f"{type(exc).__name__}: {exc}"[:500])
