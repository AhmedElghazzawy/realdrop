"""DeFacto parser and collector against real pages saved on 24 Oct 2026 (fixtures/)."""

import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

from realdrop.collectors.base import ItemFailure, RawProduct, Shard
from realdrop.collectors.defacto import parser
from realdrop.collectors.defacto.collector import DefactoCollector
from realdrop.collectors.http import CollectorBlockedError, CollectorServerError, PoliteClient

FIXTURES = Path(__file__).resolve().parents[2] / "src/realdrop/collectors/defacto/fixtures"
NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
BASE = "https://www.defacto.com.tr"
TROUSERS = f"{BASE}/regular-fit-normal-bel-duz-paca-uzun-boy-pantolon-3455834"
BRA = f"{BASE}/buzgulu-dantel-detayli-pamuklu-cikarilabilir-kap-sutyen-3518142"
BABY_SET = f"{BASE}/2li-takim-baskili-kisa-kollu-fitilli-kaskorse-tisort-beli-lastikli-sort-kiz-bebek-3272557"  # noqa: E501
GONE = f"{BASE}/silinmis-urun-3000001"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_campaign_price_is_what_you_pay_and_list_price_is_the_claim() -> None:
    product = parser.parse_product(load("product_campaign_waist_length.html"), TROUSERS, NOW)

    assert product.external_id == "3455834"
    assert product.title == "Regular Fıt Normal Bel Düz Paça Uzun Boy Pantolon"  # site's own text
    assert product.category_raw == "Erkek > Giyim > Pantolon"
    assert product.currency == "TRY"
    assert len(product.image_urls) > 1
    # "Sepette Net %40 İndirim": 1299.99 on the shelf, 779.99 at checkout for everyone.
    assert {v.price_minor for v in product.variants} == {77999}
    assert {v.original_price_minor for v in product.variants} == {129999}
    assert {v.color_raw for v in product.variants} == {"Açık Gri"}


def test_waist_and_length_sizes_and_per_size_stock() -> None:
    product = parser.parse_product(load("product_campaign_waist_length.html"), TROUSERS, NOW)
    by_size = {v.size_label: v for v in product.variants}

    assert len(product.variants) == 18
    assert by_size["28/30"].in_stock is True
    assert by_size["30/32"].in_stock is False
    assert by_size["28/30"].external_sku == "69897a43-9003-4a08-87f3-4b6d6849d28a"


def test_campaign_outside_its_dates_is_ignored() -> None:
    after_end = datetime(2026, 12, 1, tzinfo=UTC)  # campaign ends 30 Nov 23:59 Turkey time
    product = parser.parse_product(load("product_campaign_waist_length.html"), TROUSERS, after_end)
    assert {v.price_minor for v in product.variants} == {129999}
    assert {v.original_price_minor for v in product.variants} == {None}


def test_campaign_end_is_turkey_time() -> None:
    # 30 Nov 23:59 in Turkey is 20:59 UTC: one minute later the campaign is over.
    html = load("product_campaign_waist_length.html")
    last_minute = parser.parse_product(html, TROUSERS, datetime(2026, 11, 30, 20, 59, tzinfo=UTC))
    too_late = parser.parse_product(html, TROUSERS, datetime(2026, 11, 30, 21, 0, tzinfo=UTC))
    assert last_minute.variants[0].price_minor == 77999
    assert too_late.variants[0].price_minor == 129999


def test_product_without_campaign_has_no_claimed_price() -> None:
    product = parser.parse_product(load("product_no_campaign.html"), BRA, NOW)
    assert [v.size_label for v in product.variants] == ["S", "M", "L", "XL"]
    assert {v.price_minor for v in product.variants} == {49999}
    assert {v.original_price_minor for v in product.variants} == {None}
    assert all(v.in_stock for v in product.variants)


def test_mostly_sold_out_product_keeps_every_size() -> None:
    product = parser.parse_product(load("product_mostly_sold_out.html"), BABY_SET, NOW)
    assert [(v.size_label, v.in_stock) for v in product.variants] == [
        ("1-3 Ay (62cm)", True),
        ("3-6 Ay (68cm)", False),
        ("6-9 Ay (74cm)", False),
        ("9-12 Ay (80cm)", False),
        ("12-18 Ay (86cm)", False),
    ]
    assert product.variants[0].price_minor == 14999  # Sepette %70 of 499.99


def test_page_without_product_data_raises() -> None:
    html = "<html><body>Bakım çalışması</body></html>"
    assert parser.has_product_data(html) is False
    with pytest.raises(ValueError, match="DataLayer"):
        parser.parse_product(html, TROUSERS, NOW)


def test_sitemaps() -> None:
    assert parser.product_sitemaps(load("sitemap_index.xml")) == [
        f"{BASE}/sharedxml/tr-tr/product-3.xml",
        f"{BASE}/sharedxml/tr-tr/product.xml",
    ]
    assert parser.sitemap_locs(load("sitemap_product.xml")) == [TROUSERS, BRA]
    with pytest.raises(ValueError, match="no product id"):
        parser.product_id(f"{BASE}/kadin-giyim")


