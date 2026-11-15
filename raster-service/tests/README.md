# tests

Test suite for MS3. TDD: ≥ 3 tests per feature (happy / sad / edge).
Run with `.venv/Scripts/python -m pytest -q` from `raster-service/`.

## Contents

- `conftest.py` — shared fixtures: `settings`, session-scoped GeoTIFF
  `geotiff_path`, `memory_datasource`, `geotiff_datasource`, the
  parametrized `datasource` fixture (memory + geotiff swap proof),
  `dataset_config`, `repository`.
- `fakes/` — hand-written test doubles (`FailingRasterDatasource`).
- `fixtures/` — `make_test_raster.py`: generates the 3-band 10×8
  geographic GeoTIFF (+ projected/rotated variants) at test time.
  Binary fixtures are never committed.
- `unit/` — domain, ports, datasources, repository, encoder,
  composition providers.
- `api/` — HTTP contract tests, one file per endpoint.
- `integration/` — real-data tests on the delivered rejilla file
  (skipped when absent).

## Conventions

Every feature needs happy/sad/edge cases; repository behaviour is
proven datasource-agnostic via the parametrized `datasource` fixture.
