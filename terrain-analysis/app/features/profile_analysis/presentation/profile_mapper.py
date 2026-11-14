from app.features.profile_analysis.domain.elevation_profile import (
    ElevationProfile,
)
from app.features.profile_analysis.presentation.profile_schemas import (
    ProfileResponse,
    ProfileSampleSchema,
)


class ProfileMapper:
    """Domain -> response DTO adapter for ElevationProfile."""

    @staticmethod
    def to_response(profile: ElevationProfile) -> ProfileResponse:
        return ProfileResponse(
            sample_count=profile.sample_count,
            total_distance_m=profile.total_distance_m,
            elevation_gain_m=profile.elevation_gain_m,
            elevation_loss_m=profile.elevation_loss_m,
            max_slope_deg=profile.max_slope_deg,
            samples=[
                ProfileSampleSchema(
                    lat=sample.lat,
                    lon=sample.lon,
                    distance_m=sample.distance_m,
                    elevation_m=sample.elevation_m,
                    slope_deg=sample.slope_deg,
                )
                for sample in profile.samples
            ],
        )
