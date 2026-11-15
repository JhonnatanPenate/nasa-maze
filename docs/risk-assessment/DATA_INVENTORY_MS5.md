# MS5 — Phase 0 Data Inventory (`DATA_INVENTORY_MS5.md`)

> Produced in Phase 0 of `IMPLEMENTATION_PLAN_RISK_ASSESSMENT.md` (section 3.2 checklist).
> Method: every file below was opened and inspected directly (workbooks parsed
> cell-by-cell; the GeoTIFF decoded tag-by-tag **and** strip-by-strip with
> Python stdlib — `zipfile`/`xml.etree`/`struct`; JSON parsed normally).
> Row counts, units, ranges and 5-row samples are measured, not copied from docs.
> Inspection date: 2026-11-15 (branch `feature/risk-assessment`).

Legend: **[VERIFIED]** = observed in the file; **[DOC]** = stated by repo docs
(`docs/data/*`, SPECs) and consistent with inspection.

---

## 1. `data/gale/raw/ambiental/rems_resumen_horario.xlsx`

| Item | Finding |
|---|---|
| Sheets | `REMS` (single sheet) |
| Rows | 49 total = 1 header + **48 data rows** |
| Key structure | One row per `(sol, hora_lmst)` — a complete 2 sols x 24 h grid, no duplicates |
| Columns (units) | `sol` (sol, int); `hora_lmst` (LMST hour, int 0-23); `n` (sample count behind the hourly summary, 308-3699); `temp_suelo_K_media`, `temp_suelo_K_min`, `temp_suelo_K_max` (**ground temperature, K**); `temp_aire_K_media` (**air temperature mean, K**); `presion_Pa_media` (**pressure mean, Pa**); `uv_abc_W_m2_media` (**UV ABC irradiance mean, W/m2**) |
| Time coverage | `sol` in {1360, 2140}; `hora_lmst` = 0..23 complete for both sols. **No dates, no Ls, no UTC column** — the only time basis is `sol` + integer LMST hour |
| Missing values | Only `uv_abc_W_m2_media`: **11 nulls** — sol 1360 hours {9,10,14,15}, sol 2140 hours {9,10,11,12,13,14,15}. All other columns: 0 nulls |
| Sanity band (Q4) | All temperature cells inside 123-323 K (-150..+50 C): ground mean 196.7-268.8 K, ground min 170.4-263.2 K, ground max 212.6-275.3 K, air mean 199-255.7 K. Pressure 689.9-902.2 Pa (plausible for Mars). **No out-of-band values** |
| Outliers | None evident; `n` varies 308-3699 (hourly sample counts, informational) |
| vs plan | Plan guessed "air/ground temperature, pressure, humidity, maybe UV" — **there is no humidity column**; UV is present but sparsely null. Everything else matches |

5-row sample (first rows, sol 1360):

| sol | hora_lmst | n | temp_suelo_K_media | temp_suelo_K_min | temp_suelo_K_max | temp_aire_K_media | presion_Pa_media | uv_abc_W_m2_media |
|---|---|---|---|---|---|---|---|---|
| 1360 | 0 | 308 | 206.6 | 189.3 | 219.3 | 211.3 | 757.3 | 0 |
| 1360 | 1 | 3659 | 201.4 | 170.8 | 218.8 | 205.7 | 758.9 | 0 |
| 1360 | 2 | 348 | 200.3 | 171.1 | 214.9 | 202.5 | 761.2 | 0 |
| 1360 | 3 | 308 | 200.5 | 177.7 | 213.1 | 203.0 | 766.2 | 0 |
| 1360 | 4 | 308 | 198.3 | 180.5 | 213.1 | 200.7 | 767.1 | 0 |

## 2. `data/gale/raw/ambiental/rad_dosis_observaciones.xlsx`

