"""Akinon brands we collect. Feasibility, terms and quirks: docs/brands/README.md (wide scan).

Terms checked 27 Oct 2026: Koton, Mudo, GAP, Damat Tween and Marks & Spencer have no clause
against automated access. (Lacoste, also on Akinon, forbids robots and spiders: not collected.)
"""

from realdrop.collectors.akinon.collector import AkinonCollector


class KotonCollector(AkinonCollector):
    slug = "koton"
    name = "Koton"
    base_url = "https://www.koton.com"
    listing_paths = ("/erkek/",)  # ~7,000 products, 24 per page (27 Oct 2026)


class MudoCollector(AkinonCollector):
    slug = "mudo"
    name = "Mudo"
    base_url = "https://www.mudo.com.tr"
    listing_paths = ("/erkek-giyim/",)


class GapCollector(AkinonCollector):
    slug = "gap"
    name = "GAP"
    base_url = "https://gap.com.tr"
    listing_paths = ("/erkek-giyim/",)


class MarksAndSpencerCollector(AkinonCollector):
    slug = "marksandspencer"
    name = "Marks & Spencer"
    base_url = "https://www.marksandspencer.com.tr"
    # /erkek/ is a landing page without a product list; the sitemap's product URLs name the
    # audience ("erkek-yesil-pamuklu-desenli-pijama-ustu-...").
    sitemap_index = "https://www.marksandspencer.com.tr/sitemap.xml"
    url_pattern = r"\.com\.tr/erkek-"


class DamatTweenCollector(AkinonCollector):
    slug = "damattween"
    name = "Damat Tween"
    base_url = "https://www.damattween.com"
    sitemap_index = "https://www.damattween.com/sitemap.xml"
    default_audience = "men"  # a menswear brand; its products carry no gender attribute
