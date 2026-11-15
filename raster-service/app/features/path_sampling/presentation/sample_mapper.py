import math

from app.features.path_sampling.domain.path_profile import PathProfile
from app.features.path_sampling.presentation.sample_schemas import (
    SampleEntryResponse,
    SampleResponse,
)


class SampleMapper:
    """Domain -> DTO adapter for path sampling (NaN -> null on the wire)."""

    @staticmethod
    def to_response(result: PathProfile) -> SampleResponse:
        entries = [
            SampleEntryResponse(
                lat=sample.point.lat,
                lon=sample.point.lon,
                distance_m=sample.distance_m,
                value=None if not math.isfinite(value) else float(value),
            )
            for sample, value in zip(result.samples, result.values)
        ]
        return SampleResponse(
            band=result.band,
            sample_count=len(entries),
            total_distance_m=result.total_distance_m,
            samples=entries,
        )
