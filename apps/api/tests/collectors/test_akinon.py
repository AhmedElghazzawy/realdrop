"""Akinon parser and collector, on real product JSON trimmed to the fields the parser reads
(collectors/akinon/fixtures). Listing and sitemap answers are built in the tests."""

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
import pytest

from realdrop.collectors.akinon import parser
from realdrop.collectors.akinon.brands import DamatTweenCollector, KotonCollector
from realdrop.collectors.base import ItemFailure, RawProduct
from realdrop.collectors.http import CollectorBlockedError, PoliteClient

FIXTURES = Path(parser.__file__).parent / "fixtures"
URL = "https://www.koton.com/some-product-1/"


def load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return data


def sizes(product: RawProduct) -> list[tuple[str | None, bool]]:
    return [(v.size_label, v.in_stock) for v in product.variants]


def test_koton_men_jeans_waist_and_length() -> None:
    product = parser.parse_product(load("koton_men_jeans"), URL)
    assert product.external_id == "7WAM40256ND-741"  # model + colour
    assert product.audience == "men"
    assert product.category_raw == "Kot Pantolon"
    assert product.currency == "TRY"
    # Size and length options together: more waist/length pairs than the size list alone.
    assert len(product.variants) == 9
    assert ("30/32", True) in sizes(product) and ("29/30", True) in sizes(product)
    assert {v.color_raw for v in product.variants} == {"KOYU İNDİGO"}  # name, not code "741"
    assert {v.price_minor for v in product.variants} == {139999}
    assert {v.original_price_minor for v in product.variants} == {None}
    assert len(product.image_urls) == 3


def test_size_options_of_another_colour_are_dropped() -> None:
    # Koton points the "7/8 Yaş" option at the EKRU product when LACİVERT lacks that size.
    product = parser.parse_product(load("koton_kids_mixed_colors"), URL)
    assert [label for label, _ in sizes(product)] == [
        "6/7 Yaş",
        "9/10 Yaş",
        "11/12 Yaş",
        "13/14 Yaş",
    ]
    assert product.audience is None  # "Kız Çocuk" (girls) is neither men nor women


def test_retail_price_above_price_is_the_claimed_old_price() -> None:
    product = parser.parse_product(load("mudo_men_discounted"), URL)
    assert {(v.price_minor, v.original_price_minor) for v in product.variants} == {(119900, 219900)}
    assert product.audience == "men"  # from "cinsiyet": "Erkek"
    assert product.category_raw == "SWEATSHIRT"
    assert sizes(product) == [
        ("S", False),
        ("M", True),
        ("L", False),
        ("XL", False),
        ("XXL", True),
    ]


def test_lowercase_gender_value() -> None:
    product = parser.parse_product(load("marksandspencer_men"), URL)
    assert product.audience == "men"  # "gender": "erkek"
    assert product.category_raw == "Pijama & Sabahlık"


def test_colour_that_cannot_be_compared_keeps_every_size() -> None:
    product = parser.parse_product(load("gap_kids"), URL)
    assert len(product.variants) == 8
    assert product.audience is None  # "kiz_bebek"
    assert product.category_raw == "Eşofman Alt"


def test_sold_out_colour_keeps_its_own_size() -> None:
    # Every size option points at another colour; the page (Ekru, XXL) is the only Ekru product.
    product = parser.parse_product(load("damattween_color_sold_out"), URL)
    assert sizes(product) == [("XXL", False)]
    assert product.variants[0].color_raw == "Ekru"
    assert product.external_id == "9TC068600684M-E01"


def test_category_code_suffix_is_dropped_and_missing_gender_is_none() -> None:
    product = parser.parse_product(load("damattween_no_gender"), URL)
    assert product.category_raw == "ESOFMAN ÜST"  # was "ESOFMAN ÜST (159)"
    assert product.audience is None
    assert product.variants[0].color_raw == "Ekru"


