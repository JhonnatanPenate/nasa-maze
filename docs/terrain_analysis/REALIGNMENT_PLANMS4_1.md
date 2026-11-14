# MS4 Terrain Analysis Service — Realignment Plan (v2)

**Version:** 1.0.0 | **Status:** Proposed | **Date:** 2026-11-14
**Audience:** Manager (orchestrator) agent + team implementing MS4 against the delivered data package.
**Supersedes/extends:** [`IMPLEMENTATION_PLANMS4_1.md`](IMPLEMENTATION_PLANMS4_1.md) (all WPs done) — this plan realigns the **finished** implementation to the real data delivered in `data_usar/`.
**Contract of record:** [`docs/SPEC_MS4_TERRAIN_ANALYSIS.md`](../SPEC_MS4_TERRAIN_ANALYSIS.md) **v0.2.0**

---

## 1. Why realign

The original plan assumed a DEM (elevation GeoTIFF) as the terrain data source and that MS4 would compute slope via Horn's method. The data team instead delivered:

- `processed/rejilla_ruta_90m.tif` — a **routing cost grid**, 72×105 cells, 6 bands, with slope **already computed** in band 1 (`pendiente_grados`) and **no elevation band**.
- CRS `IAU_2015:49900` (Mars sphere, R = 3 396 190 m) — different from MS4's current default `planet_radius_km = 3389.5`.
- A bounded AOI (Gale crater): bounds `[137.345, -4.740, 137.455, -4.580]`, origin Bradbury Landing `(137.4416, -4.5895)`.
- The team warned the **file organization may change** — paths must stay configurable.

The architecture anticipated exactly this: the `RasterDatasource` port + swappable datasources mean the realignment is confined to infrastructure + config + mappers. **Domain logic, use cases, and API contracts stay untouched** (with one documented exception: `elevation_m` becomes nullable).

## 2. Gap analysis — current implementation vs. delivered data

| # | Gap | Impact | Resolution |
|---|---|---|---|
| G1 | No DEM delivered; `rejilla_ruta_90m.tif` has slope but no elevation | `elevation_m` has no source; slope via Horn impossible without DEM | Add grid mode: read slope band directly; `elevation_m → null`. Request DEM from data team (§6) to restore DEM mode |
| G2 | `planet_radius_km` default 3389.5 | Distance errors (~0.2%) vs. team's 59 274.69 m/deg | Change default to `3396.19` in `Settings`; update affected test expectations |
| G3 | `datasource_kind` supports `synthetic`/`geotiff`; no multi-band grid datasource | Can't read `pendiente_grados` band | New `RejillaGridDatasource` (band-indexed reads over the GeoTIFF) + mapper producing slope-array `DemWindow`-like payload |
| G4 | `elevation_m` assumed non-null in domain entities/schemas | Contract break | Make `elevation_m: float | None` in `PointAnalysis`/`ProfileSample` responses; document in spec v0.2 |
| G5 | Coverage check tied to DEM extent/nodata | Must use the rejilla extent + its nodata | Same mechanism, different array — handled by the new datasource's metadata |
| G6 | File paths may change when data team reorganizes | Startup failures | All dataset paths via `MS4_*` env vars only; never hardcoded |
| G7 | `geotiff` datasource reads single-band elevation windows | Band selection needed | Extend `RasterDatasource` read contract or add `band` parameter / `read_band_window` in `RejillaGridDatasource` only — keep port minimal (decision D2 below) |

## 3. Decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| D1 | Where does slope come from in grid mode? | Read band 1 `pendiente_grados` verbatim; do **not** recompute Horn's | Data team calibrated it; spec v0.2 §5 forbids diverging |
| D2 | Port change? | Keep `RasterDatasource` port unchanged; `RejillaGridDatasource` reads the slope band into a `DemWindow`-compatible payload via a dedicated mapper (slope array in place of elevation array, flagged `is_slope=True` or a new `SlopeGrid` domain object) | Least invasive; a `SlopeGrid` domain object is cleaner than overloading `DemWindow` — see D3 |
| D3 | Domain model for grid mode | Introduce `SlopeWindow`/`SlopeGrid` domain object carrying `slope_deg` array + `cell_size_m` + nodata; repository returns it alongside (or instead of) `DemWindow` when in grid mode | Preserves DEM path intact; use cases branch on datasource capability |
| D4 | `elevation_m` absent | Emit `null` in API responses (spec v0.2); never fabricate 0 | Honest contract; UI/Core can show "n/a" |
| D5 | Terrain classification | Unchanged — classify on the band's slope values with the same thresholds | Thresholds configurable already |
| D6 | DEM mode retained? | Yes. `synthetic` + `geotiff` datasources stay as-is for tests and future DEM delivery | Zero regression; swap test already proves pattern |
| D7 | New datasource kind name | `rejilla` | `MS4_DATASOURCE_KIND=rejilla`, `MS4_REJILLA_PATH=<path to rejilla_ruta_90m.tif>` |

