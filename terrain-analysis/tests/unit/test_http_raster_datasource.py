import json

import httpx
import numpy as np
import pytest

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.dem_window import DemWindow
from app.core.domain.geo_point import GeoPoint
from app.core.domain.halo_window import HaloWindow
from app.core.errors.exceptions import (
    DomainValidationError,
    NoCoverageError,
    UpstreamDatasourceError,
)
from app.infrastructure.datasources.dem_window_mapper import DemWindowMapper
from app.infrastructure.datasources.http_raster_datasource import (
    HttpRasterDatasource,
)

DATASET = "rejilla"
BAND = "pendiente_grados"
RES_LON = 0.0015183544372303697
RES_LAT = 0.0015183544372303732
CENTER_LAT = -4.690080696699202

BBOX = BoundingBox(min_lon=137.40, min_lat=-4.70, max_lon=137.42, max_lat=-4.68)


def window_payload(cells, core=None, center_lat=CENTER_LAT):
    rows = len(cells)
    cols = len(cells[0])
    if core is None:
        core = {"row_off": 0, "col_off": 0, "rows": rows, "cols": cols}
    return {
        "band": BAND,
        "bounds": [137.398, -4.701, 137.421, -4.679],
        "rows": rows,
        "cols": cols,
        "resolution_deg": {"lon": RES_LON, "lat": RES_LAT},
        "center_lat": center_lat,
        "core": core,
        "cells": cells,
    }


def make_datasource(handler) -> HttpRasterDatasource:
    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://ms3.test",
    )
    mapper = DemWindowMapper(3396.19 * 1000.0)
    return HttpRasterDatasource(client, mapper, dataset=DATASET, band=BAND)


def expected_window(cells, center_lat=CENTER_LAT) -> DemWindow:
    mapper = DemWindowMapper(3396.19 * 1000.0)
    raw = np.asarray(cells, dtype=np.float64)
    return mapper.to_dem_window(raw, None, RES_LON, RES_LAT, center_lat)


def assert_matches_expected(window, expected) -> None:
    assert np.array_equal(
        window.elevation, expected.elevation, equal_nan=True
    )
    assert window.cell_size_x_m == expected.cell_size_x_m
    assert window.cell_size_y_m == expected.cell_size_y_m


class TestReadWindow:
    def test_posts_bbox_and_returns_dem_window(self) -> None:
        cells = [[1.5, 2.25, 3.0], [4.5, 5.25, 6.0]]
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=window_payload(cells))

        datasource = make_datasource(handler)
        window = datasource.read_window(BBOX)

        assert captured["path"] == "/raster/rejilla/window"
        assert captured["body"] == {
            "band": BAND,
            "bbox": [137.40, -4.70, 137.42, -4.68],
        }
        assert isinstance(window, DemWindow)
        assert window.elevation.shape == (2, 3)
        assert_matches_expected(window, expected_window(cells))

    def test_null_cells_become_nan(self) -> None:
        cells = [[1.5, None], [None, 4.5]]

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=window_payload(cells))

        window = make_datasource(handler).read_window(BBOX)

        assert np.isnan(window.elevation[0, 1])
        assert np.isnan(window.elevation[1, 0])
        assert window.elevation[0, 0] == 1.5

    def test_not_intersecting_bbox_raises_no_coverage(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                404, json={"detail": "bbox does not intersect the extent"}
            )

        with pytest.raises(
            NoCoverageError,
            match="raster service: bbox does not intersect",
        ):
            make_datasource(handler).read_window(BBOX)

    def test_validation_error_raises_domain_validation(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                400, json={"detail": "window exceeds the cell cap"}
            )

        with pytest.raises(
            DomainValidationError,
            match="raster service: window exceeds the cell cap",
        ):
            make_datasource(handler).read_window(BBOX)

    def test_server_error_raises_upstream(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"detail": "dataset unavailable"})

        with pytest.raises(UpstreamDatasourceError):
            make_datasource(handler).read_window(BBOX)

    def test_timeout_raises_upstream(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out", request=request)

        with pytest.raises(UpstreamDatasourceError):
            make_datasource(handler).read_window(BBOX)

    def test_connection_error_raises_upstream(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

        with pytest.raises(UpstreamDatasourceError):
            make_datasource(handler).read_window(BBOX)

    def test_invalid_url_raises_upstream(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.InvalidURL("bad url")

        with pytest.raises(UpstreamDatasourceError):
            make_datasource(handler).read_window(BBOX)

    def test_malformed_payload_raises_upstream(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"unexpected": "shape"})

        with pytest.raises(UpstreamDatasourceError):
            make_datasource(handler).read_window(BBOX)

    def test_empty_cells_raise_upstream_not_validation(self) -> None:
        """An upstream payload that fails DemWindow validation must
        surface as 502, not as a client-facing 400."""
        payload = {
            "band": BAND,
            "bounds": [137.39, -4.71, 137.43, -4.67],
            "rows": 0,
            "cols": 0,
            "resolution_deg": {"lon": RES_LON, "lat": RES_LAT},
            "center_lat": CENTER_LAT,
            "core": {"row_off": 0, "col_off": 0, "rows": 0, "cols": 0},
            "cells": [],
        }

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        with pytest.raises(UpstreamDatasourceError):
            make_datasource(handler).read_window(BBOX)

    def test_invalid_resolution_raises_upstream_not_validation(self) -> None:
        cells = [[1.5, 2.25], [3.0, 4.5]]

        def handler(request: httpx.Request) -> httpx.Response:
            payload = window_payload(cells)
            payload["resolution_deg"] = {"lon": -1.0, "lat": RES_LAT}
            return httpx.Response(200, json=payload)

        with pytest.raises(UpstreamDatasourceError):
            make_datasource(handler).read_window(BBOX)


class TestReadWindowWithHalo:
    def test_posts_halo_cells_and_returns_halo_window(self) -> None:
        cells = [
            [1.0, 2.0, 3.0, 4.0],
            [5.0, 6.0, 7.0, 8.0],
            [9.0, 10.0, 11.0, 12.0],
            [13.0, 14.0, 15.0, 16.0],
        ]
        core = {"row_off": 1, "col_off": 1, "rows": 2, "cols": 2}
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=window_payload(cells, core))

        halo = make_datasource(handler).read_window_with_halo(BBOX, 1)

        assert captured["body"] == {
            "band": BAND,
            "bbox": [137.40, -4.70, 137.42, -4.68],
            "halo_cells": 1,
        }
        assert isinstance(halo, HaloWindow)
        assert halo.core_rows == slice(1, 3)
        assert halo.core_cols == slice(1, 3)
        assert np.array_equal(
            halo.core().elevation,
            np.array([[6.0, 7.0], [10.0, 11.0]]),
        )
        assert_matches_expected(
            halo.window, expected_window(cells)
        )

    def test_halo_clipped_at_edge_uses_asymmetric_core(self) -> None:
        cells = [[1.0, 2.0], [3.0, 4.0]]
        core = {"row_off": 0, "col_off": 0, "rows": 1, "cols": 1}

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=window_payload(cells, core))

        halo = make_datasource(handler).read_window_with_halo(BBOX, 3)

        assert halo.core_rows == slice(0, 1)
        assert halo.core_cols == slice(0, 1)
        assert halo.core().elevation.shape == (1, 1)

    def test_negative_halo_rejected_before_request(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("no HTTP request expected")

        with pytest.raises(DomainValidationError):
            make_datasource(handler).read_window_with_halo(BBOX, -1)

    def test_core_offset_outside_cells_raises_upstream(self) -> None:
        cells = [[1.0, 2.0], [3.0, 4.0]]
        core = {"row_off": -1, "col_off": 0, "rows": 2, "cols": 2}

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=window_payload(cells, core))

        with pytest.raises(UpstreamDatasourceError):
            make_datasource(handler).read_window_with_halo(BBOX, 1)

    def test_core_exceeding_cells_raises_upstream(self) -> None:
        cells = [[1.0, 2.0], [3.0, 4.0]]
        core = {"row_off": 1, "col_off": 0, "rows": 3, "cols": 2}

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=window_payload(cells, core))

        with pytest.raises(UpstreamDatasourceError):
            make_datasource(handler).read_window_with_halo(BBOX, 1)


