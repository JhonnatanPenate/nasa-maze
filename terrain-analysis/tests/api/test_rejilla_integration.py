import os
from pathlib import Path

import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient

from app.composition.dependencies import (
    build_datasource,
    get_raster_datasource,
    get_settings,
)
from app.core.config.settings import Settings
from app.core.ports.raster_datasource import RasterDatasource
from app.infrastructure.datasources.unavailable_raster_datasource import (
    UnavailableRasterDatasource,
)
from app.main import create_app

BRADBURY_LAT = -4.5895
BRADBURY_LON = 137.4416

_DEFAULT_REJILLA_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "gale"
    / "processed"
    / "rejilla_ruta_90m.tif"
)
REJILLA_PATH = Path(
    os.environ.get("MS4_REJILLA_PATH", str(_DEFAULT_REJILLA_PATH))
)

pytestmark = pytest.mark.skipif(
    not REJILLA_PATH.is_file(),
    reason=f"rejilla slope raster not found at {REJILLA_PATH}",
)


def _expected_terrain_class(slope_deg: float) -> str:
    """Mirrors the default TerrainClassifier thresholds used by the
    rejilla Settings below (flat<5, moderate<15, steep<30, hazardous)."""
    if slope_deg < 5.0:
        return "flat"
    if slope_deg < 15.0:
        return "moderate"
    if slope_deg < 30.0:
        return "steep"
    return "hazardous"


def _make_client(settings: Settings) -> TestClient:
    """Full app (all routers, real composition root) with the Settings
    and the datasource dependency overridden.

    The datasource is built through the same path the provider uses:
    `build_datasource(settings)`, falling back to
    UnavailableRasterDatasource when the build itself raises.
    """
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        datasource: RasterDatasource = build_datasource(settings)
    except Exception as exc:
        datasource = UnavailableRasterDatasource(exc)
    app.dependency_overrides[get_raster_datasource] = lambda: datasource
    return TestClient(app)


def _slope_at(ds, band: np.ndarray, lat: float, lon: float) -> float:
    row, col = ds.index(lon, lat)
    return float(band[row, col])


@pytest.fixture(scope="module")
def rejilla_settings() -> Settings:
    return Settings(
        datasource_kind="rejilla",
        rejilla_path=str(REJILLA_PATH),
    )


@pytest.fixture(scope="module")
def client(rejilla_settings: Settings) -> TestClient:
    return _make_client(rejilla_settings)


@pytest.fixture(scope="module")
def rejilla_grid():
    """The real raster kept open for the module plus band 1
    (pendiente_grados, slope degrees) as float64."""
    with rasterio.open(REJILLA_PATH) as ds:
        yield ds, ds.read(1).astype(np.float64)


class TestRejillaHealth:
    def test_health_ok_reports_rejilla_kind(
        self, client: TestClient
    ) -> None:
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "datasource": "ok",
            "datasource_kind": "rejilla",
        }


