"""Attribute and style rules on real shop titles (all 11 brands, collected 14 Nov 2026)."""

import pytest

from realdrop.pipeline.tagger import COLORS, STYLES, TAGGER_VERSION, Attributes, tag


def t(
    title: str,
    category: str | None = None,
    colors: tuple[str, ...] = (),
    raw: str | None = None,
) -> Attributes:
    return tag(title, raw, category, colors)


@pytest.mark.parametrize(
    ("names", "expected"),
    [
        (["Siyah"], ("black",)),
        (["SİYAH"], ("black",)),
        (["LACİVERT ÇİZGİLİ"], ("navy",)),
        (["Açık Mavi"], ("light_blue",)),  # the longer phrase wins over "mavi"
        (["Kırık Beyaz"], ("cream",)),
        (["Antrasit"], ("charcoal",)),
        (["Gb melanj/gb melanj"], ("grey",)),
        (["DEVE TÜYÜ"], ("camel",)),
        (["Taş"], ("beige",)),
        (["Vizon"], ("beige",)),
        (["Gülkurusu"], ("pink",)),
        (["Parlament"], ("navy",)),
        (["Army Canvas"], ("khaki",)),
        (["Siyah - Bej"], ("black", "beige")),
        (["Çok Renkli"], ("multi",)),
        (["Çok Renkli", "Siyah"], ("black",)),  # "multi" only when nothing else fits
        (["Standart"], ()),
    ],
)
def test_colour_names_become_canonical_colours(names: list[str], expected: tuple[str, ...]) -> None:
    assert t("Tişört", colors=tuple(names)).colors == expected


def test_colour_falls_back_to_the_title() -> None:
    assert t("Lacivert Regular Fit Keten Gömlek", "shirts").colors == ("navy",)
    assert t("Lacivert Regular Fit Keten Gömlek", "shirts", ("Bordo",)).colors == ("burgundy",)


@pytest.mark.parametrize(
    ("title", "fit"),
    [
        ("Regular Fıt Flanel Gömlek", "regular"),  # DeFacto writes "Fıt"
        ("Tween Super Slim Fit Siyah Chino Pantolon", "slim"),
        ("Relaxed Fit Düz Paça Eşofman Altı", "relaxed"),
        ("Comfort Fit Erkek Beyaz Sweatshirt", "relaxed"),
        ("Taş %100 Pamuk Oversize Fit Basic Erkek T-Shirt", "oversize"),
        ("Boxy Fit Fermuarlı Suni Deri Ceket", "oversize"),
        ("Antony Açık Mavi Standart Kalıp Erkek Şort", "regular"),
        ("Erkek Siyah Kemer", None),
    ],
)
def test_fit(title: str, fit: str | None) -> None:
    assert t(title).fit == fit


@pytest.mark.parametrize(
    ("title", "pattern"),
    [
        ("Erkek Lacivert Çizgili Regular Fit Uzun Kollu Gömlek", "stripe"),
        ("Pamuklu Klasik Yaka Baskılı Ekoseli Poplin Gömlek", "check"),  # check before graphic
        ("Regular Fit Bisiklet Yaka Baskı Detaylı Kısa Kollu Spor Tişört", "graphic"),
        ("Taş Regular Fit Desenli Pamuklu Balıkçı Yaka Triko Kazak", "pattern"),
        ("Regular Fit Polo Yaka Düz Erkek Yeşil Uzun Kol Tişört", "solid"),
        # "Düz Paça" is a straight leg, not a plain fabric.
        ("Regular Fit Orta Bel Düz Paça Erkek Gri Pantolon", None),
    ],
)
def test_pattern(title: str, pattern: str | None) -> None:
    assert t(title).pattern == pattern


def test_materials_and_faux_leather_is_not_leather() -> None:
    assert t("Lacivert Regular Fit %100 Keten Uzun Kol Gömlek").material == ("linen",)
    assert t("Tüylenme Yapmayan Yünlü Bisiklet Yaka Kazak").material == ("wool",)
    assert t("Uzun Kollu Fermuarlı Bomber Suni Deri Ceket").material == ("faux_leather",)
    assert t("%100 Hakiki Deri Casual Ayakkabı").material == ("leather",)


