"""DeFacto collector: product URLs from the sitemaps, one polite GET per product page.

About 14,600 product pages (Oct 2026). At 1 request/s a full pass takes about 5 hours, so the
schedule collects it in two shards (`--shard 0/2`, `--shard 1/2`) of about 2.5 hours each.
A product page that 404s, redirects away (discontinued) or is disallowed by robots.txt is skipped
as an ItemFailure. Many pages in a row without product data means something is wrong (a challenge
or maintenance page served with 200), so the run stops instead of hammering the site.
"""

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime

import httpx

from realdrop.collectors.base import BrandCollector, ItemFailure, RawProduct, Shard, in_flight
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
PAGES_IN_FLIGHT = 3  # pages downloading at once; request starts stay at rate_limit_rps


class DefactoCollector(BrandCollector):
    slug = "defacto"
    name = "DeFacto"
    base_url = BASE_URL
    rate_limit_rps = 1.0

    def __init__(
        self,
        client: PoliteClient,
        *,
        shard: Shard | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        super().__init__(client, shard=shard)
        self._now = now
        self._pages_without_data = 0

    async def fetch_catalog(self) -> AsyncIterator[RawProduct | ItemFailure]:
        urls = await self._product_urls()
        async for item in in_flight(urls, self._fetch_product, PAGES_IN_FLIGHT):
            yield item

    async def _product_urls(self) -> list[str]:
        """Every product URL in this shard, deduplicated, in sitemap order (~15k for all shards)."""
        index = await self.client.get(SITEMAP_INDEX)
        urls: dict[str, None] = {}
        for sitemap_url in product_sitemaps(index.text):
            sitemap = await self.client.get(sitemap_url)
            urls.update(
                (url, None) for url in sitemap_locs(sitemap.text) if self.shard.contains(url)
            )
        return list(urls)

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
