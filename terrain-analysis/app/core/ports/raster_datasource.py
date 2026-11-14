from abc import ABC, abstractmethod

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.dem_window import DemWindow
from app.core.domain.geo_point import GeoPoint


class RasterDatasource(ABC):
    """Data-access contract for raster DEM sources.

    Implementations may raise any exception on I/O failure; the repository
    layer wraps them into UpstreamDatasourceError. Coverage problems are
    reported by implementations raising NoCoverageError directly.
    """

    @abstractmethod
    def read_window(self, bbox: BoundingBox) -> DemWindow:
        """Return the cells covering bbox, clipped to the DEM extent.

        Raises NoCoverageError if bbox does not intersect the extent.
        """

    @abstractmethod
    def read_window_around(self, point: GeoPoint, radius_cells: int) -> DemWindow:
        """Return a (2*radius_cells+1, 2*radius_cells+1) window centred on the
        cell containing point. Cells outside the DEM extent are NaN."""

    @abstractmethod
    def ping(self) -> bool:
        """Return True when the datasource is reachable/readable."""
