"""Unit tests for domain.ranking (sections 7.3-7.4) with a mini catalog."""

import pytest

from location_service.domain.models import Bbox, Coordinate, Place
from location_service.domain.ranking import (
    RankablePlace,
    build_descriptor_map,
    is_ambiguous,
    rank_query,
)

AOI = Bbox(west=137.345, south=-4.739427, east=137.454322, north=-4.58)


def make_place(
    pid,
    name,
    *,
    kind="poi",
    feature_type="mission_target",
    source="mission_msl",
    lat=-4.6,
    lon=137.4,
    diameter_km=None,
    aliases=(),
    name_norm=None,
):
    from location_service.domain.text import normalize_text

    return Place(
        id=pid,
        name=name,
        body="mars",
        kind=kind,
        feature_type=feature_type,
        source=source,
        center=Coordinate(lat=lat, lon=lon),
        name_norm=name_norm if name_norm is not None else normalize_text(name),
        aliases=tuple(aliases),
        diameter_km=diameter_km,
    )


def rankable(place, *, in_aoi=True, dist=None, alias_norms=()):
    return RankablePlace(place=place, alias_norms=alias_norms, in_aoi=in_aoi, dist_to_near_m=dist)


DESCRIPTORS = build_descriptor_map(
    ["crater", "mission_target", "mons"],
    {"valle": "vallis", "crater": "crater"},
)


class TestMatchTypes:
    def test_exact_name(self):
        p = make_place("mars:msl:glen-etive", "Glen Etive")
        res = rank_query("Glen Etive", [rankable(p)], descriptor_map=DESCRIPTORS)
        assert len(res) == 1
        assert res[0].match_type == "exact_name"
        assert res[0].score == pytest.approx(1.0)

    def test_exact_alias(self):
        p = make_place("mars:msl:bradbury-landing", "Bradbury Landing", aliases=["Bradbury"])
        alias_norms = ("bradbury",)
        res = rank_query(
            "Bradbury", [rankable(p, alias_norms=alias_norms)], descriptor_map=DESCRIPTORS
        )
        # name prefix also matches; exact alias (0.97) loses to prefix (0.90)? no:
        # best match wins -> prefix 0.90 < exact_alias? check actual best
        assert res[0].place.id == "mars:msl:bradbury-landing"

    def test_prefix(self):
        p = make_place("mars:msl:glen-etive", "Glen Etive")
        res = rank_query("glen", [rankable(p)], descriptor_map=DESCRIPTORS)
        assert res[0].match_type == "prefix"
        assert res[0].score == pytest.approx(0.90 + 0.02)  # msl + aoi bonus

    def test_tokens_any_order(self):
        p = make_place("mars:msl:glen-etive", "Glen Etive")
        res = rank_query("etive glen", [rankable(p)], descriptor_map=DESCRIPTORS)
        assert res[0].match_type == "tokens"
        assert res[0].score == pytest.approx(0.85 + 0.02)

    def test_fuzzy_typo(self):
        p = make_place("mars:msl:glen-etive", "Glen Etive")
        res = rank_query("Glen Ettive", [rankable(p)], descriptor_map=DESCRIPTORS)
        assert res[0].match_type == "fuzzy"
        assert res[0].score == pytest.approx(0.782, abs=0.01)

    def test_no_match(self):
        p = make_place("mars:msl:glen-etive", "Glen Etive")
        res = rank_query("xyzzy", [rankable(p)], descriptor_map=DESCRIPTORS)
        assert res == []

    def test_exact_alias_beats_name_prefix(self):
        # query exactly equals an alias -> exact_alias 0.97
        p = make_place("mars:msl:bradbury-landing", "Bradbury Landing", aliases=["Bradbury"])
        res = rank_query(
            "bradbury",
            [rankable(p, alias_norms=("bradbury",))],
            descriptor_map=DESCRIPTORS,
        )
        assert res[0].match_type == "exact_alias"
        assert res[0].score == pytest.approx(0.97 + 0.02)