| Item | Finding |
|---|---|
| Sheets | `RAD` (single sheet) |
| Rows | 351 total = 1 header + **350 observations** |
| Key structure | One row per RAD observation; key = `(sol, hora_lmst)` where `hora_lmst` is **fractional** (0.08-23.95). `observacion` is an ID `OBS000`..`OBS087` **reused per sol** (88 unique IDs across 350 rows) — not a global key |
| Columns (units) | `sol` (sol, int); `observacion` (string); `hora_lmst` (fractional LMST hour); `dosis_b_uGy_h` (**dose-B rate, uGy/h**); `dosis_e_uGy_h` (**dose-E rate, uGy/h**); `unidad_original` (`'uGy/hour'` on all 350 rows) |
| Time coverage | `sol` in {1360 (88 obs), 2140 (88), 3290 (87), 4710 (87)}; each sol's `hora_lmst` spans ~0-24 h but **rows are unordered** |
| Missing values | None (0 nulls in every column). **One duplicate timestamp**: `(sol=1360, hora_lmst=15.92)` appears twice (OBS025, OBS027) — harmless for hourly means, must be tolerated by ingest |
| Per-sol dose-E range (uGy/h) | 1360: 3.7-11.2; 2140: 8.9-13.2; 3290: 7.2-12.3; **4710: 2.0-6.3** (markedly lower — different season; nearest-sol selection matters) |
| **Coverage gap** | **sol 1360 has NO observations flooring to LMST hours 6, 7, 8, 9** (nothing between hora_lmst ~5.9 and ~10.2). Javi's empty-hour rule (per-sol mean fallback) will trigger for those bins — expected behaviour, record in provenance |
| Negative values | None (min dose-E = 2.0, min dose-B = 2.2 uGy/h) |
| vs plan | Matches section 3.1 / Q3 exactly: `dosis_e_uGy_h` is the channel `MapaMision` uses; `unidad_original` confirms uGy/h; `sol` + LMST hour confirmed |

5-row sample (first rows, sol 1360 — note unordered times):

| sol | observacion | hora_lmst | dosis_b_uGy_h | dosis_e_uGy_h | unidad_original |
|---|---|---|---|---|---|
| 1360 | OBS000 | 10.20 | 9.9 | 10.5 | uGy/hour |
| 1360 | OBS001 | 10.50 | 10.1 | 10.7 | uGy/hour |
| 1360 | OBS002 | 10.78 | 10.3 | 10.6 | uGy/hour |
| 1360 | OBS003 | 11.08 | 11.2 | 10.5 | uGy/hour |
| 1360 | OBS004 | 11.37 | 10.9 | 10.6 | uGy/hour |

## 3. `data/gale/processed/rejilla_ruta_90m.tif`

| Item | Finding |
|---|---|
| Format | GeoTIFF, little-endian, magic 42, single IFD, **uncompressed** (Compression=1), chunky (PlanarConfig=1), 27 strips x 4 rows |
| Raster shape | **72 cols x 105 rows = 7 560 cells**, 6 bands, **float32** (SampleFormat=3), BitsPerSample=32 |
| Bands (order = GDAL_METADATA `DESCRIPTION`) | 1 `pendiente_grados` (deg); 2 `rugosidad_m` (m); 3 `fraccion_oscura` (fraction); 4 `inercia_termica_tiu` (TIU); 5 `albedo` (fraction); 6 `distancia_duna_m` (m). **Units are not stored in the file** — they come from service config (MS3 spec) |
| CRS / georef | Anonymous geographic CRS: `GCS Name = unknown`, `Datum = unknown`, `Ellipsoid = unknown`, sphere semi-major = semi-minor = **3 396 190 m** (GeoDoubleParams). GeoKeys: GTModelType=2 (geographic), GTRasterType=1 (PixelIsArea), user-defined datum. MS3 reports it as `IAU_2015:49900` — **the file itself does not name IAU** |
| Transform | ModelPixelScale = 0.0015183544372303697 deg/px both axes; tiepoint raster(0,0) -> model(137.345, -4.58). ~90 m/pixel in latitude; ~89.7 m in longitude at lat -4.6. North-up, row 0 = northern edge (lat -4.58), per MS3/MS4 behaviour [DOC + consistent with decoded layout] |
| Extent | bounds `[137.345, -4.739427, 137.454322, -4.58]` (min_lon, min_lat, max_lon, max_lat) — inside the Gale AOI `[137.345, -4.740, 137.455, -4.580]` |
| Nodata | `GDAL_NODATA = "nan"`; wire representation is `null` via MS3. **Exactly 1 non-finite cell in the whole file, in band 3 `fraccion_oscura`** — matches MS3 SPEC acceptance note |
| Band statistics (all 7 560 cells decoded) | `pendiente_grados`: 0-35.5 deg, mean 4.27, 0 nodata - `rugosidad_m`: 0.08-5.08 m, mean 0.76 - `fraccion_oscura`: 0-1, mean 0.199, 1 nodata - `inercia_termica_tiu`: 408.3-445.6, mean 432.6 - `albedo`: 0.22759-0.23201, mean 0.22952 - `distancia_duna_m`: 0-5400.75 m, mean 1057.2 |
| Soil/class band | **None** — correct per Q5: soil class is derived by `clasificar_tipo_suelo`, never stored |

