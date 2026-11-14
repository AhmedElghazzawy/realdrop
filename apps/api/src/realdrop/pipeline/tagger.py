"""Rule-based fashion attributes and style tags for a product. Pure: no IO, no AI.

Input is what every shop gives us: title, the shop's category path, our category
(pipeline/categorize.py) and the variants' colour names. Output follows the attribute schema in
docs/architecture/ai-design.md ("Catalog tagger"): canonical colours, pattern, fit, materials,
formality, season, a subcategory, and style tags from a closed vocabulary.

Unknown stays unknown (None or empty): a rule only fires on words that are actually there. The LLM
pass (later in Phase 5) fills what the rules leave empty and never overwrites a rule hit without a
reason. Bump TAGGER_VERSION whenever a rule changes, so pipeline/tagging.py re-tags every product.

Style tags are heuristics over the other attributes, written down so they can be argued with and
tested (tests/pipeline/test_tagger.py, on real shop titles):
- classic_tailoring: suits, blazers, overcoats, ties, formal shirts and trousers.
- old_money: refined materials or cuts (wool, cashmere, linen, knit polos, oxford, chinos, loafers,
  overcoats) in a quiet palette, no graphics.
- smart_casual: the middle of the formality scale: chinos, polos, knitwear, shirts, loafers.
- minimal: solid basics in neutral colours, no print, no loud pattern.
- streetwear: oversize/boxy/baggy cuts, hoodies, graphics, cargo, joggers, bombers, sneakers.
- workwear: flannel/lumberjack shirts, canvas, cargo, overshirts, denim jackets, boots.
- techwear: technical fabrics (water-repellent, softshell, windbreaker, puffers).
- sporty: tracksuits, performance and training wear, swimwear.
- preppy: varsity/college, rugby, argyle, cable knits, oxford stripes.
- y2k: baggy and wide-leg denim, retro and vintage washes.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Final

from realdrop.pipeline.keywords import compile_keywords
from realdrop.text import fold

TAGGER_VERSION: Final = 1

STYLES: Final = (
    "old_money",
    "streetwear",
    "minimal",
    "smart_casual",
    "classic_tailoring",
    "techwear",
    "workwear",
    "preppy",
    "sporty",
    "y2k",
)
COLORS: Final = (
    "black", "white", "cream", "grey", "charcoal", "navy", "blue", "light_blue", "red",
    "burgundy", "pink", "orange", "yellow", "green", "khaki", "beige", "camel", "brown",
    "purple", "multi",
)  # fmt: skip
NEUTRALS: Final = frozenset(
    {"black", "white", "cream", "grey", "charcoal", "navy", "beige", "camel", "brown", "khaki"}
)
# Quiet palette for old money: neutrals plus deep classic colours.
QUIET: Final = NEUTRALS | {"light_blue", "burgundy", "green", "khaki", "blue"}


def _rules(table: dict[str, list[str]]) -> list[tuple[str, re.Pattern[str]]]:
    return [(name, compile_keywords(words)) for name, words in table.items()]


# Colour words, folded. Order matters only for the "light"/"dark" qualifiers handled below.
_COLOR_RULES: Final = _rules({
    "black": ["siyah", "black", "komur"],
    "white": ["beyaz", "white", "optik beyaz"],
    "cream": ["ekru", "krem", "kirik beyaz", "off white", "off-white", "cream", "ecru", "fildisi",
              "tas beyaz"],
    "charcoal": ["antrasit", "antrasıt", "antra*", "anthracite", "charcoal", "fume", "koyu gri"],
    "grey": ["gri", "grey", "gray", "melanj", "gb melanj", "silver", "gumus"],
    "navy": ["lacivert", "laci", "navy", "parlament", "dark navy", "gece mavisi", "marine"],
    "light_blue": ["acik mavi", "buz mavi*", "light blue", "sky blue", "bebek mavi*"],
    "blue": ["mavi", "blue", "indigo", "saks", "denim", "petrol", "turkuaz", "kobalt", "royal"],
    "burgundy": ["bordo", "burgundy", "murdum", "visne", "maroon", "wine"],
    "red": ["kirmizi", "red", "fiesta", "nar cicegi"],
    "pink": ["pembe", "pink", "gul kurusu", "gulkurusu", "pudra", "fusya", "lila"],
    "orange": ["turuncu", "orange", "kiremit", "somon", "mercan", "tarcin", "safran"],
    "yellow": ["sari", "yellow", "hardal", "mustard", "limon"],
    "green": ["yesil", "green", "mint", "cagla", "zumrut", "kaktus", "sage", "olive", "zeytin",
              "nefti", "su yesili"],
    "khaki": ["haki", "khaki", "dark khaki", "asker*", "army", "military"],
    "beige": ["bej", "beige", "tas", "vizon", "kum", "sand", "stone", "taupe", "kemik", "mink"],
    "camel": ["camel", "deve tuyu", "karamel", "taba", "cognac", "konyak"],
    "brown": ["kahverengi", "kahve", "brown", "dark brown", "cikolata", "chocolate", "acı kahve"],
    "purple": ["mor", "purple", "lavanta", "eflatun"],
    "multi": ["cok renkli", "multicolor", "multi", "karma", "renkli", "allover"],
})  # fmt: skip

_PATTERN_RULES: Final = _rules({
    "stripe": ["cizgili", "cizgi", "stripe*", "cubuk*", "cizgi desen*"],
    "check": ["ekose*", "kareli", "kare desen*", "plaid", "check*", "oduncu", "pied de poule",
              "kazayagi", "glen"],
    "graphic": ["baskili", "baski", "baski detayli", "grafik", "slogan", "logo*", "lisansli",
                "print*", "graphic", "nba", "marvel", "disney", "nakisli", "embroider*"],
    "pattern": ["desenli", "desen", "jakarli", "jakar", "armurlu", "paisley", "sal desen*",
                "floral", "cicek*", "kamuflaj", "camo*", "allover", "geometrik"],
    "solid": ["duz", "basic", "tek renk", "plain", "solid"],
})  # fmt: skip

_FIT_RULES: Final = _rules({
    "oversize": ["oversize*", "oversized", "boxy", "baggy", "bol kesim", "genis kesim",
                 "extra wide", "geniş"],
    "relaxed": ["relaxed", "relax", "comfort", "loose", "rahat kalip", "rahat kesim",
                "rahat form", "wide leg", "genis paca", "bol"],
    "slim": ["slim", "slim fit", "skinny", "dar kesim", "dar kalip", "super slim", "extra slim",
             "muscle fit", "tapered"],
    "regular": ["regular", "regular fit", "standart fit", "standart kalip", "standard fit",
                "normal kesim", "normal kalip", "classic fit", "straight"],
})  # fmt: skip

_MATERIAL_RULES: Final = _rules({
    "cotton": ["pamuk*", "cotton", "pike", "poplin", "oxford", "kanvas", "gabardin", "twill"],
    "linen": ["keten", "linen"],
    "wool": ["yun", "yunlu", "wool", "kase", "merino", "tuvit", "tweed", "flanel kumas"],
    "cashmere": ["kasmir", "cashmere"],
    "leather": ["hakiki deri", "deri", "leather"],
    "faux_leather": ["suni deri", "vegan deri", "faux leather", "pu"],
    "suede": ["suet", "suede", "nubuk"],
    "denim": ["denim", "jean", "jeans", "kot"],
    "corduroy": ["kadife", "fitilli kadife", "corduroy"],
    "fleece": ["polar", "fleece", "sardonlu", "welsoft"],
    "flannel": ["flanel", "flannel", "oduncu"],
    "viscose": ["viskon", "viscose", "rayon", "modal", "tencel", "lyocell"],
    "synthetic": ["polyester", "naylon", "nylon", "elastan", "spandex", "akrilik", "acrylic",
                  "softshell"],
    "satin": ["saten", "satin", "ipek", "silk"],
})  # fmt: skip

_SUBCATEGORY_RULES: Final = _rules({
    "polo": ["polo tisort*", "polo yaka tisort*", "polo yaka t-shirt*", "polo shirt*", "polos",
             "pike polo*"],
    "hoodie": ["hoodie*", "kapusonlu", "kapsonlu", "kapuson*"],
    "overshirt": ["overshirt*", "gomlek ceket*", "shacket*"],
    "cardigan": ["hirka*", "cardigan*"],
    "turtleneck": ["balikci", "boğazli", "turtleneck*", "mock neck"],
    "vest": ["yelek*", "vest*", "gilet*"],
    "blazer": ["blazer*", "spor ceket*", "kumas ceket*"],
    "suit": ["takim elbise*", "smokin*", "suit"],
    "coat": ["palto*", "kaban*", "pardesu*", "pardosu*", "trench*", "trenckot*", "overcoat*",
             "coat"],
    "puffer": ["sisme*", "puffer*", "kapitone mont*", "down jacket*"],
    "bomber": ["bomber*"],
    "chinos": ["chino*"],
    "cargo": ["kargo*", "cargo*"],
    "joggers": ["jogger*"],
    "loafers": ["loafer*", "makosen*", "mokasen*"],
    "sneakers": ["sneaker*", "spor ayakkabi*", "trainer*"],
    "boots": ["bot", "botlar", "chelsea*", "cizme*", "boot*"],
    "tie": ["kravat*", "papyon*", "tie", "bow tie"],
})  # fmt: skip

_SEASON_RULES: Final = _rules({
    "summer": ["yazlik", "summer", "keten", "linen", "sort", "bermuda", "kolsuz", "mayo"],
    "winter": ["kislik", "winter", "yun", "yunlu", "kase", "kasmir", "palto", "kaban", "sisme",
               "puffer", "polar", "fleece", "sardonlu", "bere", "atki", "eldiven", "termal"],
    "transitional": ["mevsimlik", "gecis", "trench*", "trenckot*", "pardesu*"],
})  # fmt: skip

# Signals for the style rules (folded keywords).
_FORMAL = compile_keywords([
    "takim elbise*", "smokin*", "blazer*", "kravat*", "papyon*", "damatlik*", "kruvaze*",
    "klasik gomlek*", "klasik yaka gomlek*", "kumas pantolon*", "klasik pantolon*", "palto*",
    "kol dugme*", "frak*", "yelek takim*", "suit", "tuxedo", "dress shirt*",
])  # fmt: skip
_SMART = compile_keywords([
    "chino*", "polo", "polo yaka", "oxford", "triko*", "kazak*", "hirka*", "loafer*",
    "gabardin*", "smart", "keten gomlek*", "spor ceket*", "kumas ceket*", "balikci",
])  # fmt: skip
_STREET = compile_keywords([
    "oversize*", "boxy", "baggy", "hoodie*", "kapusonlu", "kapsonlu", "kargo*", "cargo*",
    "jogger*", "bomber*", "grafik", "slogan", "graphic", "street*", "skate*", "varsity",
    "nba", "marvel", "lisansli", "sneaker*", "trucker", "tie dye", "yikamali",
])  # fmt: skip
_WORK = compile_keywords([
    "oduncu", "flanel*", "kanvas", "canvas", "kargo*", "cargo*", "overshirt*", "gomlek ceket*",
    "worker", "utility", "workwear", "kot ceket*", "jean ceket*", "denim ceket*", "bot", "botlar",
    "chore", "carpenter",
])  # fmt: skip
_TECH = compile_keywords([
    "su itici", "su gecirmez", "water repellent", "waterproof", "softshell", "teknik",
    "ruzgarlik", "windbreaker", "outdoor", "sisme*", "puffer*", "termal", "gore-tex",
])  # fmt: skip
_SPORT = compile_keywords([
    "esofman*", "performans*", "performance", "antrenman*", "training", "running", "kosu*",
    "dry fit", "dri-fit", "fitness", "gym", "tayt*", "sporcu", "aktif spor", "mayo*", "yuzme*",
])  # fmt: skip
_PREPPY = compile_keywords([
    "kolej*", "college", "varsity", "rugby", "argyle", "baklava desen*", "sac orgu*",
    "cable knit*", "oxford", "v yaka kazak*", "kriket*", "cricket",
])  # fmt: skip
_Y2K = compile_keywords([
    "baggy", "genis paca*", "wide leg*", "retro", "vintage", "y2k", "loose fit jean*",
    "carpenter", "tie dye",
])  # fmt: skip
_REFINED = compile_keywords([
    "kasmir", "cashmere", "merino", "yun*", "wool", "keten", "linen", "oxford", "polo yaka",
    "polo tisort*", "pike", "balikci", "kruvaze", "palto*", "kaban*", "trench*", "loafer*",
    "chino*", "triko*", "hirka*", "suet", "suede", "tuvit", "tweed", "kase", "gabardin*",
])  # fmt: skip

_GROUPED: Final = re.compile(r"&|,|/|\bve\b|\band\b")
# Phrases that contain a pattern word but describe a cut: "düz paça" is a straight leg, not plain.
_NOT_A_PATTERN: Final = re.compile(r"\bduz\s+paca\w*|\bduz\s+kesim\b|\bcizgi\s+detay\w*")
_TOPS: Final = frozenset({"tshirts", "shirts", "knitwear", "sweatshirts"})
_CASUAL_CATEGORIES: Final = frozenset(
    {"tshirts", "sweatshirts", "jeans", "shorts", "tracksuits", "underwear", "swimwear"}
)


@dataclass(frozen=True)
class Attributes:
    colors: tuple[str, ...] = ()
    pattern: str | None = None
    fit: str | None = None
    material: tuple[str, ...] = ()
    formality: str | None = None
    season: tuple[str, ...] = ()
    subcategory: str | None = None
    style_tags: tuple[str, ...] = ()
    # Which text produced each field: "title", "color", "category", "inferred".
    evidence: dict[str, str] = field(default_factory=dict)


def tag(
    title: str,
    category_raw: str | None = None,
    category: str | None = None,
    color_names: Iterable[str] = (),
) -> Attributes:
    """Attributes for one product from its shop text. Never raises on odd input."""
    title_f = fold(title or "")
    # A shop's category often groups items ("Keten & Kumaş Pantolon", "Kazak & Hırka"), so only
    # its leaf is read, and only when it names one thing; our own `category` covers the rest.
    leaf_f = fold(category_raw or "").rsplit(">", 1)[-1].strip()
    single_leaf = leaf_f if leaf_f and not _GROUPED.search(leaf_f) else ""
    text = _NOT_A_PATTERN.sub(" ", f"{title_f} {single_leaf}").strip()
    evidence: dict[str, str] = {}

    colors = _colors(color_names) or _colors([title])
    if colors:
        evidence["colors"] = "color" if _colors(color_names) else "title"
    pattern = _first(_PATTERN_RULES, f"{text} {' '.join(fold(c) for c in color_names)}")
    fit = _last(_FIT_RULES, title_f) or _last(_FIT_RULES, single_leaf)
    material = _all(_MATERIAL_RULES, text)
    if "faux_leather" in material:
        material = tuple(m for m in material if m != "leather")
    subcategory = _last(_SUBCATEGORY_RULES, title_f) or _last(_SUBCATEGORY_RULES, single_leaf)
    season = _all(_SEASON_RULES, text)
    formality = _formality(text, category, subcategory)
    for name, value in (("pattern", pattern), ("fit", fit), ("material", material),
                        ("subcategory", subcategory), ("season", season)):  # fmt: skip
        if value:
            evidence[name] = "title"
    if formality:
        evidence["formality"] = "inferred"

    styles = _styles(text, category, colors, pattern, fit, material, subcategory, formality)
    if styles:
        evidence["style_tags"] = "inferred"
    return Attributes(
        colors=colors,
        pattern=pattern,
        fit=fit,
        material=material,
        formality=formality,
        season=season,
        subcategory=subcategory,
        style_tags=styles,
        evidence=evidence,
    )


def _colors(names: Iterable[str]) -> tuple[str, ...]:
    """Canonical colours in the order they first appear; "multi" only when nothing else fits."""
    found: list[tuple[int, int, str]] = []  # (text index, position, colour)
    for index, name in enumerate(names):
        folded = fold(name or "")
        taken: list[tuple[int, int]] = []
        # Longer phrases first, so "acik mavi" wins over "mavi" and "kirik beyaz" over "beyaz".
        hits = sorted(
            (
                (m.start(), m.end(), colour)
                for colour, rx in _COLOR_RULES
                for m in rx.finditer(folded)
            ),
            key=lambda h: (h[0], -(h[1] - h[0])),
        )
        for start, end, colour in hits:
            if any(start < e and end > s for s, e in taken):
                continue
            taken.append((start, end))
            found.append((index, start, colour))
    ordered = [c for _, _, c in sorted(found)]
    unique = list(dict.fromkeys(ordered))
    if len(unique) > 1 and "multi" in unique:
        unique.remove("multi")
    return tuple(unique[:3])


def _first(rules: Sequence[tuple[str, re.Pattern[str]]], text: str) -> str | None:
    """The first rule (in table order) with any match."""
    return next((name for name, rx in rules if rx.search(text)), None)


def _last(rules: Sequence[tuple[str, re.Pattern[str]]], text: str) -> str | None:
    """The rule whose match ends last; earlier rules win ties (shop titles put the noun last)."""
    best: tuple[int, int, str] | None = None
    for index, (name, rx) in enumerate(rules):
        for m in rx.finditer(text):
            candidate = (m.end(), -index, name)
            if best is None or candidate > best:
                best = candidate
    return best[2] if best else None


def _all(rules: Sequence[tuple[str, re.Pattern[str]]], text: str) -> tuple[str, ...]:
    return tuple(name for name, rx in rules if rx.search(text))


def _formality(text: str, category: str | None, subcategory: str | None) -> str | None:
    if category == "suits" or subcategory in {"suit", "blazer", "tie"} or _FORMAL.search(text):
        return "formal"
    if subcategory in {"polo", "chinos", "loafers", "cardigan", "turtleneck", "coat"}:
        return "smart_casual"
    if _SMART.search(text) or category in {"shirts", "knitwear", "trousers"}:
        return "smart_casual"
    if category in _CASUAL_CATEGORIES or category in {"shoes", "jackets", "bags"}:
        return "casual"
    return None


def _styles(
    text: str,
    category: str | None,
    colors: tuple[str, ...],
    pattern: str | None,
    fit: str | None,
    material: tuple[str, ...],
    subcategory: str | None,
    formality: str | None,
) -> tuple[str, ...]:
    tags: set[str] = set()
    loud = pattern in {"graphic", "pattern"}
    quiet = bool(colors) and all(c in QUIET for c in colors)
    neutral = bool(colors) and all(c in NEUTRALS for c in colors)
    athletic = category in {"tracksuits", "swimwear"} or bool(_SPORT.search(text))

    if formality == "formal":
        tags.add("classic_tailoring")
    if formality == "smart_casual" and not athletic:
        tags.add("smart_casual")
    if (
        _REFINED.search(text)
        and quiet
        and not loud
        and fit != "oversize"
        and category not in {"tracksuits", "underwear", "swimwear", "sweatshirts"}
        and not _STREET.search(text)
    ):
        tags.add("old_money")
    if (
        neutral
        and pattern in {None, "solid"}
        and category in _TOPS | {"trousers", "jackets", "shoes", "bags"}
        and not athletic
        and not _STREET.search(text)
    ):
        tags.add("minimal")
    streety = fit == "oversize" or pattern == "graphic" or bool(_STREET.search(text))
    if streety and category not in {"suits", "underwear"} and formality != "formal":
        tags.add("streetwear")
    if _WORK.search(text) or "flannel" in material or subcategory in {"overshirt", "cargo"}:
        tags.add("workwear")
    if _TECH.search(text) or subcategory == "puffer":
        tags.add("techwear")
    if athletic:
        tags.add("sporty")
    if _PREPPY.search(text):
        tags.add("preppy")
    if _Y2K.search(text) and category in {"jeans", "trousers", "shorts", "tshirts", "sweatshirts"}:
        tags.add("y2k")
    return tuple(s for s in STYLES if s in tags)
