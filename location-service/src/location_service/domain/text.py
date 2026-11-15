"""Text normalization and tokenization (README section 7.1). Pure, no I/O."""

from __future__ import annotations

import re
import unicodedata

_PUNCT_RE = re.compile(r"[-_'.,]+")
_SPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    """Canonical form for names, aliases, queries and descriptors.

    Order (spec 7.1): NFKD + strip diacritics -> casefold -> replace
    - _ ' . , with spaces -> collapse spaces and trim.
    """
    decomposed = unicodedata.normalize("NFKD", value)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    folded = stripped.casefold()
    spaced = _PUNCT_RE.sub(" ", folded)
    return _SPACE_RE.sub(" ", spaced).strip()


def tokenize(value: str) -> list[str]:
    """Normalized whitespace-separated tokens."""
    return normalize_text(value).split()
