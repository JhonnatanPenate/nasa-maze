"""HTTP adapters against mocked MS3/MS4 (respx) — contract + error mapping."""

import httpx
import pytest
import respx
from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import (
    DomainValidationError,
    NoCoverageError,
    UpstreamUnavailableError,
)
from app.infrastructure.datasources.http_raster_source import HttpRasterSource
from app.infrastructure.datasources.http_terrain_source import HttpTerrainSource

MS3 = "http://ms3.test"
MS4 = "http://ms4.test"
POINT = GeoPoint(lat=-4.62, lon=137.40)
PATH = [GeoPoint(lat=-4.60, lon=137.44), GeoPoint(lat=-4.65, lon=137.42)]


# --- MS3 raster ---------------------------------------------------------


@respx.mock
def test_raster_ping_ok() -> None:
    respx.get(f"{MS3}/health").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "ok",
                "datasets": [{"name": "rejilla", "readable": True}],
            },
        )
    )
    source = HttpRasterSource(httpx.Client(base_url=MS3), "rejilla", retries=0)
    assert source.ping() is True


@respx.mock
def test_raster_ping_down() -> None:
    respx.get(f"{MS3}/health").mock(side_effect=httpx.ConnectError("boom"))
    source = HttpRasterSource(httpx.Client(base_url=MS3), "rejilla", retries=0)
    assert source.ping() is False


@respx.mock
def test_raster_dataset_bands() -> None:
    respx.get(f"{MS3}/raster/rejilla/metadata").mock(
        return_value=httpx.Response(
            200,
            json={"bands": [{"name": "rugosidad_m"}, {"name": "albedo"}]},
        )
    )
    source = HttpRasterSource(httpx.Client(base_url=MS3), "rejilla", retries=0)
    assert source.dataset_bands() == ("rugosidad_m", "albedo")


@respx.mock
def test_raster_point_values_maps_nodata_to_none() -> None:
    respx.get(f"{MS3}/raster/rejilla/point").mock(
        return_value=httpx.Response(
            200,
            json={"values": {"rugosidad_m": 1.5, "fraccion_oscura": None}},
        )
    )
    source = HttpRasterSource(httpx.Client(base_url=MS3), "rejilla", retries=0)
    values = source.point_values(POINT)
    assert values == {"rugosidad_m": 1.5, "fraccion_oscura": None}


@respx.mock
def test_raster_point_404_maps_to_no_coverage() -> None:
    respx.get(f"{MS3}/raster/rejilla/point").mock(
        return_value=httpx.Response(404, json={"detail": "outside extent"})
    )
    source = HttpRasterSource(httpx.Client(base_url=MS3), "rejilla", retries=0)
    with pytest.raises(NoCoverageError):
        source.point_values(POINT)


@respx.mock
def test_raster_sample_500_maps_to_upstream() -> None:
    respx.post(f"{MS3}/raster/rejilla/sample").mock(
        return_value=httpx.Response(500, json={"detail": "boom"})
    )
    source = HttpRasterSource(httpx.Client(base_url=MS3), "rejilla", retries=0)
    with pytest.raises(UpstreamUnavailableError):
        source.sample_band("rugosidad_m", PATH, 90.0)


@respx.mock
def test_raster_point_timeout_maps_to_upstream() -> None:
    respx.get(f"{MS3}/raster/rejilla/point").mock(
        side_effect=httpx.ReadTimeout("slow")
    )
    source = HttpRasterSource(httpx.Client(base_url=MS3), "rejilla", retries=0)
    with pytest.raises(UpstreamUnavailableError):
        source.point_values(POINT)


@respx.mock
def test_raster_sample_parses_entries() -> None:
    respx.post(f"{MS3}/raster/rejilla/sample").mock(
        return_value=httpx.Response(
            200,
            json={
                "samples": [
                    {"lat": -4.6, "lon": 137.44, "distance_m": 0.0, "value": 1.0},
                    {"lat": -4.65, "lon": 137.42, "distance_m": 9000.0, "value": None},
                ]
            },
        )
    )
    source = HttpRasterSource(httpx.Client(base_url=MS3), "rejilla", retries=0)
    samples = source.sample_band("rugosidad_m", PATH, 90.0)
    assert len(samples) == 2
    assert samples[1].value is None


@respx.mock
def test_raster_transport_error_retries_then_upstream() -> None:
    route = respx.get(f"{MS3}/raster/rejilla/metadata").mock(
        side_effect=httpx.ConnectTimeout("slow")
    )
    source = HttpRasterSource(httpx.Client(base_url=MS3), "rejilla", retries=1)
    with pytest.raises(UpstreamUnavailableError):
        source.dataset_bands()
    assert route.call_count == 2  # initial + 1 retry


# --- MS4 terrain ----------------------------------------------------------


@respx.mock
def test_terrain_ping_ok() -> None:
    respx.get(f"{MS4}/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
    source = HttpTerrainSource(httpx.Client(base_url=MS4), "mars", retries=0)
    assert source.ping() is True


@respx.mock
def test_terrain_slope_at() -> None:
    respx.get(f"{MS4}/terrain/point").mock(
        return_value=httpx.Response(200, json={"slope_deg": 12.5})
    )
    source = HttpTerrainSource(httpx.Client(base_url=MS4), "mars", retries=0)
    assert source.slope_at(POINT) == pytest.approx(12.5)


@respx.mock
def test_terrain_profile_parses_samples() -> None:
    respx.post(f"{MS4}/terrain/profile").mock(
        return_value=httpx.Response(
            200,
            json={
                "samples": [
                    {"lat": -4.6, "lon": 137.44, "distance_m": 0.0, "slope_deg": 5.0},
                    {"lat": -4.65, "lon": 137.42, "distance_m": 9000.0, "slope_deg": None},
                ]
            },
        )
    )
    source = HttpTerrainSource(httpx.Client(base_url=MS4), "mars", retries=0)
    samples = source.slope_profile(PATH, 90.0)
    assert len(samples) == 2
    assert samples[0].slope_deg == 5.0
    assert samples[1].slope_deg is None


@respx.mock
def test_terrain_400_maps_to_domain_validation() -> None:
    respx.get(f"{MS4}/terrain/point").mock(
        return_value=httpx.Response(400, json={"detail": "bad path"})
    )
    source = HttpTerrainSource(httpx.Client(base_url=MS4), "mars", retries=0)
    with pytest.raises(DomainValidationError):
        source.slope_at(POINT)


@respx.mock
def test_terrain_profile_404_maps_to_no_coverage() -> None:
    respx.post(f"{MS4}/terrain/profile").mock(
        return_value=httpx.Response(404, json={"detail": "outside grid"})
    )
    source = HttpTerrainSource(httpx.Client(base_url=MS4), "mars", retries=0)
    with pytest.raises(NoCoverageError):
        source.slope_profile(PATH, 90.0)


@respx.mock
def test_terrain_profile_500_maps_to_upstream() -> None:
    respx.post(f"{MS4}/terrain/profile").mock(
        return_value=httpx.Response(503, json={"detail": "dem unavailable"})
    )
    source = HttpTerrainSource(httpx.Client(base_url=MS4), "mars", retries=0)
    with pytest.raises(UpstreamUnavailableError):
        source.slope_profile(PATH, 90.0)
