"""Category rules on real shop text (DeFacto, Koton, Mudo, GAP, M&S, Damat Tween, Les Benjamins,
Ramsey, Lufian, TommyLife, Hatemoğlu; collected 24-27 Oct 2026)."""

import pytest

from realdrop.pipeline.categorize import CATEGORIES, categorize
from realdrop.text import fold


@pytest.mark.parametrize(
    ("category_raw", "title", "expected"),
    [
        # The shop's category decides when it says something.
        (
            "Erkek > Giyim > Tişört",
            "Ultra Yumuşak Regular Fıt Polo Yaka Kısa Kollu Polo Tişört",
            "tshirts",
        ),
        ("Erkek > Giyim > Şort", "Ultra Yumuşak Relax Fıt Esnek Belli Jean Bermuda Şort", "shorts"),
        ("Erkek > Giyim > Yüzme Şortu", "Regular Fit Desenli Deniz Şortu", "swimwear"),
        ("Erkek > Giyim > Jean", "Slim Fit Jean Pantolon", "jeans"),
        ("Kot Pantolon", "Pamuklu Normal Bel Slim Fit Jean Pantolon - Brad Jean", "jeans"),
        ("Erkek > Giyim > Ceket", "Boxy Fit Fermuarlı Suni Deri Ceket", "jackets"),
        ("Erkek > Giyim > Ceket", "Slim Fit Astarlı Blazer Ceket", "suits"),
        ("DIŞ GİYİM", "Erkek Kahverengi Regular Fit Kadife Yaka Kısa Mont", "jackets"),
        ("SWEATSHIRT", "Erkek Siyah Fermuarlı Dik Yaka Sweatshirt", "sweatshirts"),
        ("Eşofman Alt", "Logo Jogger Eşofman Altı", "tracksuits"),
        ("ESOFMAN ÜST", "Tween Ekru Rayon Kazak", "tracksuits"),
        ("TAKIM ELBISE", "Damat Regular Fit Siyah Çizgili %100 Yün Takim Elbise", "suits"),
        ("Pijama & Sabahlık", "Saf Pamuklu Pijama Takımı", "underwear"),
        ("Atkı & Eldiven", "Fitil Detaylı Örme Atkı", "accessories"),
        ("Erkek > Aksesuar > Çorap", "5'li Patik Çorap", "underwear"),
        ("Erkek > Aksesuar > Çanta", "Erkek Suni Deri Çapraz Çanta", "bags"),
        ("Erkek > Ayakkabı > Terlik", "Erkek Terlik", "shoes"),
        (
            "Erkek > Üst Giyim > Erkek Kazak >Erkek Triko Kazak",
            "Rıver Erkek Kazak Vizon",
            "knitwear",
        ),
        ("ERKEK > ÜST GİYİM > T-Shirt", "Parlament Oversize Fit Baskılı Erkek T-Shirt", "tshirts"),
        (
            "Koleksiyon > Takım Elbise > Slim Fit Takım Elbise",
            "Lacivert Kareli Takım Elbise",
            "suits",
        ),
        (
            "Koleksiyon > Aksesuar > Takı > Bileklik",
            "Turuncu Hematit Taşlı Erkek Bileklik",
            "accessories",
        ),
        # English product types (Les Benjamins).
        ("Short Sleeve Tees", "SHORT SLEEVE TEE 063", "tshirts"),
        ("Zip Hoodies", "ZIP HOODIE", "sweatshirts"),
        ("Sweatpants", "SWEATPANTS", "tracksuits"),
        ("Track Tops", "HOODED TRACK TOP", "tracksuits"),
        ("Pants", "PLEATED PANTS", "trousers"),
        ("Denim Pants", "WIDE LEG DENIM PANTS", "jeans"),
        ("Leather Jackets", "ZIP UP LEATHER JACKET", "jackets"),
        ("Cardigans", "MOHAIR CARDIGAN", "knitwear"),
        ("Caps", "PRINTED BASEBALL CAP", "accessories"),
        ("Socks", "LOGO SOCKS", "underwear"),
        # No category (Ramsey): the title's last item word decides.
        (None, "Gri Çizgili Regular Fit Uzun Klasik Gömlek", "shirts"),
        (None, "Ekru Polo Yaka Jakarlı Triko", "knitwear"),
        (None, "Haki Regular Fit Gömlek Yaka Süet Deri Mont", "jackets"),
        (None, "Antrasit Regular Fit Casual Örme Triko Yelek", "knitwear"),
        (None, "Gri Düz Slim Fit Denim Pamuk Karışımlı Pantolon", "jeans"),
        (None, "Haki Düz Dokuma Regular Fit Casual Yün Karışımlı Pantolon", "trousers"),
        (None, "Beyaz Desenli Fitted Fit Duble Manşet Ata Yaka Smokin Gömlek", "shirts"),
        (None, "Siyah Deri Casual Loafer", "shoes"),
        (None, "Koyu Gri Kruvaze Yaka Dokuma Pardösü", "jackets"),
        (None, "Lacivert Eşofman Altı", "tracksuits"),
        # Nothing usable.
        (None, None, None),
        ("Koleksiyon", "Hediye Kartı", None),
        ("Skirts", "PLEATED SKIRT", None),
    ],
)
def test_categorize(category_raw: str | None, title: str | None, expected: str | None) -> None:
    assert categorize(category_raw, title) == expected


def test_categories_are_unique() -> None:
    assert len(set(CATEGORIES)) == len(CATEGORIES)


@pytest.mark.parametrize(
    ("text", "folded"),
    [("TAKIM ELBISE", "takim elbise"), ("Eşofman Altı", "esofman alti"), ("İÇ GİYİM", "ic giyim")],
)
def test_fold(text: str, folded: str) -> None:
    assert fold(text) == folded
