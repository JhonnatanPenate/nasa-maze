"""Port: raster band sampling — backed by MS3 Raster Service (`rejilla`)."""

from collections.abc import Sequence
from typing import Protocol

from app.core.domain.geo_point import GeoPoint
from app.core.domain.observations import BandSample


class RasterSource(Protocol):
    """Raster band provider. Implementations: HttpRasterSource (MS3),
    SyntheticRasterSource, UnavailableRasterSource."""

    def ping(self) -> bool:
        """True when the dataset is reachable and readable."""
        ...

    def dataset_bands(self) -> tuple[str, ...]:
        """Canonical band names of the configured dataset."""
        ...

    def point_values(self, point: GeoPoint) -> dict[str, float | None]:
        """All band values at one point; nodata -> None. Raises
        NoCoverageError outside the dataset extent."""
        ...

    def sample_band(
        self,
        band: str,
        path: Sequence[GeoPoint],
        sample_distance_m: float,
    ) -> tuple[BandSample, ...]:
        """One band's values at every arc-length sample of ``path`` —
        one batched upstream call per band."""
        ...
