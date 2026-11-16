# MS5 — Phase 0 Notes (`PHASE0_NOTES.md`)

> Phase 0 of `IMPLEMENTATION_PLAN_RISK_ASSESSMENT.md` for the Risk Assessment
> Service (MS5), Gale crater MVP. Authoritative contract:
> `docs/SPEC_MS5_RISK_ASSESSMENT.md` (takes precedence over plan details).
> Companion document: `DATA_INVENTORY_MS5.md` (file-by-file inspection).
> Branch: `feature/risk-assessment`. Inspection date: 2026-11-15.
> Everything not directly verified against code/files is marked **[VERIFY]**.

---

## 1. Coordinate convention (confirmed)

| Aspect | Value | Source |
|---|---|---|
| CRS label used by services | `IAU_2015:49900` | MS3/MS4 SPECs + code |
| Semantics | planetocentric latitude, **east-positive longitude**, degrees | MS3/MS4 SPECs |
| Longitude range accepted by MS3/MS4 | `[-180, 180]`; Gale data ~137.35-137.45 deg E fits | MS3/MS4 request schemas |
| Latitude range | `[-90, 90]` | MS3/MS4 request schemas |
| Mars radius / metres-per-degree | 3 396 190 m; ~59 274.69 m/deg | `science/crs_marte.py`, mars-geodata rules |
| Grid orientation | North-up; row 0 = northern edge (lat -4.58); cell-centre sampling | MS3/MS4 code + decoded TIFF |
| GeoTIFF CRS tag | anonymous geographic CRS on sphere R=3 396 190 m — file does **not** literally say `IAU_2015:49900`; MS3 normalizes | direct TIFF decode |
| MSL waypoints | also carry MMGIS equirectangular metres (easting/northing) — Curiosity truth, not an MS5 input | `pe_msl_vectores.json`, `science/crs_marte.py` |

**MS5 rule:** accept and emit exactly the MS3/MS4 convention (planetocentric
lat/lon degrees, lon in `[-180,180]`, CRS label `IAU_2015:49900` when a CRS is
required). Never EPSG:4326/3857. Distances on Mars use the Mars radius.

## 2. Service topology (confirmed)

| Service | Port | Base path | Status |
|---|---|---|---|
| MS1 Location | 8001 | `/location` | running pattern (ingest + catalog sqlite) |
| MS3 Raster | 8003 | `/raster` | implemented (`rejilla` dataset) |
| MS4 Terrain Analysis | 8004 | `/terrain` | implemented (grid mode reads `pendiente_grados` from MS3 window) |
| **MS5 Risk Assessment** | **8005** | `/risk` | **to be implemented — this is the service being built** |
| MS6 Routing | 8006 | `/routing` | exists; owns route dose accumulation, NOT MS5 |

MS5 runtime dependencies: **MS3** (raster values: bands 2,3,5,6 needed by SPEC
factors) and **MS4** (`/terrain/profile` for slope, per plan). MS5 must **never**
read `rejilla_ruta_90m.tif` or any GeoTIFF directly, and must not query MS1's
sqlite or MS3's storage. Environmental workbooks are ingested into MS5-owned
storage at startup/ingest time (format: implementation detail, Phase 1+).

## 3. Confirmed upstream contracts

### MS3 Raster Service (`http://host.docker.internal:8003` in compose)

| Endpoint | Purpose for MS5 |
|---|---|
| `GET /health` | liveness; raster datasets presence |
| `GET /raster/datasets` | dataset discovery (`rejilla`) |
| `GET /raster/{dataset}/metadata` | bands, bounds, resolution, crs, nodata |
| `GET /raster/{dataset}/point?lat&lon` | single-cell all-band values (nodata -> `null`) |
| `POST /raster/{dataset}/window` | bounding-box window -> `cells` grid with `resolution_deg`, `center_lat`, `core` + bounds; used for area/segment sampling |
| `POST /raster/{dataset}/sample` | point list -> per-point band values |

Dataset: `rejilla` — 72x105 cells, six bands `pendiente_grados`,
`rugosidad_m`, `fraccion_oscura`, `inercia_termica_tiu`, `albedo`,
`distancia_duna_m`. Values served **verbatim** (no recompute/reproject);
nodata is `null` on the wire (NaN in the TIFF).

### MS4 Terrain Analysis Service

