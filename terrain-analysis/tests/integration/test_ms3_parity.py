import os
from pathlib import Path

import httpx
import numpy as np
import pytest

from app.core.config.settings import Settings
from app.core.domain.bounding_box import BoundingBox
from app.core.domain.dem_window import DemWindow
from app.core.domain.geo_point import GeoPoint
from app.core.domain.halo_window import HaloWindow
from app.infrastructure.datasources.dem_window_mapper import DemWindowMapper
from app.infrastructure.datasources.geotiff_datasource import (
    GeoTiffRasterDatasource,
)
from app.infrastructure.datasources.http_raster_datasource import (
    HttpRasterDatasource,
)

MS3_URL = os.environ.get("MS4_RASTER_SERVICE_URL", "http://localhost:8003")

_REJILLA_PATH = Path(Settings().rejilla_path)

pytestmark = pytest.mark.skipif(
    not _REJILLA_PATH.is_file(),
    reason="delivered rejilla raster not present",
)


@pytest.fixture(scope="module", autouse=True)
def ms3_available() -> None:
    """Probe MS3 once per module; skip the whole suite when it is not
    serving. Runs at fixture time so collection never hits the network."""
    try:
        response = httpx.get(f"{MS3_URL}/health", timeout=2.0)
    except httpx.HTTPError:
        pytest.skip(f"MS3 raster service not reachable at {MS3_URL}")
    ok = response.status_code == 200
    if ok:
        try:
            ok = response.json().get("status") == "ok"
        except ValueError:
            ok = False
    if not ok:
        pytest.skip(f"MS3 raster service not reachable at {MS3_URL}")


@pytest.fixture(scope="module")
def local_datasource() -> GeoTiffRasterDatasource:
    settings = Settings()
    mapper = DemWindowMapper(settings.planet_radius_km * 1000.0)
    return GeoTiffRasterDatasource(
        settings.rejilla_path,
        mapper,
        settings.max_window_cells,
        band=settings.rejilla_slope_band,
    )


@pytest.fixture(scope="module")
def http_datasource():
    settings = Settings()
    client = httpx.Client(
        base_url=MS3_URL, timeout=settings.raster_timeout_s
    )
    yield HttpRasterDatasource(
        client,
        DemWindowMapper(settings.planet_radius_km * 1000.0),
        dataset=settings.raster_dataset,
        band=settings.raster_band,
    )
    client.close()


def assert_window_equal(
    http_window: DemWindow, local_window: DemWindow
) -> None:
    assert http_window.elevation.shape == local_window.elevation.shape
    assert np.array_equal(
        http_window.elevation, local_window.elevation, equal_nan=True
    )
    assert http_window.cell_size_x_m == local_window.cell_size_x_m
    assert http_window.cell_size_y_m == local_window.cell_size_y_m


def assert_halo_equal(
    http_halo: HaloWindow, local_halo: HaloWindow
) -> None:
    assert_window_equal(http_halo.window, local_halo.window)
    assert http_halo.core_rows == local_halo.core_rows
    assert http_halo.core_cols == local_halo.core_cols
    assert_window_equal(http_halo.core(), local_halo.core())


def test_ping(http_datasource) -> None:
    assert http_datasource.ping() is True


BBOX_CASES = [
    pytest.param(
        BoundingBox(
            min_lon=137.40, min_lat=-4.70, max_lon=137.42, max_lat=-4.68
        ),
        id="interior",
    ),
    pytest.param(
        BoundingBox(
            min_lon=137.355,
            min_lat=-4.63,
            max_lon=137.39,
            max_lat=-4.605,
        ),
        id="interior-north",
    ),
    pytest.param(
        BoundingBox(
            min_lon=137.30, min_lat=-4.80, max_lon=137.36, max_lat=-4.70
        ),
        id="southwest-edge-clipped",
    ),
    pytest.param(
        BoundingBox(
            min_lon=137.44, min_lat=-4.60, max_lon=137.50, max_lat=-4.55
        ),
        id="northeast-edge-clipped",
    ),
    pytest.param(
        BoundingBox(
            min_lon=137.4000,
            min_lat=-4.7000,
            max_lon=137.40001,
            max_lat=-4.69999,
        ),
        id="sub-cell-fallback",
    ),
    pytest.param(
        BoundingBox(
            min_lon=137.34, min_lat=-4.75, max_lon=137.46, max_lat=-4.57
        ),
        id="whole-extent",
    ),
]


@pytest.mark.parametrize("bbox", BBOX_CASES)
def test_read_window_parity(
    bbox, http_datasource, local_datasource
) -> None:
    assert_window_equal(
        http_datasource.read_window(bbox),
        local_datasource.read_window(bbox),
    )


HALO_CASES = [
    pytest.param(
        BoundingBox(
            min_lon=137.40, min_lat=-4.70, max_lon=137.42, max_lat=-4.68
        ),
        2,
        id="interior-halo2",
    ),
    pytest.param(
        BoundingBox(
            min_lon=137.30, min_lat=-4.80, max_lon=137.36, max_lat=-4.70
        ),
        4,
        id="southwest-edge-halo4",
    ),
    pytest.param(
        BoundingBox(
            min_lon=137.44, min_lat=-4.60, max_lon=137.50, max_lat=-4.55
        ),
        3,
        id="northeast-edge-halo3",
    ),
]


@pytest.mark.parametrize("bbox,halo_cells", HALO_CASES)
def test_read_window_with_halo_parity(
    bbox, halo_cells, http_datasource, local_datasource
) -> None:
    assert_halo_equal(
        http_datasource.read_window_with_halo(bbox, halo_cells),
        local_datasource.read_window_with_halo(bbox, halo_cells),
    )


POINT_CASES = [
    pytest.param(GeoPoint(lat=-4.65, lon=137.40), 0, id="interior-r0"),
    pytest.param(GeoPoint(lat=-4.60, lon=137.44), 3, id="interior-r3"),
    pytest.param(
        GeoPoint(lat=-4.58, lon=137.45432151948057),
        2,
        id="max-corner-clamped",
    ),
    pytest.param(
        GeoPoint(lat=-4.65, lon=137.346), 4, id="min-lon-edge-padded"
    ),
    pytest.param(
        GeoPoint(lat=-5.0, lon=137.4), 2, id="outside-extent-all-nan"
    ),
]


@pytest.mark.parametrize("point,radius_cells", POINT_CASES)
def test_read_window_around_parity(
    point, radius_cells, http_datasource, local_datasource
) -> None:
    assert_window_equal(
        http_datasource.read_window_around(point, radius_cells),
        local_datasource.read_window_around(point, radius_cells),
    )
