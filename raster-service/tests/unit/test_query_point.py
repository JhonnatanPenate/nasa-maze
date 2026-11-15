import math

import pytest

from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import (
    DatasetUnavailableError,
    NoCoverageError,
    RasterValidationError,
    UnknownBandError,
)
from app.features.point_query.application.query_point import QueryPoint
from app.infrastructure.repositories.registry_raster_repository import (
    RegistryRasterRepository,
)
from tests.fakes.failing_raster_datasource import FailingRasterDatasource

# Test grid cells: band i (1-based) holds (i-1)*100 + row*10 + col.


class TestQueryPoint:
    def test_returns_all_band_values(self, repository):
        result = QueryPoint(repository).execute(
            "test", GeoPoint(lat=-4.605, lon=137.405)
        )

        assert result.point.lat == -4.605
        assert result.point.lon == 137.405
        assert result.values == {
            "slope_deg": 0.0,
            "roughness_m": 100.0,
            "dark_fraction": 200.0,
        }

    def test_band_filter_returns_single_band(self, repository):
        result = QueryPoint(repository).execute(
            "test", GeoPoint(lat=-4.605, lon=137.405), band="roughness_m"
        )

        assert result.values == {"roughness_m": 100.0}

    def test_values_are_verbatim_python_floats(self, repository):
        result = QueryPoint(repository).execute(
            "test", GeoPoint(lat=-4.625, lon=137.425), band="slope_deg"
        )

        value = result.values["slope_deg"]
        assert type(value) is float
        assert value == 22.0  # band 1, cell (2, 2)

    def test_nodata_cell_is_nan_in_domain(self, repository):
        result = QueryPoint(repository).execute(
            "test", GeoPoint(lat=-4.615, lon=137.415), band="slope_deg"
        )

        assert math.isnan(result.values["slope_deg"])

    def test_unknown_band_raises_listing_valid_names(self, repository):
        with pytest.raises(UnknownBandError) as excinfo:
            QueryPoint(repository).execute(
                "test", GeoPoint(lat=-4.605, lon=137.405), band="nope"
            )

        assert "slope_deg" in str(excinfo.value)

    def test_point_outside_extent_raises_no_coverage(self, repository):
        with pytest.raises(NoCoverageError):
            QueryPoint(repository).execute(
                "test", GeoPoint(lat=-4.55, lon=137.44)
            )

    def test_out_of_range_coordinate_raises_validation(self, repository):
        with pytest.raises(RasterValidationError):
            QueryPoint(repository).execute(
                "test", GeoPoint(lat=95.0, lon=137.44)
            )

    def test_unavailable_dataset_raises(self, dataset_config):
        repository = RegistryRasterRepository(
            datasources={"broken": FailingRasterDatasource()},
            configs={"broken": dataset_config},
            crs_label="IAU_2015:49900",
            planet_radius_km=3396.19,
        )

        with pytest.raises(DatasetUnavailableError):
            QueryPoint(repository).execute(
                "broken", GeoPoint(lat=-4.605, lon=137.405)
            )
