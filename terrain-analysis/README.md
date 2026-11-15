# MS4 Terrain Analysis Service

FastAPI microservice that converts Digital Elevation Model (DEM) data into
navigation-relevant products for the Planetary Explorer system (MVP: Mars):
elevation, slope in degrees (Horn's method — or read verbatim from the
delivered grid in `rejilla` mode), and terrain classification
(`flat` | `moderate` | `steep` | `hazardous`).

Contract of record: `docs/SPEC_MS4_TERRAIN_ANALYSIS.md`.
Implementation plan: `docs/terrain_analysis/IMPLEMENTATION_PLANMS4_1.md`
(realigned to the delivered data by
`docs/terrain_analysis/REALIGNMENT_PLANMS4_1.md`).

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
│   │   ├── datasources/         # synthetic / geotiff (DEM or rejilla band) / unavailable
│   │   └── repositories/        # DemTerrainRepository / SlopeGridTerrainRepository
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

## Docker

The image defaults to grid mode (`MS4_DATASOURCE_KIND=rejilla`) and expects the
repo's `data/` directory mounted at `/data` (data is never baked into the image).

```bash
cd terrain-analysis
docker build -t ms4-terrain-analysis .
docker run --rm -p 8004:8004 -v "$(pwd)/../data:/data:ro" ms4-terrain-analysis
curl "http://localhost:8004/health"
```

Override any `MS4_*` variable with `-e`, e.g. `-e MS4_DATASOURCE_KIND=synthetic`.

## Test

```bash
pytest -v
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + datasource connectivity + configured `datasource_kind` |
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
| 400 | Invalid coordinates, bbox or path (out-of-range lat/lon, inverted bbox, < 2 path points), limits exceeded (`max_path_points`, `max_samples`, `max_window_cells`) | `DomainValidationError` |
| 404 | No DEM coverage at the requested location (nodata / outside extent) | `NoCoverageError` |
| 422 | Malformed request shape/types (missing params, non-numeric values, wrong bbox length) | Pydantic validation |
| 502 | Raster datasource failed or unbuildable | `UpstreamDatasourceError` |

Errors return `{"detail": "..."}` per FastAPI convention. All endpoints
return 400 for invalid coordinates (spec §4.4): `GeoPoint`/`BoundingBox`
raise `DomainValidationError` — query params and request schemas carry no
range constraints.

## Configuration

All settings read from environment variables with the `MS4_` prefix
(`app/core/config/settings.py`):

| Variable | Default | Purpose |
|---|---|---|
| `MS4_BODY` | `mars` | Celestial body label (echo only) |
| `MS4_PLANET_RADIUS_KM` | `3396.19` | Body radius for haversine distance and degrees→metres conversion (IAU_2015:49900 Mars sphere) |
| `MS4_DATASOURCE_KIND` | `synthetic` | Datasource: `synthetic` \| `geotiff` \| `rejilla` (`http` reserved) |
| `MS4_DEM_PATH` | *(empty)* | GeoTIFF path, required when `datasource_kind=geotiff` |
| `MS4_REJILLA_PATH` | `<repo root>/data/gale/processed/rejilla_ruta_90m.tif` | Slope grid GeoTIFF for `datasource_kind=rejilla`; default is absolute (anchored to repo root in `settings.py`) |
| `MS4_REJILLA_SLOPE_BAND` | `1` | 1-based raster band carrying slope in degrees (`pendiente_grados`) |
| `MS4_RASTER_SERVICE_URL` | `http://localhost:8003` | MS3 Raster Service base URL, used when `datasource_kind=http` |
| `MS4_RASTER_DATASET` | `rejilla` | MS3 dataset name for `http` mode |
| `MS4_RASTER_BAND` | `pendiente_grados` | MS3 band name read by `http` mode |
| `MS4_RASTER_TIMEOUT_S` | `5.0` | HTTP timeout (seconds) for MS3 calls |
| `MS4_RASTER_VALUES` | `slope` | `http` mode semantics: `slope` (grid mode, verbatim slope) \| `elevation` (DEM mode) |
| `MS4_SLOPE_FLAT_MAX_DEG` | `5.0` | `flat`/`moderate` boundary |
| `MS4_SLOPE_MODERATE_MAX_DEG` | `15.0` | `moderate`/`steep` boundary (=`steep_min_deg`) |
| `MS4_SLOPE_STEEP_MAX_DEG` | `30.0` | `steep`/`hazardous` boundary |
| `MS4_SAMPLE_DISTANCE_M` | `100.0` | Default profile sampling interval |
| `MS4_MAX_SAMPLES` | `1000` | Profile sample cap (→ 400) |
| `MS4_MAX_PATH_POINTS` | `100` | Input polyline point cap (→ 400) |
| `MS4_MAX_WINDOW_CELLS` | `4000000` | Max core cells per area window (→ 400) |

