from app.core.domain.bounding_box import BoundingBox
from app.core.domain.dem_window import DemWindow
from app.core.domain.geo_point import GeoPoint
from app.core.ports.raster_datasource import RasterDatasource


class FailingRasterDatasource(RasterDatasource):
    """RasterDatasource stub whose reads always fail with OSError.

    Reusable by repository and API tests that need the 502 failure path.
    """

    def read_window(self, bbox: BoundingBox) -> DemWindow:
        raise OSError("failing datasource: read_window unavailable")

    def read_window_around(self, point: GeoPoint, radius_cells: int) -> DemWindow:
        raise OSError("failing datasource: read_window_around unavailable")

    def ping(self) -> bool:
        return False
