# health

`GET /health` — liveness plus per-dataset readability (plan F1; doubles
as MS4 `HttpRasterDatasource.ping()`).

## Contents

- `presentation/health_schemas.py` — `HealthResponse` (`status`,
  `dataset_count`, `datasets[]`) and `DatasetHealth` (`name`,
  `readable`).
- `presentation/health_router.py` — answers 200 always; `degraded` when
  any registered dataset fails `RasterRepository.is_readable`, `ok` with
  `dataset_count: 0` on an empty registry.

## Layer rules

Presentation-only feature: the router talks straight to the
`RasterRepository` port via `Depends(get_repository)` — no application
layer needed (plan §3.4).
