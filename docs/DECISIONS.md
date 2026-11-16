# Architecture decisions log

Cross-service decisions and per-service defaults. Each entry records the
decision, the status, and where it is implemented.

## Location Service (`location-service/`)

| ID | Decision | Status | Notes |
|---|---|---|---|
| D1 | Canonical Bradbury Landing coordinate: `lat -4.5895, lon 137.4417` | **accepted (default)** | Route-cell snapping belongs to Raster/Routing, not this service. Seed catalog uses `mars:msl:bradbury-landing`. |
| D2 | Gazetteer acquisition: manual MVP download into `data/raw/mars/gazetteer/` | **done (MVP)** | Delivered file: USGS `MARS_nomenclature_center_pts.shp` (2055 POINT features, GCS_Mars_2000 sphere). Linked into `data/raw/mars/gazetteer/`; full catalog built at `data/processed/mars/location/location_catalog.sqlite` (2077 places). |
| D3 | Gazetteer `approval_status`: approved features only by default | **accepted (default)** | Unapproved/provisional features are excluded from the catalog and counted in `ingest_report.json`. |
| D4 | Alias/descriptor languages: Spanish + English | **accepted (default)** | `config/aliases.yaml` + `type_word_translations` in `config/gazetteer_columns.yaml`. Official names stay in the Gazetteer's language. |
| D5 | Mineral `properties` exposed per POI | **accepted (default)** | Informational attributes only; not an official scientific source. |
| D6 | UI autocomplete via `GET /v1/places/search` (small `limit`, prefix matching) | **accepted (default)** | No separate autocomplete endpoint. |
| D7 | Future Moon support | **deferred** | `body` field and ID prefixes already allow it; not implemented. |

### Implementation notes

- Python `>=3.12` (`requires-python`), developed on 3.13.5 — the only
  interpreter available in the build environment.
- Runtime is fully offline: no outbound calls; the catalog is a read-only
  SQLite file loaded once at startup (with optional `/v1/admin/reload`).
- Ingestion-only dependencies (`pandas`, `openpyxl`) live in the `ingest`
  extra, never in runtime dependencies.
- Mars geodesy is implemented locally (`domain/geo.py`, haversine with
  R = 3,396,190 m); no Earth geodesy library is used.
- Gazetteer-dependent golden cases 7–8 run unskipped once a file is
  present in `data/raw/mars/gazetteer/` (currently a symlink to the
  delivered `data/gale/raw/gazzeter/MARS_nomenclature_center_pts.shp`;
  the directory itself is git-ignored data, so fresh clones skip again).
- Golden case 13 (Bradbury Landing → Glen Etive): the spec's "≈ 14–15 km"
  appears to be an estimate; the haversine straight-line distance with
  R = 3,396,190 m is 9,026 m (the delivered route metadata reports a 10.3 km
  path). The test asserts the computed value (8–11 km) and case 23 verifies
  the formula against an independent calculation.

## Risk Assessment Service (`risk-assessment/`)

