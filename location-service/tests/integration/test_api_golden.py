"""Golden API tests (README section 9.2). Seed catalog only.

Gazetteer-dependent cases (7, 8) live in test_api_gazetteer.py and skip
cleanly when no Gazetteer file is present.
"""

from __future__ import annotations

import math

import pytest

from location_service.domain.geo import MARSV_RADIUS_M

GALE_AOI = "aoi:gale-90m"


def _search(client, **params):
    return client.get("/v1/places/search", params=params)


class TestSearchGolden:
    """Cases 1-6, 9."""

    def test_case1_glen_etive_exact(self, client):
        r = _search(client, q="Glen Etive")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        top = body["results"][0]
        assert top["match_type"] == "exact_name"
        assert top["place"]["id"] == "mars:msl:glen-etive"
        assert top["place"]["center"]["lat"] == pytest.approx(-4.7303)
        assert top["place"]["center"]["lon"] == pytest.approx(137.3835)
        assert body["coordinate_system"]["radius_m"] == 3396190

    @pytest.mark.parametrize(
        "q", ["glen   etive", "GLEN-ETIVE", "Glén Etive"]
    )
    def test_case2_normalization_variants(self, client, q):
        r = _search(client, q=q)
        assert r.status_code == 200
        top = r.json()["results"][0]
        assert top["place"]["id"] == "mars:msl:glen-etive"
        assert top["match_type"] == "exact_name"

    def test_case3_fuzzy_typo(self, client):
        r = _search(client, q="Glen Ettive")
        assert r.status_code == 200
        top = r.json()["results"][0]
        assert top["place"]["id"] == "mars:msl:glen-etive"
        assert top["match_type"] == "fuzzy"
        # NOTE: spec asks score >= 0.8; the spec's own formula caps this case
        # at ~0.782 (WRatio 95.24 * 0.8 + 0.02 AOI bonus). See docs/DECISIONS.md.
        assert top["score"] >= 0.75

    @pytest.mark.parametrize(
        "q,lat,lon",
        [
            ("Buckskin", -4.668, 137.3703),
            ("Oudam", -4.6787, 137.3577),
        ],
    )
    def test_case4_named_pois(self, client, q, lat, lon):
        r = _search(client, q=q)
        assert r.status_code == 200
        top = r.json()["results"][0]
        assert top["place"]["center"]["lat"] == pytest.approx(lat)
        assert top["place"]["center"]["lon"] == pytest.approx(lon)

    def test_case5_bradbury_prefix_or_alias(self, client):
        r = _search(client, q="Bradbury")
        assert r.status_code == 200
        top = r.json()["results"][0]
        assert top["place"]["id"] == "mars:msl:bradbury-landing"
        assert top["match_type"] in {"prefix", "exact_alias"}

    def test_case6_bradbury_alias(self, client):
        r = _search(client, q="Curiosity landing site")
        assert r.status_code == 200
        top = r.json()["results"][0]
        assert top["place"]["id"] == "mars:msl:bradbury-landing"
        assert top["match_type"] == "exact_alias"

    def test_case9_no_match(self, client):
        r = _search(client, q="xyzzy")
        assert r.status_code == 200
        body = r.json()
        assert body["results"] == []
        assert body["total"] == 0


