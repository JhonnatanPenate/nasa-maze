from app.core.domain.bounding_box import BoundingBox
from app.core.domain.dem_window import DemWindow
from app.core.domain.geo_point import GeoPoint
from app.core.domain.halo_window import HaloWindow
from app.core.errors.exceptions import UpstreamDatasourceError
from app.core.ports.raster_datasource import RasterDatasource


class UnavailableRasterDatasource(RasterDatasource):
    """Stand-in for a datasource that failed to build at wiring time.

    Created by the composition root when `build_datasource` raises (e.g.
    a misconfigured datasource_kind or missing dem_path). `ping()`
    reports False so `/health` degrades, and every read re-raises the
    stored failure as `UpstreamDatasourceError` (HTTP 502).
    """

    def __init__(self, error: Exception) -> None:
        self._error = error

    def read_window(self, bbox: BoundingBox) -> DemWindow:
        raise UpstreamDatasourceError(
            f"Raster datasource unavailable: {self._error}"
        ) from self._error

    def read_window_with_halo(
        self, bbox: BoundingBox, halo_cells: int
    ) -> HaloWindow:
        raise UpstreamDatasourceError(
            f"Raster datasource unavailable: {self._error}"
        ) from self._error

    def read_window_around(
        self, point: GeoPoint, radius_cells: int
    ) -> DemWindow:
        raise UpstreamDatasourceError(
            f"Raster datasource unavailable: {self._error}"
        ) from self._error

    def ping(self) -> bool:
        return False
