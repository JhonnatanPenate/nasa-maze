from app.core.domain.bounding_box import BoundingBox
from app.core.domain.dem_window import DemWindow
from app.core.domain.geo_point import GeoPoint
from app.core.domain.halo_window import HaloWindow
from app.core.domain.slope_window import SlopeWindow
from app.core.ports.raster_datasource import RasterDatasource
from app.core.ports.terrain_repository import TerrainRepository
from app.infrastructure.repositories.guarded_call import guarded_call


class SlopeGridTerrainRepository(TerrainRepository):
    """TerrainRepository over a RasterDatasource whose values are
    pre-computed slope in degrees (rejilla grid mode).

    The grid has no elevation band, so the DEM methods raise
    NotImplementedError; use cases must check provides_slope() first and
    call the slope_* methods instead.
    """

    def __init__(self, datasource: RasterDatasource) -> None:
        self._datasource = datasource

    def provides_slope(self) -> bool:
        return True

    def slope_window_around(
        self, point: GeoPoint, radius_cells: int = 0
    ) -> SlopeWindow:
        window = guarded_call(
            lambda: self._datasource.read_window_around(point, radius_cells)
        )
        return self._to_slope_window(window)

    def slope_window_for(self, bbox: BoundingBox) -> SlopeWindow:
        window = guarded_call(lambda: self._datasource.read_window(bbox))
        return self._to_slope_window(window)

    def is_available(self) -> bool:
        try:
            return bool(self._datasource.ping())
        except Exception:
            return False

    def elevation_at(self, point: GeoPoint) -> float:
        raise NotImplementedError("grid mode has no elevation band")

    def window_around(
        self, point: GeoPoint, radius_cells: int = 1
    ) -> DemWindow:
        raise NotImplementedError("grid mode has no elevation band")

    def window_for(self, bbox: BoundingBox) -> DemWindow:
        raise NotImplementedError("grid mode has no elevation band")

    def window_for_with_halo(
        self, bbox: BoundingBox, halo_cells: int
    ) -> HaloWindow:
        raise NotImplementedError("grid mode has no elevation band")

    @staticmethod
    def _to_slope_window(window: DemWindow) -> SlopeWindow:
        return SlopeWindow(
            slope_deg=window.elevation,
            cell_size_x_m=window.cell_size_x_m,
            cell_size_y_m=window.cell_size_y_m,
        )
