"""Colin's collector: product URLs from one sitemap, one polite GET per product page.

About 5,750 product pages (Oct 2026); at 1 request/s with pages in flight a full pass takes about
1.6 hours, so one run per day collects everything (no shards needed). robots.txt disallows any
URL containing "price" or "search"; product pages (/p/...) are allowed and PoliteClient checks
every URL anyway.

Skipped as an ItemFailure: 404s, redirects away (discontinued), robots-disallowed URLs, and a page
that keeps failing with 5xx after all retries. The run stops on many pages in a row without
product data (a challenge or maintenance page served with 200) or a few broken pages in a row.
"""

from collections.abc import AsyncIterator

import httpx

from realdrop.collectors.base import BrandCollector, ItemFailure, RawProduct, Shard, in_flight
from realdrop.collectors.colins.parser import BASE_URL, SITEMAP, has_product_data, parse_product
from realdrop.collectors.http import (
    CollectorBlockedError,
    CollectorServerError,
    PoliteClient,
    RobotsDisallowedError,
)
from realdrop.collectors.sitemap import sitemap_locs

MAX_PAGES_WITHOUT_DATA = 20
MAX_BROKEN_PAGES_IN_A_ROW = 3
PAGES_IN_FLIGHT = 3  # pages downloading at once; request starts stay at rate_limit_rps


class ColinsCollector(BrandCollector):
    slug = "colins"
    name = "Colin's"
    base_url = BASE_URL
    rate_limit_rps = 1.0

    def __init__(self, client: PoliteClient, *, shard: Shard | None = None) -> None:
        super().__init__(client, shard=shard)
        self._pages_without_data = 0
        self._broken_in_a_row = 0

    async def fetch_catalog(self) -> AsyncIterator[RawProduct | ItemFailure]:
        sitemap = await self.client.get(SITEMAP)
        # dict keeps sitemap order while dropping duplicates
        urls = list(dict.fromkeys(u for u in sitemap_locs(sitemap.text) if self.shard.contains(u)))
        async for item in in_flight(urls, self._fetch_product, PAGES_IN_FLIGHT):
            yield item

    async def _fetch_product(self, url: str) -> RawProduct | ItemFailure:
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
            return parse_product(response.text, url)
        except (KeyError, TypeError, ValueError) as exc:
            return ItemFailure(source=url, reason=f"{type(exc).__name__}: {exc}"[:500])
