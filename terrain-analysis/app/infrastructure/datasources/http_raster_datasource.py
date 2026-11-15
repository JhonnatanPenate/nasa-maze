import httpx
import numpy as np

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.dem_window import DemWindow
from app.core.domain.geo_point import GeoPoint
from app.core.domain.halo_window import HaloWindow
from app.core.errors.exceptions import (
    DomainValidationError,
    NoCoverageError,
    UpstreamDatasourceError,
)
from app.core.ports.raster_datasource import RasterDatasource
from app.infrastructure.datasources.dem_window_mapper import DemWindowMapper
from app.infrastructure.datasources.grid_geometry import GridGeometry


class HttpRasterDatasource(RasterDatasource):
    """RasterDatasource proxying the MS3 Raster Service over HTTP.

    Each read maps to `POST /raster/{dataset}/window` with the configured
    band: `read_window` sends `bbox`, `read_window_with_halo` adds
    `halo_cells` and builds the `HaloWindow` from the response `core`
    slice, and `read_window_around` sends `point` + `radius_cells`.
    `ping()` queries `GET /health` and is True only when the service
    reports `status == "ok"` and the configured dataset is readable.

    Response `cells` carry `null` for nodata; `resolution_deg` and
    `center_lat` feed `DemWindowMapper.to_dem_window` unchanged so the
    returned domain objects are identical to a local raster read.

    Error mapping: 400 -> DomainValidationError, 404 -> NoCoverageError,
    any other non-200 status, timeout or connection failure ->
    UpstreamDatasourceError.
    """

    def __init__(
        self,
        client: httpx.Client,
        mapper: DemWindowMapper,
        dataset: str,
        band: str,
    ) -> None:
        self._client = client
        self._mapper = mapper
        self._dataset = dataset
        self._band = band

    def read_window(self, bbox: BoundingBox) -> DemWindow:
        payload = self._post_window(
            {
                "band": self._band,
                "bbox": [
                    bbox.min_lon,
                    bbox.min_lat,
                    bbox.max_lon,
                    bbox.max_lat,
                ],
            }
        )
        return self._to_dem_window(payload)

    def read_window_with_halo(
        self, bbox: BoundingBox, halo_cells: int
    ) -> HaloWindow:
        if (
            isinstance(halo_cells, bool)
            or not isinstance(halo_cells, int)
            or halo_cells < 0
        ):
            raise DomainValidationError(
                f"halo_cells must be an integer >= 0, got {halo_cells!r}"
            )
        payload = self._post_window(
            {
                "band": self._band,
                "bbox": [
                    bbox.min_lon,
                    bbox.min_lat,
                    bbox.max_lon,
                    bbox.max_lat,
                ],
                "halo_cells": halo_cells,
            }
        )
        window = self._to_dem_window(payload)
        try:
            core = payload["core"]
            row_off = int(core["row_off"])
            col_off = int(core["col_off"])
            rows = int(core["rows"])
            cols = int(core["cols"])
        except (KeyError, TypeError, ValueError) as exc:
            raise UpstreamDatasourceError(
                "Raster service returned a malformed core slice"
            ) from exc
        cell_rows, cell_cols = window.elevation.shape
        if (
            row_off < 0
            or col_off < 0
            or rows < 1
            or cols < 1
            or row_off + rows > cell_rows
            or col_off + cols > cell_cols
        ):
            raise UpstreamDatasourceError(
                "Raster service returned a core slice outside the "
                "cell array"
            )
        return HaloWindow(
            window=window,
            core_rows=slice(row_off, row_off + rows),
            core_cols=slice(col_off, col_off + cols),
        )

    def read_window_around(
        self, point: GeoPoint, radius_cells: int
    ) -> DemWindow:
        GridGeometry.window_size(radius_cells)
        payload = self._post_window(
            {
                "band": self._band,
                "point": {"lat": point.lat, "lon": point.lon},
                "radius_cells": radius_cells,
            }
        )
        return self._to_dem_window(payload)

    def ping(self) -> bool:
        try:
            response = self._client.get("/health")
            if response.status_code != 200:
                return False
            body = response.json()
        except (
            httpx.HTTPError,
            httpx.InvalidURL,
            ValueError,
            KeyError,
        ):
            return False
        if not isinstance(body, dict) or body.get("status") != "ok":
            return False
        datasets = body.get("datasets")
        if not isinstance(datasets, list):
            return False
        return any(
            isinstance(entry, dict)
            and entry.get("name") == self._dataset
            and entry.get("readable") is True
            for entry in datasets
        )

    def _post_window(self, body: dict) -> dict:
        try:
            response = self._client.post(
                f"/raster/{self._dataset}/window", json=body
            )
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            raise UpstreamDatasourceError(
                f"Raster service request failed: {exc}"
            ) from exc
        if response.status_code == 400:
            raise DomainValidationError(self._response_detail(response))
        if response.status_code == 404:
            raise NoCoverageError(self._response_detail(response))
        if response.status_code != 200:
            raise UpstreamDatasourceError(
                f"Raster service returned HTTP {response.status_code}: "
                f"{self._response_detail(response)}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise UpstreamDatasourceError(
                "Raster service returned a non-JSON window response"
            ) from exc
        if not isinstance(payload, dict):
            raise UpstreamDatasourceError(
                "Raster service returned a malformed window payload"
            )
        return payload

    @staticmethod
    def _response_detail(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return f"HTTP {response.status_code}"
        if isinstance(body, dict) and body.get("detail") is not None:
            return f"raster service: {body['detail']}"
        return f"HTTP {response.status_code}"

    def _to_dem_window(self, payload: dict) -> DemWindow:
        try:
            cells = np.asarray(payload["cells"], dtype=np.float64)
            resolution = payload["resolution_deg"]
            res_lon_deg = float(resolution["lon"])
            res_lat_deg = float(resolution["lat"])
            center_lat_deg = float(payload["center_lat"])
        except (KeyError, TypeError, ValueError) as exc:
            raise UpstreamDatasourceError(
                "Raster service returned a malformed window payload"
            ) from exc
        try:
            return self._mapper.to_dem_window(
                cells, None, res_lon_deg, res_lat_deg, center_lat_deg
            )
        except DomainValidationError as exc:
            raise UpstreamDatasourceError(
                f"Raster service returned an invalid window payload: "
                f"{exc}"
            ) from exc