## 4. `data/gale/processed/modelos_por_suelo.json`

| Item | Finding |
|---|---|
| Top-level keys | `generado` ("2026-11-14T16:46:00"), `fuente` (Windows path to `gale_matriz_calibracion.xlsx` — provenance only), `variable_respuesta` = `tilt_real_grados`, `reglas_suelo`, `parametros` (`n_min=30`, `alfa=0.05`, `vif_max=5`, `se_robusto=HC3`), `resumen`, `modelos` (4), `modelo_global`, `ranking_r2` |
| `reglas_suelo` (verbatim) | `arena_dunas`: `distancia_duna_m == 0 or fraccion_oscura >= 0.5` - `lecho_rocoso_firme`: `rugosidad <= 0.60 and pendiente_grados <= 7.0 and albedo >= 0.2294` - `rocoso_fracturado`: `rugosidad >= 1.10 or pendiente_grados >= 8.0 or albedo < 0.2291` - `regolito_compacto`: resto |
| Models | All four soil models `estado="ajustado"`: `arena_dunas` n=38, metodo `lm`, r2adj=0.442, sigma=1.351; `lecho_rocoso_firme` n=220, `gls_AR1`, r2adj=0.2667, sigma=2.696; `rocoso_fracturado` n=342, `gls_AR1`, r2adj=0.2132, sigma=4.567; `regolito_compacto` n=251, `gls_AR1`, r2adj=0.1618, sigma=4.004. `modelo_global` n=851, `gls_AR1`, r2adj=0.2571, sigma=3.914 |
| Predictors per model | Terrain: `pendiente_grados`, `rugosidad`, `albedo`, `inercia_termica_tiu` (only rocoso_fracturado + global keep TIU; it is VIF-dropped for lecho/regolito). Ambient: **`dosis_rad_uGy_h` only** — `temp_suelo_K_media` is computed into `predictores_diarios` by the optimizer but **no model uses it** |
| `rango_predictores` | Per-model [lo, hi] clipping ranges recorded (e.g. global: pendiente 0.25-16.5, rugosidad 0.16-3.14, TIU 411.4-443, albedo 0.2287-0.2305, dosis_rad 10.66-12.257) |
| Coefficients | Full beta vectors + HC3/OLS standard errors + p-values + `supuestos` diagnostics per model (same diagnostics in `Bitacora_Calidad_Marte.xlsx` sheet `Auditoria_Modelos`) |
| Notes for MS5 | Predicted tilt predicts **rover tilt**, not DEM slope — never substitute for the SPEC `slope` factor. Optimizer falls back to `modelo_global` when a class `estado != "ajustado"` (not triggered today — all four are fitted). Predictor values outside `rango_predictores` are clipped |

## 5. `data/gale/processed/gale_matriz_calibracion.xlsx`

