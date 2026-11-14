# app

Application source package for the MS4 Terrain Analysis Service.

## Contents

- `main.py` — `create_app()`: FastAPI app factory; registers the health,
  point, profile and area routers plus the domain exception handlers;
  module-level `app` for uvicorn.
- `core/` — cross-cutting layers: `config`, `domain`, `application`,
  `errors`, `ports`.
- `features/` — one subpackage per API feature, each split into
  `domain` / `application` / `presentation`.
- `infrastructure/` — `datasources` and `repositories` implementations.
- `composition/` — dependency-injection wiring for FastAPI `Depends`.

## Layer rules

Dependencies point inward only: `presentation → application → domain`;
`infrastructure` implements `core/ports` abstractions; `composition` may wire
everything together. The `domain` layer must never import FastAPI, pydantic
DTOs, rasterio, or httpx.
