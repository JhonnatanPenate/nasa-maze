# tests/integration

Cross-service integration tests: they need a **running MS3 Raster Service**
and the delivered `data/gale/processed/rejilla_ruta_90m.tif`. Every test is
skipped when MS3 is unreachable or the file is absent.

## Contents

- `test_ms3_parity.py` — bit-for-bit parity between
  `HttpRasterDatasource` (HTTP reads against a live MS3, base URL from
  `MS4_RASTER_SERVICE_URL`, default `http://localhost:8003`) and
  `GeoTiffRasterDatasource` (local file reads, band
  `MS4_REJILLA_SLOPE_BAND`) over the rejilla grid: `np.array_equal(...,
  equal_nan=True)` on elevations and exact equality of metric cell sizes
  and `HaloWindow` core slices.

## Running

```bash
# MS3 must be up (e.g. the Docker container on port 8003)
pytest tests/integration -v
MS4_RASTER_SERVICE_URL=http://ms3:8003 pytest tests/integration -v
```

## Layer rules

Tests may import anything under `app/` plus httpx/numpy/pytest. They never
mock MS3 — MockTransport coverage lives in
`tests/unit/test_http_raster_datasource.py`.