| Endpoint | Purpose for MS5 |
|---|---|
| `GET /health` | liveness |
| `POST /terrain/profile` | polyline (>=2 pts) -> sampled points with `slope_deg` — **MS5 `slope` factor source** |
| `GET /terrain/point` | single-point terrain class/slope |
| `POST /terrain/area` | area stats (optional) |

Grid mode reads `pendiente_grados` directly from the delivered grid via MS3 —
MS4 does **not** recompute slope in grid mode; elevation is `null` there.
MS4 error mapping: domain validation -> 400, no coverage -> 404, malformed ->
422, MS3 failure -> 502.

## 4. Error-body format (confirmed for MS3/MS4 family)

MS3 and MS4 both return FastAPI-style bodies:

```json
{ "detail": "human-readable message" }
```

with statuses 400 (validation), 404 (not found/no coverage), 422 (malformed
shape), 503/502 (upstream/unavailable as applicable). MS5 should follow the
same `{"detail": ...}` convention for consistency within the raster/terrain
family. (MS1 Location uses RFC-7807 `application/problem+json` — different
convention, not adopted here.)

## 5. MS5 SPEC endpoints (authoritative — implement exactly)

Base path `/risk`, port 8005:

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | liveness + upstream status summary |
| GET | `/risk/point?lat&lon&sol&hora` | single-point factor scores + weighted risk |
| POST | `/risk/evaluate` | path/segment evaluation (see SPEC for exact schema) |
| GET | `/risk/factors` | factor catalog: ids `slope`, `roughness`, `dunes`, `temperature`, `radiation` + units/weights/availability |

Factor IDs (exact): `slope`, `roughness`, `dunes`, `temperature`, `radiation`.
Default weights: slope 0.4, dunes 0.2, roughness 0.15, temperature 0.15,
radiation 0.1. Risk levels: `low` <0.25, `medium` 0.25-<0.5, `high` 0.5-<0.75,
`critical` >=0.75, `unknown` when no factors available. Missing data ->
`available:false`, excluded from weighting, **never treated as safe**.
MS5 does **not** accumulate route radiation dose (MS6's job).

## 6. Environmental data provenance (for ingest, Phase 1+)

| Dataset | File | Key | Channel used | Notes |
|---|---|---|---|---|
| REMS hourly | `data/gale/raw/ambiental/rems_resumen_horario.xlsx` | `sol` + `hora_lmst` (int) | `temp_aire_K_media` for `temperature` factor | ground temp + pressure + UV also present; humidity absent |
| RAD dose | `data/gale/raw/ambiental/rad_dosis_observaciones.xlsx` | `sol` + fractional `hora_lmst` -> floor to int hour | **`dosis_e_uGy_h` only** (uGy/h) | dose-B never combined; per-sol hourly mean; empty-hour fallback = that sol's mean |

Javi's preparation rules (from `science/optimizador_rutas.py`, verified
against the workbook structure): per-sol median filter `>= 0.7*median`,
floor LMST to int hour, hourly mean, per-sol mean fallback for empty bins.
REMS workbook holds **hourly aggregates** (mean/min/max), not raw samples —
do not invent p05/p95 percentiles.

Sol coverage: REMS {1360, 2140}; RAD {1360, 2140, 3290, 4710} -> nearest-sol
selection per dataset; document which sol served each factor in responses.

## 7. Javi's science rules — provenance and caveats

Source: `science/optimizador_rutas.py`, `science/motor_rutas_adaptativo.py`,
`modelos_por_suelo.json`, `Bitacora_Calidad_Marte.xlsx`. These are the data
scientist's canonical assumptions for the Gale rover scenario:

- Soil classes (`clasificar_tipo_suelo`): `arena_dunas` if
  `distancia_duna_m==0 or fraccion_oscura>=0.5`; `lecho_rocoso_firme` if
  `rugosidad<=0.60 and pendiente<=7.0 and albedo>=0.2294`;
  `rocoso_fracturado` if `rugosidad>=1.10 or pendiente>=8.0 or albedo<0.2291`;
  else `regolito_compacto`.
- Per-soil tilt models predict **rover tilt** (deg) from terrain +
  `dosis_rad_uGy_h`; all four `estado="ajustado"` but with modest R2adj
  (0.16-0.44) and failed diagnostics on 3 of 4 classes — treat as
  explanatory/optional, never as a SPEC factor or a safety limit.
