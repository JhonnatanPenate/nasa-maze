# MS4 Terrain Analysis Service — Implementation Plan

> **v2 notice (2026-11-14):** all WPs below are `done`. The delivered `data/gale/` package changed the terrain data source (slope pre-computed, no DEM). Follow [`REALIGNMENT_PLANMS4_1.md`](REALIGNMENT_PLANMS4_1.md) and spec **v0.2.1** for the current direction.

**Version:** 1.0.0 | **Status:** Approved for execution | **Date:** 2026-11-14
**Audience:** Manager (orchestrator) agent coordinating implementation subagents.
**Contract of record:** [`docs/SPEC_MS4_TERRAIN_ANALYSIS.md`](../SPEC_MS4_TERRAIN_ANALYSIS.md) v0.1.0
**System context:** [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md)

---

## 1. Context and Role of MS4

Planetary Explorer is a microservices monorepo that computes traversable routes over planetary surfaces (MVP: Mars). MS4 — **Terrain Analysis Service** — converts Digital Elevation Model (DEM) data into navigation-relevant products:

- Elevation at a point / along a path / over an area.
- Slope in degrees (Horn's method).
- Terrain classification (`flat` | `moderate` | `steep` | `hazardous`).

**Consumers:** Core (orchestrator), MS6 Routing Engine, MS5 Risk Assessment Service (which calls `POST /terrain/profile` for slope factor scoring).

**Key architectural constraint from the docs:** the orchestrator calls each service and services operate **independently with the information received**. MS4 must not call MS5/MS6/Core. Its only external dependency is a raster data source — for this MVP, an internal swappable datasource (no real Raster Service / MS3 integration yet).

## 2. Scope

### 2.1 MVP goals (in scope)

| # | Goal |
|---|------|
| G1 | `GET /health` — liveness + datasource connectivity status |
| G2 | `GET /terrain/point` — elevation, slope, terrain class at a coordinate |
| G3 | `POST /terrain/profile` — sampled elevation/slope profile along a polyline |
| G4 | `POST /terrain/area` — aggregate elevation/slope stats over a bounding box |
| G5 | Repository pattern: computation layers never touch a datasource directly; the datasource is swappable behind `RasterDatasource` |
| G6 | Two working datasources: `SyntheticDemDatasource` (deterministic in-memory grid) and `GeoTiffRasterDatasource` (rasterio over a test fixture) |
| G7 | Clean Architecture + feature-first layout; SOLID/DRY/KISS; one class per file; every key directory has a `README.md` |
| G8 | TDD: minimum 3 tests per feature (happy path, edge case, expected failure) + API contract tests |

### 2.2 Non-goals (out of scope for this MVP)

- Real data sources, live Raster Service (MS3) HTTP integration, dataset catalogs.
- Derived-layer persistence (e.g. writing slope GeoTIFFs back to shared storage).
- Docker images / Compose.
- Rock/crater detection, multi-body support, auth, rate limiting.

## 3. Architecture

### 3.1 Layers (Clean Architecture, dependencies point inward only)

```
presentation  →  application  →  domain
     ↓                                  ↑
     └────────── infrastructure ────────┘
```

| Layer | Contains | May import | Must NOT import |
|---|---|---|---|
| `domain` | Entities, value objects, pure computation (`SlopeCalculator`, `TerrainClassifier`, `PathSampler`, `DistanceCalculator`) | stdlib, numpy | FastAPI, pydantic DTOs, rasterio, httpx |
| `application` | Use cases orchestrating domain + ports | domain, ports | FastAPI, concrete datasources |
| `ports` | Abstract interfaces (`TerrainRepository`, `RasterDatasource`) | domain | any implementation |
| `infrastructure` | Datasource implementations, repository implementations, mappers | ports, domain, rasterio, numpy | FastAPI routers |
| `presentation` | FastAPI routers, Pydantic request/response schemas, mappers | application, domain | rasterio, datasource internals |
| `composition` | DI wiring (build repository from settings for `Depends`) | everything | — |

### 3.2 Repository + Datasource pattern (hard requirement)

```
AnalyzePoint (use case)
      │ depends on
      ▼
TerrainRepository (port/ABC)          ◄── domain-facing contract
      ▲ implemented by
DemTerrainRepository                  ◄── infrastructure
      │ depends on
      ▼
RasterDatasource (port/ABC)           ◄── data-access contract
      ▲ implemented by
      ├── SyntheticDemDatasource      (deterministic numpy DEM — dev/test/default)
      ├── GeoTiffRasterDatasource     (rasterio over a GeoTIFF file)
      └── HttpRasterDatasource        (RESERVED: future MS3 client — interface only, stub optional)
```

- The datasource is selected by `Settings.datasource_kind` (`synthetic` | `geotiff`; `http` reserved) in `composition/dependencies.py`.
- **Swap rule:** if the data source contract changes (e.g. the data teammate delivers a different format), only the datasource implementation + its mapper change. Domain, use cases, and API contracts stay untouched.
- **Adapter rule:** mappers convert raw datasource payloads → `DemWindow` (domain object) at the infrastructure boundary, and domain results → response DTOs at the presentation boundary. No raw datasource types cross into the domain.

### 3.3 Error taxonomy → HTTP mapping

| Exception (raised in) | HTTP | When |
|---|---|---|
| `DomainValidationError` (domain/application) | 400 | invalid bbox, path < 2 points, limits exceeded |
| `NoCoverageError` (repository/domain) | 404 | requested location hits nodata / outside DEM extent |
| `UpstreamDatasourceError` (infrastructure) | 502 | datasource failed (file unreadable; future: MS3 down) |
| Pydantic `RequestValidationError` | 422 | malformed request shape/types (FastAPI default) |

`DomainError` is the base class. Handlers are registered once in `app/main.py` via `core/errors/error_handlers.py` and return `{"detail": "..."}` per FastAPI convention.

### 3.4 Directory tree (service root: `terrain-analysis/`)

```
terrain-analysis/
├── README.md                          # service overview, setup, run, endpoints
├── pyproject.toml
├── app/
│   ├── __init__.py
│   ├── README.md
│   ├── main.py                        # create_app(): routers + exception handlers
│   ├── core/
│   │   ├── README.md
│   │   ├── config/
│   │   │   ├── README.md
│   │   │   └── settings.py            # Settings (pydantic-settings) — see §5
│   │   ├── domain/
│   │   │   ├── README.md
│   │   │   ├── geo_point.py           # GeoPoint value object (lat/lon validation)
│   │   │   ├── dem_window.py          # DemWindow: elevation array + cell_size_m + origin + nodata
│   │   │   ├── slope_calculator.py    # Horn's method → slope_deg array
│   │   │   ├── terrain_classifier.py  # TerrainClassifier + TerrainClass enum (thresholds from config)
│   │   │   ├── distance_calculator.py # haversine on sphere, configurable body radius
│   │   │   └── path_sampler.py        # interpolate polyline → sample points every N m
│   │   ├── errors/
│   │   │   ├── README.md
│   │   │   ├── exceptions.py          # DomainError + subclasses
│   │   │   └── error_handlers.py      # register_exception_handlers(app)
│   │   └── ports/
│   │       ├── README.md
│   │       ├── terrain_repository.py  # ABC: elevation_at(point), window_for(point/bbox), ...
│   │       └── raster_datasource.py   # ABC: read_window(...), read_metadata(), ping()
│   ├── features/
│   │   ├── README.md
│   │   ├── point_analysis/
│   │   │   ├── README.md
│   │   │   ├── domain/point_analysis.py            # PointAnalysis result entity
│   │   │   ├── application/analyze_point.py        # AnalyzePoint use case
│   │   │   └── presentation/
│   │   │       ├── point_router.py                 # GET /terrain/point
│   │   │       ├── point_schemas.py                # PointAnalysisResponse
│   │   │       └── point_mapper.py                 # domain → DTO adapter
│   │   ├── profile_analysis/
│   │   │   ├── README.md
│   │   │   ├── domain/elevation_profile.py         # ElevationProfile, ProfileSample entities
│   │   │   ├── application/analyze_profile.py      # AnalyzeProfile use case
│   │   │   └── presentation/
│   │   │       ├── profile_router.py               # POST /terrain/profile
│   │   │       ├── profile_schemas.py              # ProfileRequest/ProfileResponse
│   │   │       └── profile_mapper.py
│   │   ├── area_analysis/
│   │   │   ├── README.md
│   │   │   ├── domain/area_stats.py                # AreaStats entity
│   │   │   ├── application/analyze_area.py         # AnalyzeArea use case
│   │   │   └── presentation/
│   │   │       ├── area_router.py                  # POST /terrain/area
│   │   │       ├── area_schemas.py
│   │   │       └── area_mapper.py
│   │   └── health/
│   │       ├── README.md
│   │       └── presentation/health_router.py       # GET /health
│   ├── infrastructure/
│   │   ├── README.md
│   │   ├── datasources/
│   │   │   ├── README.md
│   │   │   ├── synthetic_dem_datasource.py         # deterministic numpy DEM (fixture-grade)
│   │   │   ├── geotiff_datasource.py               # rasterio-backed reader
│   │   │   └── dem_window_mapper.py                # raw raster payload → DemWindow adapter
│   │   └── repositories/
│   │       ├── README.md
│   │       └── dem_terrain_repository.py           # TerrainRepository impl over RasterDatasource
│   └── composition/
│       ├── README.md
│       └── dependencies.py                         # FastAPI Depends providers
└── tests/
    ├── README.md
    ├── conftest.py                                  # TestClient, synthetic DEM, GeoTIFF fixture
    ├── unit/
    │   ├── test_slope_calculator.py
    │   ├── test_terrain_classifier.py
    │   ├── test_distance_calculator.py
    │   ├── test_path_sampler.py
    │   ├── test_dem_terrain_repository.py
    │   ├── test_analyze_point.py
    │   ├── test_analyze_profile.py
    │   └── test_analyze_area.py
    ├── api/
    │   ├── test_health_endpoint.py
    │   ├── test_point_endpoint.py
    │   ├── test_profile_endpoint.py
    │   └── test_area_endpoint.py
    └── fixtures/
        └── make_test_dem.py                         # deterministic test GeoTIFF generator (rasterio)
```

Rules:
- One class per file; file name = snake_case of the class name.
- `__init__.py` files stay empty (no re-export barrels) to keep imports explicit.
- Every directory marked with `README.md` above gets one, committed in the same PR/WP that creates the directory. READMEs state: purpose, contents, key classes, and layer rules that apply.

## 4. Feature Specifications (what each WP must implement)

All contracts below mirror `SPEC_MS4_TERRAIN_ANALYSIS.md` §3–§5. The spec file wins on any conflict.

### F1 — Health (`GET /health`)

- Response `200`: `{"status": "ok", "datasource": "ok"}` (or `"datasource": "unavailable"` with status `"degraded"` when `RasterDatasource.ping()` fails — still HTTP 200).

### F2 — Point analysis (`GET /terrain/point`)

- Params: `lat` (float, -90..90), `lon` (float, -180..180), `body` (default `"mars"`).
- Flow: `AnalyzePoint` → `repository.elevation_at(point)` + slope via a small DEM window around the point → `TerrainClassifier` → `PointAnalysis`.
- `200`: `{lat, lon, elevation_m, slope_deg, terrain_class}`.
- Errors: out-of-range coords → 422 (Pydantic); nodata → 404; datasource failure → 502.

### F3 — Profile analysis (`POST /terrain/profile`)

- Body: `{body?, path: [{lat, lon}...] (min 2), sample_distance_m? (default 100)}`.
- Flow: `PathSampler` interpolates sample points every `sample_distance_m` (cap: `Settings.max_samples`, path point cap: `Settings.max_path_points`) → per-sample elevation + slope → aggregates: `total_distance_m`, `elevation_gain_m`, `elevation_loss_m`, `max_slope_deg`.
- `200`: `{sample_count, total_distance_m, elevation_gain_m, elevation_loss_m, max_slope_deg, samples[]}` with `samples[] = {lat, lon, distance_m, elevation_m, slope_deg}`.
- Errors: path < 2 points or limits exceeded → 400; no coverage → 404; datasource failure → 502.
- Edge rule: a sample landing on nodata → `NoCoverageError` → 404 for the whole request (document the choice; per-spec nodata ⇒ 404).

### F4 — Area analysis (`POST /terrain/area`)

- Body: `{body?, bbox: [min_lon, min_lat, max_lon, max_lat]}`.
- Flow: validate bbox ordering → `repository` DEM window for bbox → slope array via `SlopeCalculator` → stats: `elevation_m.{min,max,mean}`, `slope_deg.{min,max,mean}`, `steep_fraction` (fraction of cells with slope ≥ `steep` threshold).
- Errors: inverted/degenerate bbox → 400; window fully nodata → 404; datasource failure → 502.

### F5 — Business rules (spec §5)

- Slope: Horn's method on 3×3 neighborhood, degrees. Nodata = NaN; out-of-array cells are treated as nodata; a NaN neighbour is replaced by linear extrapolation `2·centre − opposite` (exact for planes), falling back to the centre value when the opposite is also NaN; a cell with no valid neighbour → NaN (never a fabricated 0°). *(WP1 review decision)* `SlopeCalculator` operates on `DemWindow` (needs `cell_size_m`; convert degrees→meters via `Settings.planet_radius_km` when the datasource reports angular units — adapter's job).
- `terrain_class` (configurable thresholds): `flat` < 5°, `moderate` [5, 15), `steep` [15, 30), `hazardous` ≥ 30°.
- Coordinates echoed in planetocentric lat/lon.
- WP1 decisions: `RasterDatasource` has no `read_metadata()` — each datasource mapper converts native resolution to `DemWindow.cell_size_x_m/cell_size_y_m`; `DemWindow` carries no origin; extra domain files `bounding_box.py`, `path_sample.py`, `terrain_class.py`; antimeridian-crossing paths/bboxes unsupported (bbox → 400); `error_handlers.py` moved to WP6 (imports FastAPI).