| Item | Finding |
|---|---|
| Sheets | `Matriz_Calibracion` (single sheet) |
| Rows | 852 total = 1 header + **851 waypoint rows** (matches `modelos_por_suelo.json` global n=851) |
| Columns (20) | `sol` (**Curiosity sol of the drive**, 3-3145 — NOT an environmental sol); `lon`, `lat`, `elevacion_m` (m); `tilt_real_grados` (deg, 0-29.1); `dist_m` (m along traverse); terrain predictors `pendiente_grados` (deg), `rugosidad` (m), `fraccion_oscura`, `distancia_duna_m` (m), `inercia_termica_tiu` (TIU), `albedo`; `indice_polvo` (**all 851 values null**); `velocidad_efectiva_m_sol` (m/sol, 8 nulls); ambient `dosis_rad_uGy_h` (uGy/h, 10.66-12.257), `sol_ref_rad` (1360/3290...), `temp_suelo_K_media`, `temp_suelo_K_max` (K), `sol_ref_rems` (1360/2140); `nivel_riesgo_real` in {`bajo`, `medio`, `alto`} |
| Missing | `indice_polvo` 100 % null; `velocidad_efectiva_m_sol` 8 nulls; everything else complete |
| Time coverage | Rover sols 3-3145 across the Curiosity traverse inside the AOI (lon 137.3528-137.4494, lat -4.7397..-4.5891) |
| Use in MS5 | Calibration/sanity only. `nivel_riesgo_real` labels (`bajo/medio/alto`) are Javi's calibration labels — **not** SPEC factor scores or `low/medium/high/critical` boundaries |

5-row sample:

| sol | lon | lat | elevacion_m | tilt_real_grados | pendiente_grados | rugosidad | dosis_rad_uGy_h | sol_ref_rad | temp_suelo_K_media | sol_ref_rems | nivel_riesgo_real |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 137.4416 | -4.5895 | -4501 | 4.4 | 2.25 | 0.7 | 10.66 | 1360 | 228.917 | 1360 | bajo |
| 5 | 137.4416 | -4.5895 | -4501 | 4.4 | 2.25 | 0.7 | 10.66 | 1360 | 228.917 | 1360 | bajo |
| 16 | 137.4417 | -4.5895 | -4501 | 5.6 | 2.25 | 0.7 | 10.66 | 1360 | 228.917 | 1360 | bajo |

## 6. `data/gale/processed/gale_puntos_quimica.xlsx`

| Item | Finding |
|---|---|
| Sheets | `Objetivos_Minerales` (single sheet) |
| Rows | 22 total = 1 header + **21 mineral-target POIs** (Rocknest, John Klein, Cumberland, Windjana, Confidence Hills, Mojave2, Telegraph Peak, Buckskin, Glen Etive, Oudam, ...) |
| Columns (15) | `nombre`; `sol` (79-2842, CheMin observation sol); `lon`, `lat`; `elevacion_m` (-4520..-4128 m); mineral columns `hematita_crist_pct`, `arcilla_pct`, `amorfo_pct`, `tridimita_crist_pct`, `sulfatos_crist_pct`, `hematita_pct`, `esmectitas_pct`, `tridimita_pct`, `sulfatos_pct` (all %; **sparse — many nulls per column, e.g. `tridimita_crist_pct` has 20/21 nulls with a single 34.1 value**); `base_hematita` (`cristalina`/`muestra_total`) |
| Missing | Heavy per-column nulls (mineral assays only exist for sampled targets) |
| Use in MS5 | **Not used by MS5** (Location Service owns POI lookup; Routing uses it for targets). Recorded for completeness |

5-row sample:

| nombre | sol | lon | lat | elevacion_m | hematita_pct | base_hematita |
|---|---|---|---|---|---|---|
| Rocknest | 79 | 137.4483 | -4.5900 | -4518 | null | null |
| John Klein | 196 | 137.4491 | -4.5895 | -4520 | null | null |
| Cumberland | 283 | 137.4491 | -4.5895 | -4520 | null | null |
| Windjana | 624 | 137.4020 | -4.6388 | -4479 | null | null |
| Confidence Hills | 766 | 137.3775 | -4.6627 | -4461 | 13.4 | cristalina |

