"""Deterministic search ranking (README sections 7.2-7.4). Pure, no I/O."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from rapidfuzz import fuzz

from location_service.domain.models import Place
from location_service.domain.text import normalize_text


class MatchType(StrEnum):
    EXACT_NAME = "exact_name"
    EXACT_ALIAS = "exact_alias"
    PREFIX = "prefix"
    TOKENS = "tokens"
    FUZZY = "fuzzy"


# precedence for tie-breaking equal base scores (lower wins)
_TYPE_ORDER = {
    MatchType.EXACT_NAME: 0,
    MatchType.EXACT_ALIAS: 1,
    MatchType.PREFIX: 2,
    MatchType.TOKENS: 3,
    MatchType.FUZZY: 4,
}

_BASE_SCORE = {
    MatchType.EXACT_NAME: 1.00,
    MatchType.EXACT_ALIAS: 0.97,
    MatchType.PREFIX: 0.90,
    MatchType.TOKENS: 0.85,
}

_FUZZY_WEIGHT = 0.80  # fuzzy score = WRatio/100 * 0.80 -> range 0.48-0.80
_FUZZY_MIN_RATIO = 60.0  # discard below (LOCATION_FUZZY_MIN_SCORE=0.60 * 100)

_TYPE_BONUS = 0.05
_MISSION_AOI_BONUS = 0.02
_NEAR_BONUS = 0.02
_NEAR_RADIUS_M = 50_000.0

_SOURCE_PRIORITY = {"mission_msl": 0, "iau_gazetteer": 1, "config": 2}


@dataclass(frozen=True)
class MatchResult:
    score: float
    match_type: MatchType


@dataclass(frozen=True)
class RankablePlace:
    """A place plus the context ranking needs (precomputed by the caller)."""

    place: Place
    alias_norms: tuple[str, ...]
    in_aoi: bool  # center inside at least one known region
    dist_to_near_m: float | None = None


@dataclass(frozen=True)
class ScoredPlace:
    place: Place
    score: float
    match_type: MatchType


def build_descriptor_map(
    feature_types: Sequence[str],
    translations: Mapping[str, str],
) -> dict[str, frozenset[str]]:
    """Map normalized query token -> set of normalized feature_types it denotes.

    Includes every feature_type itself plus ES->EN descriptor translations
    (section 7.2). Keys are already-normalized tokens.
    """
    mapping: dict[str, set[str]] = {}

    def add(token: str, feature_type: str) -> None:
        mapping.setdefault(token, set()).add(feature_type)

    for ft in feature_types:
        nft = normalize_text(ft)
        if nft:
            add(nft, nft)
    for es, en in translations.items():
        nes, nen = normalize_text(es), normalize_text(en)
        if nes and nen:
            add(nes, nen)
    return {k: frozenset(v) for k, v in mapping.items()}


def _text_match(
    query_norm: str,
    target_norm: str,
    *,
    is_alias: bool,
    exempt_tokens: frozenset[str],
    fuzzy_min_ratio: float,
) -> MatchResult | None:
    """Best match of query_norm against one normalized target string."""
    if not query_norm or not target_norm:
        return None
    if query_norm == target_norm:
        if is_alias:
            return MatchResult(_BASE_SCORE[MatchType.EXACT_ALIAS], MatchType.EXACT_ALIAS)
        return MatchResult(_BASE_SCORE[MatchType.EXACT_NAME], MatchType.EXACT_NAME)

    words = target_norm.split()
    if target_norm.startswith(query_norm) or any(w.startswith(query_norm) for w in words):
        return MatchResult(_BASE_SCORE[MatchType.PREFIX], MatchType.PREFIX)

    query_tokens = set(query_norm.split())
    required = query_tokens - exempt_tokens
    if required and required <= set(words):
        return MatchResult(_BASE_SCORE[MatchType.TOKENS], MatchType.TOKENS)

    ratio = fuzz.WRatio(query_norm, target_norm)
    if ratio / 100.0 >= fuzzy_min_ratio / 100.0:
        return MatchResult(ratio / 100.0 * _FUZZY_WEIGHT, MatchType.FUZZY)
    return None


def _best_match(
    query_norm: str,
    place: Place,
    alias_norms: Sequence[str],
    *,
    exempt_tokens: frozenset[str],
    fuzzy_min_ratio: float,
) -> MatchResult | None:
    results = [
        r
        for r in (
            _text_match(
                query_norm,
                place.name_norm,
                is_alias=False,
                exempt_tokens=exempt_tokens,
                fuzzy_min_ratio=fuzzy_min_ratio,
            ),
            *(
                _text_match(
                    query_norm,
                    a,
                    is_alias=True,
                    exempt_tokens=exempt_tokens,
                    fuzzy_min_ratio=fuzzy_min_ratio,
                )
                for a in alias_norms
            ),
        )
        if r is not None
    ]
    if not results:
        return None
    return max(results, key=lambda r: (r.score, -_TYPE_ORDER[r.match_type]))


def _sort_key(item: ScoredPlace) -> tuple[float, int, float, str]:
    diameter = item.place.diameter_km if item.place.diameter_km is not None else -1.0
    return (
        -item.score,
        _SOURCE_PRIORITY.get(item.place.source, 3),
        -diameter,
        item.place.name_norm or item.place.name.casefold(),
    )


def rank_query(
    query: str,
    items: Sequence[RankablePlace],
    *,
    descriptor_map: Mapping[str, frozenset[str]],
    fuzzy_min_ratio: float = _FUZZY_MIN_RATIO,
) -> list[ScoredPlace]:
    """Score, adjust, order and filter candidates for a text query."""
    query_norm = normalize_text(query)
    if not query_norm:
        return []
    query_tokens = set(query_norm.split())
    exempt = frozenset(t for t in query_tokens if t in descriptor_map)

    scored: list[ScoredPlace] = []
    for item in items:
        match = _best_match(
            query_norm,
            item.place,
            item.alias_norms,
            exempt_tokens=exempt,
            fuzzy_min_ratio=fuzzy_min_ratio,
        )
        if match is None:
            continue
        score = match.score
        nft = normalize_text(item.place.feature_type)
        if any(nft in descriptor_map.get(t, frozenset()) for t in query_tokens):
            score += _TYPE_BONUS
        if item.place.source == "mission_msl" and item.in_aoi:
            score += _MISSION_AOI_BONUS
        if item.dist_to_near_m is not None and item.dist_to_near_m < _NEAR_RADIUS_M:
            score += _NEAR_BONUS
        scored.append(
            ScoredPlace(place=item.place, score=min(1.0, score), match_type=match.match_type)
        )
    scored.sort(key=_sort_key)
    return scored


def is_ambiguous(scored: Sequence[ScoredPlace], gap: float) -> bool:
    """Section 7.4: ambiguous if runner-up is a different place within gap.

    Exception: exactly one exact_name match from source mission_msl resolves.
    """
    if len(scored) < 2:
        return False
    top = scored[0]
    msl_exact = [
        s
        for s in scored
        if s.match_type == MatchType.EXACT_NAME and s.place.source == "mission_msl"
    ]
    if len(msl_exact) == 1 and msl_exact[0].place.id == top.place.id:
        return False
    runner_up = scored[1]
    if runner_up.place.id == top.place.id:
        return False
    return top.score - runner_up.score < gap
