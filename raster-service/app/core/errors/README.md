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

## Layer rules

`exceptions.py` is stdlib-only. The FastAPI `error_handlers.py`
(the only fastapi import allowed in `core/`) arrives in WP3.