## 5. Configuration (`core/config/settings.py`)

`Settings(BaseSettings)`, env prefix `MS4_`:

| Field | Default | Purpose |
|---|---|---|
| `body` | `"mars"` | celestial body label (echo only) |
| `planet_radius_km` | `3389.5` | Mars radius for haversine/deg→m |
| `datasource_kind` | `"synthetic"` | `synthetic` \| `geotiff` (`http` reserved) |
| `dem_path` | `""` | path to GeoTIFF when `geotiff` |
| `slope_flat_max_deg` / `slope_moderate_max_deg` / `slope_steep_max_deg` | `5.0` / `15.0` / `30.0` | class thresholds |
| `sample_distance_m` | `100.0` | default sampling interval |
| `max_samples` | `1000` | cap on profile samples → 400 |
| `max_path_points` | `100` | cap on input polyline points → 400 |
| `max_window_cells` | `4_000_000` | cap on area window size → 400 |

## 6. Dependencies (`pyproject.toml`)

- Runtime: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `numpy`, `rasterio`.
- Dev (`[dev]` extra): `pytest`, `httpx` (required by FastAPI `TestClient`).
- Pin minimum versions; avoid `latest`/unbounded upper ranges. Risk note: rasterio on Windows — if `pip install rasterio` fails, proceed with `datasource_kind=synthetic` and defer the geotiff datasource rather than blocking the MVP.
- Install: `python -m venv .venv && pip install -e ".[dev]"`.

