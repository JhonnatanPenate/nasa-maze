# core/errors

Domain error taxonomy and HTTP mapping.

## Contents (planned)

- `exceptions.py` — `DomainError` base class and subclasses:
  `DomainValidationError` (→ 400), `NoCoverageError` (→ 404),
  `UpstreamDatasourceError` (→ 502).
- `error_handlers.py` — `register_exception_handlers(app)`: FastAPI exception
  handlers returning `{"detail": "..."}` per FastAPI convention.

## Layer rules

`exceptions.py` is inner-layer code with no framework dependencies.
`error_handlers.py` is the single boundary that imports FastAPI and is wired
once in `app/main.py`.
