# app

Application source package for the MS4 Terrain Analysis Service.

## Contents

- `main.py` — `create_app()`: FastAPI app factory; registers routers and
  exception handlers (WP6).
- `core/` — cross-cutting layers: `config`, `domain`, `errors`, `ports`.
- `features/` — one subpackage per API feature, each split into
  `domain` / `application` / `presentation`.
- `infrastructure/` — `datasources` and `repositories` implementations.
- `composition/` — dependency-injection wiring for FastAPI `Depends`.

## Layer rules

Dependencies point inward only: `presentation → application → domain`;
`infrastructure` implements `core/ports` abstractions; `composition` may wire
everything together. The `domain` layer must never import FastAPI, pydantic
DTOs, rasterio, or httpx.