## 7. Test Matrix (TDD — mandatory minimum 3 per feature: happy / edge / expected-failure)

| Target | Happy path | Edge case | Expected failure |
|---|---|---|---|
| `SlopeCalculator` | known linear-gradient DEM → expected slope_deg | flat plane → 0° everywhere; window edge cells | all-nodata window → `NoCoverageError` |
| `TerrainClassifier` | 12° → `moderate` | boundaries: 5.0, 15.0, 30.0 | negative slope → `DomainValidationError` |
| `DistanceCalculator` | known lat/lon pair → expected meters | zero distance (same point) | — |
| `PathSampler` | straight path → N evenly spaced samples | exact multiple of `sample_distance_m` | sample step ≤ 0 → `DomainValidationError` |
| `DemTerrainRepository` | returns domain values from fake datasource | point on DEM boundary | datasource raises → `UpstreamDatasourceError`; nodata → `NoCoverageError` |
| Datasource swap | same repository test passes with `SyntheticDemDatasource` AND `GeoTiffRasterDatasource` (proves pattern) | — | — |
| `AnalyzePoint` | fixture DEM point → contract values | point at DEM edge | nodata point → `NoCoverageError` |
| `AnalyzeProfile` | 2-point path → expected sample_count/gain/loss | degenerate 2-identical-points path | limits exceeded → `DomainValidationError` |
| `AnalyzeArea` | small bbox → expected stats | bbox partially outside extent | inverted bbox → 400; fully nodata → `NoCoverageError` |
| API contract (all 4 endpoints) | `200` response matches spec schema exactly | 400/422 on invalid input | 404 nodata; 502 when datasource stubbed to fail |
| `GET /health` | `{"status":"ok"}` | datasource down → `"degraded"` | — |

