import pytest
from fastapi.testclient import TestClient

from app.core.config.settings import Settings
from app.features.window_read.presentation.window_router import router
from app.infrastructure.repositories.registry_raster_repository import (
    RegistryRasterRepository,
)
from tests.conftest import TEST_DATASET, mount_router
from tests.fakes.failing_raster_datasource import FailingRasterDatasource

# Test grid: extent lon 137.40..137.48, lat -4.70..-4.60, 10 rows x 8
# cols of ~0.01 deg. Band i (1-based) holds (i-1)*100 + row*10 + col;
# "slope_deg" cell (1, 1) is nodata, "dark_fraction" cell (8, 6) is NaN.


@pytest.fixture
def client(api_repository, api_settings) -> TestClient:
    return mount_router(router, api_repository, api_settings)


def _post(client: TestClient, body: dict, dataset: str = TEST_DATASET):
    return client.post(f"/raster/{dataset}/window", json=body)


class TestWindowBbox:
    def test_bbox_returns_window_with_core_block(self, client):
        # Bbox edges sit exactly on cell centres: rows 1:3 x cols 1:4.
        response = _post(
            client,
            {
                "band": "slope_deg",
                "bbox": [137.415, -4.625, 137.435, -4.615],
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["band"] == "slope_deg"
        assert body["rows"] == 2
        assert body["cols"] == 3
        assert body["core"] == {
            "row_off": 0,
            "col_off": 0,
            "rows": 2,
            "cols": 3,
        }
        assert body["cells"] == [
            [None, 12.0, 13.0],
            [21.0, 22.0, 23.0],
        ]
        assert body["resolution_deg"]["lon"] == pytest.approx(0.01)
        assert body["resolution_deg"]["lat"] == pytest.approx(0.01)
        assert body["center_lat"] == pytest.approx(-4.62)
        assert body["bounds"][0] == pytest.approx(137.41)
        assert body["bounds"][1] == pytest.approx(-4.63)
        assert body["bounds"][2] == pytest.approx(137.44)
        assert body["bounds"][3] == pytest.approx(-4.61)

    def test_halo_expands_and_marks_core(self, client):
        # Halo 2 clips to 1 on the north/west edges; the core block
        # still marks the unexpanded slice and center_lat its rows.
        response = _post(
            client,
            {
                "band": "slope_deg",
                "bbox": [137.415, -4.625, 137.435, -4.615],
                "halo_cells": 2,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["rows"] == 5
        assert body["cols"] == 6
        assert body["core"] == {
            "row_off": 1,
            "col_off": 1,
            "rows": 2,
            "cols": 3,
        }
        assert body["cells"][1][1] is None
        assert body["cells"][0] == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
        assert body["cells"][4] == [40.0, 41.0, 42.0, 43.0, 44.0, 45.0]
        assert body["center_lat"] == pytest.approx(-4.62)
        assert body["bounds"][0] == pytest.approx(137.40)
        assert body["bounds"][3] == pytest.approx(-4.60)

    def test_sub_cell_bbox_returns_single_cell(self, client):
        response = _post(
            client,
            {
                "band": "slope_deg",
                "bbox": [137.406, -4.606, 137.408, -4.604],
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["rows"] == 1
        assert body["cols"] == 1
        assert body["cells"] == [[0.0]]
        assert body["bounds"][0] == pytest.approx(137.40)
        assert body["bounds"][1] == pytest.approx(-4.61)
        assert body["bounds"][2] == pytest.approx(137.41)
        assert body["bounds"][3] == pytest.approx(-4.60)

    def test_non_intersecting_bbox_is_404(self, client):
        response = _post(
            client,
            {
                "band": "slope_deg",
                "bbox": [140.0, 10.0, 141.0, 11.0],
            },
        )

        assert response.status_code == 404

    def test_inverted_bbox_is_400(self, client):
        response = _post(
            client,
            {
                "band": "slope_deg",
                "bbox": [137.45, -4.62, 137.41, -4.61],
            },
        )

        assert response.status_code == 400

    def test_wrong_length_bbox_is_422(self, client):
        response = _post(
            client,
            {"band": "slope_deg", "bbox": [137.41, -4.62, 137.43]},
        )

        assert response.status_code == 422

    def test_core_cells_over_cap_is_400(
        self, api_repository, api_dataset_config
    ):
        settings = Settings(
            datasets={TEST_DATASET: api_dataset_config},
            max_window_cells=10,
        )
        client = mount_router(router, api_repository, settings)

        response = _post(
            client,
            {
                "band": "slope_deg",
                "bbox": [137.40, -4.70, 137.48, -4.60],
            },
        )

        assert response.status_code == 400


class TestWindowFormValidation:
    def test_both_bbox_and_point_is_400(self, client):
        response = _post(
            client,
            {
                "band": "slope_deg",
                "bbox": [137.41, -4.62, 137.43, -4.61],
                "point": {"lat": -4.615, "lon": 137.415},
                "radius_cells": 1,
            },
        )

        assert response.status_code == 400

    def test_neither_bbox_nor_point_is_400(self, client):
        response = _post(client, {"band": "slope_deg"})

        assert response.status_code == 400

    def test_point_without_radius_is_400(self, client):
        response = _post(
            client,
            {
                "band": "slope_deg",
                "point": {"lat": -4.615, "lon": 137.415},
            },
        )

        assert response.status_code == 400

    def test_negative_radius_is_400(self, client):
        response = _post(
            client,
            {
                "band": "slope_deg",
                "point": {"lat": -4.615, "lon": 137.415},
                "radius_cells": -1,
            },
        )

        assert response.status_code == 400

    def test_negative_halo_is_400(self, client):
        response = _post(
            client,
            {
                "band": "slope_deg",
                "bbox": [137.41, -4.62, 137.43, -4.61],
                "halo_cells": -1,
            },
        )

        assert response.status_code == 400

    def test_non_numeric_radius_is_422(self, client):
        response = _post(
            client,
            {
                "band": "slope_deg",
                "point": {"lat": -4.615, "lon": 137.415},
                "radius_cells": "abc",
            },
        )

        assert response.status_code == 422

    def test_point_out_of_range_latitude_is_400(self, client):
        response = _post(
            client,
            {
                "band": "slope_deg",
                "point": {"lat": 95.0, "lon": 137.415},
                "radius_cells": 1,
            },
        )

        assert response.status_code == 400


class TestWindowPoint:
    def test_radius_zero_returns_containing_cell(self, client):
        response = _post(
            client,
            {
                "band": "slope_deg",
                "point": {"lat": -4.625, "lon": 137.425},
                "radius_cells": 0,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["rows"] == 1
        assert body["cols"] == 1
        assert body["cells"] == [[22.0]]
        assert body["core"] == {
            "row_off": 0,
            "col_off": 0,
            "rows": 1,
            "cols": 1,
        }
        assert body["center_lat"] == pytest.approx(-4.625)

    def test_radius_window_matches_grid_slice(self, client):
        response = _post(
            client,
            {
                "band": "slope_deg",
                "point": {"lat": -4.625, "lon": 137.425},
                "radius_cells": 1,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["cells"] == [
            [None, 12.0, 13.0],
            [21.0, 22.0, 23.0],
            [31.0, 32.0, 33.0],
        ]

    def test_edge_window_padded_with_null(self, client):
        # Ported MS4 case: point in cell (1, 1), radius 2 overhangs the
        # north/west edges -> top row and left column are null padding.
        response = _post(
            client,
            {
                "band": "roughness_m",
                "point": {"lat": -4.615, "lon": 137.415},
                "radius_cells": 2,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["rows"] == 5
        assert body["cols"] == 5
        assert body["cells"][0] == [None] * 5
        assert all(row[0] is None for row in body["cells"])
        assert body["cells"][2][2] == 111.0
        # bounds extend beyond the dataset extent
        assert body["bounds"][0] == pytest.approx(137.40 - 0.01)
        assert body["bounds"][3] == pytest.approx(-4.60 + 0.01)

    def test_point_on_max_edge_maps_inside(self, client):
        # Ported MS4 case: the max corner clamps into cell (0, 7).
        response = _post(
            client,
            {
                "band": "slope_deg",
                "point": {"lat": -4.60, "lon": 137.48},
                "radius_cells": 0,
            },
        )

        assert response.status_code == 200
        assert response.json()["cells"] == [[7.0]]

    def test_point_outside_extent_returns_all_null(self, client):
        # Ported MS4 case: never 404; a (2r+1)^2 all-null window whose
        # center_lat is the request latitude.
        response = _post(
            client,
            {
                "band": "slope_deg",
                "point": {"lat": -4.55, "lon": 137.44},
                "radius_cells": 1,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["rows"] == 3
        assert body["cols"] == 3
        assert all(
            value is None
            for row in body["cells"]
            for value in row
        )
        assert body["center_lat"] == -4.55

    def test_halo_cells_ignored_on_point_reads(self, client):
        response = _post(
            client,
            {
                "band": "slope_deg",
                "point": {"lat": -4.625, "lon": 137.425},
                "radius_cells": 1,
                "halo_cells": 5,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["rows"] == 3
        assert body["cols"] == 3

    def test_point_radius_over_cap_is_400(
        self, api_repository, api_dataset_config
    ):
        settings = Settings(
            datasets={TEST_DATASET: api_dataset_config},
            max_window_cells=10,
        )
        client = mount_router(router, api_repository, settings)

        response = _post(
            client,
            {
                "band": "slope_deg",
                "point": {"lat": -4.65, "lon": 137.44},
                "radius_cells": 3,  # 7x7 = 49 > 10
            },
        )

        assert response.status_code == 400


class TestWindowErrors:
    def test_unknown_band_is_404_and_lists_valid_names(self, client):
        response = _post(
            client,
            {
                "band": "nope",
                "bbox": [137.41, -4.62, 137.43, -4.61],
            },
        )

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "nope" in detail
        assert "slope_deg" in detail

    def test_unknown_dataset_is_404(self, client):
        response = _post(
            client,
            {
                "band": "slope_deg",
                "bbox": [137.41, -4.62, 137.43, -4.61],
            },
            dataset="nope",
        )

        assert response.status_code == 404

    def test_unreadable_dataset_is_503(
        self, api_dataset_config, api_settings
    ):
        repository = RegistryRasterRepository(
            datasources={"broken": FailingRasterDatasource()},
            configs={"broken": api_dataset_config},
            crs_label="IAU_2015:49900",
            planet_radius_km=3396.19,
        )
        client = mount_router(router, repository, api_settings)

        response = _post(
            client,
            {
                "band": "slope_deg",
                "bbox": [137.41, -4.62, 137.43, -4.61],
            },
            dataset="broken",
        )

        assert response.status_code == 503
