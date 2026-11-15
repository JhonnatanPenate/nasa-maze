import numpy as np

from app.core.domain.bounding_box import BoundingBox
from app.infrastructure.datasources.in_memory_raster_datasource import (
    InMemoryRasterDatasource,
)
from app.infrastructure.repositories.registry_raster_repository import (
    RegistryRasterRepository,
)
from tests.fakes.failing_raster_datasource import FailingRasterDatasource

# Test grid: extent lon 137.40..137.48, lat -4.70..-4.60, 10 rows x 8 cols
# of 0.01 deg. Band i (1-based) holds (i-1)*100 + row*10 + col.
# (-4.605, 137.405) -> cell (0, 0); (-4.615, 137.415) -> (1, 1) nodata on
# band 1; (-4.685, 137.465) -> (8, 6) NaN on band 3.


def _single_cell_client(make_client, value):
    """Client over a 1x1 float32 grid holding `value` in band 'band_a'."""
    datasource = InMemoryRasterDatasource(
        np.array([[[value]]], dtype=np.float32),
        BoundingBox(min_lon=0.0, min_lat=-1.0, max_lon=1.0, max_lat=0.0),
        band_descriptions=("band_a",),
    )
    repository = RegistryRasterRepository(
        datasources={"single": datasource},
        configs={},
        crs_label="IAU_2015:49900",
        planet_radius_km=3396.19,
    )
    return make_client(repository=repository)


class TestPoint:
    def test_returns_all_band_values_verbatim(self, client):
        response = client.get(
            "/raster/test/point", params={"lat": -4.605, "lon": 137.405}
        )

        assert response.status_code == 200
        assert response.json() == {
            "lat": -4.605,
            "lon": 137.405,
            "values": {
                "slope_deg": 0.0,
                "roughness_m": 100.0,
                "dark_fraction": 200.0,
            },
        }

    def test_band_filter_returns_single_key(self, client):
        response = client.get(
            "/raster/test/point",
            params={"lat": -4.605, "lon": 137.405, "band": "roughness_m"},
        )

        assert response.status_code == 200
        assert response.json()["values"] == {"roughness_m": 100.0}

    def test_blank_band_param_returns_all_bands(self, client):
        response = client.get(
            "/raster/test/point",
            params={"lat": -4.605, "lon": 137.405, "band": ""},
        )

        assert response.status_code == 200
        assert set(response.json()["values"]) == {
            "slope_deg",
            "roughness_m",
            "dark_fraction",
        }

    def test_infinite_cell_reports_null(self, make_client):
        client = _single_cell_client(make_client, np.inf)

        response = client.get(
            "/raster/single/point", params={"lat": -0.5, "lon": 0.5}
        )

        assert response.status_code == 200
        assert response.json()["values"] == {"band_a": None}

    def test_float32_cell_comes_back_verbatim(self, make_client):
        client = _single_cell_client(make_client, np.float32(0.1))

        response = client.get(
            "/raster/single/point", params={"lat": -0.5, "lon": 0.5}
        )

        assert response.status_code == 200
        assert response.json()["values"]["band_a"] == 0.10000000149011612

    def test_numeric_nodata_cell_reports_null(self, client):
        response = client.get(
            "/raster/test/point",
            params={"lat": -4.615, "lon": 137.415, "band": "slope_deg"},
        )

        assert response.status_code == 200
        assert response.json()["values"] == {"slope_deg": None}

    def test_nan_cell_reports_null(self, client):
        response = client.get(
            "/raster/test/point",
            params={
                "lat": -4.685,
                "lon": 137.465,
                "band": "dark_fraction",
            },
        )

        assert response.status_code == 200
        assert response.json()["values"] == {"dark_fraction": None}

    def test_out_of_range_latitude_is_400(self, client):
        response = client.get(
            "/raster/test/point", params={"lat": 95.0, "lon": 137.44}
        )

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_non_numeric_coordinate_is_422(self, client):
        response = client.get(
            "/raster/test/point", params={"lat": "abc", "lon": 137.44}
        )

        assert response.status_code == 422

    def test_point_outside_extent_is_404(self, client):
        response = client.get(
            "/raster/test/point", params={"lat": -4.55, "lon": 137.44}
        )

        assert response.status_code == 404

    def test_unknown_band_is_404_and_lists_valid_names(self, client):
        response = client.get(
            "/raster/test/point",
            params={"lat": -4.605, "lon": 137.405, "band": "nope"},
        )

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "nope" in detail
        assert "slope_deg" in detail

    def test_unknown_dataset_is_404(self, client):
        response = client.get(
            "/raster/nope/point", params={"lat": -4.605, "lon": 137.405}
        )

        assert response.status_code == 404

    def test_unreadable_dataset_is_503(self, make_client, api_dataset_config):
        repository = RegistryRasterRepository(
            datasources={"broken": FailingRasterDatasource()},
            configs={"broken": api_dataset_config},
            crs_label="IAU_2015:49900",
            planet_radius_km=3396.19,
        )
        client = make_client(repository=repository)

        response = client.get(
            "/raster/broken/point", params={"lat": -4.605, "lon": 137.405}
        )

        assert response.status_code == 503
