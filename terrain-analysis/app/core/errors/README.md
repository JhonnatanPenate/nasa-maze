# core/errors

Domain error taxonomy and HTTP mapping.

## Contents

- `exceptions.py` — `DomainError` base class and subclasses:
  `DomainValidationError` (→ 400), `NoCoverageError` (→ 404),
  `UpstreamDatasourceError` (→ 502). This is the single file that holds
  the whole error hierarchy (one-class-per-file exception per the plan).
- `error_handlers.py` — `register_exception_handlers(app)` maps every
  `DomainError` to its HTTP status and returns `{"detail": "..."}` per
  FastAPI convention (unknown `DomainError` subclasses → 500). Wired once in
  `app/main.py` (WP6) and reused by feature API tests via
  `tests/api/conftest.py`.

## Layer rules

`exceptions.py` is inner-layer code with no framework dependencies.
`error_handlers.py` is the single boundary that imports FastAPI and is wired
once in `app/main.py`.
