from dataclasses import dataclass

from app.features.profile_analysis.domain.profile_sample import ProfileSample


@dataclass(frozen=True)
class ElevationProfile:
    """Sampled elevation/slope profile along a polyline, with aggregates."""

    samples: tuple[ProfileSample, ...]
    total_distance_m: float
    elevation_gain_m: float
    elevation_loss_m: float
    max_slope_deg: float

    @property
    def sample_count(self) -> int:
        return len(self.samples)
