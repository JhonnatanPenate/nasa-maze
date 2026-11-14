import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.composition.dependencies import (
    build_datasource,
    get_distance_calculator,
    get_path_sampler,
    get_raster_datasource,
    get_settings,
    get_slope_calculator,
    get_terrain_classifier,
    get_terrain_point_sampler,
    get_terrain_repository,
)
from app.core.application.terrain_point_sampler import TerrainPointSampler
from app.core.config.settings import Settings
from app.core.domain.bounding_box import BoundingBox
from app.core.domain.distance_calculator import DistanceCalculator
from app.core.domain.path_sampler import PathSampler
from app.core.domain.slope_calculator import SlopeCalculator
from app.core.domain.terrain_class import TerrainClass
from app.core.errors.error_handlers import register_exception_handlers
from app.core.errors.exceptions import UpstreamDatasourceError
from app.features.point_analysis.presentation.point_router import (
    router as point_router,
)
from app.infrastructure.datasources.geotiff_datasource import (
    GeoTiffRasterDatasource,
)
from app.infrastructure.datasources.synthetic_dem_datasource import (
    SyntheticDemDatasource,
)
from app.infrastructure.datasources.unavailable_raster_datasource import (
    UnavailableRasterDatasource,
)
from app.infrastructure.repositories.dem_terrain_repository import (
    DemTerrainRepository,
)
from tests.fixtures.make_test_dem import write_test_dem


@pytest.fixture(autouse=True)
def clear_caches():
    get_settings.cache_clear()
    get_raster_datasource.cache_clear()
    yield
    get_settings.cache_clear()
    get_raster_datasource.cache_clear()


class TestBuildDatasource:
    def test_synthetic_kind(self) -> None:
        ds = build_datasource(Settings(datasource_kind="synthetic"))
        assert isinstance(ds, SyntheticDemDatasource)
        assert ds.ping() is True

    def test_geotiff_kind(self, tmp_path, small_dem) -> None:
        elevation, extent = small_dem
        path = tmp_path / "dem.tif"
        write_test_dem(path, elevation, extent)
        ds = build_datasource(
            Settings(datasource_kind="geotiff", dem_path=str(path))
        )
        assert isinstance(ds, GeoTiffRasterDatasource)
        assert ds.ping() is True

    def test_geotiff_empty_path_raises(self) -> None:
        with pytest.raises(ValueError, match="dem_path"):
            build_datasource(
                Settings(datasource_kind="geotiff", dem_path="")
            )

    def test_http_kind_reserved_raises(self) -> None:
        with pytest.raises(ValueError, match="http"):
            build_datasource(Settings(datasource_kind="http"))


class TestProviders:
    """Providers chain via Depends defaults; in unit tests they are
    invoked with explicit arguments."""

    def test_raster_datasource_is_cached(self) -> None:
        assert get_raster_datasource() is get_raster_datasource()

    def test_terrain_repository(self) -> None:
        repo = get_terrain_repository(get_raster_datasource())
        assert isinstance(repo, DemTerrainRepository)
        assert repo.is_available() is True

    def test_slope_calculator(self) -> None:
        assert isinstance(get_slope_calculator(), SlopeCalculator)

    def test_distance_calculator_uses_planet_radius_in_metres(self) -> None:
        calc = get_distance_calculator(get_settings())
        assert isinstance(calc, DistanceCalculator)
        assert calc.radius_m == pytest.approx(
            Settings().planet_radius_km * 1000.0
        )

    def test_path_sampler(self) -> None:
        assert isinstance(
            get_path_sampler(get_distance_calculator(get_settings())),
            PathSampler,
        )

    def test_terrain_point_sampler(self) -> None:
        sampler = get_terrain_point_sampler(
            get_terrain_repository(get_raster_datasource()),
            get_slope_calculator(),
        )
        assert isinstance(sampler, TerrainPointSampler)

    def test_classifier_thresholds_come_from_settings(
        self, monkeypatch
    ) -> None:
        monkeypatch.setenv("MS4_SLOPE_FLAT_MAX_DEG", "2.0")
        get_settings.cache_clear()
        classifier = get_terrain_classifier(get_settings())
        assert classifier.classify(1.0) is TerrainClass.FLAT
        assert classifier.classify(3.0) is TerrainClass.MODERATE

    def test_classifier_steep_min_deg_matches_moderate_max(
        self, monkeypatch
    ) -> None:
        monkeypatch.setenv("MS4_SLOPE_MODERATE_MAX_DEG", "20.0")
        get_settings.cache_clear()
        classifier = get_terrain_classifier(get_settings())
        assert classifier.steep_min_deg == pytest.approx(20.0)

    def test_datasource_build_failure_yields_unavailable_datasource(
        self, monkeypatch
    ) -> None:
        # geotiff without dem_path fails build_datasource; the provider
        # must degrade instead of raising (health -> degraded, reads -> 502).
        monkeypatch.setenv("MS4_DATASOURCE_KIND", "geotiff")
        monkeypatch.delenv("MS4_DEM_PATH", raising=False)
        get_settings.cache_clear()
        get_raster_datasource.cache_clear()

        datasource = get_raster_datasource()
        assert isinstance(datasource, UnavailableRasterDatasource)
        assert datasource.ping() is False

        repository = get_terrain_repository(datasource)
        assert repository.is_available() is False
        with pytest.raises(UpstreamDatasourceError):
            repository.window_for(
                BoundingBox(
                    min_lon=77.5, min_lat=18.4, max_lon=77.6, max_lat=18.5
                )
            )


class TestSettingsOverridePropagation:
    def test_get_settings_override_reaches_point_terrain_class(
        self, synthetic_datasource
    ) -> None:
        """A dependency_overrides[get_settings] override must flow through
        the Depends chain into TerrainClassifier: with near-zero thresholds
        the ~0.2 deg plane slope classifies as hazardous (default: flat)."""
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(point_router)
        app.dependency_overrides[get_raster_datasource] = (
            lambda: synthetic_datasource
        )
        app.dependency_overrides[get_settings] = lambda: Settings(
            slope_flat_max_deg=0.01,
            slope_moderate_max_deg=0.02,
            slope_steep_max_deg=0.05,
        )

        response = TestClient(app).get(
            "/terrain/point", params={"lat": 18.5, "lon": 77.5}
        )

        assert response.status_code == 200
        assert response.json()["terrain_class"] == "hazardous"