## 7. `data/gale/processed/ruta_{esmectitas,hematita,tridimita}.geojson`

| Item | Finding |
|---|---|
| Structure | GeoJSON `FeatureCollection` with member `"crs": {"type":"name","properties":{"name":"IAU_2015:49900"}}` |
| Features | Per route: 1 `ruta_optima_completa` (full cell-centre `LineString`, N+1 vertices for N cells), N `ruta_optima` two-vertex `LineString` segments (one per grid step, diagonal steps included), 1 `contrafactual` (`ruta_modelo_global` full line) |
| Counts | esmectitas: 97 features (96-vertex master line, 95 segments, 93-vertex counterfactual) - hematita: 68 (67-vertex, 66 seg, 60-vertex cf) - tridimita: 60 (59-vertex, 58 seg, 52-vertex cf) |
| Coordinates | lon ~137.3579-137.4414, lat ~-4.7296..-4.5899 — cell-centre lon/lat, planetocentric, positive-east ~137 deg E |
| Properties | segments carry `tipo_suelo`, `modelo_usado`, `inclinacion_grados`; master carries `material`, `objetivo_mineral`, `sol_referencia`=1360, `hora_salida`=9.0, `llegada_lmst`, `dosis_uGy`, `distancia_km` |
| Use in MS5 | **Golden test paths** for `/risk/evaluate`; copy small excerpts into `tests/fixtures/` |

## 8. `data/gale/processed/ruta_*_resumen.json` + `ruta_*_tramos.xlsx`

`resumen.json` keys: `resumen`, `comparativa_dunas`, `control_calidad`.

| Route | celdas | distancia_km | llegada_lmst | dosis_uGy | espera_nocturna_h | costo_objetivo | objetivo | sol_rad / sol_rems |
|---|---|---|---|---|---|---|---|---|
| hematita | 67 | 7.73 | S+1 08:15 | 247.8 | 13.84 | 42.369 | Oudam | 1360 / 1360 |
| esmectitas | 96 | 10.30 | S+1 12:11 | 289.7 | 13.91 | 51.388 | Glen Etive | 1360 / 1360 |
| tridimita | 59 | 6.71 | S+0 17:07 | 85.1 | 0.00 | 17.591 | Buckskin | 1360 / 1360 |

`control_calidad` (identical in all three): 7 560 cells, 100 % valid, soil counts `arena_dunas` 1433 / `lecho_rocoso_firme` 1955 / `regolito_compacto` 1695 / `rocoso_fracturado` 2477, `celdas_bloqueadas_por_margen` = 117.

`*_tramos.xlsx` — sheet `Tramos`, **17 columns**: `tramo`, `hora_lmst_inicio`, `hora_lmst_fin` (**strings** `"S+0 09:00"`), `tipo_suelo`, `modelo_usado`, `r2_ajustado`, `distancia_m`, `pendiente_media_grados`, `inclinacion_media_grados`, `inclinacion_max_grados`, `dosis_tramo_uGy`, `dosis_acumulada_uGy`, `temp_suelo_K` (**string** `"min-max"` K), `lon_inicio`, `lat_inicio`, `lon_fin`, `lat_fin`. Row counts: esmectitas 19 tramos, hematita 13, tridimita 12. All three share the Bradbury departure prefix and diverge later (tridimita & hematita share tramos through ~S+0 16:50). Final `dosis_acumulada_uGy` matches `resumen.json` (247.8 / 289.7 / 85.1) and `HANDOFF_SOFTWARE.md` reference values.

Use in MS5: **non-contractual sanity checks + golden fixtures**. Per-segment elapsed time/dose accumulation is MS6's job — MS5 reports per-segment *rates* only.

## 9. `data/gale/processed/Bitacora_Calidad_Marte.xlsx`