def test_a_grouped_shop_category_does_not_leak_attributes() -> None:
    # The shop files every trouser under "Keten & Kumaş Pantolon" and every knit under
    # "Kazak & Hırka"; neither makes this trouser linen or this sweater a cardigan.
    trousers = t("Regular Fit Gri Pantolon", "trousers", raw="Erkek > Keten & Kumaş Pantolon")
    assert "linen" not in trousers.material
    knit = t("Erkek Haki Bisiklet Yaka Triko Kazak", "knitwear", raw="Erkek > Kazak & Hırka")
    assert knit.subcategory is None
    # A single-item leaf is used when the title says nothing.
    assert t("Erkek Lacivert", "knitwear", raw="Erkek > Hırka").subcategory == "cardigan"


@pytest.mark.parametrize(
    ("title", "subcategory"),
    [
        ("Siyah Regular Fit %100 Pamuk Polo Yaka Tişört", "polo"),  # Turkish for a polo shirt
        ("Yarım Fermuarlı Polo Tişört Kısa Kollu Pamuklu", "polo"),
        ("Siyah Regular Fit Düğmeli Triko Hırka", "cardigan"),
        ("Saykı Bej Slim Fit Mono Yaka Pamuklu Trençkot", "coat"),
        ("Kapaklı Cep Detaylı Dik Yaka Slim Fit Şişme Yelek", "vest"),  # the noun comes last
        ("CARGO PANT 402", "cargo"),
        ("Lumer Spor Erkek Chino Pantolon Slim Fit Antrasit", "chinos"),
        ("Siyah Kravat", "tie"),
    ],
)
def test_subcategory(title: str, subcategory: str | None) -> None:
    assert t(title).subcategory == subcategory


@pytest.mark.parametrize(
    ("title", "category", "colors", "expected", "absent"),
    [
        (
            "Beyaz Slim Fit Çizgili Kruvaze Keten Takım Elbise",
            "suits", ("Beyaz",), {"classic_tailoring", "old_money"}, {"streetwear"},
        ),
        (
            "Tüylenme Yapmayan Yünlü Balıkçı Yaka Regular Fit Mavi Kazak",
            "knitwear", ("Mavi",), {"old_money", "smart_casual"}, {"streetwear"},
        ),
        (
            "Kısa Kollu Regular Fit Pamuk Karışımlı Polo Yaka Tişört",
            "tshirts", ("EKRU",), {"old_money", "minimal"}, set(),
        ),
        (
            "Tommylife Fiesta Pamuklu Kalın Oversize Fit Baskılı Erkek T-Shirt",
            "tshirts", ("Fiesta",), {"streetwear"}, {"old_money", "minimal"},
        ),
        (
            "Regular Fit Cepli Düğmeli Klasik Yaka Uzun Kollu Oduncu Gömlek",
            "shirts", ("Kahverengi",), {"workwear"}, set(),
        ),
        (
            "Kapaklı Cep Detaylı Dik Yaka Slim Fit Şişme Yelek",
            "jackets", ("HAKİ DESENLİ",), {"techwear"}, set(),
        ),
        (
            "Igor Siyah Standart Kalıp Eşofman Takım",
            "tracksuits", ("Siyah",), {"sporty"}, {"smart_casual", "minimal", "old_money"},
        ),
        (
            "Oversize Kolej Desenli Kazak",
            "knitwear", ("SİYAH DESENLİ",), {"preppy", "streetwear"}, {"old_money"},
        ),
        (
            "Bej Standart Kalıp Basic Erkek Sweatshirt",
            "sweatshirts", ("Bej",), {"minimal"}, {"old_money", "streetwear"},
        ),
        (
            "Baggy Fit Geniş Paça Jean Pantolon",
            "jeans", ("Mavi",), {"y2k", "streetwear"}, {"old_money"},
        ),
    ],
)  # fmt: skip
def test_style_tags(
    title: str, category: str, colors: tuple[str, ...], expected: set[str], absent: set[str]
) -> None:
    styles = set(t(title, category, colors).style_tags)
    assert expected <= styles, styles
    assert not (absent & styles), styles


def test_output_uses_only_the_closed_vocabularies() -> None:
    a = t("Damat Comfort Siyah Düz Superfine Wool Takim Elbise", "suits", ("Siyah",))
    assert set(a.style_tags) <= set(STYLES)
    assert set(a.colors) <= set(COLORS)
    assert list(a.style_tags) == [s for s in STYLES if s in a.style_tags]  # stable order


def test_empty_and_odd_input_never_raises() -> None:
    assert t("") == Attributes()
    assert t("   ", None, ("",)).colors == ()
    assert isinstance(TAGGER_VERSION, int)
