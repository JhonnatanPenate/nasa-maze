# MS3 Raster Service — Implementation Plan

**Version:** 1.0.0 | **Status:** Approved for execution | **Date:** 2026-11-15
**Audience:** Manager (orchestrator) agent coordinating implementation subagents.
**Contract of record:** [`docs/SPEC_MS3_RASTER.md`](../SPEC_MS3_RASTER.md) **v0.1.1** (amendments A1–A6 of §4 already applied)
**System context:** [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) v2.1
**Integration partner:** MS4 Terrain Analysis — [`docs/SPEC_MS4_TERRAIN_ANALYSIS.md`](../SPEC_MS4_TERRAIN_ANALYSIS.md) v0.2.1, code in `terrain-analysis/`
**Reference plan (style + mechanics):** [`docs/terrain_analysis/IMPLEMENTATION_PLANMS4_1.md`](../terrain_analysis/IMPLEMENTATION_PLANMS4_1.md)

---

## 1. Context and Role of MS3

Planetary Explorer is a microservices monorepo that computes safe routes over Mars (MVP: Gale crater). MS3 — **Raster Service** — is the single HTTP access point to raster files. It owns all raster I/O (open file, coordinate→cell math, clipping, halos, nodata) and returns plain JSON / PNG so consumers never import rasterio.

**Consumers:** MS4 Terrain Analysis (first, via a new `HttpRasterDatasource`), MS5 Risk Assessment, MS6 Routing Engine, Core (PNG layers for the map).

**Constraints from the docs:**
- MS3 calls no other service. Its only dependency is local files under `data/gale/`.
- Band values are served **verbatim** — never resampled, interpolated, or recomputed (spec §5).
- CRS `IAU_2015:49900`, Mars radius **3396.19 km**; dataset paths come from env vars, never hardcoded (ARCHITECTURE §3 "Regla de oro").
- MS4's **REST contract must not change**. MS3 and MS4 share an owner, so WP8 may edit `terrain-analysis/` internals (datasource, config, composition, docs) directly.

### 1.1 Ground truth: the delivered raster (verified with rasterio on 2026-11-15)

| Property | Value | Note |
|---|---|---|
| File | `data/gale/processed/rejilla_ruta_90m.tif` | |
| Size | **width 72 cols × height 105 rows**, 6 bands, `float32` | Spec §4.2 example has width/height swapped → fixed in v0.1.1 |
| Bounds (file) | left 137.345, bottom −4.739427215909189, right 137.45432151948057, top −4.58 | Slightly smaller than the nominal AOI; report the **file** bounds |
| Resolution | 0.0015183544372303697° on both axes (≈ 90.0 m in latitude) | Geographic CRS: metric X size depends on cos(lat) |
| CRS | anonymous geographic WKT, sphere R = 3 396 190 m | No authority code → service reports the configured label `IAU_2015:49900` |
| Nodata | **NaN** on all bands | Band 3 `fraccion_oscura` has exactly **1 NaN cell** (real-data test) |
| Band names | stored in the file's band **descriptions**: `pendiente_grados`, `rugosidad_m`, `fraccion_oscura`, `inercia_termica_tiu`, `albedo`, `distancia_duna_m` | Read names from the file; config fallback only |
| Units | **not stored** in the file | Come from config |
| Ranges | b1 0–35.5, b2 0.08–5.08, b3 0–1, b4 408.3–445.6, b5 0.2276–0.2320, b6 0–5400.75 | Default PNG ranges / sanity tests |

## 2. Scope

### 2.1 MVP goals (in scope)

