"""Sitemap parsing shared by collectors. Pure: XML text in, URLs out."""

import xml.etree.ElementTree as ET

_SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
_ROOT_ENDS = ("</urlset>", "</sitemapindex>")


def sitemap_locs(xml_text: str) -> list[str]:
    """Every <loc> in a sitemap or sitemap index, in document order.

    DeFacto's product-5.xml (Oct 2026) has stale text after `</urlset>`, as if a shorter file was
    written over a longer one. Everything up to the first closing root tag is a complete document,
    so the tail is cut off; any other XML error still raises.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        end = min(
            (i + len(tag) for tag in _ROOT_ENDS if (i := xml_text.find(tag)) >= 0), default=-1
        )
        if end < 0:
            raise
        root = ET.fromstring(xml_text[:end])
    return [loc.text.strip() for loc in root.iter(f"{_SITEMAP_NS}loc") if loc.text]
