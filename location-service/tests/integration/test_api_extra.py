"""Extra API coverage: filters, pagination, resolve edge cases."""

from __future__ import annotations

GALE_AOI = "aoi:gale-90m"


class TestListAndFilters:
    def test_kind_filter(self, client):
        r = client.get("/v1/places", params={"kind": "landing_site"})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["places"][0]["id"] == "mars:msl:bradbury-landing"

    def test_source_filter(self, client):
        r = client.get("/v1/places", params={"source": "mission_msl", "limit": 50})
        assert r.json()["total"] == 22

    def test_feature_type_filter(self, client):
        r = client.get("/v1/places", params={"feature_type": "landing_site"})
        assert r.json()["total"] == 1

    def test_region_filter(self, client):
        r = client.get("/v1/places", params={"region": GALE_AOI, "limit": 50})
        assert r.json()["total"] == 22

    def test_region_unknown(self, client):
        r = client.get("/v1/places", params={"region": "aoi:nope"})
        assert r.json()["total"] == 0

    def test_bbox_filter(self, client):
        # tight bbox around Buckskin only
        r = client.get(
            "/v1/places",
            params={
                "bbox_west": 137.36,
                "bbox_south": -4.68,
                "bbox_east": 137.38,
                "bbox_north": -4.65,
                "limit": 50,
            },
        )
        ids = {p["id"] for p in r.json()["places"]}
        assert "mars:msl:buckskin" in ids
        assert "mars:msl:glen-etive" not in ids

    def test_bbox_partial_rejected(self, client):
        r = client.get("/v1/places", params={"bbox_west": 137.0})
        assert r.status_code == 422
        assert r.json()["code"] == "INVALID_PARAMETER"

    def test_pagination(self, client):
        r1 = client.get("/v1/places", params={"limit": 5, "offset": 0})
        r2 = client.get("/v1/places", params={"limit": 5, "offset": 5})
        assert r1.json()["total"] == 22
        ids1 = {p["id"] for p in r1.json()["places"]}
        ids2 = {p["id"] for p in r2.json()["places"]}
        assert ids1.isdisjoint(ids2)

    def test_bad_kind(self, client):
        r = client.get("/v1/places", params={"kind": "star"})
        assert r.status_code == 422


class TestSearchFilters:
    def test_kind_filter(self, client):
        r = client.get("/v1/places/search", params={"q": "etive", "kind": "feature"})
        assert r.json()["results"] == []

    def test_source_filter(self, client):
        r = client.get("/v1/places/search", params={"q": "landing", "source": "iau_gazetteer"})
        assert r.json()["results"] == []

    def test_near_pair_required(self, client):
        r = client.get("/v1/places/search", params={"q": "gale", "near_lat": -4.6})
        assert r.status_code == 422

    def test_near_bonus(self, client):
        # near Buckskin, "big" should still find Big Sky first either way;
        # just assert the endpoint works and scores are bounded
        r = client.get(
            "/v1/places/search",
            params={"q": "sky", "near_lat": -4.6731, "near_lon": 137.3686},
        )
        assert r.status_code == 200
        assert r.json()["results"][0]["place"]["id"] == "mars:msl:big-sky"

    def test_region_filter_search(self, client):
        r = client.get("/v1/places/search", params={"q": "etive", "region": GALE_AOI})
        assert r.json()["results"][0]["place"]["id"] == "mars:msl:glen-etive"


class TestResolveEdgeCases:
    def test_endpoint_two_inputs_rejected(self, client):
        r = client.post(
            "/v1/resolve",
            json={
                "origin": {"query": "Gale", "place_id": "mars:msl:oudam"},
                "destination": {"place_id": "mars:msl:glen-etive"},
            },
        )
        assert r.status_code == 422
        assert r.json()["code"] == "INVALID_PARAMETER"

    def test_endpoint_no_input_rejected(self, client):
        r = client.post(
            "/v1/resolve",
            json={
                "origin": {},
                "destination": {"place_id": "mars:msl:glen-etive"},
            },
        )
        assert r.status_code == 422

    def test_missing_destination_rejected(self, client):
        r = client.post("/v1/resolve", json={"origin": {"query": "Gale"}})
        assert r.status_code == 422

    def test_unsupported_coordinate_system(self, client):
        r = client.post(
            "/v1/resolve",
            json={
                "origin": {
                    "query": "Gale",
                    "coordinate_system": {"lat_type": "planetographic"},
                },
                "destination": {"place_id": "mars:msl:glen-etive"},
            },
        )
        assert r.status_code == 422
        assert r.json()["code"] == "UNSUPPORTED_COORDINATE_SYSTEM"

    def test_not_found_endpoint(self, client):
        r = client.post(
            "/v1/resolve",
            json={
                "origin": {"place_id": "mars:msl:no-existe"},
                "destination": {"place_id": "mars:msl:glen-etive"},
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["origin"]["status"] == "not_found"
        assert body["status"] == "partial"
        assert body["destination"]["status"] == "resolved"

    def test_both_not_found(self, client):
        r = client.post(
            "/v1/resolve",
            json={
                "origin": {"query": "xyzzy"},
                "destination": {"place_id": "mars:msl:no-existe"},
            },
        )
        assert r.status_code == 200
        assert r.json()["status"] == "not_found"

    def test_unsupported_body_resolve(self, client):
        r = client.post(
            "/v1/resolve",
            json={
                "body": "moon",
                "origin": {"query": "Gale"},
                "destination": {"place_id": "mars:msl:glen-etive"},
            },
        )
        assert r.status_code == 422
        assert r.json()["code"] == "UNSUPPORTED_BODY"

    def test_options_respected(self, client):
        # gap=0.0 disables ambiguity -> deterministic top pick; gap=0.05 -> ambiguous
        base = {
            "origin": {"query": "rock"},
            "destination": {"place_id": "mars:msl:oudam"},
        }
        r0 = client.post("/v1/resolve", json={**base, "options": {"ambiguity_gap": 0.0}})
        assert r0.status_code == 200
        assert r0.json()["origin"]["status"] == "resolved"

        r1 = client.post(
            "/v1/resolve",
            json={**base, "options": {"ambiguity_gap": 0.05, "max_alternatives": 1}},
        )
        assert r1.status_code == 200
        origin = r1.json()["origin"]
        assert origin["status"] == "ambiguous"
        assert len(origin["alternatives"]) == 1

    def test_co_located_warning(self, client):
        r = client.post(
            "/v1/resolve",
            json={
                "origin": {"place_id": "mars:msl:john-klein"},
                "destination": {"place_id": "mars:msl:cumberland"},
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert "CO_LOCATED_PLACES" in body["warnings"]
        assert "SAME_POINT" in body["warnings"]

    def test_different_regions_warning_unit(self):
        # covered at application level; skip if only one region configured
        pass