## Datasources

Selected by `MS4_DATASOURCE_KIND` in `composition/dependencies.py`:

| Kind | Source | Mode / notes |
|---|---|---|
| `synthetic` (default) | `SyntheticDemDatasource.default()` | DEM mode. Deterministic in-memory 1200×1200 DEM covering **lon 77–78, lat 18–19**; elevation is −2500 m plus layered sinusoidal hills and a planar tilt, with a **nodata hole at lon 77.90–77.95 / lat 18.90–18.95** so 404 paths are testable |
| `geotiff` | `GeoTiffRasterDatasource` on `MS4_DEM_PATH` | DEM mode. The raster must be single-band, **geographic (lon/lat degrees), north-up**, non-rotated; other projections are rejected. Requires `rasterio`; if it cannot be installed, run with `MS4_DATASOURCE_KIND=synthetic` |
| `rejilla` | `GeoTiffRasterDatasource(band=MS4_REJILLA_SLOPE_BAND)` on `MS4_REJILLA_PATH` + `SlopeGridTerrainRepository` | **Grid mode.** Slope is read verbatim from the `pendiente_grados` band — never recomputed (no Horn's). `elevation_m` is reported as `null` (keys stay present); profile `elevation_gain_m`/`elevation_loss_m` and area `elevation_m` are likewise `null` |
| `http` | `HttpRasterDatasource` against `MS4_RASTER_SERVICE_URL` (`POST /raster/{MS4_RASTER_DATASET}/window`, `GET /health`) | Raster Service (MS3) client mode. Cell reads are served by MS3 with bit-for-bit parity to a local `GeoTiffRasterDatasource` read (proven by `tests/integration/test_ms3_parity.py`). `MS4_RASTER_VALUES=slope` wires `SlopeGridTerrainRepository` (grid mode); `elevation` wires `DemTerrainRepository`. Note: MS3 enforces its own window cap (1 000 000 cells, `MS3_MAX_WINDOW_CELLS`) which is stricter than `MS4_MAX_WINDOW_CELLS` (4 000 000); oversized windows surface as 400 either way |

### Run against the delivered Gale data

The data team delivered `rejilla_ruta_90m.tif` — a 6-band routing cost
grid of the Gale crater corridor (`docs/data/HANDOFF_SOFTWARE.md`,
packaged under `data/gale/processed/`; data is local, never committed).
Band 1, `pendiente_grados`, carries slope in degrees; there is no
elevation band. Bounds `[137.345, -4.739427, 137.454322, -4.58]`,
72×105 cells.

```bash
cd terrain-analysis
MS4_DATASOURCE_KIND=rejilla uvicorn app.main:app --port 8004

curl "http://localhost:8004/terrain/point?lat=-4.5895&lon=137.4416"  # Bradbury Landing
```

### Run via the MS3 Raster Service

The same rejilla data can be served remotely by MS3 (port 8003) instead
of read from the local file — identical responses, no rasterio reads in
MS4:

```bash
MS4_DATASOURCE_KIND=http \
MS4_RASTER_SERVICE_URL=http://localhost:8003 \
  uvicorn app.main:app --port 8004
```

`GET /health` echoes `"datasource_kind": "rejilla"` (or `"http"`) so
operators can tell grid mode from DEM mode.

If datasource construction itself fails (e.g. `geotiff` without
`MS4_DEM_PATH`), the service still boots: `get_raster_datasource` falls
back to an `UnavailableRasterDatasource` whose `ping()` is `False`
(`/health` → `degraded`) and whose reads return 502. The fallback is
cached (`lru_cache`) for the process lifetime, so `/health` remains
`degraded` until the service is restarted with corrected configuration.
