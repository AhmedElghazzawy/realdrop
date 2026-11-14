"""sitemap_locs: the shared sitemap reader used by the Akinon, Colin's and T-Soft collectors."""

import xml.etree.ElementTree as ET

import pytest

from realdrop.collectors.sitemap import sitemap_locs

A = "https://shop.example.com/regular-fit-pantolon-3455834"
B = "https://shop.example.com/pamuklu-gomlek-3518142"
SITEMAP = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{A}</loc><lastmod>2026-10-24</lastmod></url>
  <url><loc>{B}</loc><lastmod>2026-10-24</lastmod></url>
</urlset>
"""


def test_reads_every_loc_in_order() -> None:
    assert sitemap_locs(SITEMAP) == [A, B]


def test_stale_tail_after_the_root_still_parses() -> None:
    # Shape of DeFacto's product-5.xml on 24 Oct 2026: a truncated old copy after </urlset>.
    assert sitemap_locs(SITEMAP + "let Yaka Kazak</image:title>\n  </url>\n</urlset>\n") == [A, B]


def test_a_page_that_is_not_xml_still_raises() -> None:
    with pytest.raises(ET.ParseError):
        sitemap_locs("<html>Bakım</html")