class TestReadWindowAround:
    def test_posts_point_and_radius(self) -> None:
        cells = [[float(r * 3 + c) for c in range(3)] for r in range(3)]
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=window_payload(cells))

        point = GeoPoint(lat=-4.6, lon=137.44)
        window = make_datasource(handler).read_window_around(point, 1)

        assert captured["body"] == {
            "band": BAND,
            "point": {"lat": -4.6, "lon": 137.44},
            "radius_cells": 1,
        }
        assert window.elevation.shape == (3, 3)
        assert_matches_expected(window, expected_window(cells))

    def test_point_outside_extent_returns_all_nan_window(self) -> None:
        cells = [[None] * 5 for _ in range(5)]

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=window_payload(cells))

        point = GeoPoint(lat=-5.0, lon=137.4)
        window = make_datasource(handler).read_window_around(point, 2)

        assert window.elevation.shape == (5, 5)
        assert window.is_all_nodata()

    def test_negative_radius_rejected_before_request(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("no HTTP request expected")

        point = GeoPoint(lat=-4.6, lon=137.44)
        with pytest.raises(DomainValidationError):
            make_datasource(handler).read_window_around(point, -1)


class TestPing:
    def _health_handler(self, body, status=200):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status, json=body)

        return handler

    def test_true_when_ok_and_dataset_readable(self) -> None:
        body = {
            "status": "ok",
            "dataset_count": 1,
            "datasets": [{"name": "rejilla", "readable": True}],
        }
        assert make_datasource(self._health_handler(body)).ping() is True

    def test_false_when_degraded(self) -> None:
        body = {
            "status": "degraded",
            "dataset_count": 1,
            "datasets": [{"name": "rejilla", "readable": True}],
        }
        assert make_datasource(self._health_handler(body)).ping() is False

    def test_false_when_dataset_unreadable(self) -> None:
        body = {
            "status": "degraded",
            "dataset_count": 1,
            "datasets": [{"name": "rejilla", "readable": False}],
        }
        assert make_datasource(self._health_handler(body)).ping() is False

    def test_false_when_dataset_missing(self) -> None:
        body = {
            "status": "ok",
            "dataset_count": 1,
            "datasets": [{"name": "other", "readable": True}],
        }
        assert make_datasource(self._health_handler(body)).ping() is False

    def test_false_when_service_down(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

        assert make_datasource(handler).ping() is False

    def test_false_on_non_200(self) -> None:
        assert (
            make_datasource(self._health_handler({}, status=503)).ping()
            is False
        )

    def test_false_on_malformed_health_json(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"<html>oops</html>")

        assert make_datasource(handler).ping() is False

    def test_unexpected_error_propagates(self) -> None:
        """ping() only swallows transport/parsing failures; unexpected
        exceptions surface instead of silently degrading health."""
        def handler(request: httpx.Request) -> httpx.Response:
            raise RuntimeError("bug")

        with pytest.raises(RuntimeError):
            make_datasource(handler).ping()
