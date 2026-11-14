# MS4 Terrain Analysis Service

FastAPI microservice that converts Digital Elevation Model (DEM) data into
navigation-relevant products for the Planetary Explorer system (MVP: Mars):
elevation, slope in degrees (Horn's method), and terrain classification
(`flat` | `moderate` | `steep` | `hazardous`).

Contract of record: `docs/SPEC_MS4_TERRAIN_ANALYSIS.md`.
Implementation plan: `docs/terrain_analysis/IMPLEMENTATION_PLANMS4_1.md`.

## Architecture

Clean Architecture with a feature-first layout; dependencies point inward only:

```
presentation  →  application  →  domain
     ↓                                  ↑
     └────────── infrastructure ────────┘
```

- `app/core/domain` — pure computation (no fastapi / rasterio / DTOs).
- `app/core/ports` — abstract interfaces (`TerrainRepository`, `RasterDatasource`).
- `app/features/<feature>` — `domain` / `application` / `presentation` per feature.
- `app/infrastructure` — datasource and repository implementations.
- `app/composition` — DI wiring; selects the datasource via `Settings.datasource_kind`.

## Setup (Windows, Git Bash)

```bash
cd terrain-analysis
py -3.12 -m venv .venv
source .venv/Scripts/activate
pip install -e ".[dev]"
```

Python 3.12 is required for rasterio wheel availability on Windows.

## Run

```bash
uvicorn app.main:app --port 8004
```

## Test

```bash
pytest -v
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + datasource connectivity |
| GET | `/terrain/point?lat=&lon=&body=` | Elevation, slope, terrain class at a coordinate |
| POST | `/terrain/profile` | Sampled elevation/slope profile along a polyline |
| POST | `/terrain/area` | Aggregate elevation/slope stats over a bounding box |

## Configuration

Environment variables use the `MS4_` prefix (see `app/core/config/settings.py`).
`MS4_DATASOURCE_KIND` selects the raster datasource: `synthetic` (default,
deterministic in-memory DEM), `geotiff` (reads `MS4_DEM_PATH` via rasterio),
`http` (reserved for a future Raster Service / MS3 client).

**Note:** the `rasterio` package is required for the `geotiff` datasource.
If rasterio cannot be installed, run with `MS4_DATASOURCE_KIND=synthetic`.