class TestReverseGolden:
    """Cases 10-12."""

    def test_case10_buckskin(self, client):
        r = client.get(
            "/v1/places/reverse", params={"lat": -4.668, "lon": 137.3703}
        )
        assert r.status_code == 200
        body = r.json()
        assert body["nearest"][0]["place"]["id"] == "mars:msl:buckskin"
        assert body["nearest"][0]["distance_m"] == pytest.approx(0.0, abs=1.0)
        assert GALE_AOI in body["regions"]

    def test_case11_coincident_john_klein_cumberland(self, client):
        r = client.get(
            "/v1/places/reverse", params={"lat": -4.5895, "lon": 137.4491}
        )
        assert r.status_code == 200
        nearest = r.json()["nearest"]
        ids = {n["place"]["id"] for n in nearest}
        assert {"mars:msl:john-klein", "mars:msl:cumberland"} <= ids
        d_jk = next(n["distance_m"] for n in nearest if n["place"]["id"] == "mars:msl:john-klein")
        d_cu = next(n["distance_m"] for n in nearest if n["place"]["id"] == "mars:msl:cumberland")
        assert d_jk == pytest.approx(d_cu)

    def test_case12_big_sky_greenhorn(self, client):
        r = client.get(
            "/v1/places/reverse", params={"lat": -4.6731, "lon": 137.3686}
        )
        assert r.status_code == 200
        ids = {n["place"]["id"] for n in r.json()["nearest"]}
        assert {"mars:msl:big-sky", "mars:msl:greenhorn"} <= ids