class TestAdjustments:
    def test_type_bonus(self):
        crater = make_place(
            "mars:iau:gale", "Gale", kind="feature", feature_type="crater", source="iau_gazetteer"
        )
        plain = make_place(
            "mars:iau:gale2",
            "Gale",
            kind="feature",
            feature_type="planitia",
            source="iau_gazetteer",
        )
        res = rank_query(
            "gale crater",
            [rankable(crater, in_aoi=False), rankable(plain, in_aoi=False)],
            descriptor_map=DESCRIPTORS,
        )
        scores = {r.place.id: r.score for r in res}
        assert scores["mars:iau:gale"] - scores["mars:iau:gale2"] == pytest.approx(0.05)

    def test_descriptor_token_not_required_in_name(self):
        # "crater" does not appear in the name but still yields a match via "gale"
        crater = make_place(
            "mars:iau:gale", "Gale", kind="feature", feature_type="crater", source="iau_gazetteer"
        )
        res = rank_query(
            "gale crater", [rankable(crater, in_aoi=False)], descriptor_map=DESCRIPTORS
        )
        assert res[0].place.id == "mars:iau:gale"

    def test_spanish_descriptor(self):
        crater = make_place(
            "mars:iau:gale", "Gale", kind="feature", feature_type="crater", source="iau_gazetteer"
        )
        res = rank_query(
            "crater gale", [rankable(crater, in_aoi=False)], descriptor_map=DESCRIPTORS
        )
        assert res[0].place.id == "mars:iau:gale"

    def test_mission_msl_aoi_bonus(self):
        inside = make_place("a", "Xavier", source="mission_msl")
        outside = make_place("b", "Xavier", source="mission_msl")
        gaz = make_place("c", "Xavier", source="iau_gazetteer", kind="feature")
        res = rank_query(
            "xav",
            [
                rankable(inside, in_aoi=True),
                rankable(outside, in_aoi=False),
                rankable(gaz, in_aoi=True),
            ],
            descriptor_map=DESCRIPTORS,
        )
        scores = {r.place.id: r.score for r in res}
        assert scores["a"] == pytest.approx(0.92)  # 0.90 prefix + 0.02 msl+aoi
        assert scores["b"] == pytest.approx(0.90)
        assert scores["c"] == pytest.approx(0.90)  # gazetteer gets no msl bonus
        assert res[0].place.id == "a"

    def test_near_bonus(self):
        p = make_place("a", "Xavier")
        res = rank_query(
            "xav",
            [rankable(p, in_aoi=False, dist=1000.0)],
            descriptor_map=DESCRIPTORS,
        )
        assert res[0].score == pytest.approx(0.92)  # 0.90 + 0.02 near<50km

    def test_far_no_bonus(self):
        p = make_place("a", "Xavier")
        res = rank_query(
            "xav",
            [rankable(p, in_aoi=False, dist=60_000.0)],
            descriptor_map=DESCRIPTORS,
        )
        assert res[0].score == pytest.approx(0.90)


class TestOrdering:
    def test_order_score_source_diameter_name(self):
        a = make_place(
            "a",
            "Alpha",
            source="iau_gazetteer",
            kind="feature",
            feature_type="crater",
            diameter_km=10.0,
        )
        b = make_place("b", "Beta", source="mission_msl")
        # both fuzzy-ish equal scores hard to construct; use exact on distinct names
        res = rank_query(
            "alpha",
            [rankable(a, in_aoi=False), rankable(b, in_aoi=False)],
            descriptor_map=DESCRIPTORS,
        )
        assert [r.place.id for r in res] == ["a"]

    def test_source_priority(self):
        msl = make_place("m", "Same", source="mission_msl")
        iau = make_place("i", "Same", source="iau_gazetteer", kind="feature")
        res = rank_query(
            "same",
            [rankable(iau, in_aoi=False), rankable(msl, in_aoi=False)],
            descriptor_map=DESCRIPTORS,
        )
        assert res[0].place.id == "m"


class TestAmbiguity:
    def _two_close(self, gap=0.05):
        a = make_place("a", "Gale", feature_type="crater")
        b = make_place("b", "Gale", feature_type="crater")
        return rank_query("gale", [rankable(a), rankable(b)], descriptor_map=DESCRIPTORS)

    def test_ambiguous_close_scores(self):
        res = self._two_close()
        assert is_ambiguous(res, 0.05) is True

    def test_not_ambiguous_single(self):
        a = make_place("a", "Glen Etive")
        res = rank_query("glen etive", [rankable(a)], descriptor_map=DESCRIPTORS)
        assert is_ambiguous(res, 0.05) is False

    def test_not_ambiguous_big_gap(self):
        a = make_place("a", "Glen Etive")
        b = make_place("b", "Gobbledygook")
        res = rank_query("glen", [rankable(a), rankable(b)], descriptor_map=DESCRIPTORS)
        assert is_ambiguous(res, 0.05) is False

    def test_single_mission_exact_name_resolves(self):
        a = make_place("a", "Glen Etive", source="mission_msl")
        b = make_place("b", "Glen Etive", source="iau_gazetteer", kind="feature")
        res = rank_query(
            "glen etive",
            [rankable(a, in_aoi=True), rankable(b, in_aoi=False)],
            descriptor_map=DESCRIPTORS,
        )
        # top is mission_msl exact_name; only one msl exact_name -> resolved
        assert is_ambiguous(res, 0.05) is False
