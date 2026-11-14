from abc import ABC, abstractmethod

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.dem_window import DemWindow
from app.core.domain.geo_point import GeoPoint
from app.core.domain.halo_window import HaloWindow


class RasterDatasource(ABC):
    """Data-access contract for raster DEM sources.

    Implementations may raise any exception on I/O failure; the repository
    layer wraps them into UpstreamDatasourceError. Coverage problems are
    reported by implementations raising NoCoverageError directly.
    """

    @abstractmethod
    def read_window(
        self, bbox: BoundingBox, halo_cells: int = 0
    ) -> DemWindow:
        """Return the cells covering bbox, clipped to the DEM extent.

        With halo_cells > 0 the window additionally includes up to that
        many real DEM rows/columns beyond the bbox on every side (clipped
        at the DEM edge). Raises NoCoverageError if bbox does not
        intersect the extent.
        """

    @abstractmethod
    def read_window_with_halo(
        self, bbox: BoundingBox, halo_cells: int
    ) -> HaloWindow:
        """Return the bbox window plus a halo of real DEM cells.

        The result's window covers the bbox expanded by up to halo_cells
        rows/columns on every side, clipped at the DEM edge; its core
        slices mark the part a plain read_window(bbox) would return. The
        window-size cap (max_window_cells) applies to the core cell count
        only, not to the halo.
        """

    @abstractmethod
    def read_window_around(self, point: GeoPoint, radius_cells: int) -> DemWindow:
        """Return a (2*radius_cells+1, 2*radius_cells+1) window centred on the
        cell containing point. Cells outside the DEM extent are NaN."""

    @abstractmethod
    def ping(self) -> bool:
        """Return True when the datasource is reachable/readable."""
