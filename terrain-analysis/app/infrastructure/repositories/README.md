# infrastructure/repositories

Concrete `TerrainRepository` implementations.

## Contents

- `dem_terrain_repository.py` — `DemTerrainRepository`: implements the
  `TerrainRepository` port on top of a `RasterDatasource`. `elevation_at`
  reads the single cell containing the point (NaN → `NoCoverageError`);
  `window_around`/`window_for` delegate to the datasource; `is_available`
  maps any `ping()` failure to `False`. `DomainError` subclasses pass
  through unchanged; every other exception is wrapped in
  `UpstreamDatasourceError` (chained via `from`).

## Layer rules

Implements `core/ports` and returns `core/domain` types only. Translates
datasource failures into `UpstreamDatasourceError` and nodata coverage gaps
into `NoCoverageError`. Contains no FastAPI or presentation code.