| # | Goal |
|---|------|
| G1 | `GET /health` — liveness + per-dataset readability (also MS4's `ping()`) |
| G2 | `GET /raster/datasets` + `GET /raster/{dataset}/metadata` |
| G3 | `GET /raster/{dataset}/point` — band value(s) at a coordinate |
| G4 | `POST /raster/{dataset}/window` — bbox / bbox+halo / point+radius cell windows, **bit-for-bit parity with MS4's `GridBackedRasterDatasource`** |
| G5 | `POST /raster/{dataset}/sample` — values along a polyline |
| G6 | `GET /raster/{dataset}/layer/{band}` — rendered PNG with georeferencing headers |
| G7 | Repository + Datasource pattern: use cases depend on `RasterRepository`; the repository explicitly depends on the `RasterDatasource` port; datasources are swappable (`geotiff`, `memory`) |
| G8 | Clean Architecture + feature-first; one class per file; README in every main folder; English only |
| G9 | TDD: ≥ 3 tests per feature (happy / sad / edge) + API contract tests |
| G10 | Docker image for MS3 (port 8003, data mounted read-only) |
| G11 | MS4 integration: `HttpRasterDatasource` in `terrain-analysis/` + parity test + two-container smoke (no Compose) |

### 2.2 Non-goals

- Docker Compose (explicitly deferred), XYZ/WMTS tiles, COG overviews, PNG of a sub-bbox.
- Writes / uploads / catalog versioning (MS2), serving `.xlsx`/GeoJSON (consumers read those directly).
- Auth, rate limiting, multi-body, reprojection.
- A shared Python package between services: each service owns its own copy of the grid math, so neither depends on the other (§4 D3).

## 3. Architecture

### 3.1 Layers (dependencies point inward only)

```
presentation  →  application  →  domain
     ↓                              ↑
     └──────── infrastructure ──────┘        composition wires everything
```

| Layer | Contains | May import | Must NOT import |
|---|---|---|---|
| `core/domain` | Value objects + pure math (`GeoPoint`, `BoundingBox`, `GridGeometry`, `CellWindow`, `DatasetMetadata`, `BandInfo`, `DistanceCalculator`, `PathSampler`, `ColorRamp`) | stdlib, numpy | fastapi, pydantic, rasterio, httpx |
| `core/ports` | ABCs: `RasterRepository`, `RasterDatasource`, `ImageEncoder` (+ `RawRasterMetadata` dataclass) | domain | any implementation |
| `core/errors` | Exception taxonomy; `error_handlers.py` is the only fastapi import in `core/` | stdlib, fastapi (handlers only) | rasterio |
| `features/*/application` | Use cases | domain, ports | fastapi, rasterio, concrete infra |
| `features/*/presentation` | Routers, Pydantic schemas, domain→DTO mappers | application, domain | rasterio, datasource internals |
| `infrastructure` | Datasources (rasterio, in-memory), repository impl, PNG encoder | ports, domain, rasterio, numpy, stdlib | fastapi |
| `composition` | DI providers (`Depends`) built from `Settings` | everything | — |

### 3.2 Repository + Datasource pattern (hard requirement)

```
ListDatasets / GetMetadata / QueryPoint / ReadWindow / SamplePath / RenderLayer   (use cases)
        │ depend on
        ▼
RasterRepository (port)                 ◄── domain-facing: dataset names, metadata, NaN-normalised cells
        ▲ implemented by
RegistryRasterRepository                ◄── infrastructure: name → datasource map, nodata → NaN, error wrapping
        │ constructor-injected: Mapping[str, RasterDatasource]
        ▼
RasterDatasource (port)                 ◄── data-access: one instance per dataset file
        ▲ implemented by
        ├── GeoTiffRasterDatasource     (rasterio; opens per call; no handles held)
        ├── InMemoryRasterDatasource    (numpy arrays; dev/tests; deterministic)
        └── UnavailableRasterDatasource (build-failure placeholder → 503 + health "degraded")
```

Port signatures (WP1 freezes them):

```python
class RasterDatasource(ABC):
    def read_metadata(self) -> RawRasterMetadata: ...  # extent, rows, cols, band descriptions, nodata, geographic?, north-up?
    def read_cells(self, band_index: int, rows: slice, cols: slice) -> np.ndarray: ...  # raw values; in-grid slices only
    def ping(self) -> bool: ...

class RasterRepository(ABC):
    def dataset_names(self) -> list[str]: ...
    def metadata(self, dataset: str) -> DatasetMetadata: ...  # UnknownDatasetError / DatasetUnavailableError
    def read_cells(self, dataset: str, band: str, rows: slice, cols: slice) -> np.ndarray: ...  # float64, nodata → NaN
    def is_readable(self, dataset: str) -> bool: ...
```

- **Swap rule:** a new format (DEM arrives, a COG, …) = new datasource + config entry. Use cases, domain and API stay untouched.
- **Adapter rule:** raw rasterio types never leave `infrastructure/`. `RawRasterMetadata` → `DatasetMetadata` (domain) happens inside the repository, merging config (units, CRS label, colormaps).
- **Index math lives in the domain** (`GridGeometry`), used by use cases; datasources only do I/O on already-clipped slices.

### 3.3 Error taxonomy → HTTP

| Exception | HTTP | When |
|---|---|---|
| `RasterValidationError` | 400 | coord out of range, inverted bbox, `bbox`+`point` both/neither, missing `radius_cells`, path < 2 pts, limits exceeded, unknown colormap |
| `UnknownDatasetError` / `UnknownBandError` (subclasses of `NotFoundError`) | 404 | name not registered / band not in dataset (`detail` lists valid names) |
| `NoCoverageError` (subclass of `NotFoundError`) | 404 | bbox doesn't intersect extent; `/point` outside extent; `/sample` path fully outside extent |
| `DatasetUnavailableError` | 503 | file missing/corrupt, not geographic, rotated, or not north-up |
| Pydantic `RequestValidationError` | 422 | wrong JSON shape/types (FastAPI default) |

Base class `RasterServiceError`. Handlers registered once in `app/main.py` via `core/errors/error_handlers.py`; body `{"detail": "..."}`.

### 3.4 Directory tree (service root: `raster-service/`)

```
raster-service/
├── README.md                     # overview, setup, run, env vars, endpoints, Docker
├── AGENTS.md                     # service-local agent rules + commands (WP9)
├── CLAUDE.md                     # "@AGENTS.md"
├── pyproject.toml
├── Dockerfile
├── .dockerignore
├── app/
│   ├── README.md
│   ├── main.py                   # create_app(): routers + exception handlers
│   ├── core/
│   │   ├── README.md
│   │   ├── config/      README.md, settings.py, dataset_config.py
│   │   ├── domain/      README.md, geo_point.py, bounding_box.py, grid_geometry.py, cell_window.py,
│   │   │                band_info.py, dataset_metadata.py, distance_calculator.py, path_sampler.py,
│   │   │                path_sample.py, color_ramp.py
│   │   ├── errors/      README.md, exceptions.py, error_handlers.py
│   │   └── ports/       README.md, raster_repository.py, raster_datasource.py, image_encoder.py,
│   │                    raw_raster_metadata.py
│   ├── features/
│   │   ├── README.md
│   │   ├── health/          README.md, presentation/{health_router,health_schemas}.py
│   │   ├── datasets/        README.md, application/{list_datasets,get_metadata}.py,
│   │   │                    presentation/{datasets_router,datasets_schemas,datasets_mapper}.py
│   │   ├── point_query/     README.md, application/query_point.py, domain/point_values.py,
│   │   │                    presentation/{point_router,point_schemas,point_mapper}.py
│   │   ├── window_read/     README.md, application/read_window.py, domain/window_request.py,
│   │   │                    presentation/{window_router,window_schemas,window_mapper}.py
│   │   ├── path_sampling/   README.md, application/sample_path.py, domain/path_profile.py,
│   │   │                    presentation/{sample_router,sample_schemas,sample_mapper}.py
│   │   └── layer_render/    README.md, application/render_layer.py, domain/rendered_layer.py,
│   │                        presentation/layer_router.py
│   ├── infrastructure/
│   │   ├── README.md
│   │   ├── datasources/     README.md, geotiff_raster_datasource.py, in_memory_raster_datasource.py,
│   │   │                    unavailable_raster_datasource.py
│   │   ├── repositories/    README.md, registry_raster_repository.py, guarded_call.py
│   │   └── rendering/       README.md, png_encoder.py          # stdlib zlib + struct, no Pillow
│   └── composition/
│       ├── README.md
│       └── dependencies.py
└── tests/
    ├── README.md
    ├── conftest.py               # Settings, in-memory datasource, TestClient with dependency_overrides
    ├── fakes/        README.md, failing_raster_datasource.py
    ├── fixtures/     README.md, make_test_raster.py   # generates a small multi-band GeoTIFF at test time
    ├── unit/         README.md   # domain, use cases, repository, datasources, encoder
    ├── api/          README.md   # one contract file per endpoint
    └── integration/  README.md, test_rejilla_real.py  # skipped when the delivered file is absent
```

Rules: one class per file (file = snake_case of the class); empty `__init__.py`; each README states purpose, contents, key classes and the layer rules that apply. Binary fixtures are generated at test time, never committed.

## 4. Decisions and spec amendments (v0.1.1)

A1–A6 are **already applied** to `docs/SPEC_MS3_RASTER.md` (v0.1.1, changelog in its header); they are kept here as the rationale. The spec wins on any later conflict.

| # | Topic | Amendment |
|---|---|---|
| A1 | Metadata | `width: 72, height: 105`; add `resolution_deg: {"lon", "lat"}`; `resolution_m` = latitude cell size (`res_lat_deg · π/180 · R`). `nodata: null` when the file sentinel is NaN. |
| A2 | Window geometry | Replace `cell_size_m` with `resolution_deg: {lon, lat}` and add `center_lat` — exactly the inputs of MS4's `DemWindowMapper.to_dem_window(raw, nodata, res_lon_deg, res_lat_deg, center_lat_deg)`. `center_lat` = mean latitude of the **core** rows (bbox forms, mirrors `GridGeometry.rows_mean_lat`) or the containing cell's row-centre latitude (point form; the request `lat` when outside the extent). |
| A3 | Point+radius outside extent | The window `point` form never 404s: out-of-extent cells are `null` padding (mirrors MS4's port docstring "Cells outside the DEM extent are NaN"). The `/point` endpoint outside extent → 404. |
| A4 | Unknown band | Always **404** (spec §5 said "400/404"), `detail` lists valid band names. |
| A5 | `/sample` coverage | Samples on nodata or outside extent → `value: null`; 404 only if **every** sample lies outside the extent. Same arc-length sampling as MS4 `PathSampler` (positions 0, step, 2·step, … + final vertex; haversine, R = 3396.19 km). Caps `max_path_points` 100 / `max_samples` 1000 → 400. |
| A6 | PNG layer | stdlib encoder (`zlib` + `struct`), RGBA 8-bit, one pixel per cell (72×105), row 0 = north, nodata → alpha 0. Colour range from config `value_ranges[band]`, else finite min/max. Extra header `X-Raster-Value-Range: min,max` for legends. Colormaps: `slope` (green→yellow→red), `viridis` (5-stop approx.), `grayscale`. Unknown colormap → 400. |

| # | Engineering decision | Choice | Rationale |
|---|---|---|---|
| D1 | Port | **8003** (MS4 is 8004) | Service N → port 800N |
| D2 | Coordinate→cell semantics | Reproduce MS4 `GridGeometry` exactly: bbox selects cells whose **centres** fall inside (ε = 1e-9 index units), clipped to the grid; empty selection falls back to the single cell containing the intersection centre; `cell_at` floors and clamps max edges; halo clipped at grid edges; cap evaluated on **core** cells; resolution = extent / size | Required for G4 parity; MS4 tests already pin this behaviour |
| D3 | Independence from MS4 code | MS3 **does not import** anything from `terrain-analysis/` and there is no shared package. MS3 writes its own `GridGeometry`, `PathSampler`, `DistanceCalculator` (test-first, reusing MS4 test cases as the behaviour spec). The two services only agree on the **HTTP contract**; the parity test (WP8) proves they compute the same thing | A shared package would couple both services (same release, same deps); a few small classes written twice is the price of independent deploys |
| D4 | Float fidelity | Serialise `float(np.float32_value)` (float64 repr); **never round** | Python's shortest-repr JSON round-trips exactly → MS4 receives identical values to a local read |
| D5 | NaN on the wire | Convert NaN → `None` in presentation mappers (JSON cannot carry NaN) | Spec §5 "null is the only nodata representation" |
| D6 | Dataset registry | `Settings.datasets: dict[str, DatasetConfig]`; default `{"rejilla": DatasetConfig(path=Settings.rejilla_path, …)}`; full override via `MS3_DATASETS` (JSON), path-only via `MS3_REJILLA_PATH` | Simplest env-driven registry; adding the DEM later = one config entry |
| D7 | Band names | From file band descriptions; `DatasetConfig.band_names` used when descriptions are empty | The delivered file already carries canonical names |
| D8 | Metadata caching | Repository caches `DatasetMetadata` per dataset after the first successful read; cells are read per request | File is 7 560 cells; no handles held (spec §6) |
| D9 | Datasource selection | `DatasetConfig.kind: Literal["geotiff", "memory"]` (`memory` = deterministic synthetic grid for dev/demo without data) | Explicit swap point required by G7 |
| D10 | PNG encoder | Behind the `ImageEncoder` port; `PngEncoder` in `infrastructure/rendering/` | Keeps the use case pure; zero new dependency |
| D11 | Window cap | `max_window_cells` default **1 000 000** on MS3 | JSON size guard; whole rejilla = 7 560 cells; MS4 keeps its own cap |
| D12 | MS4 HTTP client | `httpx` sync `Client`, moved from MS4 `[dev]` to runtime deps; tests use `httpx.MockTransport` | Already in MS4's toolchain; no new dependency |
| D13 | Coordinate range errors | 400 (domain), not 422 | Same decision as MS4; spec §4.7 says 400 |

## 5. Feature Specifications (what each WP must implement)

All payloads follow `SPEC_MS3_RASTER.md` v0.1.1. Default dataset in examples: `rejilla`.

### F1 — Health (`GET /health`)
- Always `200`: `{"status": "ok"|"degraded", "dataset_count": 1, "datasets": [{"name": "rejilla", "readable": true}]}`; `degraded` when any dataset is unreadable.

### F2 — Datasets (`GET /raster/datasets`, `GET /raster/{dataset}/metadata`)
- List: `{"datasets": [{"name", "path", "readable"}]}` (path as configured).
- Metadata: `{name, crs, bounds, width, height, resolution_deg{lon,lat}, resolution_m, bands[{index, name, unit, nodata}]}`.
- Errors: unknown dataset 404; unreadable 503.

### F3 — Point query (`GET /raster/{dataset}/point?lat&lon[&band]`)
- Flow: `QueryPoint` → `GridGeometry.cell_at` → `repository.read_cells` 1×1 per band (or the single band) → `PointValues`.
- `200`: `{lat, lon, values: {band: float|null}}`.
- Errors: out-of-range coords 400; outside extent 404; unknown band 404; unreadable 503.

### F4 — Window read (`POST /raster/{dataset}/window`)
- Forms: `{band, bbox, halo_cells?}` | `{band, point, radius_cells}`; exactly one of `bbox`/`point` (else 400); `halo_cells` ignored with `point`; `radius_cells`/`halo_cells` ints ≥ 0.
- `200`: `{band, bounds, rows, cols, resolution_deg{lon,lat}, center_lat, core{row_off,col_off,rows,cols}, cells[[...]]}`; row 0 northernmost; `bounds` = outer edges of the returned cells (point form may extend beyond the extent).
- Errors: bbox not intersecting 404; core cells > cap or `(2r+1)² > cap` 400; unknown band 404; unreadable 503.
- **Parity cases ported from MS4** (`terrain-analysis/tests/**` around `GridGeometry`/`GridBackedRasterDatasource`): centre-inclusion selection, single-cell fallback for a sub-cell bbox, halo clipped asymmetrically at the edge with correct `core`, point at max edge clamped, point outside extent → all-null `(2r+1)²`.

### F5 — Path sampling (`POST /raster/{dataset}/sample`)
- Body `{band, path[{lat,lon}] (2..max_path_points), sample_distance_m?}`; default step = dataset `resolution_m`.
- `200`: `{band, sample_count, total_distance_m, samples[{lat, lon, distance_m, value}]}` per A5.

### F6 — Layer render (`GET /raster/{dataset}/layer/{band}?colormap=`)
- `200 image/png` + headers `X-Raster-Bounds`, `X-Raster-CRS`, `X-Raster-Value-Range`.
- All-NaN band → fully transparent PNG (200). Constant band → mid-ramp colour (no division by zero).

### F7 — MS4 `HttpRasterDatasource` (in `terrain-analysis/`)
- New `app/infrastructure/datasources/http_raster_datasource.py` implementing MS4's existing `RasterDatasource` port **unchanged**:
  - `read_window(bbox)` → `POST /raster/{ds}/window {band, bbox}`.
  - `read_window_with_halo(bbox, h)` → same + `halo_cells`; builds `HaloWindow` from `core`.
  - `read_window_around(point, r)` → `{band, point, radius_cells}`.
  - `ping()` → `GET /health`; True iff `status == "ok"` and the configured dataset is readable.
  - Payload → domain via the existing `DemWindowMapper.to_dem_window(cells(None→NaN), None, res.lon, res.lat, center_lat)`.
  - HTTP mapping: 400 → `DomainValidationError`, 404 → `NoCoverageError`, 5xx / timeout / connection error → `UpstreamDatasourceError` (→ MS4 502).
- MS4 `Settings` additions (prefix `MS4_`): `raster_service_url="http://localhost:8003"`, `raster_dataset="rejilla"`, `raster_band="pendiente_grados"`, `raster_timeout_s=5.0`, `raster_values: Literal["slope","elevation"]="slope"`.
- `composition/dependencies.py`: `datasource_kind == "http"` builds `HttpRasterDatasource`; repository = `SlopeGridTerrainRepository` when `raster_values == "slope"`, else `DemTerrainRepository`. Update the "'http' is reserved" error message.
- MS4 REST contract, domain and use cases untouched; MS4 `README.md`/`AGENTS.md` document the `http` mode + env vars.

## 6. Configuration, Dependencies, Docker

### 6.1 MS3 `Settings` (`core/config/settings.py`, env prefix `MS3_`)

| Field | Default | Purpose |
|---|---|---|
| `planet_radius_km` | `3396.19` | distances + `resolution_m` |
| `crs_label` | `"IAU_2015:49900"` | reported CRS (file WKT is anonymous) |
| `rejilla_path` | `<repo>/data/gale/processed/rejilla_ruta_90m.tif` (anchored via `Path(__file__).resolve().parents[4]`, like MS4) | default dataset path |
| `datasets` | `{"rejilla": DatasetConfig(...)}` | registry (JSON override `MS3_DATASETS`) |
| `max_window_cells` | `1_000_000` | window cap → 400 |
| `max_path_points` / `max_samples` | `100` / `1000` | sampling caps → 400 |

`DatasetConfig`: `path`, `kind` (`geotiff` \| `memory`), `band_names: list[str] = []`, `band_units: dict[str, str]` (rejilla default: `deg, m, fraction, tiu, fraction, m`), `colormaps: dict[str, str]` (default `pendiente_grados→slope`, `albedo→grayscale`, others `viridis`), `value_ranges: dict[str, tuple[float, float]]` (default `pendiente_grados: (0, 35)`).

### 6.2 Dependencies (`pyproject.toml`, Python ≥ 3.12)

- Runtime: `fastapi>=0.115,<1`, `uvicorn[standard]>=0.30,<1`, `pydantic>=2,<3`, `pydantic-settings>=2,<3`, `numpy>=1.26,<3`, `rasterio>=1.3,<2` (same pins as MS4).
- Dev: `pytest>=8,<9`, `httpx>=0.27,<1`. No Pillow / matplotlib (A6, D10).
- Venv: `py -3.12 -m venv .venv` (rasterio wheels on Windows — same decision as MS4).

### 6.3 Docker image (WP7)

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MS3_REJILLA_PATH=/data/gale/processed/rejilla_ruta_90m.tif

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
# libexpat1: required by the GDAL bundled in the rasterio wheel, missing from slim
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir . \
    && useradd --create-home ms3

USER ms3
EXPOSE 8003
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import json,sys,urllib.request; sys.exit(0 if json.load(urllib.request.urlopen('http://localhost:8003/health'))['status']=='ok' else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
```

- Data is **mounted read-only**, never copied: `-v "<repo>/data:/data:ro"`.
- `.dockerignore`: `.venv`, `tests`, `**/__pycache__`, `.pytest_cache`, `*.tif`.
- Build context: `raster-service/`. No Compose file in this plan.

## 7. Test Matrix (TDD — ≥ 3 per feature: happy / sad / edge)

| Target | Happy path | Sad path | Edge case |
|---|---|---|---|
| `GridGeometry` | bbox → expected slices; `cell_at` interior | non-intersecting bbox → `NoCoverageError`; cap exceeded → `RasterValidationError` | sub-cell bbox fallback; point on max edge clamped; cell centre exactly on bbox edge (ε) |
| `DistanceCalculator` / `PathSampler` | known distance (59 274.69 m per degree of latitude); straight path → N samples | < 2 points / step ≤ 0 / > `max_samples` → 400 | exact multiple of step (no duplicate tail); identical points |
| `ColorRamp` | value → expected RGBA at stops | unknown name → 400 | NaN → alpha 0; constant range → no div-by-zero |
| `RegistryRasterRepository` | metadata + cells from in-memory datasource; numeric sentinel → NaN | unknown dataset → 404; unknown band → 404; datasource raises → `DatasetUnavailableError` | NaN sentinel passes through; band names fall back to config |
| Datasource swap | the same repository suite passes with `InMemoryRasterDatasource` AND `GeoTiffRasterDatasource` (generated fixture) | non-geographic / rotated fixture → 503 | float32 value served verbatim (exact equality) |
| `PngEncoder` | valid signature + IHDR width/height + IDAT inflates to expected bytes | non-2D / wrong dtype array → error | all-transparent image |
| F1 health | all readable → `ok` | missing file → `degraded` (still 200) | zero datasets configured → `ok`, `dataset_count: 0` |
| F2 datasets / metadata | schema exact; band names + units | unknown dataset 404 | unreadable dataset listed `readable: false`; its metadata → 503 |
| F3 point | known cell → raw value | outside extent 404; `lat=95` → 400; unknown band 404 | nodata cell → `null`; `band` filter → single key |
| F4 window | bbox → array equals fixture slice; `center_lat`/`resolution_deg` correct | both/neither `bbox`/`point` 400; cap 400; non-intersecting 404 | halo clipped at edge + `core`; point form outside extent → all nulls; sub-cell bbox → 1×1 |
| F5 sample | 2-point path → count/distance/values | 1-point path 400; fully outside 404 | partially outside → nulls; default step = `resolution_m` |
| F6 layer | 200 `image/png` + 3 headers | unknown band 404; unknown colormap 400 | all-NaN band → transparent PNG; constant band |
| Real data (`tests/integration`) | 72 × 105, 6 canonical names, resolution per §1.1 | — | band 3 has exactly one `null`; skip when the file is absent |
| F7 `HttpRasterDatasource` (MockTransport) | window payload → `DemWindow` equal to local mapper output; halo → `HaloWindow.core()` | 404 → `NoCoverageError`; 400 → `DomainValidationError`; 503 / timeout → `UpstreamDatasourceError`; `ping` False when MS3 is down or `degraded` | nulls → NaN; point form outside extent |
| F7 parity (`terrain-analysis/tests/integration/test_ms3_parity.py`, skipped unless MS3 reachable at `MS4_RASTER_SERVICE_URL`) | ≥ 10 bboxes/points over rejilla: `HttpRasterDatasource` arrays and cell sizes == `GeoTiffRasterDatasource(band=1)` exactly (`np.array_equal(..., equal_nan=True)`) | — | edge bbox, sub-cell bbox, halo at edge, point at corner |

Layout: `tests/unit/` (domain, use cases, repository, infra), `tests/api/` (one contract file per endpoint; FastAPI `TestClient` + `app.dependency_overrides` with the in-memory datasource), `tests/integration/` (real data). Fixture `make_test_raster.py`: 3 bands, 10 rows × 8 cols, geographic CRS, one numeric-nodata cell, one NaN cell, known plane values.

## 8. Work Packages (execution plan for the manager)

Dependency graph — a WP starts only when its predecessors are **committed and green**:

```
WP0 → WP1 → WP2 → WP3 ─┬─ WP4 (window) ───────────┐
                       └─ WP5a (sample) → WP5b ───┴→ WP6 (wiring) → WP7 (Docker) → WP8 (MS4 integration) → WP9 (review & docs)
```

| WP | Scope | Files (new unless noted) | Acceptance | Model | Status |
|---|---|---|---|---|---|
| **WP0 Bootstrap** (manager, no subagent) | MS3 agent profiles §9.2; package skeleton | `.devin/agents/ms3-*.md`, `raster-service/{pyproject.toml,CLAUDE.md}`, `app/__init__.py`, `app/core/config/{settings,dataset_config}.py`, dir skeleton + stub READMEs, `tests/conftest.py` (minimal) | `pip install -e ".[dev]"` OK; `pytest` exit 5 (no tests) accepted; `python -c "from app.core.config.settings import Settings; print(Settings().datasets)"` | orchestrator | done |
| **WP1 Core domain** | value objects, `GridGeometry`, `CellWindow`, `DatasetMetadata`, `BandInfo`, `DistanceCalculator`, `PathSampler`, `ColorRamp`; ports; `exceptions.py` (no handlers) | `app/core/{domain,ports,errors}/**` (minus `error_handlers.py`), `tests/unit/test_*` | §7 domain rows green; `grep -rE "fastapi\|rasterio\|pydantic\|httpx" app/core/domain app/core/ports` empty | `swe` | done |
| **WP2 Infrastructure** | 3 datasources, repository, `guarded_call`, `PngEncoder`, `composition/dependencies.py`, fixture generator, fakes | `app/infrastructure/**`, `app/composition/**`, `tests/fixtures/**`, `tests/fakes/**`, repo/datasource/encoder tests | datasource-swap suite green on both datasources; error mapping verified | `swe` | done |
| **WP3 Health + Datasets + Point** | F1, F2, F3; `error_handlers.py`; minimal `app/main.py` | `core/errors/error_handlers.py`, `app/main.py`, `features/{health,datasets,point_query}/**`, their api tests | contract tests incl. 400/404/503 | `swe` | done |
| **WP4 Window** | F4 + MS4 parity cases | `features/window_read/**` + tests | all F4 rows + ported MS4 cases green | `sonnet` (trickiest math) | pending |
| **WP5a Sample** | F5 | `features/path_sampling/**` + tests | F5 rows green | `swe` | pending |
| **WP5b Layer** | F6 | `features/layer_render/**` + tests | F6 rows green; PNG inflates in test | `swe` | pending |
| **WP6 App wiring** | register all routers; real-data integration test; service README | `app/main.py` (edit), `tests/integration/**`, `raster-service/README.md` | `uvicorn app.main:app --port 8003` serves all endpoints; `pytest -v` fully green; smoke §11.1 | `swe` | pending |
| **WP7 Docker** | image per §6.3 | `Dockerfile`, `.dockerignore`, README "Docker" section | `docker build -t ms3-raster raster-service` OK; container healthy with mounted data; smoke §11.2 | `swe` | pending |
| **WP8 MS4 integration** | F7 in `terrain-analysis/` | `terrain-analysis/app/infrastructure/datasources/http_raster_datasource.py`; edits: `terrain-analysis/app/core/config/settings.py`, `terrain-analysis/app/composition/dependencies.py`, `terrain-analysis/pyproject.toml` (httpx → runtime), `terrain-analysis/{README,AGENTS}.md`, `terrain-analysis/app/infrastructure/datasources/README.md`; tests: `terrain-analysis/tests/unit/test_http_raster_datasource.py`, `terrain-analysis/tests/integration/{README.md,test_ms3_parity.py}` | MS4 full suite still green (no regression); MockTransport tests green; parity test green against a running MS3; smoke §11.3 shows identical bodies | `sonnet` (cross-service, edits existing code) | pending |
| **WP9 Review & docs** | final gate | README completions, `raster-service/AGENTS.md`, fixes from review, this plan's status + deviations | DoD §10 fully checked | reviewer (`sonnet`) + `swe` for fixes | pending |

**Execution order:** WP0 → WP1 → WP2 → WP3 strictly sequential (foreground). WP3 delivers `error_handlers.py` and the `main.py` skeleton, which WP4/WP5 tests reuse (they mount their own router on a local `FastAPI()` + `register_exception_handlers`, so they never touch `main.py`). After WP3: **WP4 and WP5a in parallel background** (disjoint directories); WP5b after WP5a. WP6 → WP7 → WP8 → WP9 sequential (foreground).

## 9. Agent Orchestration Guide

### 9.1 Roles and models (optimised for context + tokens)

| Role | Model | Why |
|---|---|---|
| **Orchestrator (root)** | `opus` (Claude Opus) | Holds this plan, sequences WPs, verifies tests itself, owns integration decisions |
| **Developer** | `swe` (lightweight) by default; `sonnet` for WP4 and WP8 | WPs are scoped with exact file lists; only the parity math and the cross-service edit warrant a stronger model |
| **Reviewer** | `sonnet` (intermediate), read-only | One WP diff at a time; deep enough for contract/architecture checks, cheaper than `opus` |
| **Exploration** | not needed by default | This plan carries contracts, data facts and MS4 semantics; spawn `subagent_explore` only for an unexpected question |

### 9.2 Setup in WP0 — MS3 subagent profiles

The existing `.devin/agents/tdd-developer.md` / `code-reviewer.md` are MS4-specific (reviewer on `opus`). Create three MS3 profiles; `model:` in the frontmatter is the only way to run a subagent on a model different from the parent's.

`.devin/agents/ms3-tdd-developer.md`:
```markdown
---
name: ms3-tdd-developer
description: Implements one MS3 Raster Service work package test-first
model: swe
---

You are a TDD implementation subagent for the MS3 Raster Service (`raster-service/`).

Rules:
1. Read ONLY the plan/spec sections named in the prompt (docs/raster_service/IMPLEMENTATION_PLANMS3_1.md,
   docs/SPEC_MS3_RASTER.md) and the files listed. Do not explore the repo beyond them.
2. Create/modify only the files listed in the prompt. Anything else → report it as a deviation.
3. Red → green: write failing tests first (>= 3 per feature: happy, sad, edge), then minimal code.
4. Architecture: presentation → application → domain; domain/ports never import fastapi, pydantic, rasterio, httpx;
   use cases depend on RasterRepository only; the repository receives RasterDatasource instances by constructor;
   one class per file; empty __init__.py; English only; comments only for non-obvious geospatial math.
5. Every new directory gets a README.md (purpose, contents, key classes, layer rules).
6. Run `pytest -q` from the service root before reporting.
7. Report in <= 15 lines: files created/changed, test counts (passed/failed), deviations, open questions.
```

`.devin/agents/ms3-tdd-developer-plus.md`: identical body, `name: ms3-tdd-developer-plus`, `model: sonnet` (used for WP4, WP8).

`.devin/agents/ms3-code-reviewer.md`:
```markdown
---
name: ms3-code-reviewer
description: Reviews one MS3 work package diff for contract, architecture and test adequacy
model: sonnet
allowed-tools: [read, grep, glob, exec]
---

You are a read-only reviewer for the MS3 Raster Service. Review ONLY the diff named in the prompt
(`git diff <base>..HEAD -- <paths>`); open other files only to resolve a specific doubt.

Check, in order:
1. Contract: payloads, headers and status codes match docs/SPEC_MS3_RASTER.md v0.1.1.
2. Architecture: layer imports (plan §3.1); repository ← RasterDatasource injection; no rasterio outside infrastructure.
3. Data rules: values verbatim (no rounding/resampling), NaN → null, R = 3396.19 km, paths only from config.
4. Parity (WP4/WP8): cell selection, halo/core, point padding, center_lat identical to MS4 GridBackedRasterDatasource.
5. Tests: >= 3 per feature (happy/sad/edge); contract tests present.
Report at most 20 findings as `file:line — blocker|major|minor — fix`. Do not edit files.
```

### 9.3 Spawn mechanics

- `run_subagent(profile="ms3-tdd-developer" | "ms3-tdd-developer-plus", ...)` per WP; `profile="ms3-code-reviewer"` per WP review.
- **Foreground:** WP1, WP2, WP3, WP6, WP7, WP8. **Background:** WP4 + WP5a fan-out (WP5b may join once WP5a lands; never > 3 concurrent).
- Fixes go back to the **same** developer via `resume=<agent_id>` (keeps its context; cheaper than a fresh spawn).

### 9.4 Prompt template (subagents are stateless — paths, not pasted content)

```
WP<n> — <title>. Service root: raster-service/ (WP8: terrain-analysis/).
Read: docs/raster_service/IMPLEMENTATION_PLANMS3_1.md §1.1, §3.1–§3.3, §4 (rows <..>), §5 F<k>, §7 rows <..>;
      docs/SPEC_MS3_RASTER.md §<..>.  (WP4/WP8 also: terrain-analysis/app/infrastructure/datasources/
      {grid_geometry,grid_backed_raster_datasource,dem_window_mapper}.py)
Files to create/modify (exhaustive): <list from §8>.
Existing modules you may import: <paths from earlier WPs>.
Done when: <acceptance column of §8>.
```

### 9.5 Standard loop per WP

```
1. Spawn developer (fg/bg) with the §9.4 prompt
2. On completion → manager runs `pytest -q` itself (never trust the report)
3. Spawn reviewer (fg) with `git diff <wp-base>..HEAD -- <wp paths>`
4. Blockers/majors → resume the same developer with the findings → back to 2
5. Green + clean review → one conventional commit, e.g. `feat(raster-service): WP4 window read with MS4 parity`;
   update §8 status. Branch: `feature/raster-service`. Do not push.
```

Token hygiene: the reviewer sees only the WP diff; the manager passes paths, never file contents; one review per WP (not per file); ≤ 3 background agents; minors are batched into WP9.

## 10. Definition of Done (WP9 gate)

- [ ] `pytest -v` green in `raster-service/`; every feature has ≥ 3 tests (happy/sad/edge) + contract tests for all 7 endpoints.
- [ ] Payloads, headers and codes match SPEC v0.1.1 (400/404/422/503 covered by tests).
- [ ] Repository suite passes with `InMemoryRasterDatasource` AND `GeoTiffRasterDatasource` (swap proof).
- [ ] `grep -rE "fastapi|rasterio|pydantic|httpx" raster-service/app/core/domain raster-service/app/core/ports raster-service/app/features/*/application` → empty.
- [ ] Every directory in §3.4 has a README; root README documents setup, env vars, endpoints, Docker.
- [ ] Real-data integration test green (72 × 105, 6 bands, 1 `null` in band 3).
- [ ] Docker image builds; container healthy with mounted `data/`; no data or secrets inside the image.
- [ ] MS4: full suite green (no regression); `HttpRasterDatasource` unit tests green; parity test green; smoke §11.3 shows identical `/terrain/point` and `/terrain/area` bodies in `rejilla` vs `http` mode.
- [ ] MS4 REST contract unchanged (only internal datasource/config/composition/docs touched).
- [ ] English only; no Compose file; no comments beyond non-obvious math.

## 11. Verification Commands (manager runs at integration)

### 11.1 Local
```bash
cd raster-service
py -3.12 -m venv .venv && source .venv/Scripts/activate
pip install -e ".[dev]"
pytest -v
uvicorn app.main:app --port 8003 &
curl "http://localhost:8003/health"
curl "http://localhost:8003/raster/datasets"
curl "http://localhost:8003/raster/rejilla/metadata"
curl "http://localhost:8003/raster/rejilla/point?lat=-4.5895&lon=137.4416"
curl -X POST "http://localhost:8003/raster/rejilla/window" -H "Content-Type: application/json" \
  -d '{"band":"pendiente_grados","bbox":[137.40,-4.70,137.42,-4.68],"halo_cells":1}'
curl -X POST "http://localhost:8003/raster/rejilla/sample" -H "Content-Type: application/json" \
  -d '{"band":"rugosidad_m","path":[{"lat":-4.60,"lon":137.44},{"lat":-4.65,"lon":137.42}]}'
curl -D - -o slope.png "http://localhost:8003/raster/rejilla/layer/pendiente_grados"
```

### 11.2 Docker (MS3 alone)
```bash
docker build -t ms3-raster raster-service
docker run --rm -d --name ms3 -p 8003:8003 -v "$(pwd)/data:/data:ro" ms3-raster
curl "http://localhost:8003/health"          # {"status":"ok",...}
docker stop ms3
```

### 11.3 MS3 + MS4 together (no Compose)
```bash
docker network create pe-net
docker build -t ms4-terrain terrain-analysis
docker run --rm -d --name ms3 --network pe-net -p 8003:8003 -v "$(pwd)/data:/data:ro" ms3-raster
docker run --rm -d --name ms4-http --network pe-net -p 8004:8004 \
  -e MS4_DATASOURCE_KIND=http -e MS4_RASTER_SERVICE_URL=http://ms3:8003 ms4-terrain
docker run --rm -d --name ms4-local -p 8014:8004 -v "$(pwd)/data:/data:ro" ms4-terrain   # rejilla mode
curl "http://localhost:8004/health"                                        # datasource ok, kind http
diff <(curl -s "http://localhost:8004/terrain/point?lat=-4.6&lon=137.44") \
     <(curl -s "http://localhost:8014/terrain/point?lat=-4.6&lon=137.44")  # no output = parity
diff <(curl -s -X POST localhost:8004/terrain/area -H 'Content-Type: application/json' -d '{"bbox":[137.40,-4.70,137.44,-4.64]}') \
     <(curl -s -X POST localhost:8014/terrain/area -H 'Content-Type: application/json' -d '{"bbox":[137.40,-4.70,137.44,-4.64]}')
(cd terrain-analysis && MS4_RASTER_SERVICE_URL=http://localhost:8003 pytest tests/integration/test_ms3_parity.py -v)
docker stop ms3 ms4-http ms4-local && docker network rm pe-net
```

## 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Parity drift between MS3 and MS4 grid math | D2 + ported MS4 cases in WP4 + live parity test in WP8 (exact equality, not tolerance) |
| Float precision loss on the wire | D4 (no rounding); parity test uses `np.array_equal` |
| NaN breaks JSON serialisation | D5 in presentation mappers; covered by nodata tests |
| Wrong width/height from the spec example | §1.1 ground truth + A1; real-data test pins 72 × 105 |
| rasterio install fails on Windows | Python 3.12 venv; `memory` datasource keeps dev unblocked; Docker as fallback runtime |
| Data path moves again (`data_usar/` → `data/gale/` precedent) | Only `MS3_REJILLA_PATH` / `MS3_DATASETS`; nothing hardcoded beyond the repo-anchored default |
| Regression in MS4 while adding the `http` datasource | WP8 touches only infra/config/composition/docs; REST contract unchanged; full MS4 suite must stay green before commit |
| Parallel WPs collide on `main.py` / handlers | WP3 owns both before the fan-out; WP4/WP5 mount routers on a local app in tests; WP6 does final registration |
| Subagent cost | `swe` default; `sonnet` only for WP4/WP8 and reviews; diff-only reviews; `resume` for fixes; ≤ 3 background agents |

---

**Deviations recorded during execution:** _(manager appends here)_

**Execution tracking:** the manager updates the §8 Status column (`pending → in_progress → done`) after each WP so this file stays the auditable source of truth.
