import numpy as np
import pytest

from app.composition.dependencies import (
    build_datasource,
    get_distance_calculator,
    get_path_sampler,
    get_raster_datasource,
    get_settings,
    get_slope_calculator,
    get_terrain_classifier,
    get_terrain_repository,
)
from app.core.config.settings import Settings
from app.core.domain.distance_calculator import DistanceCalculator
from app.core.domain.path_sampler import PathSampler
from app.core.domain.slope_calculator import SlopeCalculator
from app.core.domain.terrain_class import TerrainClass
from app.infrastructure.datasources.geotiff_datasource import (
    GeoTiffRasterDatasource,
)
from app.infrastructure.datasources.synthetic_dem_datasource import (
    SyntheticDemDatasource,
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
    def test_raster_datasource_is_cached(self) -> None:
        assert get_raster_datasource() is get_raster_datasource()

    def test_terrain_repository(self) -> None:
        repo = get_terrain_repository()
        assert isinstance(repo, DemTerrainRepository)
        assert repo.is_available() is True

    def test_slope_calculator(self) -> None:
        assert isinstance(get_slope_calculator(), SlopeCalculator)

    def test_distance_calculator_uses_planet_radius_in_metres(self) -> None:
        calc = get_distance_calculator()
        assert isinstance(calc, DistanceCalculator)
        assert calc.radius_m == pytest.approx(
            Settings().planet_radius_km * 1000.0
        )

    def test_path_sampler(self) -> None:
        assert isinstance(get_path_sampler(), PathSampler)

    def test_classifier_thresholds_come_from_settings(
        self, monkeypatch
    ) -> None:
        monkeypatch.setenv("MS4_SLOPE_FLAT_MAX_DEG", "2.0")
        get_settings.cache_clear()
        classifier = get_terrain_classifier()
        assert classifier.classify(1.0) is TerrainClass.FLAT
        assert classifier.classify(3.0) is TerrainClass.MODERATE
