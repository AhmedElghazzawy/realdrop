import pytest

from realdrop.text import normalize, tr_lower, tr_upper

COMBINING_DOT = "̇"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("I", "ı"),
        ("İ", "i"),
        ("İSTANBUL", "istanbul"),
        ("IĞDIR", "ığdır"),
        ("KIŞLIK KABAN", "kışlık kaban"),
        ("ŞİŞLİ ÇARŞI", "şişli çarşı"),
        ("Siyah Oversize Kaban", "siyah oversize kaban"),
        ("", ""),
    ],
)
def test_tr_lower(raw: str, expected: str) -> None:
    assert tr_lower(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("i", "İ"),
        ("ı", "I"),
        ("istanbul", "İSTANBUL"),
        ("ıspanak", "ISPANAK"),
        ("kışlık kaban", "KIŞLIK KABAN"),
        ("", ""),
    ],
)
def test_tr_upper(raw: str, expected: str) -> None:
    assert tr_upper(raw) == expected


def test_tr_lower_never_leaves_a_combining_dot() -> None:
    # This is the bug plain str.lower() has: "İ".lower() == "i" + U+0307.
    assert "İ".lower() == "i" + COMBINING_DOT
    assert COMBINING_DOT not in tr_lower("İZMİR")


def test_decomposed_dotted_i_is_handled() -> None:
    decomposed = "I" + COMBINING_DOT + "STANBUL"  # looks like "İSTANBUL" but is two code points
    assert tr_lower(decomposed) == "istanbul"


@pytest.mark.parametrize("word", ["istanbul", "ığdır", "kışlık", "şişli çarşı", "ekru"])
def test_round_trip(word: str) -> None:
    assert tr_lower(tr_upper(word)) == word


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  siyah   kaban \n", "siyah kaban"),
        ("I" + COMBINING_DOT + "zmir", "İzmir"),
        ("tab\tand nbsp", "tab and nbsp"),
        ("", ""),
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert normalize(raw) == expected