Test layout: `tests/unit/` for domain/application/repository; `tests/api/` for endpoint contract tests. `conftest.py` provides: `TestClient` wired with `SyntheticDemDatasource`, a fixed deterministic DEM, and a session-scoped test GeoTIFF generated by `tests/fixtures/make_test_dem.py` (generated at test time — do NOT commit binary fixtures).

## 8. Work Packages (execution plan for the manager agent)

Dependency graph — a WP can start only when its predecessors are **merged and green**:

```
WP0 → WP1 → WP2 → ┬─ WP3 (point)
                  ├─ WP4 (profile)   → WP6 → WP7
                  └─ WP5 (area)
```

| WP | Scope | Files (new) | Acceptance | Status |
|---|---|---|---|---|
| **WP0 Bootstrap** | package skeleton, tooling | `pyproject.toml`, `app/__init__.py`, `app/core/config/settings.py`, dir skeleton + stub READMEs, `tests/conftest.py` (minimal) | `pip install -e ".[dev]"` works; `pytest` collects 0 tests exit 5→OK; `python -c "from app.core.config.settings import Settings"` passes | done |
| **WP1 Core domain** | pure computation + ports + errors | everything under `core/domain/`, `core/ports/`, `core/errors/` + unit tests | all §7 domain tests green; zero imports of fastapi/rasterio in `core/` | done |
| **WP2 Infrastructure** | datasource port impls + repository | `infrastructure/**`, `composition/dependencies.py`, `tests/fixtures/make_test_dem.py` + repo/datasource tests | repository swap test green with BOTH datasources; error mapping verified | done |
| **WP3 Point feature** | F2 end-to-end | `features/point_analysis/**` + its tests | `GET /terrain/point` contract test green incl. 404/502 cases | done |
| **WP4 Profile feature** | F3 end-to-end | `features/profile_analysis/**` + its tests | `POST /terrain/profile` contract test green incl. limit/404 cases | done |
| **WP5 Area feature** | F4 end-to-end | `features/area_analysis/**` + its tests | `POST /terrain/area` contract test green incl. bbox/404 cases | done |
| **WP6 App wiring** | service assembly | `app/main.py`, `features/health/**`, `error_handlers` registration, root `README.md` | `uvicorn app.main:app` serves all 4 endpoints; `/health` works; `pytest -v` fully green | done |
| **WP7 Review & docs** | quality gate | README completions, fixes from review | DoD checklist (§10) fully checked | done |