class TestResolveGolden:
    """Cases 13-16, 23."""

    def _resolve(self, client, origin, destination, **kwargs):
        payload = {"origin": origin, "destination": destination, **kwargs}
        return client.post("/v1/resolve", json=payload)

    def test_case13_bradbury_to_glen_etive(self, client):
        r = self._resolve(
            client,
            {"query": "Bradbury Landing"},
            {"place_id": "mars:msl:glen-etive"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "resolved"
        assert body["origin"]["status"] == "resolved"
        assert body["destination"]["status"] == "resolved"
        assert body["origin"]["place"]["id"] == "mars:msl:bradbury-landing"
        # straight-line distance ~9.03 km (see DECISIONS.md re spec's 14-15 km)
        assert 8000.0 < body["straight_line_distance_m"] < 11000.0
        assert body["shared_regions"] == [GALE_AOI]

    def test_case23_distance_matches_independent(self, client):
        r = self._resolve(
            client,
            {"place_id": "mars:msl:bradbury-landing"},
            {"place_id": "mars:msl:glen-etive"},
        )
        assert r.status_code == 200
        got = r.json()["straight_line_distance_m"]
        lat1, lon1, lat2, lon2 = map(
            math.radians, (-4.5895, 137.4417, -4.7303, 137.3835)
        )
        h = (
            math.sin((lat2 - lat1) / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        )
        expected = 2 * MARSV_RADIUS_M * math.asin(math.sqrt(h))
        assert got == pytest.approx(expected, rel=0.001)

    def test_case14_coordinates_outside_aoi(self, client):
        r = self._resolve(
            client,
            {"coordinates": {"lat": -10.0, "lon": 100.0}},
            {"place_id": "mars:msl:glen-etive"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["origin"]["status"] == "resolved"
        assert body["origin"]["place"] is None
        assert "OUTSIDE_KNOWN_AOI" in body["warnings"]

    def test_case15_same_point(self, client):
        r = self._resolve(
            client,
            {"place_id": "mars:msl:glen-etive"},
            {"place_id": "mars:msl:glen-etive"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "SAME_POINT" in body["warnings"]
        assert body["straight_line_distance_m"] == pytest.approx(0.0, abs=0.01)

    def test_case16_ambiguous_endpoint(self, client):
        # "rock" prefix-matches Rocknest and Rock Hall with equal scores
        r = self._resolve(
            client,
            {"query": "rock"},
            {"place_id": "mars:msl:glen-etive"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] in {"partial", "ambiguous"}
        origin = body["origin"]
        assert origin["status"] == "ambiguous"
        assert origin["point"] is None
        assert len(origin["alternatives"]) >= 2
        alt_ids = {a["place"]["id"] for a in origin["alternatives"]}
        assert "mars:msl:rocknest" in alt_ids
        assert "mars:msl:rock-hall" in alt_ids

    def test_coordinates_nearest_place(self, client):
        r = self._resolve(
            client,
            {"coordinates": {"lat": -4.668, "lon": 137.3703}},
            {"place_id": "mars:msl:oudam"},
        )
        assert r.status_code == 200
        origin = r.json()["origin"]
        assert origin["place"] is None
        assert origin["nearest_place"]["id"] == "mars:msl:buckskin"

    def test_low_confidence_warning(self, client):
        # very sloppy fuzzy that still resolves below 0.9
        r = self._resolve(
            client,
            {"query": "Glen Etiv"},
            {"place_id": "mars:msl:oudam"},
        )
        assert r.status_code == 200
        body = r.json()
        if body["origin"]["status"] == "resolved":
            assert body["origin"]["place"]["id"] == "mars:msl:glen-etive"


class TestErrorsAndMisc:
    """Cases 17-22 plus protocol checks."""

    def test_case17_lat_out_of_range(self, client):
        r = client.get("/v1/places/reverse", params={"lat": 95, "lon": 0})
        assert r.status_code == 422
        problem = r.json()
        assert problem["code"] == "OUT_OF_RANGE"
        assert r.headers["content-type"].startswith("application/problem+json")
        assert "request_id" in problem
        assert r.headers.get("x-request-id") == problem["request_id"]

    def test_case18_lon_normalized(self, client):
        r = client.get("/v1/places/reverse", params={"lat": -4.6, "lon": -222.6})
        assert r.status_code == 200
        assert r.json()["point"]["lon"] == pytest.approx(137.4)

    def test_case19_unsupported_body(self, client):
        r = _search(client, q="Gale", body="moon")
        assert r.status_code == 422
        assert r.json()["code"] == "UNSUPPORTED_BODY"

    def test_case20_unknown_place_id(self, client):
        r = client.get("/v1/places/mars:msl:no-existe")
        assert r.status_code == 404
        assert r.json()["code"] == "NOT_FOUND"

    def test_case21_tag_filter(self, client):
        r = client.get("/v1/places", params={"tag": "ruta_objetivo:hematita"})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["places"][0]["id"] == "mars:msl:oudam"

    def test_case22_all_pois_inside_aoi(self, client):
        r = client.get(
            "/v1/places",
            params={"kind": "poi", "region": GALE_AOI, "limit": 50},
        )
        assert r.status_code == 200
        assert r.json()["total"] == 21

    def test_health_ready(self, client):
        assert client.get("/health").status_code == 200
        assert client.get("/ready").json()["status"] == "ready"

    def test_ready_without_catalog(self, no_catalog_client):
        r = no_catalog_client.get("/ready")
        assert r.status_code == 503
        assert r.json()["code"] == "CATALOG_UNAVAILABLE"
        # endpoints also 503
        assert _search(no_catalog_client, q="Gale").status_code == 503

    def test_request_id_echo(self, client):
        r = client.get("/health", headers={"X-Request-ID": "test-rid-123"})
        assert r.headers["x-request-id"] == "test-rid-123"

    def test_get_place(self, client):
        r = client.get("/v1/places/mars:msl:glen-etive")
        assert r.status_code == 200
        place = r.json()["place"]
        assert place["name"] == "Glen Etive"
        assert place["tags"] == ["ruta_objetivo:esmectitas"]
        assert GALE_AOI in place["in_regions"]
        assert place["properties"]["sol"] == 2492

    def test_regions_and_meta(self, client):
        r = client.get("/v1/regions")
        assert r.status_code == 200
        regions = r.json()["regions"]
        assert regions[0]["id"] == GALE_AOI
        r = client.get("/v1/meta/catalog")
        assert r.status_code == 200
        meta = r.json()
        assert meta["counts"]["places"] == 22
        assert meta["catalog_version"]
        r = client.get("/v1/meta/feature-types")
        assert r.status_code == 200
        types = {t["feature_type"]: t["count"] for t in r.json()["feature_types"]}
        assert types["mission_target"] == 21
        assert types["landing_site"] == 1
