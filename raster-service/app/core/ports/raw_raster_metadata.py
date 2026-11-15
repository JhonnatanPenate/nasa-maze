from dataclasses import dataclass

from app.core.domain.bounding_box import BoundingBox


@dataclass(frozen=True)
class RawRasterMetadata:
    """What a RasterDatasource reports about its file, before the
    repository merges config (units, CRS label, colormaps) into the
    domain DatasetMetadata."""

    extent: BoundingBox
    rows: int
    cols: int
    band_descriptions: tuple[str | None, ...]
    nodata: float | None
    is_geographic: bool
    is_north_up: bool
