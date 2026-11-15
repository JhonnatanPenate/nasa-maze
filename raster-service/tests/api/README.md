# tests/api

HTTP contract tests — one file per endpoint of
`docs/SPEC_MS3_RASTER.md`, run through `fastapi.testclient.TestClient`.

## Contents

- `test_app.py` — route-registration smoke, OpenAPI surface, and the
  500 catch-all error handler.
- `test_health.py` — `GET /health`.
- `test_datasets.py` — `GET /raster/datasets`.
- `test_metadata.py` — `GET /raster/{dataset}/metadata`.
- `test_point.py` — `GET /raster/{dataset}/point`.
- `test_window.py` — `POST /raster/{dataset}/window`.
- `test_sample.py` — `POST /raster/{dataset}/sample`.
- `test_layer.py` — `GET /raster/{dataset}/layer/{band}`.

## Fixtures (tests/conftest.py)

- `client` — `TestClient` over `create_app()` backed by the in-memory
  test grid: dataset `test`, 10 rows x 8 cols float32, bands
  `slope_deg` / `roughness_m` / `dark_fraction`
  (see `tests/fixtures/make_test_raster.py`).
- `make_client(repository=..., settings=...)` — same, with the injected
  doubles swapped via `dependency_overrides` (e.g. a
  `FailingRasterDatasource`-backed repository for the 503 path).
- `mount_router(router, repository, settings=None)` — mounts a single
  router on a bare FastAPI app with the service error handlers, for
  tests that should not touch `app.main`.