**Execution order note for the manager:** WP0–WP2 are strictly sequential. WP3, WP4, WP5 touch disjoint directories and MAY run as parallel background subagents after WP2 merges. WP6 needs all three merged. WP7 runs last.

## 9. Agent Orchestration Guide (how the manager uses subagents)

This plan is written for a Devin CLI manager agent. Below are the role→model assignments and the exact mechanics, derived from Devin docs (`models.mdx`, `subagents.mdx`).

### 9.1 Roles and recommended models

| Role | Model | Rationale (per Devin docs) |
|---|---|---|
| **Orchestrator (root/manager agent)** | `opus` or `gpt` | Multi-file coordination, dependency tracking, integration decisions — use a frontier reasoning model |
| **Developer (code writing)** | `swe` (fast/cheap) or `sonnet` for trickier WPs | WPs here are well-scoped; `swe` covers most implementation at low cost |
| **Reviewer** | `opus` or `gpt` | Review benefits from deep reasoning; runs read-only so it's cheap on volume |
| **Research/exploration** | `subagent_explore` default (router-selected) | Read-only; keeps cost off the parent's premium model |

### 9.2 Required setup before WP0 — create custom subagent profiles

`model:` in a custom profile's frontmatter is the **only** way to run a write-capable subagent on a model other than the parent's. The manager MUST create these two files first (project-level config):