- Optimizer constants: nominal speed 1000 m/h; DEM slope block >=25 deg;
  predicted tilt block >=20 deg; safety margin `tilt + 1.96*sigma <= 20 deg`;
  thermal operating band 230-290 K; daylight LMST window 7-17; speed factor
  `max(0.1, 1-tilt/30)`; `arena_dunas` x0.40 penalty.
- **Caveat:** these are inherited engineering assumptions for a
  `baseline_mars_rover` profile, not certified vehicle limits. Vehicle
  profiles/restrictions are additive MS5 behaviour (plan) and must be clearly
  labelled as configurable defaults, reviewed at Gate 1. The LMST 7-17 motion
  window is an MS6 scheduling concern, not an MS5 risk block.
- `nivel_riesgo_real` labels in the calibration matrix (`bajo/medio/alto`)
  are Javi's calibration labels — **not** MS5 risk levels.

## 8. Conflicts / surprises vs the implementation plan

1. **REMS has no humidity column** (plan guessed "maybe humidity") — columns
   are ground temp (media/min/max K), air temp mean K, pressure Pa, UV ABC.
   Temperature factor must use `temp_aire_K_media` (air) — ground temp is
   supplementary; SPEC factor name is `temperature`, unit/semantics per SPEC.
2. **RAD workbook rows are unordered and `observacion` IDs repeat per sol** —
   ingest must key on `(sol, floor(hora_lmst))`, not on `observacion`.
   One duplicate `(sol=1360, hora=15.92)` pair exists; hourly-mean ingest
   tolerates it.
3. **sol 1360 RAD has a 4-hour gap (LMST 6-9)** — empty-bin fallback will fire;
   provenance must record fallback usage.
4. **GeoTIFF CRS is anonymous** (sphere R=3396190 m) — MS3 labels it
   `IAU_2015:49900`; MS5 inherits that label via MS3 metadata, do not read the
   TIFF to "verify" the CRS name.
5. **MS4 grid mode returns `elevation: null`** — anything needing elevation
   must not rely on MS4 grid mode; MS5 factors don't need elevation anyway.
6. **Plan's "area/meta and optional batch" endpoints are additive** — SPEC is
   silent; implement only if time allows, reviewed at Gate 1, and never let
   them change SPEC fields/formula.
7. **`indice_polvo` (dust index) is 100% null** in the calibration matrix —
   no dust-factor data exists; do not fabricate one.

## 9. Open items marked [VERIFY]

- Exact request/response field names of `POST /risk/evaluate` body —
  **[VERIFY against `docs/SPEC_MS5_RISK_ASSESSMENT.md` section on evaluate]**
  during Phase 1 contract freeze.
- Whether MS5 `/health` should report per-upstream (MS3/MS4) sub-status or a
  single status — follow SPEC; **[VERIFY]**.
- Environmental storage format for ingested workbooks (sqlite/json/parquet)
  — implementation choice, Phase 1; **[VERIFY]** against repo conventions.
- Whether MS5 needs `inercia_termica_tiu` band at all — SPEC factors map to
  slope(MS4), roughness(band2), dunes(bands 3+6), temperature(REMS),
  radiation(RAD); TIU appears unused by SPEC factors — **[VERIFY]** at
  contract freeze; fetch only needed bands via MS3 window/sample.
- Port 8005 availability in the dev environment — **[VERIFY]** at Phase 1
  compose time.

## 10. Phase 0 gate checklist

- [x] §0.2 reading list completed (agent profile, AI docs, AGENTS template,
      ARCHITECTURE, DECISIONS, SPEC_MS5/MS3/MS4, data handoff docs,
      DATA_SOURCES, terrain-analysis implementation + tests, raster-service
      features + architecture test, location-service ingest/config/contract,
      science scripts).
- [x] §3.2 data inspection of all listed files against real data.
- [x] `DATA_INVENTORY_MS5.md` produced with all 10 checklist answers.
- [x] `PHASE0_NOTES.md` produced (conventions, URLs, errors, ports, schemas,
      conflicts, provenance, [VERIFY] items).
- [x] No service code, no skeleton, no contract changes, no other-service
      modifications. Only `docs/risk-assessment/*.md` written.
- [ ] **GATE 0 — awaiting human review/approval before Phase 1.**
