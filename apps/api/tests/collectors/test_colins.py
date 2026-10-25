"""Colin's parser and collector, on trimmed real pages (collectors/colins/fixtures)."""

from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

from realdrop.collectors.base import ItemFailure, RawProduct
from realdrop.collectors.colins import parser
from realdrop.collectors.colins.collector import ColinsCollector
from realdrop.collectors.http import CollectorBlockedError, PoliteClient

FIXTURES = Path(parser.__file__).parent / "fixtures"
BASE = parser.BASE_URL
JEANS = f"{BASE}/p/baggy-fit-erkek-blue-black-denim-jean-pantolon-50225"
DISCOUNTED_JEANS = f"{BASE}/p/balloon-fit-erkek-mavi-jean-pantolon-46451"
CARDIGAN = f"{BASE}/p/regular-fit-kadin-siyah-hirka-27498"
SWEATER = f"{BASE}/p/regular-fit-polo-yaka-jakarli-erkek-antrasit-kazak-46748"
GONE = f"{BASE}/p/discontinued-erkek-gomlek-11111"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_full_price_jeans_with_sold_out_sizes() -> None:
    product = parser.parse_product(load("product_men_sold_out_sizes.html"), JEANS)
    assert (product.external_id, product.title) == (
        "50225",
        "Baggy Fit Erkek Blue Black Denim Jean Pantolon",  # runs of spaces collapsed
    )
    assert product.category_raw == "Erkek Giyim > Erkek Pantolon"
    assert product.audience == "men"
    assert product.currency == "TRY"
    assert len(product.image_urls) == 8
    first, second = product.variants[:2]
    assert (first.external_sku, first.size_label, first.in_stock) == ("383549", "28-30", True)
    # The "notify me" suffix is dropped from sold-out labels.
    assert (second.size_label, second.in_stock) == ("28-32", False)
    assert {v.price_minor for v in product.variants} == {199990}
    assert {v.original_price_minor for v in product.variants} == {None}
    assert {v.color_raw for v in product.variants} == {"Lution Wash"}
    assert len(product.variants) == 20


def test_discounted_price_keeps_the_claimed_old_price() -> None:
    product = parser.parse_product(load("product_men_discounted.html"), DISCOUNTED_JEANS)
    assert product.variants[0].price_minor == 99999
    assert product.variants[0].original_price_minor == 139990  # "1399,90 TL"


def test_womens_category_skips_the_catalog_wide_levels() -> None:
    product = parser.parse_product(load("product_women_discounted.html"), CARDIGAN)
    # "Kadın Hırka<Tüm Kadın Ürünleri<Kadın Giyim<Tüm Ürünler"
    assert product.category_raw == "Kadın Giyim > Kadın Hırka"
    assert product.audience == "women"
    assert [v.in_stock for v in product.variants] == [True, False, False, False]
    assert product.variants[0].original_price_minor == 99990


def test_campaign_only_category_takes_audience_from_the_title() -> None:
    product = parser.parse_product(load("product_campaign_category.html"), SWEATER)
    assert product.category_raw == "Öğretmenler Günü Hediyesi"
    assert product.audience == "men"
    assert product.description == "%52 Pamuk %48 Akrilik"


@pytest.mark.parametrize(
    ("category", "title", "audience"),
    [
        ("Erkek Giyim > Erkek Pantolon", "Jean", "men"),
        (None, "Regular Fit Kadın Siyah Hırka", "women"),
        (None, "Kemer", None),
        (None, "Erkek ve Kadın Unisex Bere", None),  # both words: unclear, so no audience
        ("Kadın Giyim > Kadın Hırka", "Erkek Arkadaşa Hediye", "women"),  # category wins
    ],
)
def test_audience(category: str | None, title: str, audience: str | None) -> None:
    assert parser._audience(category, title) == audience


def test_not_a_product_page() -> None:
    page = "<html><body>Bakım çalışması</body></html>"
    assert parser.has_product_data(page) is False
    with pytest.raises(ValueError, match="JSON-LD"):
        parser.parse_product(page, JEANS)
    assert parser.has_product_data(load("product_men_sold_out_sizes.html")) is True


def test_product_id() -> None:
    assert parser.product_id(JEANS) == "50225"
    with pytest.raises(ValueError, match="no product id"):
        parser.product_id(f"{BASE}/c/erkek-giyim-modelleri-2")


def _site(pages: dict[str, str] | None = None) -> httpx.MockTransport:
    default = {
        "/robots.txt": "User-agent: *\nDisallow: /*price*\nDisallow: /*search*\n",
        "/SitemapProducts": load("sitemap_products.xml"),
        urlsplit(JEANS).path: load("product_men_sold_out_sizes.html"),
        urlsplit(CARDIGAN).path: load("product_women_discounted.html"),
        urlsplit(SWEATER).path: load("product_campaign_category.html"),
    }
    pages = default | (pages or {})

    def handler(request: httpx.Request) -> httpx.Response:
        body = pages.get(request.url.path)
        return httpx.Response(404) if body is None else httpx.Response(200, text=body)

    return httpx.MockTransport(handler)


async def no_sleep(seconds: float) -> None:
    return None


async def collect(transport: httpx.MockTransport) -> list[RawProduct | ItemFailure]:
    client = PoliteClient(user_agent="realdrop-bot/test", transport=transport, sleep=no_sleep)
    async with client:
        return [item async for item in ColinsCollector(client).fetch_catalog()]


async def test_collector_reads_the_sitemap_dedupes_and_skips_missing() -> None:
    results = await collect(_site())
    products = [r for r in results if isinstance(r, RawProduct)]
    failures = [r for r in results if isinstance(r, ItemFailure)]
    # The cardigan is listed twice but fetched once; pages finish in any order.
    assert sorted(p.external_id for p in products) == ["27498", "46748", "50225"]
    assert failures == [ItemFailure(source=GONE, reason="HTTP 404")]


async def test_collector_stops_when_pages_stop_looking_like_products() -> None:
    urls = "".join(f"<url><loc>{BASE}/p/urun-{n:05d}</loc></url>" for n in range(50))
    sitemap = f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    challenge = {f"/p/urun-{n:05d}": "<html>Lütfen bekleyin...</html>" for n in range(50)}
    with pytest.raises(CollectorBlockedError, match=r"2[01] product pages in a row"):
        await collect(_site({"/SitemapProducts": sitemap, **challenge}))
