"""Unit tests for domain.text normalization (section 7.1)."""
import pytest

from location_service.domain.text import normalize_text, tokenize


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Glén-Etive ", "glen etive"),
        ("glen   etive", "glen etive"),
        ("GLEN-ETIVE", "glen etive"),
        ("Glen Etive", "glen etive"),
        ("cráter Gale", "crater gale"),
        ("O'Brien, Jr.", "o brien jr"),
        ("  spaced   out  ", "spaced out"),
        ("underscored_name.test", "underscored name test"),
        ("Aeolis Mons", "aeolis mons"),
        ("", ""),
    ],
)
def test_normalize_text(raw, expected):
    assert normalize_text(raw) == expected


def test_tokenize():
    assert tokenize("Glén-Etive") == ["glen", "etive"]
    assert tokenize("a  b	c") == ["a", "b", "c"]
    assert tokenize("") == []
