# MS5 — Risk Assessment Service: Implementation Plan

> **Plan path in repo:** `docs/risk-assessment/IMPLEMENTATION_PLAN_RISK_ASSESSMENT.md`
> **Service directory to create:** `risk-assessment/` (python package `app`, same layout as `terrain-analysis/`)
> **Scope:** Mars only. MVP region: **Gale crater** (the only region with real data in `data/gale/`).
> **Audience:** an AI coding agent working autonomously, with a human reviewer at the gates marked **[GATE]**.

---

## 0. How to use this document

### 0.1 Rules of engagement

1. **Read before writing.** Complete Phase 0 before creating any code. Do not skip it.
2. **Authority order when documents conflict:**
   `docs/SPEC_MS5_RISK_ASSESSMENT.md` > `docs/DECISIONS.md` > `docs/ARCHITECTURE.md` > this plan.
   Apply every behavior and contract detail stated by the SPEC. Where it is silent, preserve the original plan below. If a plan addition changes the published API, identify it as a plan extension and get it approved at Gate 1; do not present it as a SPEC requirement.
3. **Contract first.** No endpoint logic before the OpenAPI contract is written and reviewed (Phase 1 gate).
4. **Do not modify other services** (`raster-service/`, `terrain-analysis/`, `location-service/`, `routing-engine/`, `science/`). If you need a change there, write it down in `docs/risk-assessment/UPSTREAM_REQUESTS.md` and continue with a fake/synthetic adapter.
5. **No network access at runtime or in tests.** The whole project is offline-first.
6. **Mirror existing conventions.** `terrain-analysis/` and `raster-service/` are the reference implementations for layout, naming, error handling, settings, Docker, and tests. When in doubt, open the equivalent file there and copy its style.
7. **Small verifiable steps.** After each task: run the tests, update the relevant `README.md`, commit. Never leave the suite red.
8. **Record assumptions.** Every non-obvious modelling choice (thresholds, weights, formulas) goes into `docs/DECISIONS.md` with its source (SPEC, Javi's science code/data, or an explicitly marked placeholder). Preserve the distinction between an inherited optimizer assumption and a certified rover safety limit.
9. **Code identifiers, docstrings and docs in English.** Data file names and column names stay in their original Spanish.

### 0.2 Reading list (Phase 0, in this order)

| # | File | Why |
|---|------|-----|
| 1 | `AGENTS.md`, `CLAUDE.md`, `docs/ai/agentes.md`, `docs/ai/USO-DE-IA.md`, `docs/ai/plantilla-AGENTS-servicio.md` | Project rules for AI agents; template for this service's own `AGENTS.md` |
| 2 | `docs/ARCHITECTURE.md`, `docs/DECISIONS.md` | System-level decisions |
| 3 | `docs/SPEC_MS5_RISK_ASSESSMENT.md` | **Authoritative spec for this service** |
| 4 | `docs/SPEC_MS3_RASTER.md`, `docs/SPEC_MS4_TERRAIN_ANALYSIS.md` | Upstream contracts MS5 will consume |
| 5 | `docs/data/HANDOFF_SOFTWARE.md`, `docs/data/SETUP_EQUIPO_SOFTWARE.md`, `docs/data/EJEMPLO_API_RESPUESTA.json`, `DATA_SOURCES.md` | What the data team delivered and how they expect it to be used |
| 6 | `terrain-analysis/` (all `README.md` files, `app/main.py`, `app/composition/`, `app/core/config/settings.py`, `app/infrastructure/datasources/http_raster_datasource.py`, `tests/`) | Reference implementation to mirror |
| 7 | `raster-service/app/features/{point_query,path_sampling,window_read,datasets}` + `tests/unit/test_architecture.py` | Upstream endpoints; architecture-test pattern |
| 8 | `location-service/src/location_service/ingest/`, `config/*.yaml`, `tests/contract/test_openapi.py` | Pattern for offline ingestion + YAML config + contract test |
| 9 | `science/README.md`, `science/motor_rutas_adaptativo.py`, `science/optimizador_rutas.py`, `science/crs_marte.py` | Scientific constants, units, CRS conventions the science team already used |

**Deliverable of reading:** a short note `docs/risk-assessment/PHASE0_NOTES.md` listing: coordinate convention (lon 0–360 vs ±180, planetocentric vs planetographic), URL prefix and error-body format used by MS3/MS4, ports used by each service, the schemas confirmed below, and any remaining conflict with this plan. The requested plan location is `docs/risk-assessment/` (hyphenated).

---

## 1. Mission and scope

**Responsibility:** implement the MS5 contract in `docs/SPEC_MS5_RISK_ASSESSMENT.md` and the additional capabilities retained from this plan where the SPEC is silent. The SPEC-defined behavior is mandatory; plan extensions are identified separately and reviewed at Gate 1.

### 1.1 In scope (MVP)

- Risk assessment for a **point** and a **path (route polyline)** on Mars/Gale.
- The SPEC factor catalog: **slope**, **roughness**, **dunes**, **temperature**, and **radiation**. A missing factor dataset is reported as unavailable and excluded from weighting.
- Explainable output with SPEC fields plus the plan's additive confidence, provenance, data-quality and assumptions details.
- `sol` and `hora` select the environmental profile as defined by the SPEC. Use configurable default sol `1360` (matches MS6 and delivered Gale data); choose the nearest available sol in the factor datasets being used and echo the selected sol. For path evaluation, `hora` defaults to `12`. For point queries, if no hour is supplied, evaluate all hourly bins and return the worst case.
- Preserve the original plan's vehicle profiles and limits, restrictions as additional response details, area assessment, metadata, and optional batch evaluation. These are additions to—not replacements for—the SPEC API.
- Default vehicle profile: `baseline_mars_rover`, a generic Gale surface-rover profile, not a claim about a specific flight rover. Seed it from the explicit baseline parameters in `science/optimizador_rutas.py` (nominal speed, tilt/slope passability, uncertainty margin, thermal band, solar window and dune speed factor); preserve their formulas and mark them as inherited optimizer assumptions, not certified flight limits. Do not leave those already-defined values as arbitrary placeholders.
- Core is the orchestration boundary: it coordinates MS6 routing and MS5 risk evaluation. MS5 does not call MS6; MS6's existing API/contract is not changed by this plan.
- Offline operation: all environmental statistics precomputed into a local SQLite artifact.

### 1.2 Out of scope (MVP)

- Route computation, A*/Dijkstra, cost surfaces (→ MS6 Routing Engine).
- Computing slopes or DEM derivatives (→ MS4). MS5 consumes slope from MS4 and raster factors from MS3; it never recomputes them.
- Downloading datasets (→ MS2). Reading GeoTIFFs for production queries (→ MS3).
- Route-time dose accumulation and total traversal dose (MS6 owns this in the current SPEC), generated risk rasters, multi-planet support, real-time dust-storm/weather feeds, ML prediction, and Earth↔Mars calendar conversion (Ls/sol from UTC).
- Plan extensions such as area assessment, vehicle profiles and batch evaluation are not part of the published SPEC contract; implement them as additional capabilities without changing SPEC-defined behavior.

### 1.3 Honest limits of the data (must be reflected in the API)

- **Radiation is almost spatially uniform inside Gale.** The SPEC treats radiation as a dose rate selected by `sol`/`hora`; do not accumulate dose over route duration in MS5 (that remains MS6's job).
- **Temperature varies mostly with local time and season**, not with position inside a 90 m grid.
- **Terrain and raster factors are spatial** at the delivered grid resolution (about 90 m).
- Therefore the path evaluation must return per-segment risk and an overall weighted risk, as specified by the SPEC.

---

## 2. Position in the system

```
Core ──► Risk Assessment (MS5) ──► Raster Service (MS3)      [HTTP: environmental raster factors]
                               └─► Terrain Analysis (MS4)    [HTTP: slope profile]
                               └─► local risk_catalog.sqlite [hourly environmental profiles]
Core ──► Routing Engine (MS6) [route]
     └─► Risk Assessment (MS5) [point/path/area assessment of returned/candidate geometry]
```

- MS5 **never** opens another service's SQLite and, at runtime, **never** reads GeoTIFFs directly. Raster access = MS3 HTTP only.
  *(Note: MS4 has a direct `geotiff_datasource` / `grid_backed_raster_datasource` for pragmatic reasons plus a parity test against MS3. MS5 should not repeat that; it is a deliberate decision — log it as D-MS5-1.)*
- Every upstream is behind a **port**, with three adapters: `http` (real), `synthetic` (deterministic, for tests and standalone dev), `unavailable` (always raises → exercises the upstream error path). Selected via settings, exactly like MS4.
- MS5 must start, pass `/health` and answer from `synthetic` mode without MS3/MS4 running.
- **Orchestration decision:** Core is the only service coordinating the user-facing flow: it calls MS6 for a route, then MS5 to assess that geometry and combines the results. MS5 does not call MS6, and the current MS6 contract remains unchanged. This MVP adds risk assessment/warnings to the returned route; feeding MS5 scores back into MS6's optimizer requires a later MS6-owned integration and is not implied here.
- MS4 path input is `POST /terrain/profile` (`path`, optional `sample_distance_m`) and returns ordered samples with `distance_m` and `slope_deg`. MS3 path sampling is `POST /raster/{dataset}/sample` (`band`, `path`, optional `sample_distance_m`); call it for each required raster band (`rugosidad_m`, `distancia_duna_m`, `fraccion_oscura`, and `inercia_termica_tiu`). Both services sample at arc-length points; use a common 90 m step for MS5 so values align to the delivered grid, and keep the MS4/MS3 contracts unchanged.

---

## 3. Data: what MS5 needs and where it comes from

### 3.1 Inventory (verify every row in Phase 0)

| Source (repo path) | Expected content **[VERIFY]** | Use in MS5 | Runtime access |
|---|---|---|---|
| `data/gale/raw/ambiental/rems_resumen_horario.xlsx` | REMS hourly summaries: air/ground temperature, pressure, humidity, maybe UV; some time reference (sol, LMST, Ls?) | **Thermal climatology** by local-time bin (and season bin if Ls available); pressure as optional radiation covariate | **Ingest only** → SQLite |
| `data/gale/raw/ambiental/rad_dosis_observaciones.xlsx` | RAD dose-B/dose-E observations by sol and fractional LMST hour, in µGy/h | **Dose-E hourly background profile**, prepared with Javi's per-sol filter and hourly aggregation | **Ingest only** → SQLite |
| `data/gale/processed/rejilla_ruta_90m.tif` | 72×105 grid; documented bands: `pendiente_grados`, `rugosidad_m`, `fraccion_oscura`, `inercia_termica_tiu`, `albedo`, `distancia_duna_m` | Raster factors are read through MS3; slope is obtained through MS4 as required by the SPEC | **Via MS3 HTTP only** |
| `data/gale/processed/modelos_por_suelo.json` | Per-soil regression models predicting observed rover `tilt_real_grados`; four terrain classes plus a global model, with predictor ranges, adjusted R² and residual sigma | Use the supplied classes/model for the optional vehicle-tilt restriction and explainability; it is not the MS4 `slope` factor or a slope limit | Ingest model/config metadata only if the optional restriction is implemented; clip predictors to each model's published range as the canonical optimizer does |
| `data/gale/processed/gale_matriz_calibracion.xlsx`, `gale_puntos_quimica.xlsx` | Calibration matrix with rover waypoints, observed tilt, terrain predictors and `nivel_riesgo_real`; chemistry/soil points | Calibration and non-contractual sanity checks; preserve the risk-label definition and source context | Phase 0 inspection; do not map these labels directly to SPEC scores/levels |
| `data/gale/processed/ruta_{esmectitas,hematita,tridimita}.geojson` + `_resumen.json` + `_tramos.xlsx` | Three already-optimised science routes with per-segment attributes | **Golden test paths** for the path endpoint; sanity comparison with segment attributes | Test fixtures (copy small excerpts into `tests/fixtures/`) |
| `data/gale/processed/Bitacora_Calidad_Marte.xlsx` | Data quality log | Phase 0 context for interpreting input quality; the SPEC does not require a separate response field for it | Inspect; ingest only if needed internally |
| `data/gale/raw/pe_msl_vectores.json` | Unknown (MSL-related vectors; possibly positions/traverse) | Identify in Phase 0. May serve as traverse truth or ephemeris | Decide in Phase 0 |
| `data/gale/raw/gazzeter/*` / `data/processed/mars/location/location_catalog.sqlite` | Place names | **Not used by MS5** (Location Service owns it) | — |
| MS4 API (`/terrain/profile`) | Slope in degrees along a profile | `slope` factor | HTTP |
| `science/*.py`, `science/README.md` | Javi's canonical optimizer, model fitting and calibration-label rules | Reuse the explicit Gale baseline values/formulas below for plan extensions; document source/version and do **not** treat them as certified vehicle limits or replace SPEC scoring | Reading only |

**Already verified from the checked-in Gale package (record these facts in `DATA_INVENTORY_MS5.md`):**

- `rems_resumen_horario.xlsx` has 48 observations: sols 1360 and 2140, each with LMST hours 0–23. It contains ground temperature mean/min/max and air temperature mean in kelvin, plus pressure and UV. Javi's optimizer scores thermal stress from hourly ground-temperature mean against `BANDA_TERMICA_OPERATIVA_K = (230, 290)` K.
- `rad_dosis_observaciones.xlsx` has 350 observations across sols 1360, 2140, 3290, and 4710. The columns include fractional `hora_lmst`, `dosis_b_uGy_h`, `dosis_e_uGy_h`, and source unit `uGy/hour`.
- Therefore sol 1360 is a usable configurable default (`RISK_DEFAULT_SOL`, default 1360). Select the nearest available sol independently for each requested environmental dataset, matching `MapaMision` (`sol_rad` and `sol_rems`); retain the requested/reference sol and expose each factor's actual selected sol in provenance. Do not require a shared sol where one dataset has no observation.
- `modelos_por_suelo.json` contains four terrain classes and regressions predicting `tilt_real_grados` (including a global model). Its soil-class rules are: `arena_dunas` when `distancia_duna_m == 0` or `fraccion_oscura >= 0.5`; otherwise `lecho_rocoso_firme` when `rugosidad <= 0.60`, `pendiente_grados <= 7.0`, and `albedo >= 0.2294`; otherwise `rocoso_fracturado` when `rugosidad >= 1.10`, `pendiente_grados >= 8.0`, or `albedo < 0.2291`; otherwise `regolito_compacto`. Preserve this precedence and the model's predictor clipping/ranges. Predicted tilt is not the MS4 slope factor.
- Javi's model/optimizer baseline explicitly uses: nominal speed `1000 m/h`; speed factor `max(0.1, 1 - predicted_tilt/30)`; dune multiplier `1 - 0.60` (retain 40% of computed speed); blocked if DEM slope `>= 25°`, predicted tilt `>= 20°`, or `predicted_tilt + 1.96*sigma > 20°`; thermal operating band `230–290 K`; and motion window `7 <= LMST < 17`. These are inherited Gale optimizer assumptions for the generic profile, not certified capabilities of a flight rover. The motion window is MS6's wait/scheduling rule, not an MS5 terrain-blocking restriction.
- The optional tilt model's terrain predictors are supplied through the same aligned MS4/MS3 samples: MS4 slope for `pendiente_grados`, MS3 roughness/albedo/thermal inertia, and the mapped soil/dune inputs; ambient predictors use the selected-sol hourly REMS mean and filtered RAD-E profile. Clip predictors to the model's stored ranges and use its global model only as Javi's fallback for a class without a fitted model. If a required predictor is unavailable, mark the tilt estimate/restriction unavailable rather than substituting zero.
- Javi's calibration labels (`nivel_riesgo_real`) use documented approximate incident-sol ranges, observed `tilt_real_grados >= 12°` as medium and `>= 20°` as high, plus local slope `>= 15°` or a mapped dune field as medium when no higher label applies. Preserve them only as calibration/sanity evidence; they are not the SPEC's normalized factors or `low/medium/high/critical` score boundaries.
- `ruta_*_tramos.xlsx` includes observed segment soil labels, distance, LMST start/end, slope/inclination, dose and ground-temperature ranges. These are useful golden-test/context data, not proof of vehicle safety limits.

### 3.2 Phase 0 data-inspection checklist (produce `docs/risk-assessment/DATA_INVENTORY_MS5.md`)

For **each** file above, record: file/sheet/key structure, column names with **units**, row count, time coverage (sols, dates, Ls), time reference used (UTC, LMST, sol+hour?), missing-value convention, obvious outliers, and a 5-row sample. Then answer:

1. Can the workbook rows be keyed to `sol` and LMST `hora` as the SPEC requires? If not, report the affected environmental factor as unavailable; do not silently substitute a different time basis.
2. Is **Ls (season)** available? This is not required by the SPEC; record it as optional context only and do not add seasonal API behavior without approval.
3. RAD unit and time basis are verified in the delivered workbook: dose-rate columns are `dosis_b_uGy_h` and `dosis_e_uGy_h`, with source unit `uGy/hour`, and observations carry `sol` and LMST hour. Use `dosis_e_uGy_h`, matching `MapaMision`; do not combine channels.
4. Sanity band for REMS temperatures: air/ground between roughly −150 °C and +50 °C. Outside → parse/unit error.
5. Verify the documented six raster bands (`pendiente_grados`, `rugosidad_m`, `fraccion_oscura`, `inercia_termica_tiu`, `albedo`, `distancia_duna_m`) and their nodata values against MS3 metadata. The factor API follows the SPEC names; do not assume there is a soil/class band.
6. Record the supplied soil-class rules, model predictors/ranges, adjusted R² and residual sigma from `modelos_por_suelo.json`. Use the model only for predicted rover tilt and the optional vehicle restriction; use MS4 `slope_deg` for the SPEC `slope` factor. Apply Javi's explicit optimizer limits in the generic vehicle profile, with their inherited-assumption caveat in §3.1; do not create a sixth factor.
7. `*_tramos.xlsx` may be used for a non-contractual sanity check. Do not require per-segment elapsed time, dose accumulation, or soil limits in MS5; route-time accumulation belongs to MS6.
8. What is `pe_msl_vectores.json`?
9. What does `Bitacora_Calidad_Marte.xlsx` flag as unreliable (datasets, periods, regions)?
10. What coordinate convention do GeoJSONs and the grid use? (Longitude 0–360E vs −180–180; planetocentric vs planetographic.) **MS5 must accept and emit the same convention as MS3/MS4.** Use the project's Mars CRS (`IAU_2015:49900`) where a CRS is required; never use terrestrial EPSG codes.

**[GATE 0]** Present `DATA_INVENTORY_MS5.md` + `PHASE0_NOTES.md` to the human. Confirm MS3/MS4 contracts and coordinate behavior before implementation. The RAD channel, workbook time/unit coverage, soil classes, model interpretation and inherited optimizer parameters are specified above from Javi's checked-in code/data; document their provenance and caveat, rather than reopening them as unanswered decisions. Missing optional data means its factor is unavailable per the SPEC, not that the API or risk model should be expanded.

---

## 4. Risk model

Design principle: **simple, explainable, configurable, testable.** The SPEC's factor IDs, weights, level boundaries, unknown-risk rule and route-time dose boundary are authoritative. Retain the plan's vehicle, restriction, confidence, provenance and area capabilities only as additive behavior; they must not alter the SPEC weighted-score calculation.

### 4.1 Common concepts

- Each available factor has a normalized `score ∈ [0, 1]`; an unavailable factor has `available: false` and does not participate in the weighted mean.
- Overall risk is the weighted mean of available factor scores. If none are available, return `overall_risk: null` and `risk_level: "unknown"`; never treat missing data as safe.
- Risk levels follow the SPEC: `low` < 0.25, `medium` 0.25–<0.5, `high` 0.5–<0.75, `critical` ≥ 0.75. Do not use the original plan's `moderate` label.
- Emit the SPEC warning codes when configured factor thresholds are crossed.
- Preserve the original plan's `confidence ∈ {high, medium, low}` and provenance/data-quality/assumptions details as additional explanatory fields.
- A selected vehicle profile may produce additional restrictions (code, blocking, message, factor, value, limit). Per the SPEC weighted-average rule, restrictions are reported separately and do not silently replace the computed weighted risk or force it to 1.0.
- Preserve Javi's optimizer clock convention for the optional path-time summary: LMST is represented by 24 numeric hourly bins and wraps modulo 24; derive elapsed hours from distance and the profile's effective speed in `m/h`. Do not add a separate `SECONDS_PER_SOL` conversion that is absent from the canonical optimizer. MS5 still reports radiation rate only and never integrates route dose.

### 4.2 Factors

**Factor catalog and sources (SPEC §3):**

| Factor | Source | Required behavior |
|---|---|---|
| `slope` | MS4 `/terrain/profile` | Score MS4 slope in degrees using configurable thresholds. Use the SPEC's illustrative 0 at `<=5°`, 1 at `>=30°` linear normalization as the initial baseline; emit the Javi-aligned warning at `>=15°` and apply the generic-profile traversal restriction at `>=25°`. Reuse this aligned MS4 slope as `pendiente_grados` for Javi's soil classification/tilt model; do not substitute predicted rover tilt for the SPEC slope factor. |
| `roughness` | MS3 raster band `rugosidad_m` | Score using configured thresholds. Javi's `<=0.60` and `>=1.10` values classify soil/model regimes; they are not published roughness risk-score thresholds. |
| `dunes` | MS3 bands `distancia_duna_m`, `fraccion_oscura` | Use Javi's mapped-dune condition (`distancia_duna_m == 0`) or dark fraction `>=0.5` for the dune-soil class. Emit the initial mapped-dune warning for `distancia_duna_m == 0`, matching the calibration-label rule; any broader proximity threshold remains configurable because Javi's code does not define one. |
| `temperature` | REMS workbook and `inercia_termica_tiu` context | Select the hourly ground-temperature mean by the independently selected REMS sol and LMST hour; preserve REMS min/max as source summaries. Use Javi's operational band `230–290 K` for thermal excess/warning and convert to Celsius only at an API/config boundary that requires it. Javi defines the excess formula, not the full [0,1] risk-score scale; keep that normalization separately configurable. |
| `radiation` | RAD workbook | Select the hourly profile by requested `sol`/`hora`; express rate in µGy/h. Do not integrate it over route duration in MS5. |

For `radiation`, use `dosis_e_uGy_h`, matching the canonical optimizer. Match its profile preparation: per sol, retain observations at or above `0.7 * median(dosis_e_uGy_h)`, floor fractional LMST to the integer hour, and take the hourly mean. For an empty hour in a sol that otherwise has valid observations, use that selected sol's mean rate (as `MapaMision` does) and mark the fallback in provenance/confidence. This filter is the optimizer's background-profile rule, not an SEP detector or MS5 alert threshold. Do not combine with `dosis_b_uGy_h`.

Use the SPEC's suggested warning vocabulary: `STEEP_SLOPE_NDEG`, `BAGNOLD_DUNES_NEARBY`, `HIGH_ROUGHNESS`, `EXTREME_COLD_ZONE`, and `HIGH_RADIATION_RATE`. Exact threshold values must be configurable and sourced or explicitly marked as placeholders. Nodata/missing values produce `available: false`, not a zero score.

Retain the original plan's calculation detail where the SPEC is silent, but derive it from Javi's available inputs: store the selected per-hour radiation rate and source coverage; do not invent SEP-event thresholds or percentiles from the filtered profile. Preserve REMS mean/min/max by sol/hour; they are descriptive hourly summaries, not p05/p95. A radiation alert threshold remains configurable under the SPEC and is separate from the optimizer's 0.7-median filter. Radiation is always a rate warning in MS5; do not integrate it over route time.

### 4.3 Composite

Compute each point/segment risk as `Σ(w_i · score_i) / Σ(w_i)` over available factors only, using the SPEC defaults: slope 0.4, dunes 0.2, roughness 0.15, temperature 0.15, radiation 0.1. Do not use the former terrain/thermal/radiation weights or a dominance multiplier. If the denominator is zero, return the SPEC's unknown-risk response. For path `overall_risk`, use the distance-weighted mean of segment risks (segment length / total path length). Keep plan restrictions separate from the factor score formula.

### 4.4 Path aggregation

Evaluate the requested polyline using the SPEC path contract: return per-segment factor scores, availability and warnings, plus `overall_risk` as the distance-weighted mean of segment risks. Use one batched MS4 profile call where its existing contract supports it.

Retain the original plan's additional path details: sample at configurable `sampling_step_m` (default grid resolution, 90 m); calculate `distance_m` and elapsed hours using the vehicle profile's effective speed, seeded from Javi's `1000 m/h` nominal value and terrain modifiers; advance LMST in the optimizer's 24-bin convention; include per-segment local time, summary mean/p95, dominant factor, total distance/duration, hotspots and restrictions. Select the nearest available sol independently for each environmental dataset and keep each dataset's selected sol fixed along the path; advance/wrap LMST across samples. Keep `segments` in the response as required by the SPEC. Radiation remains a per-segment rate selected at the segment's LMST hour; do not calculate cumulative dose or compare a route dose budget in MS5. For thermal summary, use Javi's hourly-mean excess formula `max(0, 230 - T_mean) + max(0, T_mean - 290)` and integrate excess as `K·h` over segment duration; do not claim exact minutes outside the band or percentile margins from hourly summaries.

### 4.5 Response details

Return all fields defined by the SPEC, including segment `factor_scores` with `available`, warning codes, and `warnings_summary`. Also retain the original plan's additive `confidence`, `provenance`, `data_quality_notes`, and `assumptions` fields; their shape must not change or replace any SPEC field.

---

## 5. Configuration files (`risk-assessment/config/`)

| File | Content |
|---|---|
| `vehicle_profiles.yaml` | Default `baseline_mars_rover` seeded with Javi's `1000 m/h` nominal speed, tilt speed formula (`max(0.1, 1 - tilt/30)`), dune speed multiplier `0.40`, slope block `>=25°`, predicted-tilt block `>=20°` or `tilt + 1.96*sigma >20°`, and thermal band `230–290 K`. These are configurable inherited optimizer assumptions, not certified flight limits. Keep the `[7,17)` LMST motion window as MS6 wait/scheduling behavior, not an MS5 blocking restriction. Keep dose budget unset; dose accumulation belongs to MS6. |
| `risk_thresholds.yaml` | SPEC normalization and level boundaries; Javi-aligned slope warning `>=15°`, profile blocking limits, dune class/warning conditions, temperature band and configurable radiation warning threshold. Keep soil-class thresholds distinct from factor-score thresholds. Preserve SPEC risk-level boundaries. |
| `risk_weights.yaml` | SPEC factor weights and model version: slope 0.4, dunes 0.2, roughness 0.15, temperature 0.15, radiation 0.1. No dominance multiplier. |
| `environment_columns.yaml` | column mapping for the REMS/RAD workbooks (mirrors `location-service/config/gazetteer_columns.yaml`): source column → canonical name, unit, conversion |

All loaders validate with pydantic and fail fast on startup with a clear message.

---

## 6. Internal architecture

Same hexagonal/feature layout as `terrain-analysis/`. Dependency rule (enforced by `tests/unit/test_architecture.py`, copy the pattern from `raster-service`):

`features/*/presentation → features/*/application → core/{domain,ports}`; `infrastructure → core/ports`; `composition` is the only place that wires concrete adapters; **`core/domain` imports nothing from FastAPI, pydantic-settings, httpx, sqlite3, or openpyxl.**

```
risk-assessment/
├── AGENTS.md                      # from docs/ai/plantilla-AGENTS-servicio.md
├── CLAUDE.md
├── Dockerfile
├── pyproject.toml
├── README.md
├── config/                        # §5
├── data/seed/                     # risk_catalog_seed.sqlite + ingest_report.json (committed, like location-service)
├── app/
│   ├── main.py                    # create_app(), router registration, error handlers
│   ├── composition/
│   │   ├── dependencies.py        # settings → adapters → use cases (split per feature like MS4 if it grows)
│   │   └── README.md
│   ├── core/
│   │   ├── config/settings.py     # pydantic-settings, env prefix RISK_
│   │   ├── domain/
│   │   │   ├── geo_point.py  bounding_box.py  distance_calculator.py  path_sampler.py # semantics aligned with MS3/MS4
│   │   │   ├── local_solar_time.py           # Mars-hour wrap-around and sol/time advancement
│   │   │   ├── risk_level.py               # enum + score→level mapping
│   │   │   ├── factor_assessment.py        # score, availability, value/unit/threshold
│   │   │   ├── restriction.py               # optional plan extension; does not override weighted risk
│   │   │   ├── vehicle_profile.py           # optional plan extension
│   │   │   ├── radiation_risk.py
│   │   │   ├── temperature_risk.py
│   │   │   ├── slope_risk.py
│   │   │   ├── roughness_risk.py
│   │   │   ├── dunes_risk.py
│   │   │   ├── bounding_box.py              # area extension
│   │   │   ├── risk_aggregator.py          # §4.3 / §4.4
│   │   │   └── README.md
│   │   ├── errors/{exceptions.py,error_handlers.py}   # same error body as MS3/MS4
│   │   └── ports/
│   │       ├── terrain_source.py           # point / profile terrain observations (MS4)
│   │       ├── raster_source.py            # layer sampling + dataset metadata (MS3)
│   │       ├── environment_repository.py   # climatology lookups (SQLite)
│   │       └── vehicle_profile_repository.py
│   ├── features/
│   │   ├── point_assessment/{application,domain,presentation}
│   │   ├── path_assessment/{application,domain,presentation}
│   │   ├── area_assessment/{application,domain,presentation} # plan extension
│   │   ├── vehicle_profiles/{application,presentation}       # plan extension
│   │   ├── factors/presentation              # available factors and data coverage
│   │   ├── meta/presentation                 # plan extension
│   │   └── health/presentation
│   ├── infrastructure/
│   │   ├── datasources/
│   │   │   ├── http_terrain_source.py   http_raster_source.py
│   │   │   ├── synthetic_terrain_source.py  synthetic_raster_source.py
│   │   │   └── unavailable_terrain_source.py  unavailable_raster_source.py
│   │   └── repositories/
│   │       ├── sqlite_environment_repository.py
│   │       ├── yaml_vehicle_profile_repository.py
│   │       └── guarded_call.py            # timeout/retry/translate to UpstreamUnavailable (copy MS4 pattern)
│   └── ingest/                            # offline preparation CLI (python -m app.ingest)
│       ├── __main__.py  config_loader.py  rems.py  rad.py  validate.py  writer.py
└── tests/                                 # §10
```

Conventions: one use case per file in `application/`, dataclass/pydantic schemas only in `presentation/*_schemas.py`, mapper functions between domain objects and schemas (`*_mapper.py`), every package has a `README.md` stating its responsibility (as in the existing services).

---

## 7. API contract

The mandatory API is `docs/SPEC_MS5_RISK_ASSESSMENT.md` §3–§7. Preserve its request fields, response fields, status codes, factor IDs, defaults, and examples. The following plan extensions are additional endpoints/fields not specified there; document both contracts in the OpenAPI and review the additive schemas with Core/Routing at Gate 1 without changing SPEC-defined behavior.

Contract artifacts to produce in Phase 1:
- `docs/api-contracts/risk-assessment-service.md` (human-readable; follow `location-service.md`)
- `packages/contracts/risk-assessment/openapi.yaml` (machine-readable; checked against the app's generated OpenAPI)

### 7.1 Endpoints and inputs

| Method & path | Purpose |
|---|---|
| `GET /health` | Report MS4/Raster connectivity. |
| `POST /risk/evaluate` | Evaluate a polyline. Required: `path` (at least two `{lat, lon}` points). Optional: `factors` (default all available), `sol` (nearest available sol used and echoed), `hora` (LMST 0–23, default 12), and `body` (default `mars`). |
| `GET /risk/point?lat=…&lon=…` | Evaluate risk at one point. |
| `GET /risk/factors` | List the SPEC factor catalog and data coverage/availability. |
| `GET /risk/vehicle-profiles` | Plan extension: list configured vehicle profiles and limits. |
| `GET /risk/meta` | Plan extension: expose thresholds/weights, model version, provenance and coverage. |
| `POST /risk/area` | Plan extension: aggregate risk over a bbox with level counts, blocked fraction, statistics and hotspots. |
| `POST /risk/path/batch` | Optional plan extension: evaluate multiple candidate paths in one call. |

The five factor IDs are exactly `slope`, `roughness`, `dunes`, `temperature`, and `radiation`. MS4 supplies slope; MS3 supplies the raster factors; local Excel-derived profiles supply temperature and radiation. The API base path is `/risk`. Use the coordinate convention of MS3/MS4, established in Phase 0.

For `GET /risk/point`, preserve the original plan's optional time/profile behavior using SPEC terminology: accept optional `sol` and `hora` (not a competing `local_time_hours`). If `hora` is omitted, evaluate all hourly bins for the selected/default sol and return the worst case; include a `by_hour` summary only when `include_hourly=true`. If `sol` is omitted, use configurable `RISK_DEFAULT_SOL` (default `1360`). This is additive to the SPEC point query, which only names `lat` and `lon`. For `POST /risk/evaluate`, the SPEC default `hora=12` applies and omitted `sol` resolves through the same configurable default.

The path request may additionally accept `vehicle_profile` (default `baseline_mars_rover`), `speed_mps` (optional override, converted to `m/h` for the Javi profile formulas), and `sampling_step_m` (default 90 m; matches MS3 dataset resolution). Treat `hora` as departure LMST and advance by elapsed hours in Javi's 24-bin modulo-24 convention. Select the nearest available sol independently per environmental dataset; keep each selected sol fixed along the path and expose it in factor provenance. Path summaries may include `max_level`, `mean_score`, `p95_score`, `dominant_factor`, `total_distance_m`, `total_duration_s`, `end_local_time_hours`, `hotspots`, and `blocking_segments` as additive plan fields. Do not include cumulative radiation dose.

The area extension accepts a bbox, `sol`, `hora`, `vehicle_profile`, and capped `max_cells` (default e.g. 250,000); it returns level counts, blocked fraction, mean/p95 risk, per-factor statistics and hotspots, not a per-cell raster.

### 7.2 Responses and aggregation

The SPEC fields are mandatory. `POST /risk/evaluate` returns `overall_risk`, `risk_level`, per-segment `factor_scores` (`score` and `available`), segment `warnings`, and `warnings_summary`. `GET /risk/point` returns the point coordinates, `risk`, `risk_level`, factor scores, and warnings. Each segment's risk is the weighted mean of its available factors using the SPEC weights. The path `overall_risk` is the distance-weighted mean of segment risks; no available factors means `overall_risk: null` and `risk_level: "unknown"`.

Retain the original plan's additive fields `confidence`, `provenance`, `data_quality_notes`, `assumptions`, and (when a profile is selected) `restrictions`; these do not replace or redefine SPEC fields. Keep `segments` in the SPEC response and do not let an option suppress required output. Do not return cumulative dose from MS5: the SPEC assigns route-time dose accumulation to MS6.

### 7.3 Errors and partial data

Use the shared MS3/MS4 error-body format, confirmed in Phase 0. Follow the SPEC status codes: `400` for invalid path/factors, `404` for no coverage, and `502` when MS4 or Raster is unavailable. Retain the original plan's `503 CLIMATOLOGY_UNAVAILABLE` for a missing/corrupt local catalog, `404 VEHICLE_PROFILE_NOT_FOUND` for the optional profile extension, `422 AREA_TOO_LARGE` for an oversized area request, and sanitized `500 INTERNAL_ERROR`, subject to shared error-format conventions. Missing factor data is represented with `available: false` and excluded from weighting; no available factors yields the unknown-risk response, never a zero score.

---

## 8. Offline ingestion pipeline (`python -m app.ingest`)

Mirrors `location-service/src/location_service/ingest/`.

1. **Load** REMS and RAD workbooks (path from CLI args / settings; default `data/gale/raw/ambiental/…`) using the column mapping in `config/environment_columns.yaml`.
2. **Normalize**: canonical column names, documented units, `sol` and LMST `hora` where present, nulls → `NULL`. Do not infer a conversion from Earth UTC to Mars `sol`/LMST; that conversion is outside the SPEC.
3. **Validate**: sanity bands (§3.2), duplicate timestamps, monotonic time, negative doses, impossible temperatures. Rejected/flagged rows are counted and listed in the report — never silently dropped.
4. **Aggregate**: retain REMS profiles keyed by sol/hour with the supplied mean/min/max; retain RAD profiles keyed by sol and `floor(hora_lmst)`, filtered to `dosis_e_uGy_h >= 0.7 * per-sol median`, using the hourly mean. For an empty RAD hour in an otherwise valid selected sol, apply the optimizer's per-sol mean fallback and record the fallback. Do not invent percentiles from aggregates or fill missing REMS hours; mark an unavailable REMS hour unavailable. The delivered REMS workbook does not provide raw samples for p05/p95 recomputation.
5. Store radiation rate provenance and coverage. The `0.7 * median` filter is Javi's existing optimizer background-profile rule, not an SEP detector or MS5 alert threshold. Keep the MS5 warning threshold separately configurable per SPEC; do not integrate dose over route duration or compare a cumulative dose budget in MS5.
6. **Write** `risk_catalog.sqlite` atomically (temp file + rename) with tables: `thermal_climatology`, `radiation_climatology`, `meta(key,value)` (source files + SHA-256, ingest timestamp, units, bin config, thresholds), `data_quality(dataset, period, note, severity)`.
7. **Report** `ingest_report.json` (counts, ranges, rejected rows, bins with low sample, source hashes).
8. Output to `data/processed/mars/risk/` (consistent with `data/processed/mars/location/`) and a copy to `risk-assessment/data/seed/` for Docker.

The service reads the SQLite **read-only** (`file:…?mode=ro`, `uri=True`). Runtime image does **not** need openpyxl; put it in an `ingest` optional dependency group.

---

## 9. Stack and tooling

| Concern | Choice | Notes |
|---|---|---|
| Language/runtime | Python **3.13** (matches `.pyc` in repo) | Check `pyproject.toml` of MS4 for the exact `requires-python` |
| API | **FastAPI** + **Pydantic v2** | Schemas only in `presentation/` |
| Settings | `pydantic-settings`, env prefix `RISK_` | See §9.1 |
| HTTP client (upstream) | `httpx` (sync or async — **match MS4's `http_raster_datasource.py`**) | Timeouts + bounded retries in `guarded_call.py` |
| Numerics | `numpy` | Hourly profile aggregation, configured score normalization and summary statistics |
| Config files | `PyYAML` + pydantic validation | |
| Catalog | stdlib `sqlite3` | Read-only at runtime |
| Ingest only | `pandas` + `openpyxl` (+ `numpy`) | Read the delivered `.xlsx` workbooks with `pandas.read_excel`; keep these out of runtime dependencies if possible |
| Geospatial libs (`rasterio`/GDAL) | **Not needed** at runtime | MS5 gets raster values via MS3. Allowed only in dev/ingest if Phase 0 needs to inspect the grid |
| Tests | `pytest`, `pytest-cov`, FastAPI `TestClient`/`httpx`, `respx` (mock HTTP) | |
| Quality | `ruff` (lint+format), `mypy` (domain + ports strict) | Use whatever MS3/MS4 already configure |
| Container | `Dockerfile` modelled on MS4; non-root; no network needed at runtime | |

### 9.1 Settings (env vars)

`RISK_DATASOURCE_MODE` (`http|synthetic|unavailable`), `RISK_RASTER_BASE_URL`, `RISK_TERRAIN_BASE_URL`, `RISK_UPSTREAM_TIMEOUT_S`, `RISK_UPSTREAM_RETRIES`, `RISK_CATALOG_PATH`, `RISK_CONFIG_DIR`, `RISK_DEFAULT_SOL` (default `1360`, nearest available sol selected), `RISK_DEFAULT_VEHICLE_PROFILE` (`baseline_mars_rover`), `RISK_MAX_PATH_POINTS` (if needed for request protection), `RISK_MAX_AREA_CELLS`, `RISK_LOG_LEVEL`. Provide `.env.example` entries in the root `.env.example` (do not break others). Pick a free port by checking existing Dockerfiles/compose (suggest 8005 if unused).

---

## 10. Testing strategy

Target: **domain ≥ 95 % line coverage, overall ≥ 85 %**, entire suite runs offline in a few seconds.

```
tests/
├── unit/          # pure domain + config loaders + application with fakes
├── api/           # TestClient with dependency overrides (synthetic adapters)
├── contract/      # generated OpenAPI == packages/contracts/risk-assessment/openapi.yaml
├── integration/   # real catalog + golden routes; real MS3/MS4 only if reachable (skip otherwise)
├── fakes/         # failing_terrain_source.py, failing_raster_source.py, fake_environment_repository.py
└── fixtures/      # tiny REMS/RAD xlsx, tiny catalog sqlite, excerpts of ruta_*.geojson
```

Must-have tests:

- **Domain (hand-computed expected values):** score clamping/monotonicity per factor; level boundaries (exact thresholds); weighted mean over available factors; unknown-risk rule when no factor is available; nearest-sol selection per dataset and `hora` bounds/default; 24-bin LMST wrap-around; Javi's RAD filtering/hour aggregation/empty-bin fallback; thermal excess from hourly mean and the 230–290 K band; soil-class precedence and predictor clipping; tilt-margin and slope restrictions without changing the weighted risk; nodata handling (missing ≠ safe).
- **Ingest:** fixture workbooks → expected filtered hourly dose-E and REMS mean/min/max profiles, including per-sol empty-hour fallback; unit-conversion; sanity-band flagging; rejected-row accounting; idempotent output; atomic write.
- **Architecture test:** forbidden imports per layer (copy from `raster-service/tests/unit/test_architecture.py`).
- **Adapters:** `respx`-mocked HTTP for MS3/MS4 (success, 404, 5xx, timeout → the SPEC's `502` upstream response); synthetic adapters deterministic.
- **API:** every endpoint happy path + each error code (`400`, `404`, `502`); error bodies match the shared error format; `/health` connectivity.
- **Contract:** committed OpenAPI is in sync with the app.
- **API extensions:** if approved at Gate 1, cover vehicle profiles, `meta`, area, confidence/provenance, restrictions and their error cases.
- **Golden routes:** run `ruta_esmectitas`, `ruta_hematita`, `ruta_tridimita` through `/risk/evaluate` (synthetic or real upstream). Assert: runs without error and deterministic; total distance matches `_resumen.json` within tolerance; compare risk/factor coverage with available segment attributes in `_tramos.xlsx` as a non-contractual sanity check.
- **Parity:** coordinate handling agrees with MS3/MS4 for shared vectors; reuse their distance/path sampling rather than copying implementations.
- **Offline test (final gate):** run service + tests with outbound network disabled.

---

## 11. Phased work plan

### Phase 0 — Orientation & data inventory
Tasks: §0.2 reading list; §3.2 checklist; create `PHASE0_NOTES.md`, `DATA_INVENTORY_MS5.md`; list conflicts with this plan.
Done when: **[GATE 0]** approved.

### Phase 1 — Contract & skeleton
Tasks:
1. `risk-assessment/` skeleton (dirs, `pyproject.toml`, `Dockerfile`, `AGENTS.md`/`CLAUDE.md` from template, package READMEs).
2. `docs/api-contracts/risk-assessment-service.md` and `packages/contracts/risk-assessment/openapi.yaml` (§7).
3. FastAPI app with `/health`, `/risk/point`, `/risk/evaluate`, and `/risk/factors` implemented or stubbed to validate against the SPEC contract; also stub the retained plan extensions `/risk/vehicle-profiles`, `/risk/meta`, and `/risk/area`.
4. Contract test + architecture test.
Done when: suite green, contract matches the SPEC, **[GATE 1]** human and Routing/Core owners confirm integration details without changing the SPEC silently.

### Phase 2 — Ingestion & climatology
Tasks: `config/environment_columns.yaml`; `app/ingest/*`; `risk_catalog.sqlite` generation from the real workbooks; `SqliteEnvironmentRepository` + port; fixtures + tests; seed copy; `ingest_report.json` reviewed.
Done when: `python -m app.ingest` reproducibly builds the catalog; repository returns Javi-compatible hourly dose-E and REMS mean/min/max profiles with selected-sol/source provenance; report shows no unexplained rejected rows.

### Phase 3 — Risk model (pure domain, TDD)
Tasks: factor scoring for `slope`, `roughness`, `dunes`, `temperature`, `radiation`; weighted `risk_aggregator`; optional vehicle profile/restriction rules that do not override the weighted risk; YAML config loaders (`vehicle_profiles`, `risk_thresholds`, `risk_weights`); log every non-SPEC threshold in `DECISIONS.md`.
Done when: ≥ 95 % domain coverage; all §10 domain tests pass; thresholds each have a documented source or a `placeholder` tag.

### Phase 4 — Ports, adapters, use cases: point & evaluate
Tasks: ports; synthetic + unavailable adapters first; `guarded_call`; `HttpTerrainSource`/`HttpRasterSource` against the real MS3/MS4 contracts (use `respx` and, if available, the running stack); call MS4 `/terrain/profile` once per path and sample required MS3 bands at the same 90 m step; use cases `assess_point`, `evaluate_path`; routers/mappers/schemas; composition wiring by settings mode.
Done when: point and evaluate endpoints work end-to-end in `synthetic` mode and against real MS3/MS4 (integration test, auto-skipped if not reachable); upstream failure uses the SPEC's `502` response and never fabricates a score.

### Phase 5 — Plan extensions, factor coverage, golden routes
Tasks: `/risk/factors`, `/risk/meta`, `/risk/area`, and `/risk/vehicle-profiles` (the latter three are plan extensions); golden-route tests; data-quality details and confidence/provenance; performance check for a 50-segment path under 3 seconds, as required by the SPEC.
Done when: all SPEC endpoints and factor-availability behavior are compliant, and plan extensions have tests and documented additive schemas.

### Phase 6 — Integration & hand-off
Tasks: add `risk-assessment` to `docker-compose` (don't break other services); run with real MS3/MS4 containers; offline run; write `docs/risk-assessment/HANDOFF_ROUTING_CORE.md` (how Core and Routing consume point/path assessments, example requests); update root `README.md`, `ARCHITECTURE.md` status table; final DECISIONS entries.
Done when: Definition of Done (§12) is fully checked. **[GATE 2]**

### Phase 7 — Optional extensions (only after Gate 2; any extension that changes a SPEC-defined behavior requires a SPEC revision)
1. **Derived risk raster** `risk_map.tif` (COG) built by a CLI (`python -m app.build_layer`), written to `data/processed/mars/…` and registered in the catalog so MS3 can serve it and MS6 can use it as a cost surface. *Requires team agreement on who owns write access to `data/processed/` and how MS3's dataset registry discovers new layers.*
2. `POST /risk/path/batch` for route comparison (confirm schema at Gate 1).
3. Departure-window recommendation.
4. Radiation spatial modifiers.
5. Additional environmental factors if the data supports them.

---

## 12. Definition of Done

- [ ] `docs/risk-assessment/{PHASE0_NOTES,DATA_INVENTORY_MS5,HANDOFF_ROUTING_CORE}.md` exist and are current.
- [ ] `risk-assessment/AGENTS.md` + `CLAUDE.md` created from the template; every package has a `README.md`.
- [ ] Contract in `docs/api-contracts/` and `packages/contracts/risk-assessment/openapi.yaml`; contract test green.
- [ ] `python -m app.ingest` builds `risk_catalog.sqlite` from the real Gale workbooks; `ingest_report.json` reviewed; seed copy committed.
- [ ] Point, evaluate, factors, and health endpoints implemented exactly as in the SPEC.
- [ ] Vehicle profiles, meta, area, confidence/provenance/data-quality details and restriction reporting are implemented as additive plan extensions, without altering SPEC-defined scores or fields.
- [ ] Missing factor data is never scored as safe; no available factors returns the SPEC's unknown-risk response.
- [ ] Works in `synthetic`, `http` and `unavailable` modes; upstream failure → the SPEC's 502 response.
- [ ] No runtime dependency on Internet, on other services' databases, or on direct GeoTIFF access.
- [ ] Test suite green offline; coverage targets met; architecture test green.
- [ ] Docker image builds; service runs under Docker Compose with MS3/MS4.
- [ ] All thresholds/weights/limits documented in `DECISIONS.md` with source or `placeholder` flag.
- [ ] No files outside `risk-assessment/`, `docs/`, `packages/contracts/risk-assessment/`, `data/processed/mars/risk/`, `docker-compose`/`.env.example` entries were modified.

---

## 13. SPEC decisions and open questions

The following are fixed by the SPEC and must not be changed by a plan extension:

1. **Factors and weights:** use `slope`, `roughness`, `dunes`, `temperature`, `radiation` and weights 0.4, 0.15, 0.2, 0.15, 0.1 respectively.
2. **Risk levels and unavailable data:** use `low`, `medium`, `high`, `critical`; ignore unavailable factors in the weighted mean; if all are unavailable return `null`/`unknown`.
3. **API:** `/risk/evaluate`, `/risk/point`, `/risk/factors`, `/health`; evaluate-path request uses `sol`/`hora`; default `hora=12`; echo the supplied/reference `sol`, select the nearest actual sol independently per environmental dataset, and report each selected sol in factor provenance.
4. **Radiation:** score the selected rate profile; route-time dose accumulation belongs to MS6.
5. **Errors/performance:** invalid path/factors `400`, no coverage `404`, MS3/MS4 unavailable `502`; 50-segment evaluation under 3 seconds using a batched MS4 call.

The user decisions and repository evidence resolve these plan questions:

1. **Default sol:** configurable `RISK_DEFAULT_SOL`, default `1360`; choose the nearest available sol independently for each requested environmental dataset, matching `MapaMision`, and expose the actual selected sol per factor while echoing the request/reference sol.
2. **Point time:** preserve the original behavior; without `hora`, evaluate all hours and return the worst case, with `by_hour` only when `include_hourly=true`.
3. **Vehicle profile:** use `baseline_mars_rover`, a generic Gale profile seeded with the explicit optimizer values/formulas in §3.1 and §5. Do not claim it represents Curiosity or another flight vehicle; label these values as inherited optimizer assumptions, not certified flight limits.
4. **Restrictions:** report restrictions separately; they do not override the SPEC weighted risk or force `critical`.
5. **Path aggregation:** weight segment risks by segment distance.
6. **Orchestration:** Core orchestrates MS6 route generation followed by MS5 assessment and combines their responses. No direct service-to-service call or MS6 contract change is included.
7. **Javi's checked-in science rules:** use the four soil-class predicates, per-soil tilt models/ranges, and the explicit optimizer defaults documented in §3.1. Use RAD dose-E and its `0.7 * per-sol median` filter/hourly mean/fallback exactly as `MapaMision`. Calibration labels from `nivel_riesgo_real` are comparison evidence, not MS5 score labels. REMS has hourly mean/min/max temperature in Kelvin for sols 1360/2140; RAD has dose-B and dose-E rates in µGy/h for sols 1360/2140/3290/4710.

The original plan is retained wherever the SPEC is silent. The following items are therefore plan extensions, not published SPEC requirements:

- Default and optional vehicle profiles; vehicle-specific limits and restriction details.
- `GET /risk/vehicle-profiles`, `GET /risk/meta`, `POST /risk/area`, and optional batch evaluation.
- Additive `confidence`, `provenance`, `data_quality_notes`, `assumptions`, and restrictions in response bodies.
- Soil classification and model-based vehicle-tilt restrictions using Javi's rules; factor-score thresholds not specified by Javi remain configurable separately.
- Sampling-step control for path evaluation and any further hand-off requirements.

**Remaining items before Gate 1:**

1. **Unspecified factor thresholds:** Javi's code does not define normalized score thresholds for roughness, radiation alerts, thermal excess severity, or dune proximity beyond the mapped-dune rule. Keep these values explicitly configurable/placeholders; do not infer them from soil-class thresholds or optimizer cost weights. The 230–290 K band defines the thermal excess envelope, not its complete [0,1] score scale. The SPEC's illustrative slope normalization and Javi's 15° warning/25° block remain the initial slope behavior.
2. **Model scope:** use the delivered regressions and ranges for the Gale MVP only; record model version, predictor clipping and fallback-to-global behavior. Do not generalize the model to another region or treat its output as observed tilt.
3. **Extension schemas:** Core owners review additive point/path fields and area/meta/vehicle endpoints. Keep `/risk/path/batch` as the original plan's optional later extension.
4. **Effort:** apply the SPEC's two-day target to its required endpoints and shared integration. Complete original-plan area, metadata, vehicle and batch extensions after that baseline if time allows.
5. **Risk feedback into routing:** Core calls MS6 then MS5 and attaches assessment results; MS6's optimizer does not consume MS5 scores. Feeding MS5 scores back into route selection requires a separately approved MS6 integration.

---

## 14. Quick checklist for the agent at the start of each session

1. `git status` clean? Tests green? Which phase/gate am I in?
2. Re-read the **[VERIFY]** items relevant to today's task.
3. Write/adjust the test first; implement; run `ruff`, `mypy`, `pytest`.
4. Update the package `README.md` and `DECISIONS.md` for anything non-obvious.
5. Commit with a message referencing the phase (e.g. `ms5(p3): risk factor scoring`).