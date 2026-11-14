# core/errors

Domain error taxonomy and HTTP mapping.

## Contents

- `exceptions.py` — `DomainError` base class and subclasses:
  `DomainValidationError` (→ 400), `NoCoverageError` (→ 404),
  `UpstreamDatasourceError` (→ 502). This is the single file that holds
  the whole error hierarchy (one-class-per-file exception per the plan).
- `error_handlers.py` — **deferred to WP6** (it imports FastAPI):
  `register_exception_handlers(app)` returning `{"detail": "..."}` per
  FastAPI convention, wired once in `app/main.py`.

## Layer rules

`exceptions.py` is inner-layer code with no framework dependencies.
`error_handlers.py` is the single boundary that imports FastAPI and is wired
once in `app/main.py`.
