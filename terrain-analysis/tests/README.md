# tests

Test suite for the MS4 Terrain Analysis Service (TDD: minimum happy path,
edge case, and expected failure per feature, plus API contract tests).

## Contents

- `conftest.py` — shared fixtures: `settings`, `small_dem` (deterministic
  21×21 plane DEM with one nodata cell at (5,5), extent lon 77.4–77.6 /
  lat 18.4–18.6), `dem_window_mapper`, `synthetic_datasource`,
  `geotiff_datasource` (session-scoped GeoTIFF written via
  `fixtures/make_test_dem.py` from the same array/extent), and the
  parametrized `datasource` fixture (`synthetic`/`geotiff`) powering the
  repository swap-proof tests.
- `unit/` — domain, application, infrastructure, and repository unit tests
  (domain calculators, `test_dem_window_mapper`, `test_grid_geometry`,
  `test_synthetic_dem_datasource`, `test_geotiff_datasource`,
  `test_dem_terrain_repository` (incl. `window_for_with_halo` swap-proof
  cases), `test_terrain_point_sampler`, `test_dependencies`, plus feature
  use-case tests).
- `api/` — endpoint contract tests verifying SPEC_MS4 schemas and
  400/404/422/502 codes (`test_health_endpoint`, `test_point_endpoint`,
  `test_profile_endpoint`, `test_area_endpoint`) plus `test_app.py`
  covering `create_app()` routes and the default-datasource smoke
  requests. `api/conftest.py` `make_client` accepts optional `datasource`
  and `settings` keyword overrides.
- `fixtures/` — `make_test_dem.py`: deterministic test GeoTIFF generator
  (generated at test time via rasterio; binaries are never committed).
- `fakes/` — reusable port test doubles (`FailingRasterDatasource` for the
  502/`is_available` failure paths).

## Layer rules

Tests may import any layer. Unit tests for `core/domain` must run without
FastAPI or rasterio imports. Contract tests pin the SPEC_MS4 response
schemas.
