# features

Feature-first packages: one subpackage per API capability.

## Contents

- `point_analysis/` — `GET /terrain/point` (F2).
- `profile_analysis/` — `POST /terrain/profile` (F3).
- `area_analysis/` — `POST /terrain/area` (F4).
- `health/` — `GET /health` (F1).

Each feature is split into `domain/` (result entities), `application/`
(use cases orchestrating domain + ports), and `presentation/` (FastAPI
router, pydantic schemas, domain→DTO mapper).

## Layer rules

Inside a feature, dependencies point inward: `presentation → application →
domain`. Use cases depend on `TerrainRepository` (a port), never on a concrete
datasource. Presentation may import application and domain, but never
rasterio or datasource internals.