`.devin/agents/tdd-developer.md`:
```markdown
---
name: tdd-developer
description: Implements a scoped work package test-first; writes minimal code to pass
model: swe
---

You are a TDD implementation subagent for the MS4 Terrain Analysis Service.

Rules:
1. Follow the work package scope in the prompt EXACTLY — do not create files outside it.
2. Write failing tests first (tests/unit or tests/api per the plan), then implement until green.
3. Architecture rules: dependencies point inward (presentation→application→domain);
   domain never imports fastapi/pydantic-DTOs/rasterio; one class per file; English only;
   no comments unless explaining non-obvious geospatial math.
4. Create a README.md in every new directory you make.
5. Run `pytest -v` before reporting. Report: files created, test results, deviations.
```

`.devin/agents/code-reviewer.md`:
```markdown
---
name: code-reviewer
description: Reviews a work package diff for correctness, architecture rules, and contract compliance
model: opus
allowed-tools: [read, grep, glob, exec]
---

You are a code review subagent for the MS4 Terrain Analysis Service.

Check, in order:
1. Contract compliance: responses match docs/SPEC_MS4_TERRAIN_ANALYSIS.md schemas and error codes.
2. Layer violations: domain imports (no fastapi/rasterio), repository pattern respected
   (use cases depend on TerrainRepository port, never on a datasource).
3. Test adequacy: >=3 tests per feature (happy/edge/failure); contract tests exist.
4. Bugs: off-by-one in sampling, nodata handling, bbox validation, slope math units.
5. Report findings as file:line with severity (blocker/major/minor). Do not edit code.
```

### 9.3 Spawn mechanics

- `run_subagent(profile="tdd-developer", ...)` for WPs; `profile="code-reviewer"` for review; built-in `subagent_explore` for any open research question.
- **Foreground** for blocking WPs (WP0–WP2, WP6). **Background** for the parallel fan-out (WP3+WP4+WP5 simultaneously).
- Subagents are stateless: every prompt MUST include the WP scope, the exact file list to create, the relevant spec section, and the architecture rules summary (§3.1). Point them at this plan file and `SPEC_MS4_TERRAIN_ANALYSIS.md`.
- After each dev subagent returns: manager runs `pytest -v` itself, then spawns `code-reviewer`; blocker findings go back to the same dev subagent via `resume` before merge.
- Keep parallelism bounded (max 3 concurrent background dev subagents) — each subagent has its own cost.

