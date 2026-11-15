# MS3 Raster Service

Single HTTP access point to Mars raster files for the Planetary Explorer
monorepo. MS3 owns all raster I/O — opening files, coordinate→cell math,
clipping, halos, nodata — and returns plain JSON / PNG so consumers
(MS4 Terrain Analysis, MS5 Risk Assessment, MS6 Routing Engine, Core)
never import rasterio. Band values are served **verbatim**: never
resampled, interpolated, or recomputed.

The MVP registers one dataset, `rejilla` →
`data/gale/processed/rejilla_ruta_90m.tif` (72 cols × 105 rows, 6
float32 bands, CRS `IAU_2015:49900`, Mars radius 3396.19 km).

Contract of record: `docs/SPEC_MS3_RASTER.md`. Implementation plan:
`docs/raster_service/IMPLEMENTATION_PLANMS3_1.md`. Data provenance:
see `DATA_SOURCES.md` at the repo root.

## Setup

Requires Python ≥ 3.12 (rasterio wheels on Windows).

```bash
cd raster-service
py -3.12 -m venv .venv
source .venv/Scripts/activate
pip install -e ".[dev]"
```

## Run

```bash
uvicorn app.main:app --port 8003
```

## Test

```bash
pytest -q
```

## Environment variables

All settings use the `MS3_` prefix (`app/core/config/settings.py`).

| Variable | Default | Purpose |
|---|---|---|
| `MS3_REJILLA_PATH` | `<repo>/data/gale/processed/rejilla_ruta_90m.tif` | Path of the default `rejilla` dataset |
| `MS3_DATASETS` | `{"rejilla": {"path": MS3_REJILLA_PATH}}` | Full dataset registry as a JSON object: name → `DatasetConfig` (`path`, `kind`: `geotiff`\|`memory`, `band_names`, `band_units`, `colormaps`, `value_ranges`) |
| `MS3_MAX_WINDOW_CELLS` | `1000000` | Cap on window cell counts → 400 |
| `MS3_MAX_PATH_POINTS` | `100` | Max vertices in a `/sample` path → 400 |
| `MS3_MAX_SAMPLES` | `1000` | Max samples along a path → 400 |
| `MS3_PLANET_RADIUS_KM` | `3396.19` | Mars radius for distances and `resolution_m` |
| `MS3_CRS_LABEL` | `IAU_2015:49900` | Reported CRS (file WKT is anonymous) |

Dataset paths come only from configuration — never hardcoded.

## Endpoints

Base URL `/raster`, port `8003`.

| Endpoint | Purpose | curl |
|---|---|---|
| `GET /health` | Liveness + per-dataset readability (MS4's `ping()`) | `curl "http://localhost:8003/health"` |
| `GET /raster/datasets` | List registered datasets | `curl "http://localhost:8003/raster/datasets"` |
| `GET /raster/{dataset}/metadata` | Extent, size, resolution, bands | `curl "http://localhost:8003/raster/rejilla/metadata"` |
| `GET /raster/{dataset}/point?lat&lon[&band]` | Band value(s) at a coordinate | `curl "http://localhost:8003/raster/rejilla/point?lat=-4.5895&lon=137.4416"` |
| `POST /raster/{dataset}/window` | Cell window by `bbox` (+`halo_cells`) or `point`+`radius_cells` | `curl -X POST "http://localhost:8003/raster/rejilla/window" -H "Content-Type: application/json" -d '{"band":"pendiente_grados","bbox":[137.40,-4.70,137.42,-4.68],"halo_cells":1}'` |
| `POST /raster/{dataset}/sample` | Values along a polyline | `curl -X POST "http://localhost:8003/raster/rejilla/sample" -H "Content-Type: application/json" -d '{"band":"rugosidad_m","path":[{"lat":-4.60,"lon":137.44},{"lat":-4.65,"lon":137.42}]}'` |
| `GET /raster/{dataset}/layer/{band}[?colormap]` | Rendered PNG (`image/png`, one pixel per cell, `X-Raster-Bounds`/`X-Raster-CRS`/`X-Raster-Value-Range` headers) | `curl -D - -o slope.png "http://localhost:8003/raster/rejilla/layer/pendiente_grados"` |

Errors: `400` invalid input / limits, `404` unknown dataset or band / no
coverage, `422` malformed JSON, `503` unreadable dataset file.

## Architecture

Clean Architecture, feature-first; dependencies point inward only:

```
presentation  →  application  →  domain
     ↓                              ↑
     └──────── infrastructure ──────┘        composition wires everything
```

- `app/core/domain` — value objects and pure math (`GridGeometry`,
  `DistanceCalculator`, `PathSampler`, `ColorRamp`, …); stdlib + numpy
  only.
- `app/core/ports` — `RasterRepository`, `RasterDatasource`,
  `ImageEncoder` ABCs.
- `app/features/*/application|presentation` — one use case + router per
  feature (health, datasets, point, window, sample, layer).
- `app/infrastructure` — datasources (`GeoTiffRasterDatasource`,
  `InMemoryRasterDatasource`, `UnavailableRasterDatasource`),
  `RegistryRasterRepository`, `PngEncoder`.
- `app/composition` — `Depends` providers built from `Settings`.

**Repository + Datasource swap:** use cases depend only on the
`RasterRepository` port; the repository receives `RasterDatasource`
instances by constructor (name → datasource map from `MS3_DATASETS`).
A new raster format = a new datasource class + a config entry; use
cases, domain and API stay untouched.

## Docker

See WP7.
