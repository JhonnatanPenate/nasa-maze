# app/features

Feature-first modules — one folder per REST endpoint. Each keeps its own
`application/` (use cases), optional `domain/` (result objects) and
`presentation/` (router + pydantic schemas + domain→DTO mapper).

## Contents

- `health/` — `GET /health`: liveness + per-dataset readability (MS4's
  `ping()`); presentation only.
- `datasets/` — `GET /raster/datasets` (registry list with configured
  paths) and `GET /raster/{dataset}/metadata`.
- `point_query/` — `GET /raster/{dataset}/point`: nearest-cell band
  value(s) at a coordinate, verbatim, nodata → null.
- `window_read/` — `POST /raster/{dataset}/window` (WP4).
- `path_sampling/` — `POST /raster/{dataset}/sample` (WP5a).
- `layer_render/` — `GET /raster/{dataset}/layer/{band}` PNG (WP5b).

## Layer rules

- `application/` may import `core/domain`, `core/ports`, `core/errors` —
  never fastapi, pydantic, rasterio or concrete infrastructure.
- `presentation/` may import `application`, `core/*` and `composition`
  (for `Depends` providers); it owns all pydantic DTOs and the NaN →
  null / verbatim-float serialisation rules.
