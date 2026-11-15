from typing import Sequence

from app.core.domain.distance_calculator import DistanceCalculator
from app.core.domain.geo_point import GeoPoint
from app.core.domain.path_sampler import PathSampler
from app.core.errors.exceptions import (
    NoCoverageError,
    RasterValidationError,
)
from app.core.ports.raster_repository import RasterRepository
from app.features.path_sampling.domain.path_profile import PathProfile


class SamplePath:
    """Nearest-cell band values along a polyline at regular arc-length
    intervals; no interpolation (F5/A5)."""

    def __init__(
        self,
        repository: RasterRepository,
        planet_radius_km: float = 3396.19,
        max_path_points: int = 100,
        max_samples: int = 1000,
    ) -> None:
        self._repository = repository
        self._sampler = PathSampler(
            DistanceCalculator(planet_radius_km * 1000.0)
        )
        self._max_path_points = max_path_points
        self._max_samples = max_samples

    def execute(
        self,
        dataset: str,
        path: Sequence[GeoPoint],
        band: str,
        sample_distance_m: float | None = None,
    ) -> PathProfile:
        if len(path) < 2:
            raise RasterValidationError(
                f"Path needs at least 2 points, got {len(path)}"
            )
        if len(path) > self._max_path_points:
            raise RasterValidationError(
                f"Path holds {len(path)} points, exceeding the limit of "
                f"{self._max_path_points}"
            )
        metadata = self._repository.metadata(dataset)
        band_name = metadata.band(band).name
        step = (
            metadata.resolution_m
            if sample_distance_m is None
            else sample_distance_m
        )
        samples = self._sampler.sample(path, step, self._max_samples)
        geometry = metadata.grid_geometry()
        cells = [geometry.cell_at(sample.point) for sample in samples]
        inside = [cell for cell in cells if cell is not None]
        if not inside:
            raise NoCoverageError(
                "Every sample of the path lies outside the extent of "
                f"dataset {dataset!r}"
            )
        row_off = min(cell[0] for cell in inside)
        col_off = min(cell[1] for cell in inside)
        window = self._repository.read_cells(
            dataset,
            band_name,
            slice(row_off, max(cell[0] for cell in inside) + 1),
            slice(col_off, max(cell[1] for cell in inside) + 1),
        )
        values = [
            float("nan")
            if cell is None
            else float(window[cell[0] - row_off, cell[1] - col_off])
            for cell in cells
        ]
        return PathProfile(
            band=band_name,
            total_distance_m=samples[-1].distance_m,
            samples=tuple(samples),
            values=tuple(values),
        )
