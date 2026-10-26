"""Turkish-safe text helpers.

Python's str.lower()/str.upper() follow language-neutral Unicode rules, which are wrong for Turkish:
    "I".lower()  -> "i"   (Turkish needs dotless "ı")
    "İ".lower()  -> "i̇"   ("i" + U+0307 combining dot: looks right, breaks equality and search)
    "i".upper()  -> "I"   (Turkish needs dotted "İ")
This module is the only place in the codebase allowed to call str.lower()/str.upper() directly.
"""

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")

# Map the four Turkish I letters first; the rest of the alphabet is safe for str.lower()/upper().
_TR_LOWER = str.maketrans({"I": "ı", "İ": "i"})
_TR_UPPER = str.maketrans({"i": "İ", "ı": "I"})


def normalize(text: str) -> str:
    """Return NFC-normalized text with runs of whitespace collapsed to one space and ends stripped.

    NFC matters because retailer feeds sometimes send decomposed letters ("I" + U+0307 instead of
    "İ"), which look identical but compare unequal.
    """
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", text)).strip()


def tr_lower(text: str) -> str:
    """Lowercase with Turkish rules: "I" -> "ı", "İ" -> "i". Input is NFC-normalized first."""
    return unicodedata.normalize("NFC", text).translate(_TR_LOWER).lower()


def tr_upper(text: str) -> str:
    """Uppercase with Turkish rules: "i" -> "İ", "ı" -> "I". Input is NFC-normalized first."""
    return unicodedata.normalize("NFC", text).translate(_TR_UPPER).upper()


_TR_FOLD = str.maketrans("ıiğüşöçâîû", "iigusocaiu")


def fold(text: str) -> str:
    """Lowercase (Turkish rules) and drop Turkish letters' marks, for keyword matching only.

    "TAKIM ELBISE", "Takım Elbise" and "takim elbise" all become "takim elbise". Never display it.
    """
    return normalize(tr_lower(text)).translate(_TR_FOLD)