### 9.4 Standard workflow loop (per WP)

```
1. Spawn tdd-developer (fg or bg) with WP prompt
2. On completion → run pytest -v (manager verifies, don't trust reports)
3. Spawn code-reviewer (fg) on the WP diff
4. Blockers? → resume dev subagent with findings → back to 2
5. Green + clean review → commit with conventional message, update this plan's WP status
```

## 10. Definition of Done (final gate, WP7)

- [x] `pytest -v` fully green; every feature has ≥3 tests incl. contract tests for all 4 endpoints.
- [x] Responses match SPEC_MS4 schemas and error codes (400/404/502 verified by tests).
- [x] `datasource_kind=synthetic` AND `geotiff` both pass the repository test suite (swap proof).
- [x] No import of `fastapi`, `rasterio`, or presentation DTOs inside `core/domain` or `application` (grep-verified).
- [x] Every directory in §3.4 has its `README.md`; service root README documents setup/run.
- [x] `uvicorn app.main:app` boots; smoke: `GET /health`, `GET /terrain/point?lat=18.4&lon=77.5`, `POST /terrain/profile`, `POST /terrain/area` return contract responses on the synthetic DEM.
- [x] No Docker artifacts; no secrets; English only.

## 11. Verification Commands (manager runs at integration)

```bash
cd terrain-analysis
python -m venv .venv && source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -v
uvicorn app.main:app --port 8004 &
curl "http://localhost:8004/health"
curl "http://localhost:8004/terrain/point?lat=18.4&lon=77.5"
curl -X POST "http://localhost:8004/terrain/profile" -H "Content-Type: application/json" \
  -d '{"path":[{"lat":18.4,"lon":77.5},{"lat":18.5,"lon":77.6}],"sample_distance_m":100}'
curl -X POST "http://localhost:8004/terrain/area" -H "Content-Type: application/json" \
  -d '{"bbox":[77.5,18.4,77.6,18.5]}'
```

## 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| rasterio fails to install on Windows | Synthetic datasource keeps MVP unblocked; defer `geotiff` behind config flag; note in README |
| Contract drift vs SPEC_MS4 | API contract tests in `tests/api/` are the guard; reviewer checks spec first |
| Subagent fan-out cost | Max 3 parallel dev subagents; batch review per WP not per file |
| Slope units bug (deg vs m cell size) | `DemWindow.cell_size_m` is mandatory; adapter converts; unit test with known gradient pins correctness |
| Layer violations creep in during parallel WPs | Architecture rules embedded in the dev subagent prompt + reviewer gate + §10 grep check |

---

**Deviations from §3.4 recorded during execution (WP1–WP7):**

- Added `app/core/application/` (`TerrainPointSampler`, `TerrainPointSample`) — shared point sampling for point + profile features.
- Added domain files `bounding_box.py`, `path_sample.py`, `terrain_class.py`, `halo_window.py`.
- Added `infrastructure/datasources/{grid_geometry,grid_backed_raster_datasource,unavailable_raster_datasource}.py`; `RasterDatasource` gained `read_window_with_halo` (area slope uses a 1-cell halo so border slopes use real neighbours); no `read_metadata()`.
- Added per-feature providers `app/composition/{point,profile,area}_dependencies.py`; providers chain via FastAPI `Depends`.
- Added `features/health/presentation/health_schemas.py`, `features/*/domain/` extra entities (`profile_sample.py`, `value_stats.py`), `tests/fakes/`.
- `GET /terrain/point` returns **400** (not 422) for out-of-range coordinates, per spec §4.4 (spec wins over F2).
- `steep_fraction` counts cells with slope ≥ `slope_moderate_max_deg` (steep + hazardous).

**Execution tracking:** the manager agent SHOULD update the WP table (§8) with status (`pending → in_progress → done`) as work proceeds, keeping this file the auditable source of truth.
