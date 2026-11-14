# composition

Composition root: dependency-injection wiring for FastAPI `Depends`.

## Contents

- `dependencies.py` — plain callables (no FastAPI import) usable with
  `Depends`: `get_settings` (lru_cached), `build_datasource(settings)` —
  selects `SyntheticDemDatasource` / `GeoTiffRasterDatasource` from
  `Settings.datasource_kind` (`http` is reserved and raises `ValueError`,
  as does `geotiff` with an empty `dem_path`), `get_raster_datasource`
  (lru_cached singleton), `get_terrain_repository`, and the domain-service
  providers `get_slope_calculator`, `get_terrain_classifier` (thresholds
  from settings), `get_distance_calculator`
  (`planet_radius_km * 1000` metres), `get_path_sampler`.

## Conventions

Feature work packages add their use-case providers in separate files named
`app/composition/<feature>_dependencies.py` (e.g.
`point_dependencies.py`), keeping this file free of feature imports.

## Layer rules

This is the only layer allowed to import everything (presentation,
application, domain, infrastructure). All outward knowledge converges here
so inner layers stay free of concrete dependencies.
