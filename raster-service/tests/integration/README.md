# tests/integration

Integration tests against real, on-disk data — no in-memory doubles and
no dependency overrides. The app is assembled with `create_app()` and the
real default `Settings`, so requests exercise the full stack:
presentation → application → domain → `RegistryRasterRepository` →
`GeoTiffRasterDatasource` → `data/gale/processed/rejilla_ruta_90m.tif`.

## Contents

- `test_rejilla_real.py` — contract test over the delivered rejilla
  raster. Pins the ground truth of
  `docs/raster_service/IMPLEMENTATION_PLANMS3_1.md` §1.1: 72 cols × 105
  rows, 6 canonical band names in order, `IAU_2015:49900`, resolution
  ≈ 0.0015183544372303697°, file bounds, exactly one `null` in band
  `fraccion_oscura`, a 6-value point read, and a 72×105 PNG layer.
  The whole module skips when `Settings().rejilla_path` does not exist
  (the data package is not committed to git).

## Layer rules

Tests may import `app.*` at any layer; they run against the assembled
service, so they also verify `composition` wiring with real datasources.
The raster file itself is generated/delivered outside this repo —
never write to it from a test.
