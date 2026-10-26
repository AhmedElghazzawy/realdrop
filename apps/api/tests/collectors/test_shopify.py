"""Shopify parser and collector, on real `/products.json` products trimmed to the fields the parser
reads (collectors/shopify/fixtures). The home page and catalog pages are built in the tests."""

import copy
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from realdrop.collectors.base import ItemFailure, RawProduct, Shard
from realdrop.collectors.http import CollectorError, PoliteClient
from realdrop.collectors.shopify import parser
from realdrop.collectors.shopify.brands import LesBenjaminsCollector
from realdrop.collectors.shopify.collector import ShopifyCollector

FIXTURES = Path(parser.__file__).parent / "fixtures"
BASE = "https://shop.example.com"


def products(name: str) -> list[dict[str, Any]]:
    data = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return list(data["products"])


def parse(product: dict[str, Any]) -> list[RawProduct]:
    return parser.parse_product(product, BASE, "TRY")


def test_men_jacket_sizes_stock_and_identity() -> None:
    (jacket,) = parse(products("lesbenjamins_page")[0])
    assert jacket.external_id == "9014965665871-Black"
    assert str(jacket.url) == (
        f"{BASE}/products/zip-up-leather-jacket-lb26fwclamulj-001?variant=46434130952271"
    )
    assert jacket.audience == "men"
    assert jacket.category_raw == "Leather Jackets"
    assert jacket.currency == "TRY"
    assert [(v.size_label, v.in_stock) for v in jacket.variants][:4] == [
        ("XXS", False),
        ("XS", False),
        ("S", True),
        ("M", True),
    ]
    assert {v.color_raw for v in jacket.variants} == {"Black"}
    # compare_at_price "0.00" means no old price.
    assert {(v.price_minor, v.original_price_minor) for v in jacket.variants} == {(1999900, None)}


def test_gender_tags() -> None:
    _, women, unisex = products("lesbenjamins_page")
    assert parse(women)[0].audience == "women"
    assert parse(unisex)[0].audience is None  # "unisex" is neither
    assert parser._audience(["men", "women"]) is None
    assert parser._audience(["x-men"]) is None
    assert parser._audience(["Erkek"]) == "men"


def test_fit_and_size_options_join_and_compare_at_is_the_old_price() -> None:
    suit, shirt = (parse(p)[0] for p in products("ramsey_page"))
    assert suit.variants[0].size_label == "6 DROP/46"  # Renk / Kalıp / Beden
    assert suit.variants[0].color_raw == "Antrasit"
    assert (suit.variants[0].price_minor, suit.variants[0].original_price_minor) == (
        999500,
        2499500,
    )
    assert suit.category_raw is None  # Ramsey leaves product_type empty
    assert shirt.variants[0].price_minor == 27920  # "279.20"


def test_a_product_with_two_colours_becomes_two_products() -> None:
    jacket = copy.deepcopy(products("lesbenjamins_page")[0])
    brown = copy.deepcopy(jacket["variants"][2])
    brown.update(id=1, option1="Brown", title="Brown / S", available=False)
    jacket["variants"].append(brown)
    jacket["images"].append({"src": "https://cdn.example.com/brown.jpg", "variant_ids": [1]})
    black, brown_product = parse(jacket)
    assert brown_product.external_id == "9014965665871-Brown"
    assert [(v.size_label, v.in_stock) for v in brown_product.variants] == [("S", False)]
    assert [str(u) for u in brown_product.image_urls] == ["https://cdn.example.com/brown.jpg"]
    assert str(brown_product.url).endswith("?variant=1")
    assert len(black.variants) == 8


def test_a_product_without_options() -> None:
    bag = copy.deepcopy(products("lesbenjamins_page")[2])
    bag["options"] = [{"name": "Title", "position": 1, "values": ["Default Title"]}]
    bag["variants"][0].update(option1="Default Title", option2=None)
    (product,) = parse(bag)
    assert product.external_id == "9015218536527"
    assert product.variants[0].size_label is None
    assert product.variants[0].color_raw is None


# --- collector ---------------------------------------------------------------------------------


def home(currency: str) -> str:
    return f'<script>Shopify.currency = {{"active":"{currency}","rate":"1.0"}};</script>'


def shop(pages: list[list[dict[str, Any]]], currency: str = "TRY") -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /cart\n")
        if path == "/":
            return httpx.Response(200, text=home(currency))
        if path == "/products.json":
            assert request.url.params["limit"] == "250"
            page = int(request.url.params["page"])
            return httpx.Response(
                200, json={"products": pages[page - 1] if page <= len(pages) else []}
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


class Shop(ShopifyCollector):
    slug = "shop"
    name = "Shop"
    base_url = BASE


class MenswearShop(Shop):
    default_audience = "men"


async def no_sleep(seconds: float) -> None:
    return None


async def collect(
    collector_class: type[ShopifyCollector],
    transport: httpx.MockTransport,
    shard: Shard | None = None,
) -> list[RawProduct | ItemFailure]:
    client = PoliteClient(user_agent="realdrop-bot/test", transport=transport, sleep=no_sleep)
    async with client:
        return [item async for item in collector_class(client, shard=shard).fetch_catalog()]


async def test_reads_every_page_and_keeps_men_only() -> None:
    men, women, unisex = products("lesbenjamins_page")
    broken = {"handle": "broken", "id": 9}  # no options or variants
    results = await collect(Shop, shop([[men, women], [unisex, broken]]))
    assert [r.external_id for r in results if isinstance(r, RawProduct)] == ["9014965665871-Black"]
    (failure,) = [r for r in results if isinstance(r, ItemFailure)]
    assert failure.source == f"{BASE}/products/broken"
    assert failure.reason.startswith("KeyError")


async def test_a_menswear_brand_gets_its_default_audience() -> None:
    results = await collect(MenswearShop, shop([products("ramsey_page")]))
    assert [r.audience for r in results if isinstance(r, RawProduct)] == ["men", "men"]


async def test_shards_split_the_products() -> None:
    pages = [products("ramsey_page") + products("lesbenjamins_page")]
    halves = [await collect(MenswearShop, shop(pages), Shard(i, 2)) for i in range(2)]
    ids = [{r.external_id for r in half if isinstance(r, RawProduct)} for half in halves]
    assert not ids[0] & ids[1]
    assert len(ids[0] | ids[1]) == 4  # the women's jacket is dropped in both


async def test_stops_when_the_shop_shows_another_currency() -> None:
    with pytest.raises(CollectorError, match="shows prices in USD, expected TRY"):
        await collect(Shop, shop([products("ramsey_page")], currency="USD"))


def test_les_benjamins_is_configured() -> None:
    assert LesBenjaminsCollector.base_url == "https://lesbenjamins.com"
    assert LesBenjaminsCollector.only_audience == "men"
