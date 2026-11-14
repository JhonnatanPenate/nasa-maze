# tests/fakes

Reusable test doubles implementing `core/ports` contracts.

## Contents

- `failing_raster_datasource.py` — `FailingRasterDatasource`: a
  `RasterDatasource` stub that raises `OSError` on every read
  (`read_window`, `read_window_with_halo`, `read_window_around`) and
  reports `ping() == False`. Used by repository tests
  (`UpstreamDatasourceError` mapping, `is_available() == False`) and by
  API tests that need the HTTP 502 path or `/health` `degraded`.

## Rules

Fakes implement the port ABCs so type errors surface at construction time.
Keep them behaviour-free: no half-working logic, no data.
