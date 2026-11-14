# features/health

Health feature: liveness plus datasource connectivity (`GET /health`, plan F1).

## Contents (planned)

- `presentation/health_router.py` — router for `GET /health`; reports
  `{"status": "ok", "datasource": "ok"}` or `{"status": "degraded",
  "datasource": "unavailable"}` when `RasterDatasource.ping()` fails
  (still HTTP 200).

## Layer rules

Presentation may call the `RasterDatasource` port (obtained via
`composition/dependencies.py`) but must not import concrete datasource
implementations or rasterio.
