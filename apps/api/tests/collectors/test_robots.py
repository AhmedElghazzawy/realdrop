"""RFC 9309 matching, incl. the wildcard rules real shops use (stdlib robotparser ignores them)."""

import pytest

from realdrop.collectors.robots import RobotsRules

UA = "realdrop-bot/0.1 (+https://github.com/AhmedElghazzawy/realdrop)"
SHOP = "https://shop.example.com"

DEFACTO_LIKE = """
# comment
User-agent: *
Disallow: *q=*
Disallow: *--*
Disallow: /product/
Disallow: /tr-tr/
Disallow: /*sortorder*

User-agent: AdsBot-Google
Disallow:
"""


@pytest.mark.parametrize(
    ("path", "allowed"),
    [
        ("/tailored-fit-duz-paca-pantolon-3375263", True),
        ("/sharedxml/tr-tr/product.xml", True),
        ("/arama?q=ceket", False),  # wildcard inside the query
        ("/some--thing-123", False),  # wildcard in the middle of the path
        ("/product/123", False),
        ("/tr-tr/anything", False),
        ("/pantolon?sortorder=asc", False),
        ("/robots.txt", True),
    ],
)
def test_wildcard_rules(path: str, allowed: bool) -> None:
    rules = RobotsRules(DEFACTO_LIKE, UA)
    assert rules.can_fetch(SHOP + path) is allowed


def test_dollar_anchors_the_end() -> None:
    rules = RobotsRules("User-agent: *\nDisallow: /*.pdf$\n", UA)
    assert not rules.can_fetch(f"{SHOP}/files/a.pdf")
    assert rules.can_fetch(f"{SHOP}/files/a.pdf?download=1")


def test_longest_match_wins_and_allow_wins_ties() -> None:
    rules = RobotsRules(
        "User-agent: *\nDisallow: /shop/\nAllow: /shop/jeans/\nDisallow: /x\nAllow: /x\n", UA
    )
    assert not rules.can_fetch(f"{SHOP}/shop/coats")
    assert rules.can_fetch(f"{SHOP}/shop/jeans/1")  # longer Allow beats shorter Disallow
    assert rules.can_fetch(f"{SHOP}/x")  # same length: Allow wins


def test_our_group_replaces_the_star_group() -> None:
    text = "User-agent: *\nDisallow: /\n\nUser-agent: REALDROP-BOT\nAllow: /\nCrawl-delay: 3\n"
    rules = RobotsRules(text, UA)
    assert rules.can_fetch(f"{SHOP}/anything")
    assert rules.crawl_delay == 3.0


def test_consecutive_user_agent_lines_share_one_group() -> None:
    text = "User-agent: googlebot\nUser-agent: realdrop-bot\nDisallow: /private\n"
    rules = RobotsRules(text, UA)
    assert not rules.can_fetch(f"{SHOP}/private/1")


def test_other_bots_groups_do_not_apply_to_us() -> None:
    rules = RobotsRules("User-agent: EtaoSpider\nDisallow: /\n", UA)
    assert rules.can_fetch(f"{SHOP}/p/1")
    assert rules.crawl_delay is None


def test_empty_disallow_means_allow_and_bad_lines_are_ignored() -> None:
    rules = RobotsRules("garbage line\nUser-agent: *\nDisallow:\nCrawl-delay: soon\n", UA)
    assert rules.can_fetch(f"{SHOP}/a")
    assert rules.crawl_delay is None