| ID | Decision | Status | Notes |
|---|---|---|---|
| MS5-D1 | Longitude wire convention: east-positive **[-180, 180]** | **accepted** | Matches MS3/MS4 request convention (Gale ≈ 137°E). The location catalog's 0..360 convention is NOT used on MS5 endpoints. |
| MS5-D2 | Error body format `{"detail": "..."}` (MS3/MS4 style) | **accepted** | MS1's RFC 7807 `application/problem+json` deliberately not adopted. Plan-named codes (`AREA_TOO_LARGE`, `VEHICLE_PROFILE_NOT_FOUND`, `CLIMATOLOGY_UNAVAILABLE`) are prefixed into `detail`. |
| MS5-D3 | Structural request-shape errors -> FastAPI 422; domain validation -> 400 | **accepted** | Same convention as MS4: schemas leave value ranges unconstrained so GeoPoint/PathSampler raise `DomainValidationError` -> 400; missing/wrong-typed fields stay 422. SPEC §4.3 only pins 400/404/502. |
| MS5-D4 | `/health` shape: `{status, datasource_mode, terrain, raster, environment}` | **accepted (Gate 1 review)** | SPEC §6 requires "MS4/raster connectivity"; environment catalog added as third upstream. Always 200; degraded instead of erroring (MS4 pattern). |
| MS5-D5 | `GET /risk/point` without `hora` evaluates all 24 LMST hours, returns worst | **accepted (Gate 1 review)** | SPEC §3.2 only specifies `lat`/`lon`; `sol`/`hora`/`include_hourly`/`factors` are additive plan-extension params. `by_hour` only with `include_hourly=true`. |
| MS5-D6 | Environmental storage: SQLite catalog (`risk_catalog.sqlite`) built offline by `python -m app.ingest` | **pending Phase 2** | Tables `thermal_climatology`, `radiation_climatology`, `meta`, `data_quality`; keyed by `(sol, floor(hora_lmst))` per Phase 0 findings. Runtime opens `mode=ro`; MS5 never reads the workbooks or MS1/MS3 storage. |
| MS5-D7 | Factor scores deferred to Phase 3; Phase 1 returns `score: null`, `risk: null`, `risk_level: "unknown"` | **accepted** | `available` flags already reflect real coverage (terrain ping, raster bands, environmental sols). SPEC §5 unknown-risk rule honored — never a silent zero. |
| MS5-D8 | Threshold placeholders in `config/risk_thresholds.yaml` marked `placeholder` | **accepted** | Roughness/radiation/dune-proximity/temperature-margin thresholds are configurable stand-ins pending Phase 3 calibration; Javi's constants are inherited assumptions, not certified limits. Weights and level boundaries are SPEC-fixed. |
| MS5-D9 | Plan-extension endpoints retained as additive stubs | **accepted (Gate 1 review)** | `GET /risk/vehicle-profiles`, `GET /risk/meta`, `POST /risk/area` (Phase 1: validates + caps, `aggregation: "pending"`), plus additive request/response fields on SPEC endpoints. None alter SPEC fields, weights, or the weighted-risk formula; no route dose accumulation (MS6). |
| MS5-D10 | `inercia_termica_tiu` band ingested but not a SPEC factor | **accepted** | SPEC factor `temperature` sources REMS hourly profiles; the TI band is kept as observed context for terrain coupling (Phase 3 decision). |
| MS5-D11 | Python `>=3.13`, Docker `python:3.13-slim` | **accepted** | Plan §6 targets 3.13; no rasterio dependency so no 3.12 wheel constraint (unlike MS4). |
| MS5-D12 | Standalone `risk-assessment/docker-compose.yml`; no root compose entry yet | **accepted** | Root compose integration deferred to full-stack wiring (plan gate). |

### Implementation notes

- Datasource modes (`RISK_DATASOURCE_MODE`): `synthetic` (deterministic
  fakes inside the delivered Gale extent), `http` (MS3 `/raster/*` + MS4
  `/terrain/*` via httpx with bounded retries), `unavailable` (always-fail
  adapters -> degraded health, 502 on reads).
- Composition root is `app/composition/dependencies.py`; `core/domain`
  stays free of FastAPI/pydantic/httpx/sqlite3/openpyxl/pandas/rasterio
  (enforced by `tests/unit/test_architecture.py`).
- Path evaluation calls MS4 `/terrain/profile` once and MS3 `/sample` once
  per required band at the same arc-length step (PathSampler semantics
  identical to MS3/MS4, R = 3,396,190 m).
- RAD channel: dose-E (`dosis_e_uGy_h`) only; dose-B kept for provenance,
  never combined. REMS has no humidity column (Phase 0 inventory).
- Port 8005 assumed free; Docker build/runtime not yet verified (no Docker
  in this environment).
