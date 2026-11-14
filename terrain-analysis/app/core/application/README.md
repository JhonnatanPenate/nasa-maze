# core/application

Core-level application services shared across features.

## Contents

- `terrain_point_sample.py` — `TerrainPointSample` frozen dataclass:
  `elevation_m`, `slope_deg` sampled at one coordinate.
- `terrain_point_sampler.py` — `TerrainPointSampler(repository,
  slope_calculator)`: `sample(point)` issues a single
  `TerrainRepository.window_around(point, 1)` read; NaN centre elevation
  → `NoCoverageError("No DEM coverage at ...")`; a valid centre whose
  slope is undefined → `NoCoverageError("Slope undefined at ...: no
  valid neighbouring cells")`. Used by the point and profile use cases.

## Layer rules

Application services may import `core/ports` and `core/domain` (plus
`core/errors`) only — never FastAPI, pydantic DTOs, or concrete
datasource implementations.
