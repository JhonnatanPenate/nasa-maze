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
| MS5-D6 | Environmental storage: SQLite catalog (`risk_catalog.sqlite`) built offline by `python -m app.ingest` | **done (Phase 2)** | Tables `thermal_climatology`, `radiation_climatology`, `meta`, `data_quality`; keyed by `(sol, floor(hora_lmst))` per Phase 0 findings. Runtime opens `mode=ro`; MS5 never reads the workbooks or MS1/MS3 storage. Seed copy committed under `data/seed/`. |
| MS5-D7 | Factor scores deferred to Phase 3; Phase 1 returns `score: null`, `risk: null`, `risk_level: "unknown"` | **superseded by Phase 3** | Scoring landed in `core/domain/*_risk.py`; Phase 1 stubs were replaced. The unknown-risk rule still applies whenever no factor is available/scored. |
| MS5-D8 | Threshold placeholders in `config/risk_thresholds.yaml` marked `placeholder` | **accepted** | Roughness/radiation/dune-proximity/temperature-margin thresholds are configurable stand-ins pending Phase 3 calibration; Javi's constants are inherited assumptions, not certified limits. Weights and level boundaries are SPEC-fixed. Phase 3 values logged in MS5-D13..D17. |
| MS5-D9 | Plan-extension endpoints retained as additive stubs | **accepted (Gate 1 review)** | `GET /risk/vehicle-profiles`, `GET /risk/meta`, `POST /risk/area` (Phase 1: validates + caps, `aggregation: "pending"`), plus additive request/response fields on SPEC endpoints. None alter SPEC fields, weights, or the weighted-risk formula; no route dose accumulation (MS6). |
| MS5-D10 | `inercia_termica_tiu` band ingested but not a SPEC factor | **accepted** | SPEC factor `temperature` sources REMS hourly profiles; the TI band feeds the Javi tilt model as a predictor (Phase 3, MS5-D19/D20) and remains observed context only — never a scored factor. |
| MS5-D11 | Python `>=3.13`, Docker `python:3.13-slim` | **accepted** | Plan §6 targets 3.13; no rasterio dependency so no 3.12 wheel constraint (unlike MS4). |
| MS5-D12 | Standalone `risk-assessment/docker-compose.yml`; no root compose entry yet | **accepted** | Root compose integration deferred to full-stack wiring (plan gate). |
| MS5-D13 | `slope` score = SPEC illustrative baseline: 0 at `<=5°`, 1 at `>=30°`, linear (`score_floor_deg`/`score_ceil_deg`); warning `STEEP_SLOPE_{deg}DEG` at `>=15°` | **accepted** | Score ramp is SPEC §5's own example; 15° warning and 25° block are Javi optimizer constants (`optimizador_rutas.py:45-47`). The 25° block lives in the vehicle profile, not the score. |
| MS5-D14 | `roughness` score ramp `0.5–3.0 m`, warning `HIGH_ROUGHNESS` at `>=1.5 m` | **placeholder** | Javi's `rugosidad <=0.60` / `>=1.10` are soil-regime boundaries, not a published risk scale; the ramp/warning are configurable stand-ins pending calibration. |
| MS5-D15 | `dunes` score = max(proximity ramp, dark-fraction ratio); `BAGNOLD_DUNES_NEARBY` on `distancia_duna_m <= proximity_warning_m` (100 m) or `fraccion_oscura >= 0.5` | **mixed** | Dark-fraction 0.5 and the mapped-dune rule (`distancia_duna_m == 0`) are Javi `regla_suelo arena_dunas`; `proximity_warning_m = 100 m` and the score normalization are **placeholder** — Javi defines no broader proximity threshold. |
| MS5-D16 | `temperature` scored on REMS **ground-temp mean** vs Javi band 230–290 K; score = `clamp01(excess_K / score_full_scale_K)` with `score_full_scale_K = 60`; `EXTREME_COLD_ZONE` when the mean exits the band by more than `warning_margin_K = 10` | **mixed** | Band (230–290 K) and excess formula `max(0,230-T)+max(0,T-290)` are Javi `BANDA_TERMICA_OPERATIVA_K`/`integrar_exposicion`; the 60 K full scale, 10 K warning margin, and the single-code coverage of both cold and hot excursions are **placeholder** interpretations (SPEC suggests only `EXTREME_COLD_ZONE`). REMS min/max stay descriptive summaries, not percentiles. |
| MS5-D17 | `radiation` score = `clamp01(dosis_e_uGy_h / score_full_scale_uGy_h)` with full scale 30 µGy/h; `HIGH_RADIATION_RATE` at `>= warning_uGy_h = 20` | **placeholder** | Dose-E channel and hourly rate semantics are SPEC/Javi; both numeric thresholds are configurable stand-ins. The ingest-time `0.7 * median` filter is Javi's background-profile rule, explicitly NOT an alert threshold; MS5 never integrates route dose (MS6). |
| MS5-D18 | `baseline_mars_rover`: 1000 m/h nominal, speed `max(0.1, 1 - tilt/30)`, dune multiplier 0.40, blocks slope `>=25°`, tilt `>=20°` or `tilt + 1.96σ > 20°`, thermal band 230–290 K advisory (non-blocking) | **accepted (inherited)** | All values are Javi optimizer constants (`optimizador_rutas.py:44-48, 325-329, 252-257`); dune multiplier 0.40 = `1 - FACTOR_DESLIZAMIENTO_ARENA(0.60)`. Restrictions are reported separately and never alter the SPEC weighted risk or force `critical`. Missing tilt predictors fall back to unpenalized nominal speed (documented assumption). Javi's `[7,17)` LMST motion window stays MS6 scheduling, not an MS5 restriction. |
| MS5-D19 | Tilt models: `config/modelos_por_suelo.json` is a committed copy of the delivered `data/gale/processed/modelos_por_suelo.json` | **accepted** | Runtime needs the per-soil linear tilt models offline; the file is a science-pipeline artifact (4 soil models `estado=ajustado` + `modelo_global`, predictors clipped to `rango_predictores`, `sigma_residual` for the margin rule). Loader validates intercept/coefficients/ranges and fails fast. |
| MS5-D20 | Soil classification = Javi 4-class precedence `arena_dunas > lecho_rocoso_firme > rocoso_fracturado > regolito_compacto` with exact thresholds (1.10/8.0/0.2291, 0.60/7.0/0.2294, `dist==0`/`dark>=0.5`); MS4 `slope_deg` reused as `pendiente_grados` | **accepted** | Mirrors `clasificar_tipo_suelo` (`optimizador_rutas.py:73-85`) and `reglas_suelo` in the model JSON. Any nodata input -> unclassified -> global tilt model; predicted tilt is never a SPEC factor nor a substitute for MS4 slope. |
| MS5-D21 | LMST = 24 integer bins mod 24; elapsed hours = `distance_m / effective_speed_m_h` (m/h clock, no UTC/Ls conversion) | **accepted** | Javi optimizer convention; no UTC/date/Ls exists in the delivered data (Phase 0 inventory Q2). Route dose accumulation remains MS6. |
| MS5-D22 | `confidence ∈ {high, medium, low}` derived from scored-cell coverage: `>=0.9` high, `>=0.5` medium, else low | **placeholder** | Plan §4.1 fixes the vocabulary but not the metric; coverage ratio is the simplest explainable heuristic pending calibration. |
| MS5-D23 | Path summary semantics: `mean_score`/`p95_score` = unweighted mean / nearest-rank p95 of scored segment risks; `dominant_factor` = highest mean factor score (SPEC order breaks ties); segment environment evaluated at the **arrival** LMST bin; path evaluation always fetches MS4 slope + 5 MS3 bands (`rugosidad_m`, `fraccion_oscura`, `inercia_termica_tiu`, `albedo`, `distancia_duna_m`) because additive restrictions need soil/tilt inputs even when `factors` selects a subset; daily tilt predictors = mean of the selected sol's 24 hourly catalog values; `provenance.thermal_excess_Kh` integrates Javi's hourly excess over segment hours | **mixed** | Plan §4.4/§7.1 requires the fields but not their exact estimators; arrival-hour sampling matches the existing "assess the arrival sample" convention; the always-fetch policy keeps restrictions independent of the `factors` subset (one batched MS4 call + 5 MS3 calls, still inside the SPEC NFR). |
| MS5-D24 | `POST /risk/area` grid: corner-anchored samples at the delivered `rejilla` pitch (`GRID_RES_DEG` ≈ 0.001518° ≈ 90 m), `cell_count = ceil(dx/res)*ceil(dy/res)`; one `slope_at` + one `point_values` per cell (O(2·cells) upstream reads — modest bboxes only, `max_cells` is the guard); environmental context resolved once per request (climatology is spatially uniform); cells outside coverage -> `unknown` level + `uncovered_cells`, `blocked_fraction` denominator = covered cells only, hotspots capped at 100 sorted by risk desc | **accepted** | Plan §7.1 requires level counts/blocked fraction/stats/hotspots but not the sampling scheme; reusing the raster pitch keeps cells aligned with MS3's native grid and the Phase 1 cap estimate consistent. Restrictions feed `blocked_fraction` only — never scores (same rule as paths). |
| MS5-D25 | Deployment: no root `docker-compose.yml` exists — MS5 ships a standalone `risk-assessment/docker-compose.yml` with repo-root-relative paths (merge-ready; standalone via `--project-directory .`); catalog/config reach the container via volumes, never baked into the image; `docker build`/compose run and live MS3/MS4 integration are **deferred** (no docker in the dev env) — `tests/integration/test_live_upstream.py` auto-skips until :8003/:8004 are up | **accepted** | Matches the `location-service` standalone-snippet convention; offline verification (synthetic + unavailable modes, real SQLite catalog) covers everything testable without docker. |

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
