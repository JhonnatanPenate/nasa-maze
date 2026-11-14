# features/health

Health feature: liveness plus datasource connectivity (`GET /health`, plan F1).

## Contents

- `presentation/health_schemas.py` — `HealthResponse`: `status`
  (`"ok" | "degraded"`) and `datasource` (`"ok" | "unavailable"`).
- `presentation/health_router.py` — `GET /health`: always answers 200.
  Reports `{"status": "ok", "datasource": "ok"}` when
  `TerrainRepository.is_available()` is true, else
  `{"status": "degraded", "datasource": "unavailable"}`. A datasource
  that fails to build at provider time is covered too: the composition
  root substitutes `UnavailableRasterDatasource` (ping `False`), so the
  endpoint degrades instead of erroring.

## Layer rules

The router depends on the `TerrainRepository` port via
`Depends(get_terrain_repository)`; it must not import concrete datasource
implementations or rasterio.
