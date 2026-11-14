from abc import ABC, abstractmethod

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.dem_window import DemWindow
from app.core.domain.geo_point import GeoPoint


class TerrainRepository(ABC):
    """Domain-facing contract used by application use cases.

    Implementations translate datasource results into domain objects and map
    failures: nodata/outside-extent -> NoCoverageError, datasource failure ->
    UpstreamDatasourceError.
    """

    @abstractmethod
    def elevation_at(self, point: GeoPoint) -> float:
        """Elevation in metres at point. Raises NoCoverageError on nodata or
        outside the DEM extent."""

    @abstractmethod
    def window_around(self, point: GeoPoint, radius_cells: int = 1) -> DemWindow:
        """DEM window centred on the cell containing point."""

    @abstractmethod
    def window_for(self, bbox: BoundingBox) -> DemWindow:
        """DEM window covering bbox. Raises NoCoverageError when bbox does not
        intersect the DEM extent."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when the underlying datasource is reachable."""