def _site(robots: str = "User-agent: *\nDisallow: *--*\n") -> httpx.MockTransport:
    pages = {
        "/robots.txt": robots,
        "/sharedxml/tr-tr/sitemapindex.xml": load("sitemap_index.xml"),
        "/sharedxml/tr-tr/product.xml": load("sitemap_product.xml"),
        "/sharedxml/tr-tr/product-3.xml": load("sitemap_product-3.xml"),
        urlsplit(TROUSERS).path: load("product_campaign_waist_length.html"),
        urlsplit(BRA).path: load("product_no_campaign.html"),
        urlsplit(BABY_SET).path: load("product_mostly_sold_out.html"),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        body = pages.get(request.url.path)
        return httpx.Response(404) if body is None else httpx.Response(200, text=body)

    return httpx.MockTransport(handler)


async def no_sleep(seconds: float) -> None:
    return None


async def collect(transport: httpx.MockTransport) -> list[RawProduct | ItemFailure]:
    client = PoliteClient(user_agent="realdrop-bot/test", transport=transport, sleep=no_sleep)
    async with client:
        return [item async for item in DefactoCollector(client, now=lambda: NOW).fetch_catalog()]


async def test_collector_walks_sitemaps_dedupes_and_skips_missing_products() -> None:
    results = await collect(_site())

    products = [r for r in results if isinstance(r, RawProduct)]
    failures = [r for r in results if isinstance(r, ItemFailure)]
    # Pages download concurrently, so order is not guaranteed; the trousers appear in both
    # sitemaps but are fetched once.
    assert sorted(p.external_id for p in products) == ["3272557", "3455834", "3518142"]
    assert failures == [ItemFailure(source=GONE, reason="HTTP 404")]


def _broken(paths: set[str]) -> httpx.MockTransport:
    """The normal fake site, except that these paths always answer 502."""
    site = _site()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path in paths:
            return httpx.Response(502)
        return site.handle_request(request)

    return httpx.MockTransport(handler)


async def test_one_broken_page_is_skipped_not_the_whole_run() -> None:
    results = await collect(_broken({urlsplit(BRA).path}))
    products = [r for r in results if isinstance(r, RawProduct)]
    failures = [r for r in results if isinstance(r, ItemFailure)]
    assert sorted(p.external_id for p in products) == ["3272557", "3455834"]
    assert any(f.source == BRA and "HTTP 502" in f.reason for f in failures)


async def test_broken_pages_in_a_row_stop_the_run() -> None:
    every_product = {urlsplit(u).path for u in (TROUSERS, BRA, BABY_SET, GONE)}
    with pytest.raises(CollectorServerError, match="HTTP 502"):
        await collect(_broken(every_product))


async def test_collector_skips_a_url_robots_disallows() -> None:
    robots = "User-agent: *\nDisallow: /*sutyen*\n"
    results = await collect(_site(robots))
    failures = [r for r in results if isinstance(r, ItemFailure)]
    assert ItemFailure(source=BRA, reason="robots.txt disallows this URL") in failures


async def test_collector_stops_when_pages_stop_looking_like_products() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/sharedxml/tr-tr/sitemapindex.xml":
            return httpx.Response(200, text=load("sitemap_index.xml"))
        if request.url.path.endswith(".xml"):
            urls = "".join(f"<url><loc>{BASE}/urun-{n:07d}</loc></url>" for n in range(50))
            return httpx.Response(
                200,
                text=f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
            )
        return httpx.Response(200, text="<html>Lütfen bekleyin...</html>")  # challenge-like page

    # With pages in flight, two can finish in the same tick, so the message may say 20 or 21.
    with pytest.raises(CollectorBlockedError, match=r"2[01] product pages in a row"):
        await collect(httpx.MockTransport(handler))


def test_dry_run_formats_prices_turkish_style() -> None:
    from realdrop.collectors.run import describe, format_try

    assert format_try(129999) == "1.299,99 TL"
    assert format_try(5) == "0,05 TL"
    product = parser.parse_product(load("product_campaign_waist_length.html"), TROUSERS, NOW)
    assert "779,99 TL (claimed 1.299,99 TL)" in describe(product)


async def test_collector_only_fetches_its_shard() -> None:
    client = PoliteClient(user_agent="realdrop-bot/test", transport=_site(), sleep=no_sleep)
    seen: list[str] = []
    async with client:
        for index in range(2):
            collector = DefactoCollector(client, shard=Shard(index, 2), now=lambda: NOW)
            seen += [
                item.source if isinstance(item, ItemFailure) else str(item.url)
                async for item in collector.fetch_catalog()
            ]
    assert sorted(seen) == sorted({TROUSERS, BRA, BABY_SET, GONE})  # each exactly once


def test_sitemap_with_stale_tail_after_the_root_still_parses() -> None:
    # Shape of DeFacto's product-5.xml on 24 Oct 2026.
    xml = load("sitemap_product.xml") + "let Yaka Kazak</image:title>\n  </url>\n</urlset>\n"
    assert parser.sitemap_locs(xml) == [TROUSERS, BRA]


def test_sitemap_that_is_not_xml_still_raises() -> None:
    with pytest.raises(ET.ParseError):
        parser.sitemap_locs("<html>Bakım</html")