class TestRejillaPoint:
    def test_bradbury_landing_returns_band_slope_and_null_elevation(
        self, client: TestClient, rejilla_grid
    ) -> None:
        ds, band = rejilla_grid
        response = client.get(
            "/terrain/point",
            params={"lat": BRADBURY_LAT, "lon": BRADBURY_LON},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["elevation_m"] is None
        expected = _slope_at(ds, band, BRADBURY_LAT, BRADBURY_LON)
        assert payload["slope_deg"] == pytest.approx(expected, rel=1e-6)
        # Known value at the Bradbury Landing cell for the current file.
        assert payload["slope_deg"] == pytest.approx(2.25)
        assert payload["terrain_class"] == _expected_terrain_class(expected)

    def test_known_cells_match_band(
        self, client: TestClient, rejilla_grid
    ) -> None:
        ds, band = rejilla_grid
        max_row, max_col = np.unravel_index(np.nanargmax(band), band.shape)
        cells = [
            (0, 0),
            (band.shape[0] - 1, band.shape[1] - 1),
            (band.shape[0] // 2, band.shape[1] // 2),
            (int(max_row), int(max_col)),
        ]
        for row, col in cells:
            lon, lat = ds.xy(row, col)
            response = client.get(
                "/terrain/point", params={"lat": lat, "lon": lon}
            )

            assert response.status_code == 200, f"cell ({row}, {col})"
            payload = response.json()
            expected = float(band[row, col])
            assert payload["elevation_m"] is None
            assert payload["slope_deg"] == pytest.approx(
                expected, rel=1e-6
            ), f"cell ({row}, {col}) at lat={lat}, lon={lon}"
            assert payload["terrain_class"] == _expected_terrain_class(
                expected
            )

    def test_max_slope_cell_is_hazardous(
        self, client: TestClient, rejilla_grid
    ) -> None:
        ds, band = rejilla_grid
        row, col = np.unravel_index(np.nanargmax(band), band.shape)
        expected = float(band[row, col])
        assert expected >= 30.0
        lon, lat = ds.xy(row, col)

        response = client.get(
            "/terrain/point", params={"lat": lat, "lon": lon}
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["slope_deg"] == pytest.approx(expected, rel=1e-6)
        assert payload["terrain_class"] == "hazardous"


class TestRejillaProfile:
    def test_bradbury_profile_samples_match_band(
        self, client: TestClient, rejilla_grid
    ) -> None:
        ds, band = rejilla_grid
        response = client.post(
            "/terrain/profile",
            json={
                "path": [
                    {"lat": BRADBURY_LAT, "lon": BRADBURY_LON},
                    {"lat": -4.70, "lon": 137.40},
                ],
                "sample_distance_m": 500.0,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["elevation_gain_m"] is None
        assert payload["elevation_loss_m"] is None
        samples = payload["samples"]
        assert payload["sample_count"] == len(samples) > 1
        for sample in samples:
            assert sample["elevation_m"] is None
            expected = _slope_at(ds, band, sample["lat"], sample["lon"])
            assert sample["slope_deg"] == pytest.approx(
                expected, rel=1e-6
            ), f"sample at lat={sample['lat']}, lon={sample['lon']}"
        assert payload["max_slope_deg"] == pytest.approx(
            max(sample["slope_deg"] for sample in samples)
        )


class TestRejillaArea:
    def test_full_extent_stats_match_band(
        self, client: TestClient, rejilla_grid
    ) -> None:
        _, band = rejilla_grid
        response = client.post(
            "/terrain/area",
            json={"bbox": [137.345, -4.740, 137.455, -4.580]},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["elevation_m"] is None
        stats = payload["slope_deg"]
        assert stats["min"] == pytest.approx(
            float(np.nanmin(band)), rel=1e-6
        )
        assert stats["max"] == pytest.approx(
            float(np.nanmax(band)), rel=1e-6
        )
        assert stats["mean"] == pytest.approx(
            float(np.nanmean(band)), rel=1e-6
        )
        valid = band[np.isfinite(band)]
        assert payload["steep_fraction"] == pytest.approx(
            float(np.count_nonzero(valid >= 15.0)) / valid.size
        )


class TestRejillaFailures:
    def test_point_outside_extent_returns_404(
        self, client: TestClient
    ) -> None:
        response = client.get(
            "/terrain/point", params={"lat": 0.0, "lon": 0.0}
        )

        assert response.status_code == 404
        assert "detail" in response.json()

    def test_profile_leaving_extent_returns_404(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/terrain/profile",
            json={
                "path": [
                    {"lat": BRADBURY_LAT, "lon": BRADBURY_LON},
                    {"lat": -4.85, "lon": 137.40},
                ],
                "sample_distance_m": 500.0,
            },
        )

        assert response.status_code == 404
        assert "detail" in response.json()

    def test_missing_rejilla_file_returns_502_and_degraded_health(
        self,
    ) -> None:
        bad_settings = Settings(
            datasource_kind="rejilla",
            rejilla_path=str(
                REJILLA_PATH.parent / "missing_rejilla.tif"
            ),
        )
        bad_client = _make_client(bad_settings)

        health = bad_client.get("/health")
        assert health.status_code == 200
        assert health.json() == {
            "status": "degraded",
            "datasource": "unavailable",
            "datasource_kind": "rejilla",
        }

        response = bad_client.get(
            "/terrain/point",
            params={"lat": BRADBURY_LAT, "lon": BRADBURY_LON},
        )
        assert response.status_code == 502
        assert "detail" in response.json()
