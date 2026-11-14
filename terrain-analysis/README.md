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

## Project layout

```
terrain-analysis/
├── app/
│   ├── main.py                  # create_app(): routers + exception handlers
│   ├── core/
│   │   ├── config/settings.py   # Settings (pydantic-settings, MS4_ prefix)
│   │   ├── domain/              # pure computation (no fastapi/rasterio)
│   │   ├── application/         # shared application services (TerrainPointSampler)
│   │   ├── errors/              # DomainError taxonomy + HTTP handlers
│   │   └── ports/               # TerrainRepository + RasterDatasource ABCs
│   ├── features/
│   │   ├── health/              # GET /health
│   │   ├── point_analysis/      # GET /terrain/point
│   │   ├── profile_analysis/    # POST /terrain/profile
│   │   └── area_analysis/       # POST /terrain/area
│   ├── infrastructure/
│   │   ├── datasources/         # synthetic / geotiff / unavailable datasource
│   │   └── repositories/        # DemTerrainRepository
│   └── composition/             # DI providers wired with FastAPI Depends
└── tests/                       # unit/, api/ contract tests, fixtures/, fakes/
```

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

### Example requests (synthetic DEM)

```bash
curl "http://localhost:8004/health"

curl "http://localhost:8004/terrain/point?lat=18.4&lon=77.5"

curl -X POST "http://localhost:8004/terrain/profile" \
  -H "Content-Type: application/json" \
  -d '{"path":[{"lat":18.4,"lon":77.5},{"lat":18.5,"lon":77.6}],"sample_distance_m":100}'

curl -X POST "http://localhost:8004/terrain/area" \
  -H "Content-Type: application/json" \
  -d '{"bbox":[77.5,18.4,77.6,18.5]}'
```

### Error codes

| HTTP | Condition | Raised by |
|---|---|---|
| 400 | Invalid bbox/path, limits exceeded (`max_path_points`, `max_samples`, `max_window_cells`) | `DomainValidationError` |
| 404 | No DEM coverage at the requested location (nodata / outside extent) | `NoCoverageError` |
| 422 | Malformed request shape/types (e.g. out-of-range `lat`/`lon` on `GET /terrain/point`) | Pydantic validation |
| 502 | Raster datasource failed or unbuildable | `UpstreamDatasourceError` |

Errors return `{"detail": "..."}` per FastAPI convention.
Note: out-of-range coordinates are 422 on `GET /terrain/point` (query-param
constraints) but 400 on the POST endpoints, where `GeoPoint`/`BoundingBox`
raise `DomainValidationError` by plan decision.

## Configuration

All settings read from environment variables with the `MS4_` prefix
(`app/core/config/settings.py`):

| Variable | Default | Purpose |
|---|---|---|
| `MS4_BODY` | `mars` | Celestial body label (echo only) |
| `MS4_PLANET_RADIUS_KM` | `3389.5` | Body radius for haversine distance and degrees→metres conversion |
| `MS4_DATASOURCE_KIND` | `synthetic` | Datasource: `synthetic` \| `geotiff` (`http` reserved) |
| `MS4_DEM_PATH` | *(empty)* | GeoTIFF path, required when `datasource_kind=geotiff` |
| `MS4_SLOPE_FLAT_MAX_DEG` | `5.0` | `flat`/`moderate` boundary |
| `MS4_SLOPE_MODERATE_MAX_DEG` | `15.0` | `moderate`/`steep` boundary (=`steep_min_deg`) |
| `MS4_SLOPE_STEEP_MAX_DEG` | `30.0` | `steep`/`hazardous` boundary |
| `MS4_SAMPLE_DISTANCE_M` | `100.0` | Default profile sampling interval |
| `MS4_MAX_SAMPLES` | `1000` | Profile sample cap (→ 400) |
| `MS4_MAX_PATH_POINTS` | `100` | Input polyline point cap (→ 400) |
| `MS4_MAX_WINDOW_CELLS` | `4000000` | Max core cells per area window (→ 400) |

## Datasources

Selected by `MS4_DATASOURCE_KIND` in `composition/dependencies.py`:

- **`synthetic` (default)** — `SyntheticDemDatasource.default()`: a
  deterministic in-memory 1200×1200 DEM covering **lon 77–78, lat 18–19**.
  Elevation is −2500 m plus layered sinusoidal hills and a planar tilt,
  with a **nodata hole at lon 77.90–77.95 / lat 18.90–18.95** so 404 paths
  are testable.
- **`geotiff`** — `GeoTiffRasterDatasource` reads `MS4_DEM_PATH` via
  rasterio. The DEM must be a single-band, **geographic (lon/lat degrees),
  north-up**, non-rotated raster; other projections are rejected.
  `rasterio` is required for this datasource; if it cannot be installed,
  run with `MS4_DATASOURCE_KIND=synthetic`.
- **`http`** — reserved for a future Raster Service (MS3) client;
  selecting it raises a configuration error.

If datasource construction itself fails (e.g. `geotiff` without
`MS4_DEM_PATH`), the service still boots: `get_raster_datasource` falls
back to an `UnavailableRasterDatasource` whose `ping()` is `False`
(`/health` → `degraded`) and whose reads return 502.
