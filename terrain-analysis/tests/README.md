# tests

Test suite for the MS4 Terrain Analysis Service (TDD: minimum happy path,
edge case, and expected failure per feature, plus API contract tests).

## Contents

- `conftest.py` — shared fixtures (default `Settings`; later: `TestClient`
  wired with `SyntheticDemDatasource`, a deterministic DEM, and a
  session-scoped generated test GeoTIFF).
- `unit/` — domain, application, and repository unit tests
  (`test_slope_calculator`, `test_terrain_classifier`,
  `test_distance_calculator`, `test_path_sampler`,
  `test_dem_terrain_repository`, `test_analyze_point`,
  `test_analyze_profile`, `test_analyze_area`).
- `api/` — endpoint contract tests (`test_health_endpoint`,
  `test_point_endpoint`, `test_profile_endpoint`, `test_area_endpoint`)
  verifying SPEC_MS4 schemas and 400/404/422/502 codes.
- `fixtures/` — `make_test_dem.py`: deterministic test GeoTIFF generator
  (generated at test time via rasterio; binaries are git-ignored).

## Layer rules

Tests may import any layer. Unit tests for `core/domain` must run without
FastAPI or rasterio imports. Contract tests pin the SPEC_MS4 response
schemas.