| Sheet | Rows | Content |
|---|---|---|
| `Auditoria_Modelos` | 6 (5 models) | Per soil + global: n, metodo, r2adj, sigma, Shapiro/BP/DW p-values, VIF max, rho_AR1, SE type, and booleans `normalidad_ok`, `homocedasticidad_ok`, `independencia_ok`, `se_robustos_aplicados` |
| `Coeficientes_Objetivo` | 38 | beta coefficients per model **plus `_parametro_objetivo` rows** documenting the optimizer constants (incl. velocidad_maxima 1000 m/h, factor_deslizamiento_arena 0.60, peso_* values) |
| `Objetivos_Minerales` | 22 | Copy of `gale_puntos_quimica.xlsx` |
| `Rutas_Optimas` | 45 | Consolidated per-tramo rows for the 3 routes (adds `material_objetivo`, `celdas_arena_en_ruta`, totals) |

**Quality flags it raises:** only `arena_dunas` passes all three diagnostics; `lecho_rocoso_firme` fails normality + independence; `rocoso_fracturado` and `regolito_compacto` fail all three; global fails all three. These are *model* diagnostics (tilt regressions), not dataset-unreliability flags — there is **no sheet flagging unreliable environmental periods/regions**.

## 10. `data/gale/processed/mapa_rutas_gale.png`

120 KB PNG render of the 3 routes (matplotlib output of `dibujar_mapa_rutas`). Display asset only — not consumed by MS5.

## 11. `data/gale/raw/pe_msl_vectores.json`

| Item | Finding |
|---|---|
| Structure | JSON object with **4 FeatureCollections**: `MSL_waypoints`, `MSL_traverse`, `MSL_SurfaceSites`, `MSL_waypoints_current` |
| `MSL_waypoints` | **1 389 features**; properties `RMC, site, drive, sol (3-5073), easting, northing` (**MMGIS equirectangular metres**, per `science/crs_marte.py` `CRS_MSL_EQC`), `elev_geoid`, `lon`, `lat`, `roll`, `pitch`, `yaw`, `yaw_rad`, `tilt`, `dist_m`, `dist_total_m`, `dist_km`, `dist_mi`, `drive_type` |
| `MSL_traverse` | 1 317 LineString features with `Length` (m) and 3-D coordinates `[lon, lat, elev]` |
| `MSL_SurfaceSites` | 4 polygons (named drill/site areas) |
| `MSL_waypoints_current` | 1 feature (latest waypoint, sol 5073) |
| Answer to Q8 | **It is the Curiosity/MSL traverse truth** (waypoints + traverse line + surface sites), already consumed by MS1 (Location). For MS5 it is optional context (traverse truth/ephemeris); **not required by any SPEC factor** |

## 12. Files confirmed NOT used by MS5

- `data/gale/raw/gazzeter/MARS_nomenclature_center_pts.*` — USGS IAU nomenclature shapefile set (MS1 Gazetteer source; already ingested into `data/processed/mars/location/location_catalog.sqlite`).
- `data/processed/mars/location/location_catalog.sqlite` — MS1 catalog.
- `science/*.py`, `science/*.R` — Javi's canonical optimizer/model code; read-only reference.
- `_rejilla_suelo_tilt.npy` — optimizer cache from the handoff package's `auxiliares/`; **not present** under `data/gale/`; irrelevant to MS5.

---

## Section 3.2 Checklist answers

**Q1 — Can workbook rows be keyed to `sol` + LMST `hora`?**
**Yes.** REMS: `sol` (int) + `hora_lmst` (int 0-23), complete 2x24 grid.
RAD: `sol` (int) + fractional `hora_lmst`; Javi's optimizer bins by `int(hora_lmst) % 24`
(truncation = floor for these positive values) then hourly mean — the SPEC's
`sol`/`hora` selection is directly supported. Caveats: REMS covers only sols
{1360, 2140} vs RAD {1360, 2140, 3290, 4710} -> **per-dataset nearest-sol
selection is mandatory** (SPEC already requires it). sol 1360 RAD lacks LMST
hours 6-9 -> empty-bin fallback applies. No UTC/Ls/season column exists — nothing
to convert; do not infer one.

