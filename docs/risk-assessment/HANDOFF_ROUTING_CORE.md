# MS5 Risk Assessment — handoff to Core & Routing (MS6)

**Service:** `risk-assessment/` — FastAPI, port **8005**, base path `/risk`.
**Contract (authoritative):** `docs/SPEC_MS5_RISK_ASSESSMENT.md`.
**Machine contract:** `packages/contracts/risk-assessment/openapi.yaml`.
**Human contract:** `docs/api-contracts/risk-assessment-service.md`.
**Status:** Phase 6 complete — all SPEC endpoints + additive plan extensions
implemented; 293 tests green offline; docker run deferred (see §7).

MS5 is the **single source of truth** for normalized point/path risk,
warnings, factor availability, environmental provenance and additive
explainability (confidence, restrictions, data-quality notes). Core should
call it for point checks and candidate-path scoring; Routing (MS6) owns
route optimization **and route-time radiation dose accumulation** — MS5
never returns cumulative dose.

---

## 1. Endpoints Core/Routing will use

| Method & path | Purpose | SPEC? |
|---|---|---|
| `GET /health` | liveness + upstream/catalog connectivity | yes |
| `GET /risk/point?lat&lon[&sol&hora&include_hourly&factors]` | risk at one point | yes |
| `POST /risk/evaluate` | risk along a polyline | yes |
| `GET /risk/factors` | factor catalog + live data coverage | yes |
| `GET /risk/vehicle-profiles` | configured vehicle profiles/limits | extension |
| `GET /risk/meta` | weights, thresholds, model version, coverage, CRS | extension |
| `POST /risk/area` | aggregate risk stats over a bbox (no raster) | extension |

All coordinates are planetocentric lat/lon degrees, CRS `IAU_2015:49900`,
lon east-positive in [-180, 180] — same convention as MS3/MS4.

## 2. `POST /risk/evaluate` — the main integration point

Request:

```json
{
  "body": "mars",
  "path": [{"lat": -4.60, "lon": 137.44}, {"lat": -4.65, "lon": 137.42}],
  "factors": ["slope", "roughness", "dunes", "temperature", "radiation"],
  "sol": 1360,
  "hora": 9,
  "sampling_step_m": 90.0,
  "vehicle_profile": "baseline_mars_rover",
  "speed_mps": null
}
```

- `path`: ≥ 2 vertices (max `RISK_MAX_PATH_POINTS` = 1000). Intermediate
  vertices only shape the polyline — segments are resampled at
  `sampling_step_m` (default 90 m, `RISK_MAX_SAMPLES` = 1000).
- `factors`: subset of the five SPEC ids; omitted → all available.
- `sol`: reference sol; the **nearest available sol is chosen independently
  per dataset** (REMS {1360, 2140}; RAD {1360, 2140, 3290, 4710}) and echoed
  in `provenance`/`sol`.
- `hora`: **departure LMST bin** (0–23, default 12). Each segment's
  environment is evaluated at its **arrival** bin; elapsed hours advance by
  effective-speed travel time with mod-24 wrap.
- `vehicle_profile`/`speed_mps`: additive (plan) — `speed_mps` overrides
  the profile's nominal speed.

Response highlights (SPEC fields first, additives after):

```json
{
  "overall_risk": 0.51, "risk_level": "high",
  "segments": [{"from": {...}, "to": {...}, "distance_m": 90.0,
                "risk": 0.62, "factor_scores": {"slope": {"score": 0.4, "available": true}, ...},
                "warnings": ["STEEP_SLOPE_16DEG"], "local_time_hour": 10}],
  "warnings_summary": ["STEEP_SLOPE_16DEG"],
  "sol": 1360, "hora": 9, "total_distance_m": 3190.6,
  "max_level": "high", "mean_score": 0.48, "p95_score": 0.61,
  "dominant_factor": "slope", "total_duration_s": 11487.0,
  "end_local_time_hours": 12.19, "confidence": "high",
  "provenance": {"reference_sol": 1360, "rems_sol": 1360, "rad_sol": 1360,
                 "scoring": "ms5-risk-v0.1", "vehicle_profile": "baseline_mars_rover",
                 "sampling_step_m": 90.0, "thermal_excess_Kh": 1.23},
  "data_quality_notes": [], "assumptions": [...],
  "restrictions": [{"segment": 3, "code": "SLOPE_BLOCK", "blocking": true, ...}],
  "hotspots": [{"segment": 7, "risk": 0.71, "level": "high", "distance_m": 90.0}],
  "blocking_segments": [3, 7]
}
```

Semantics Core/Routing must respect:

- `overall_risk` = **distance-weighted mean** of segment risks over
  available factors; `risk_level` ∈ `low|medium|high|critical|unknown`
  (boundaries 0.25/0.5/0.75; `unknown` when nothing scored — never a
  silent zero).
- `factor_scores[f].score` ∈ [0,1] or `null`; `available=false` means no
  coverage — the factor is **excluded** from weighting, never safe.
- `radiation` is a **rate** (`µGy/h`-normalized score), not a dose. **Do
  not look for cumulative dose in MS5 — MS6 accumulates it.**
