# features/profile_analysis

Profile analysis feature: sampled elevation/slope profile along a polyline
(`POST /terrain/profile`, plan F3).

## Contents

- `domain/profile_sample.py` — `ProfileSample` value object (`lat`, `lon`,
  `distance_m`, `elevation_m`, `slope_deg`).
- `domain/elevation_profile.py` — `ElevationProfile` entity (`samples`,
  `total_distance_m`, `elevation_gain_m`, `elevation_loss_m`,
  `max_slope_deg`, `sample_count` property).
- `application/analyze_profile.py` — `AnalyzeProfile` use case: `PathSampler`
  interpolation (capped by `max_samples` / `max_path_points`), one
  `TerrainRepository.window_around` read per sample, aggregates (distance,
  gain, loss, max slope).
- `presentation/profile_router.py` — `APIRouter` for `POST /terrain/profile`;
  use case injected via `Depends(get_analyze_profile)` from
  `app/composition/profile_dependencies.py`.
- `presentation/profile_schemas.py` — `PathPointSchema`, `ProfileRequest`,
  `ProfileSampleSchema`, `ProfileResponse` DTOs.
- `presentation/profile_mapper.py` — `ProfileMapper` domain → DTO adapter.

## Layer rules

`presentation → application → domain`. The use case depends on the
`TerrainRepository` port only. A sample landing on nodata raises
`NoCoverageError` → 404 for the whole request; path < 2 points or limits
exceeded → 400 via `DomainValidationError`. Request schemas carry no
range/min-length constraints so those validations surface as domain
errors (400), while malformed shapes stay 422.