@pytest.mark.parametrize(
    ("value", "audience"),
    [
        ("Erkek", "men"),
        ("erkek", "men"),
        ("Kadın", "women"),
        ("KADIN", "women"),
        ("Erkek Çocuk", None),
        ("kiz_bebek", None),
        ("", None),
    ],
)
def test_gender_values(value: str, audience: str | None) -> None:
    assert parser.audience_of({"gender": value}) == audience


# --- collector ---------------------------------------------------------------------------------

KOTON = KotonCollector.base_url


def listing(paths: list[str], page: int, pages: int) -> dict[str, Any]:
    return {
        "pagination": {"current_page": page, "num_pages": pages},
        "products": [{"absolute_url": p} for p in paths],
    }


def koton_site(products: dict[str, dict[str, Any] | str]) -> httpx.MockTransport:
    """Men's listing over two pages; product paths answer with the given JSON or raw text."""
    pages = {1: ["/jean-1/", "/kids-2/"], 2: ["/jean-1-again/", "/gone-3/"]}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /account/\n")
        if path == "/erkek/":
            assert request.headers["accept"] == "application/json"
            page = int(request.url.params.get("page", "1"))
            return httpx.Response(200, json=listing(pages[page], page, len(pages)))
        body = products.get(path)
        if body is None:
            return httpx.Response(404)
        if isinstance(body, str):
            return httpx.Response(200, text=body)
        return httpx.Response(200, json=body)

    return httpx.MockTransport(handler)


async def no_sleep(seconds: float) -> None:
    return None


async def collect(
    collector_class: type[KotonCollector] | type[DamatTweenCollector],
    transport: httpx.MockTransport,
) -> list[RawProduct | ItemFailure]:
    client = PoliteClient(user_agent="realdrop-bot/test", transport=transport, sleep=no_sleep)
    async with client:
        return [item async for item in collector_class(client).fetch_catalog()]


async def test_listing_pages_men_only_and_one_entry_per_colour() -> None:
    jeans = load("koton_men_jeans")
    site = koton_site(
        {"/jean-1/": jeans, "/jean-1-again/": jeans, "/kids-2/": load("koton_kids_mixed_colors")}
    )
    results = await collect(KotonCollector, site)
    products = [r for r in results if isinstance(r, RawProduct)]
    failures = [r for r in results if isinstance(r, ItemFailure)]
    # Both listing pages read; the girls' item dropped (men only); the jeans colour kept once.
    assert [p.external_id for p in products] == ["7WAM40256ND-741"]
    assert failures == [ItemFailure(source=f"{KOTON}/gone-3/", reason="HTTP 404")]


async def test_html_instead_of_json_is_a_failure_and_many_stop_the_run() -> None:
    challenge = "<html>Lütfen bekleyin</html>"
    paths = {f"/p-{n}/": challenge for n in range(30)}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/erkek/":
            return httpx.Response(200, json=listing(list(paths), 1, 1))
        return httpx.Response(200, text=paths[request.url.path])

    with pytest.raises(CollectorBlockedError, match=r"2[01] product pages in a row"):
        await collect(KotonCollector, httpx.MockTransport(handler))


async def test_sitemap_brand_gets_its_default_audience() -> None:
    base = DamatTweenCollector.base_url
    product_url = f"{base}/tween-esofman-ust-1/"

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(404)
        if path == "/sitemap.xml":
            return httpx.Response(200, text=sitemap([f"{base}/sitemaps/sitemap-products-1.xml"]))
        if path == "/sitemaps/sitemap-products-1.xml":
            return httpx.Response(200, text=sitemap([product_url]))
        if path == urlsplit(product_url).path:
            return httpx.Response(200, json=load("damattween_no_gender"))
        return httpx.Response(404)

    (product,) = await collect(DamatTweenCollector, httpx.MockTransport(handler))
    assert isinstance(product, RawProduct)
    assert product.audience == "men"  # no gender attribute; a menswear brand


def sitemap(urls: list[str]) -> str:
    locs = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    return f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{locs}</urlset>'