**Q2 — Is Ls (season) available?**
**No.** No `Ls`, solar-longitude, date, or UTC column in any inspected workbook,
GeoJSON, or JSON. Seasonal context is unavailable; record as absent, do not add
seasonal API behaviour.

**Q3 — RAD unit and time basis**
**Verified.** `dosis_e_uGy_h` / `dosis_b_uGy_h` in **uGy/h**
(`unidad_original = 'uGy/hour'` on every row), keyed by `sol` + fractional LMST
hour. Use `dosis_e_uGy_h` only (matches `MapaMision`); never combine channels.

**Q4 — REMS sanity band**
**Pass.** All air/ground temperature cells within -150..+50 C (123-323 K);
pressure 689.9-902.2 Pa plausible. No parse/unit errors detected.

**Q5 — Raster bands vs MS3 metadata**
**Verified at file level:** exactly the 6 documented bands in the documented
order, float32, nodata NaN, `fraccion_oscura` has exactly 1 nodata cell (MS3
SPEC's acceptance note reproduced). No soil/class band exists — soil class is
derived. Band units are not in the file; MS3 serves them from config.
MS5 consumes bands **through MS3 only** at runtime.

**Q6 — Soil classes, model predictors/ranges, R2, sigma**
Recorded in section 4 above. All four class models + global are `ajustado`.
Predictor clipping ranges per model are in `rango_predictores`. The tilt model
is for the optional vehicle restriction/explainability only — the SPEC `slope`
factor comes from MS4 `slope_deg`. Javi's optimizer limits (1000 m/h nominal,
`max(0.1, 1-tilt/30)` speed factor, x0.40 on `arena_dunas`, block at DEM slope
>=25 deg / predicted tilt >=20 deg / tilt+1.96sigma >20 deg, thermal band
230-290 K, motion window LMST [7,17)) are inherited-assumption values for the
generic `baseline_mars_rover` profile — **not certified flight limits**; the
motion window belongs to MS6 scheduling, not an MS5 block.

**Q7 — `*_tramos.xlsx` usage**
Usable for non-contractual sanity checks and golden fixtures (structure in
section 8). No per-segment elapsed time, dose accumulation, or soil limits are
required of MS5; route-time dose accumulation stays in MS6.

**Q8 — `pe_msl_vectores.json`**
Curiosity/MSL traverse truth: 1 389 waypoints (sol 3-5073, MMGIS easting/
northing metres + lon/lat + attitude), 1 317 traverse LineStrings, 4
surface-site polygons, 1 current waypoint. Optional context only; not an MS5
factor input.

**Q9 — What does `Bitacora_Calidad_Marte.xlsx` flag as unreliable?**
It flags **model diagnostics**, not data periods/regions: per-soil tilt
regressions fail normality/homoscedasticity/independence checks (only
`arena_dunas` passes all three). Side findings: `indice_polvo` is 100 % null in
the calibration matrix; `velocidad_efectiva_m_sol` has 8 nulls; RAD sol 1360 has
a 4-hour observation gap (LMST 6-9) and one duplicate timestamp. No sheet marks
specific sols/regions as unreliable.

**Q10 — Coordinate convention**
GeoJSONs and the grid use **planetocentric lat/lon in degrees**, longitude
positive east ~137.4 deg E (numerically identical under 0-360 deg E and +/-180
deg conventions since <180), labelled `IAU_2015:49900` (sphere R = 3 396 190 m,
59 274.69 m/degree). The GeoTIFF itself declares an *anonymous* geographic CRS
on the same sphere; MS3 normalizes the label to `IAU_2015:49900`. MS3/MS4 accept
`lat` in [-90, 90], `lon` in [-180, 180] — all Gale coordinates fit. **MS5 must
accept and emit the same convention as MS3/MS4**; never use terrestrial EPSG
codes. See `PHASE0_NOTES.md` section 1 for the consolidated convention.
