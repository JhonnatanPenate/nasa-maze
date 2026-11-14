# composition

Composition root: dependency-injection wiring for FastAPI `Depends`.

## Contents

- `dependencies.py` — providers chained via `Depends` defaults:
  - `get_settings` (lru_cached) and `build_datasource(settings)` —
    selects `SyntheticDemDatasource` / `GeoTiffRasterDatasource` from
    `Settings.datasource_kind` (`http` is reserved and raises
    `ValueError`, as does `geotiff` with an empty `dem_path`).
  - `get_raster_datasource` (lru_cached singleton) — a build failure does
    **not** propagate: it falls back to `UnavailableRasterDatasource`,
    whose `ping()` is `False` (`/health` → `degraded`) and whose reads
    raise `UpstreamDatasourceError` → 502.
  - `get_terrain_repository(datasource=Depends(get_raster_datasource))`,
    `get_terrain_classifier(settings=Depends(get_settings))`,
    `get_distance_calculator(settings=Depends(get_settings))`,
    `get_path_sampler(distance_calculator=Depends(get_distance_calculator))`,
    `get_terrain_point_sampler(repository=Depends(get_terrain_repository),
    slope_calculator=Depends(get_slope_calculator))`,
    `get_slope_calculator()`.
- `point_dependencies.py` / `profile_dependencies.py` /
  `area_dependencies.py` — use-case providers built only from the chained
  providers above, so `dependency_overrides` on `get_settings` or
  `get_raster_datasource` propagate end-to-end (e.g. custom slope
  thresholds reach `/terrain/point`'s `terrain_class`; a custom
  `TerrainClassifier` supplies `AnalyzeArea.steep_min_deg` via the
  classifier's `steep_min_deg` property).

## Conventions

Feature work packages add their use-case providers in separate files named
`app/composition/<feature>_dependencies.py`, keeping `dependencies.py`
free of feature imports.

## Layer rules

This is the only layer allowed to import everything (presentation,
application, domain, infrastructure). All outward knowledge converges here
so inner layers stay free of concrete dependencies.
