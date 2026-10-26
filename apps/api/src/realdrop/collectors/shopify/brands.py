"""Shopify brands we collect. Feasibility, terms and quirks: docs/brands/README.md (wide scan).

Les Benjamins (26 Oct 2026): robots.txt allows /products.json; no clause against automated
access found. Products are tagged "men", "women" or "unisex"; we keep "men".
Not collected (yet): Giesto and Ramsey answer our identified requests with 429 after a request
or two (Shopify's "local_rate_limited"); retried later, never worked around.
"""

from realdrop.collectors.shopify.collector import ShopifyCollector


class LesBenjaminsCollector(ShopifyCollector):
    slug = "lesbenjamins"
    name = "Les Benjamins"
    base_url = "https://lesbenjamins.com"