- `restrictions`/`blocking_segments`/`hotspots`/`confidence`/
  `data_quality_notes`/`assumptions`/`provenance` are **additive**:
  informative, never alter SPEC scores; restrictions never force
  `critical`.
- `end_local_time_hours` ∈ [0,24) = `(hora + total_duration_s/3600) % 24`.

`GET /risk/point` is the same model at one location; omit `hora` to get the
worst of all 24 LMST bins (`by_hour` added only with `include_hourly=true`).

## 3. Errors (shared MS3/MS4 `{"detail": "..."}` body)

| HTTP | When |
|---|---|
| 400 | invalid path/factors/coords/hour/sol/speed (`DomainValidationError`) |
| 404 | no coverage at location; `VEHICLE_PROFILE_NOT_FOUND` prefix for bad profile |
| 422 | `AREA_TOO_LARGE` — `/risk/area` over `max_cells` |
| 502 | MS3/MS4 transport failure, 5xx, malformed payload |
| 503 | `CLIMATOLOGY_UNAVAILABLE` — catalog missing/corrupt |
| 500 | `INTERNAL_ERROR` sanitized |

Plan-named codes are prefixed into `detail` (e.g.
`"VEHICLE_PROFILE_NOT_FOUND: ..."`). Missing factor data is **not** an
error — it surfaces as `available:false` in scores and `/risk/factors`.

## 4. Additive extensions (not in SPEC — confirm with owners before relying)

- `GET /risk/factors` — catalog + live `available` per factor +
  `environmental_sols` per dataset. Use at startup/UI to grey out factors.
- `GET /risk/vehicle-profiles` — YAML profiles (`baseline_mars_rover`
  today): nominal speed, slope/tilt block limits, thermal band,
  `dose_budget_uGy` (informational — dose math is MS6).
- `GET /risk/meta` — weights, thresholds, model version, upstream/catalog
  coverage, CRS. Use for "about this assessment" UI or debugging.
- `POST /risk/area` — `{bbox:[min_lon,min_lat,max_lon,max_lat], sol?,
  hora?, vehicle_profile?, max_cells?}` → level counts, blocked fraction,
  mean/p95, per-factor stats, ≤100 hotspots. **Statistics only, never a
  per-cell raster.** O(2·cells) upstream reads — keep bboxes modest
  (full Gale AOI ≈ 7 700 cells ≈ ~90 m pitch).

## 5. Configuration (env, `RISK_` prefix — see `.env.example`)

`RISK_DATASOURCE_MODE` = `synthetic` (default, deterministic fakes, no
upstreams) | `http` (MS3 `:8003`, MS4 `:8004`) | `unavailable` (all reads
fail → factors `available:false`, reads → 502). Catalog:
`RISK_CATALOG_PATH` → `RISK_SEED_CATALOG_PATH` fallback (SQLite built by
`python -m app.ingest`). Other knobs: `RISK_DEFAULT_SOL` (1360),
`RISK_DEFAULT_VEHICLE_PROFILE`, `RISK_MAX_*`, `RISK_SAMPLING_STEP_M`,
`RISK_UPSTREAM_TIMEOUT_S`/`_RETRIES`, `RISK_CONFIG_DIR`, `RISK_LOG_LEVEL`.

## 6. For Routing (MS6) specifically

- MS6 already computes routes with the Javi optimizer (cost incl. dose).
  MS5 is complementary: score **candidate polylines** (e.g. MS6 alternates)
  via `/risk/evaluate`, or annotate MS6's chosen route per segment
  (`factor_scores`, `warnings`, `restrictions`, `local_time_hour`).
- To compare N candidates cheaply, evaluate them sequentially — each call
  is one batched MS4 + ≤5 MS3 upstream reads (~0.05 s synthetic for ~100
  segments). `POST /risk/path/batch` remains an optional Phase-7
  extension, not committed.
- If MS6 wants MS5's predicted tilt/soil per segment, they are **not** in
  the SPEC response; only `restrictions` expose derived blocking reasons.
  Requesting richer per-segment diagnostics is a future additive field —
  raise it as a SPEC/contract change, not silently.

## 7. Deployment status & what's needed

- **Done & verified offline:** all endpoints in `synthetic` mode with the
  real REMS/RAD SQLite catalog (this env has no docker/network services);
  `unavailable` mode degrades correctly (502 reads, `available:false`
  factors); full suite 293 passed / 3 skipped (live-upstream tests
  auto-skip).
- **Deferred (needs docker):** `docker build` of `risk-assessment/Dockerfile`,
  compose run against real MS3/MS4 containers, live integration re-run.
- **Compose:** no root `docker-compose.yml` exists yet — each service ships
  a standalone snippet. `risk-assessment/docker-compose.yml` uses
  root-relative paths (`build: ./risk-assessment`, `./data/...` volumes)
  so it merges cleanly into a future root compose; standalone use:
  `docker compose --project-directory . -f risk-assessment/docker-compose.yml up`.
  For the merged stack MS5 needs env `RISK_DATASOURCE_MODE=http`,
  `RISK_RASTER_BASE_URL=http://raster-service:8003`,
  `RISK_TERRAIN_BASE_URL=http://terrain-analysis:8004` plus the catalog
  volume mounts already in the snippet. No changes to other services'
  contracts were required (see `UPSTREAM_REQUESTS.md` — none open).
