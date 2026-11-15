# app/core/errors

Exception taxonomy shared by every layer.

## Contents

- `exceptions.py`:
  - `RasterServiceError` — base class.
  - `RasterValidationError` — bad input (HTTP 400).
  - `NotFoundError` — base for `UnknownDatasetError`, `UnknownBandError`
    (detail lists valid names) and `NoCoverageError` (HTTP 404).
  - `DatasetUnavailableError` — file missing/corrupt/not geographic/not
    north-up (HTTP 503).
- `error_handlers.py` — `register_exception_handlers(app)`: maps the
  taxonomy above by walking `type(error).__mro__` (unmapped
  `RasterServiceError` → 500) and registers a catch-all
  `Exception` handler → 500 `{"detail": "internal error"}`.

## Layer rules

`exceptions.py` is stdlib-only. `error_handlers.py` is the only fastapi
import allowed in `core/`; it is wired in `app.main.create_app()` and in
`tests.conftest.mount_router`.
