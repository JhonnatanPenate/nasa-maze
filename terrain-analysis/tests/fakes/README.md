# tests/fakes

Reusable test doubles implementing `core/ports` contracts.

## Contents

- `failing_raster_datasource.py` — `FailingRasterDatasource`: a
  `RasterDatasource` stub that raises `OSError` on every read
  (`read_window`, `read_window_with_halo`, `read_window_around`) and
  reports `ping() == False`. Used by repository tests
  (`UpstreamDatasourceError` mapping, `is_available() == False`) and by
  API tests that need the HTTP 502 path or `/health` `degraded`.
- `fake_slope_terrain_repository.py` — `FakeSlopeTerrainRepository`: a
  `TerrainRepository` stub for grid mode. `provides_slope()` is True and
  `slope_window_around`/`slope_window_for` serve windows from a small
  in-memory slope array over a fixed extent (out-of-extent cells read as
  NaN, non-intersecting bboxes raise `NoCoverageError`). DEM methods
  raise `NotImplementedError`.

## Rules

Fakes implement the port ABCs so type errors surface at construction time.
Keep them behaviour-free: no half-working logic, no data.
