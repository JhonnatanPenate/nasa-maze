# features/profile_analysis

Profile analysis feature: sampled elevation/slope profile along a polyline
(`POST /terrain/profile`, plan F3).

## Contents (planned)

- `domain/elevation_profile.py` — `ElevationProfile` and `ProfileSample` entities.
- `application/analyze_profile.py` — `AnalyzeProfile` use case: `PathSampler`
  interpolation (capped by `max_samples` / `max_path_points`), per-sample
  elevation + slope, aggregates (distance, gain, loss, max slope).
- `presentation/profile_router.py` — router for `POST /terrain/profile`.
- `presentation/profile_schemas.py` — `ProfileRequest` / `ProfileResponse` DTOs.
- `presentation/profile_mapper.py` — domain → DTO adapter.

## Layer rules

`presentation → application → domain`. The use case depends on the
`TerrainRepository` port only. A sample landing on nodata raises
`NoCoverageError` → 404 for the whole request; path < 2 points or limits
exceeded → 400 via `DomainValidationError`.
