import math

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.dem_window import DemWindow
from app.core.domain.geo_point import GeoPoint
from app.core.domain.halo_window import HaloWindow
from app.core.errors.exceptions import NoCoverageError
from app.core.ports.raster_datasource import RasterDatasource
from app.core.ports.terrain_repository import TerrainRepository
from app.infrastructure.repositories.guarded_call import guarded_call


class DemTerrainRepository(TerrainRepository):
    """TerrainRepository port implementation over a RasterDatasource.

    Domain errors raised by the datasource (NoCoverageError,
    DomainValidationError) pass through unchanged; any other failure is
    wrapped in UpstreamDatasourceError so callers see only the domain
    taxonomy.
    """

    def __init__(self, datasource: RasterDatasource) -> None:
        self._datasource = datasource

    def elevation_at(self, point: GeoPoint) -> float:
        window = guarded_call(
            lambda: self._datasource.read_window_around(point, 0)
        )
        value = window.center_value()
        if not math.isfinite(value):
            raise NoCoverageError(
                f"No DEM coverage at lat={point.lat}, lon={point.lon}"
            )
        return value

    def window_around(
        self, point: GeoPoint, radius_cells: int = 1
    ) -> DemWindow:
        return guarded_call(
            lambda: self._datasource.read_window_around(point, radius_cells)
        )

    def window_for(self, bbox: BoundingBox) -> DemWindow:
        return self.window_for_with_halo(bbox, 0).window

    def window_for_with_halo(
        self, bbox: BoundingBox, halo_cells: int
    ) -> HaloWindow:
        return guarded_call(
            lambda: self._datasource.read_window_with_halo(bbox, halo_cells)
        )

    def is_available(self) -> bool:
        try:
            return bool(self._datasource.ping())
        except Exception:
            return False
