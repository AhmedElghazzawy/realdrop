"""Keyword matching on folded Turkish/English shop text, shared by the category and attribute rules.

Keywords are written folded (realdrop.text.fold: Turkish-lowercase, marks dropped), as whole words.
A trailing "*" matches any ending ("gomle*" covers "gomlek" and "gomlegi"); a space matches any run
of whitespace. Pure: no IO.
"""

import re
from collections.abc import Iterable


def keyword_pattern(keyword: str) -> str:
    word = re.escape(keyword.rstrip("*")).replace(r"\ ", r"\s+")
    return rf"\b{word}\w*" if keyword.endswith("*") else rf"\b{word}\b"


def compile_keywords(keywords: Iterable[str]) -> re.Pattern[str]:
    """One regex for a keyword list. Longest first: alternatives are tried in order, so "triko"
    would otherwise match before "triko yelek" gets a chance."""
    ordered = sorted(keywords, key=len, reverse=True)
    return re.compile("|".join(keyword_pattern(k) for k in ordered))
