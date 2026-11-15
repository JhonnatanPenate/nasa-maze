# infrastructure/repositories

Concrete `TerrainRepository` implementations.

## Contents

- `dem_terrain_repository.py` — `DemTerrainRepository`: implements the
  `TerrainRepository` port on top of a `RasterDatasource`. `elevation_at`
  reads the single cell containing the point (NaN → `NoCoverageError`);
  `window_around`/`window_for` delegate to the datasource;
  `window_for(bbox)` delegates to `window_for_with_halo(bbox, 0)`, which
  returns the full `HaloWindow` (window + core slices); `is_available`
  maps any `ping()` failure to `False`.
  `DomainError` subclasses pass through unchanged; every other exception
  is wrapped in `UpstreamDatasourceError` (chained via `from`).
- `guarded_call.py` — `guarded_call(call)`: the shared error-mapping
  wrapper (DomainError passthrough, other exceptions →
  `UpstreamDatasourceError`) used by both repositories.
- `slope_grid_terrain_repository.py` — `SlopeGridTerrainRepository`:
  `TerrainRepository` for rejilla grid mode, where the datasource band
  holds pre-computed slope in degrees. `provides_slope()` is `True`;
  `slope_window_around`/`slope_window_for` convert the datasource
  `DemWindow` payload into a `SlopeWindow` verbatim (no slope
  recomputation). The DEM methods (`elevation_at`, `window_*`) raise
  `NotImplementedError` because the grid has no elevation band.

## Layer rules

Implements `core/ports` and returns `core/domain` types only. Translates
datasource failures into `UpstreamDatasourceError` and nodata coverage gaps
into `NoCoverageError`. Contains no FastAPI or presentation code.
