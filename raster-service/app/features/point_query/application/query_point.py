from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import NoCoverageError
from app.core.ports.raster_repository import RasterRepository
from app.features.point_query.domain.point_values import PointValues


class QueryPoint:
    """Nearest-cell band value(s) at one coordinate; no interpolation."""

    def __init__(self, repository: RasterRepository) -> None:
        self._repository = repository

    def execute(
        self, dataset: str, point: GeoPoint, band: str | None = None
    ) -> PointValues:
        metadata = self._repository.metadata(dataset)
        band_names = (
            [metadata.band(band).name]
            if band is not None
            else metadata.band_names()
        )
        cell = metadata.grid_geometry().cell_at(point)
        if cell is None:
            raise NoCoverageError(
                f"Point (lat={point.lat}, lon={point.lon}) lies outside "
                f"the extent of dataset {dataset!r}"
            )
        rows = slice(cell[0], cell[0] + 1)
        cols = slice(cell[1], cell[1] + 1)
        values = {
            name: float(
                self._repository.read_cells(dataset, name, rows, cols)[0, 0]
            )
            for name in band_names
        }
        return PointValues(point=point, values=values)
