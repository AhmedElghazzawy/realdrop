"""Map a shop's own category and title to one of our categories, with fixed keyword rules.

Every shop names categories its own way ("Erkek > Giyim > Tişört", "SWEATSHIRT", "Kot Pantolon",
"Short Sleeve Tees", none at all), so the menu and filters use our short list instead. No AI: the
rules are fixed, cheap and tested (tests/pipeline/test_categorize.py, on real shop text). The LLM
extractor (Phase 5) can refine the products these rules leave as None.

Matching: the shop's most specific category level (the last "a > b > c" part) first, then the
whole path, then the title when the category says nothing usable ("Koleksiyon", missing).

Within one text the keyword that **ends last** wins, because Turkish and English product names
put the item type last: "Jean Bermuda Şort" is shorts, "Polo Yaka Kazak" knitwear, "Short Sleeve
Tees" T-shirts, "Kot Ceket" a jacket. On a tie the earlier rule wins, so the more specific phrase
sits in an earlier rule: "Yüzme Şortu" (swimwear, not shorts), "Kot Pantolon" (jeans, not
trousers), "Blazer Ceket" (suits, not jackets). Keywords are whole words on folded text
(realdrop.text.fold), so "ESOFMAN", "Eşofman" and "eşofman" all match "esofman".
"""

import re
from typing import Final

from realdrop.text import fold

# Our categories, in menu order. Labels live in the web app's i18n files.
CATEGORIES: Final = (
    "tshirts",
    "shirts",
    "knitwear",
    "sweatshirts",
    "jackets",
    "suits",
    "trousers",
    "jeans",
    "shorts",
    "tracksuits",
    "underwear",
    "swimwear",
    "shoes",
    "bags",
    "accessories",
)

# (category, keywords). Keywords are folded; a trailing "*" matches any ending ("gomle*" covers
# "gomlek" and "gomlegi"). The order only breaks ties between matches that end at the same place.
_RULES: Final[list[tuple[str, list[str]]]] = [
    ("swimwear", ["mayo", "mayo sort*", "yuzme sort*", "deniz sort*", "swim*", "boardshort*"]),
    (
        "underwear",
        [
            "boxer*", "kulot*", "atlet*", "corap*", "sock*", "pijama*", "pijama takim*",
            "ev giyim*", "sabahlik*", "underwear", "ic giyim", "brief*", "trunks", "loungewear",
            "pyjama*", "pajama*",
        ],
    ),
    ("suits", ["takim elbise*", "blazer*", "blazer ceket*", "smokin*", "suit", "suits"]),
    ("jeans", ["jean", "jeans", "kot", "kot pantolon*", "denim pantolon*"]),
    (
        "tracksuits",
        [
            "esofman*", "esofman alt*", "esofman ust*", "esofman takim*", "jogger*",
            "sweatpant*", "track*",
        ],
    ),
    ("shorts", ["sort", "sortu", "sortlar*", "bermuda*", "short", "shorts"]),
    ("trousers", ["pantolon*", "trouser*", "pants", "chino*"]),
    ("sweatshirts", ["sweatshirt*", "hoodie*", "sweat"]),
    # "Polo Yaka" is a collar ("Polo Yaka Kazak" is knitwear); a polo shirt says "Polo Tişört".
    ("tshirts", ["tisort*", "t-shirt*", "tshirt*", "tee", "tees", "polos", "polo shirt*"]),
    ("shirts", ["gomle*", "shirt", "shirts", "overshirt*"]),
    (
        "knitwear",
        [
            "kazak*", "triko*", "hirka*", "suveter*", "cardigan*", "knit*", "sweater*", "jumper*",
            "triko yelek*", "orme yelek*", "knit vest*",
        ],
    ),
    (
        "jackets",
        [
            "mont*", "kaban*", "ceket*", "parka*", "yelek*", "yagmurluk*", "dis giyim",
            "jacket*", "coat*", "bomber*", "trench*", "puffer*", "vest*", "outerwear", "palto*",
            "pardesu*", "pardosu*",
        ],
    ),
    (
        "shoes",
        [
            "ayakkabi*", "sneaker*", "bot", "botlar", "cizme*", "terlik*", "loafer*",
            "sandalet*", "shoe*", "boot*", "slipper*", "espadril*",
        ],
    ),
    ("bags", ["canta*", "bag", "bags", "backpack*", "valiz*"]),
    (
        "accessories",
        [
            "aksesuar*", "kemer*", "cuzdan*", "sapka*", "bere*", "atki*", "eldiven*", "gozluk*",
            "kravat*", "papyon*", "saat*", "bileklik*", "kolye*", "yuzuk*", "kartlik*",
            "parfum*", "havlu*", "mendil*", "fular*", "taki", "kol dugme*", "anahtarlik*",
            "semsiye*", "cap", "caps", "beanie*", "scarf*", "scarves", "belt*", "wallet*", "hat",
            "hats", "tie", "ties", "glove*", "sunglasses", "jewel*", "bracelet*", "perfume*",
        ],
    ),
]  # fmt: skip


def _pattern(keyword: str) -> str:
    word = re.escape(keyword.rstrip("*")).replace(r"\ ", r"\s+")
    return rf"\b{word}\w*" if keyword.endswith("*") else rf"\b{word}\b"


# Longest keyword first: regex alternatives are tried in order, so "triko" would otherwise match
# before "triko yelek" gets a chance.
_COMPILED: Final = [
    (category, re.compile("|".join(_pattern(k) for k in sorted(keywords, key=len, reverse=True))))
    for category, keywords in _RULES
]


# A broad shop category narrowed by a word anywhere in the category or title: DeFacto files
# blazers under "Ceket" ("Slim Fit Astarlı Blazer Ceket"), and denim trousers are jeans wherever
# the word sits ("Slim Fit Denim Pamuk Karışımlı Pantolon").
_REFINE: Final = {
    "jackets": ("suits", re.compile(r"\bblazer")),
    "trousers": ("jeans", re.compile(r"\b(denim|jean|jeans|kot)\b")),
}


def categorize(category_raw: str | None, title: str | None) -> str | None:
    """Our category for a product, or None when neither text matches a rule."""
    for text in (_leaf(category_raw), category_raw, title):
        if text and (found := _match(fold(text))):
            refine = _REFINE.get(found)
            if refine and refine[1].search(fold(f"{category_raw or ''} {title or ''}")):
                return refine[0]
            return found
    return None


def _leaf(category_raw: str | None) -> str | None:
    if not category_raw:
        return None
    return category_raw.split(">")[-1].strip() or None


def _match(text: str) -> str | None:
    best: tuple[int, int, str] | None = None  # (end, -rule index, category): the max wins
    for index, (category, pattern) in enumerate(_COMPILED):
        for found in pattern.finditer(text):
            candidate = (found.end(), -index, category)
            if best is None or candidate > best:
                best = candidate
    return best[2] if best else None