## 4. Work packages (realignment)

Dependency: `R0 → R1 → R2/R3 (parallel) → R4 → R5`

| WP | Scope | Files touched | Acceptance |
|---|---|---|---|
| **R0 Config** | `planet_radius_km` default → `3396.19`; add `rejilla_path`, `datasource_kind += "rejilla"` | `app/core/config/settings.py`, affected distance tests | tests green with corrected expected distances |
| **R1 Domain** | `SlopeWindow` domain object (+ `slope_at`, `window_for` additions on `TerrainRepository` port if needed); `elevation_m` optional in `PointAnalysis`/`ProfileSample` | `core/domain/slope_window.py`, feature domain entities | unit tests green; zero rasterio imports in domain |
| **R2 RejillaDatasource** | rasterio reader for `rejilla_ruta_90m.tif` band 1 (parametrizable band), nodata handling, mapper → `SlopeWindow` | `infrastructure/datasources/rejilla_grid_datasource.py`, `slope_window_mapper.py`, `composition/dependencies.py` | swap test: same repository behavior vs synthetic; 404 on out-of-extent; 502 on unreadable file |
| **R3 Null-elevation plumbing** | use cases + presentation schemas tolerate `elevation_m=None`; health reports active datasource kind | `features/*/application`, `*_schemas.py`, `health_router.py` | contract tests updated; `elevation_m: null` asserted |
| **R4 Integration test w/ real file** | end-to-end `GET /terrain/point` + `POST /terrain/profile` against the real `rejilla_ruta_90m.tif` (path via env; skip test if file absent) | `tests/api/test_rejilla_integration.py`, `conftest.py` | slope values match band 1 at known cells; bounds Bradbury → valid response |
| **R5 Docs & review** | update `terrain-analysis/README.md` (datasource kinds, env vars), this plan's status, code review pass | README, AGENTS.md | clean review; one conventional commit per WP on `feature/terrain-analysis` |

## 5. Test matrix additions

| Target | Happy | Edge | Failure |
|---|---|---|---|
| `RejillaGridDatasource` | reads slope at known cell of fixture TIF (mini 3×3 GeoTIFF generated in-test, mirroring band semantics) | cell on grid edge | file missing → `UpstreamDatasourceError`; out-of-bounds → `NoCoverageError` |
| Grid-mode `AnalyzePoint` | point inside Gale bounds → `slope_deg` from band, `elevation_m: null` | — | nodata cell → 404 |
| Grid-mode `AnalyzeProfile` | path across fixture grid → samples with slope, `elevation_*_m` null | path partially outside extent | — |
| Radius change | `DistanceCalculator` expected values recomputed at R=3396.19 | — | — |

## 6. Open requests to the data team

1. **Source DEM** used to derive `pendiente_grados` (to restore `elevation_m` + Horn validation). If it won't arrive, grid mode stays the production mode and `elevation_m` remains `null` permanently — acceptable per spec v0.2.
2. Confirm `rejilla_ruta_90m.tif` nodata value and exact grid registration (cell-center vs. corner origin) once the file is delivered.
3. Notify new directory layout before reorganizing `data_usar/` so env vars can be updated in one place.

## 7. What does NOT change

- API contract (paths, params, response shape — only `elevation_m` may be `null`).
- `SlopeCalculator` (Horn's), `TerrainClassifier`, `PathSampler`, error taxonomy, layer rules.
- WP0–WP7 history and all existing tests (except radius-dependent expectations).

## 8. Status tracker

| WP | Status |
|---|---|
| R0 Config | pending |
| R1 Domain | pending |
| R2 RejillaDatasource | pending — blocked until `rejilla_ruta_90m.tif` is delivered (can build against generated fixture meanwhile) |
| R3 Null-elevation plumbing | pending |
| R4 Integration test | pending — blocked on real file |
| R5 Docs & review | pending |
