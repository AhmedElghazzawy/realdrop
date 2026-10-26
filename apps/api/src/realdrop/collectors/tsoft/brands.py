"""T-Soft brands we collect. Feasibility, terms and quirks: docs/brands/README.md (wide scan).

Terms checked 27 Oct 2026 (membership agreements): Lufian, TommyLife and Hatemoğlu have no clause
against automated access. Not collected: Süvari (Ticimax; its agreement bans "multiple queries
with automated programs"); Sarar (T-Soft; terms page not found, owner to check).
"""

from realdrop.collectors.tsoft.collector import TsoftCollector


class LufianCollector(TsoftCollector):
    slug = "lufian"
    name = "Lufian"
    base_url = "https://www.lufian.com"
    product_sitemap = "https://www.lufian.com/xml/sitemap/product.xml"  # ~4,200 URLs (26 Oct)


class TommyLifeCollector(TsoftCollector):
    slug = "tommylife"
    name = "TommyLife"
    base_url = "https://www.tommylife.com.tr"
    product_sitemap = "https://www.tommylife.com.tr/xml/sitemap/product.xml"  # ~3,800 URLs


class HatemogluCollector(TsoftCollector):
    slug = "hatemoglu"
    name = "Hatemoğlu"
    base_url = "https://www.hatemoglu.com"
    product_sitemap = "https://www.hatemoglu.com/xml/sitemap/product.xml"  # ~11,300 URLs
    default_audience = "men"  # a menswear brand; categories start with "Koleksiyon"
