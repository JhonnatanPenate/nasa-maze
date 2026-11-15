# Spec: Raster Service (MS3)
**Version:** 0.1.1 | **Status:** Draft — aligned with `data/gale/` package | **Date:** 2026-11-15 | **Effort target:** 2 days (spec-driven development)

> First version. The delivered data package contains exactly one raster: `data/gale/processed/rejilla_ruta_90m.tif` (72 cols × 105 rows, 6 bands, CRS `IAU_2015:49900`, AOI `[137.345, -4.740, 137.455, -4.580]`). MS3 is the single HTTP access point to raster files so that MS4/MS5/MS6/Core never open GeoTIFFs directly. Its contract is designed to back MS4's reserved `HttpRasterDatasource` (`read_window`, `read_window_with_halo`, `read_window_around`, `ping`).
>
> **v0.1.1** (realigned with the real file, see `docs/raster_service/IMPLEMENTATION_PLANMS3_1.md` §1.1/§4): width/height fixed (72×105); nodata is NaN → `nodata: null`; metadata and window responses expose `resolution_deg`; window `cell_size_m` replaced by `resolution_deg` + `center_lat` (exact inputs of MS4's `DemWindowMapper`); `point` windows pad out-of-extent cells with `null` instead of 404; unknown band is always `404`; `/sample` null semantics and caps defined; PNG encoding, colormap catalog and `X-Raster-Value-Range` header defined.

## 1. Service Identity

| Field | Value |
|---|---|
| Name | Raster Service |
| ID | MS3 |
| Stack | Python + FastAPI, Rasterio/GDAL |
| Port | `8003` |
| Depends on | Local raster files in shared storage (`data/gale/`); no other service |
| Consumed by | Terrain Analysis Service (MS4), Risk Assessment Service (MS5), Routing Engine (MS6), Core |

## 2. Purpose

Administers access to geospatial raster files and exposes their values and bands over REST. It owns all raster I/O — opening files, resolving coordinates to cells, clipping windows, nodata handling — so consumers receive plain JSON arrays/values in the dataset's native CRS (`IAU_2015:49900`) and never deal with rasterio, transforms, or nodata sentinels.

Datasets are registered by configuration (name → path). The MVP registers one dataset, `rejilla` → `data/gale/processed/rejilla_ruta_90m.tif`; a future DEM registers the same way without code changes. Band values are served **verbatim** — MS3 never resamples, recomputes, or reprojects the delivered science (band `pendiente_grados` is the data team's slope, not a derivative to recompute).

Additionally it renders a band as a PNG layer (clipped to the dataset extent) so Core/frontend can paint the map without raster tooling.

## 3. Inputs (API Contract)

Base URL: `/raster`

### 3.1 `GET /raster/datasets` — List registered datasets

No parameters.

### 3.2 `GET /raster/{dataset}/metadata` — Raster metadata

| Param | Type | Required | Description |
|---|---|---|---|
| `dataset` | path | yes | Registered dataset name (MVP: `rejilla`) |

### 3.3 `GET /raster/{dataset}/point` — Band value(s) at a coordinate

| Param | Type | Required | Description |
|---|---|---|---|
| `lat` | float | yes | Planetocentric latitude |
| `lon` | float | yes | Planetocentric longitude |
| `band` | string | no | Band name (e.g. `pendiente_grados`); default: all bands |

Nearest-cell sampling; no interpolation (matches the optimizer's grid semantics).

### 3.4 `POST /raster/{dataset}/window` — Cell window read

```json
{
  "band": "pendiente_grados",
  "bbox": [137.40, -4.70, 137.45, -4.60],
  "halo_cells": 1
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `band` | string | yes | Band name |
| `bbox` | [min_lon, min_lat, max_lon, max_lat] | one of `bbox` / `point` | Cells covering the bbox, clipped to the dataset extent |
| `point` | {`lat`, `lon`} | one of `bbox` / `point` | With `radius_cells`, returns a `(2·radius+1)²` window centred on the containing cell (MS4 `read_window_around`) |
| `radius_cells` | int | with `point` | Radius in cells around `point` |
| `halo_cells` | int | no, default 0 | Extra rows/cols of real cells on every side of a `bbox` read, clipped at the edge (MS4 `read_window_with_halo`); response marks the core slice |

Exactly one of `bbox` / `point` must be present (`400` otherwise); `radius_cells` is required with `point`; `radius_cells` and `halo_cells` are integers ≥ 0. `halo_cells` is ignored on `point` reads. The window-size cap (§5) applies to the core cell count, not the halo; for `point` reads it applies to `(2·radius+1)²`.

Cell selection (identical to MS4 `GridGeometry`): a `bbox` selects the cells whose **centres** fall inside it, clipped to the extent; a bbox covering no cell centre falls back to the single cell containing the centre of its intersection with the extent. A `point` resolves to the containing cell (points on the max edge clamp into the boundary cell). A `point` window **never** returns 404: cells outside the extent are `null` padding (all `null` when the point itself is outside).

### 3.5 `POST /raster/{dataset}/sample` — Values along a path

```json
{
  "band": "rugosidad_m",
  "path": [ {"lat": -4.60, "lon": 137.44}, {"lat": -4.65, "lon": 137.42} ],
  "sample_distance_m": 90
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `band` | string | yes | Band name |
| `path` | array of {lat, lon} | yes | Polyline, 2..`max_path_points` (default 100) points |
| `sample_distance_m` | number | no | Sampling interval (> 0), default = dataset `resolution_m` |

Samples are taken at arc-length positions `0, step, 2·step, …` plus the final vertex (haversine, R = 3396.19 km; same as MS4 `PathSampler`). More than `max_samples` (default 1000) → `400`.

### 3.6 `GET /raster/{dataset}/layer/{band}` — Rendered band as PNG

| Param | Type | Required | Description |
|---|---|---|---|
| `band` | path | yes | Band name |
| `colormap` | string | no | One of `slope` (green→yellow→red), `viridis`, `grayscale`; default per band from config (`pendiente_grados` → `slope`, `albedo` → `grayscale`, others → `viridis`) |

Returns an RGBA 8-bit `image/png` of the full dataset extent, one pixel per cell (72×105 for `rejilla`), row 0 = north. The colour range is the configured `value_range` for the band (default `pendiente_grados: 0–35`), else the band's finite min/max. Response headers carry the extent (`X-Raster-Bounds: min_lon,min_lat,max_lon,max_lat`), `X-Raster-CRS` and `X-Raster-Value-Range: min,max` so the frontend can georeference the image as a map overlay and draw a legend.

### Data dependencies (what the service needs)

- `data/gale/processed/rejilla_ruta_90m.tif` — 72 cols × 105 rows, 6 `float32` bands whose canonical names are stored as band descriptions: `pendiente_grados`, `rugosidad_m`, `fraccion_oscura`, `inercia_termica_tiu`, `albedo`, `distancia_duna_m`. Anonymous geographic CRS on the Mars sphere (R = 3 396 190 m), reported as `IAU_2015:49900`; file bounds `[137.345, -4.739427, 137.454322, -4.580]` (inside the nominal AOI); resolution 0.0015183544° (~90 m); nodata NaN; units not stored in the file (come from config).
- Configuration: dataset registry (name → path, band index ↔ name mapping, per-band colormap) via env vars / config file under `MS3_` prefix; `max_window_cells`; `planet_radius_km = 3396.19`. **Paths are never hardcoded** — the package was already relocated once (`data_usar/` → `data/gale/`).

## 4. Outputs (API Contract)

### 4.1 Datasets response `200`

```json
{
  "datasets": [
    {
      "name": "rejilla",
      "path": "data/gale/processed/rejilla_ruta_90m.tif",
      "readable": true
    }
  ]
}
```

### 4.2 Metadata response `200`

```json
{
  "name": "rejilla",
  "crs": "IAU_2015:49900",
  "bounds": [137.345, -4.739427215909189, 137.45432151948057, -4.58],
  "width": 72,
  "height": 105,
  "resolution_deg": { "lon": 0.0015183544372303697, "lat": 0.0015183544372303697 },
  "resolution_m": 90.0,
  "bands": [
    { "index": 1, "name": "pendiente_grados", "unit": "deg", "nodata": null },
    { "index": 2, "name": "rugosidad_m", "unit": "m", "nodata": null }
  ]
}
```

> `bounds` are the file's real bounds. `resolution_m` is the latitude cell size (`resolution_deg.lat · π/180 · R`); the longitude cell size in metres depends on latitude. Band `unit` values come from registry config when the file does not declare them. `nodata` is `null` when the file sentinel is NaN.

### 4.3 Point response `200`

```json
{
  "lat": -4.6,
  "lon": 137.44,
  "values": { "pendiente_grados": 12.7, "rugosidad_m": 0.31 }
}
```

> Nodata cells are reported as `null`. With `band` specified, `values` contains only that band.

### 4.4 Window response `200`

```json
{
  "band": "pendiente_grados",
  "bounds": [137.402, -4.698, 137.448, -4.602],
  "rows": 11,
  "cols": 5,
  "resolution_deg": { "lon": 0.0015183544372303697, "lat": 0.0015183544372303697 },
  "center_lat": -4.65,
  "core": { "row_off": 1, "col_off": 1, "rows": 9, "cols": 3 },
  "cells": [[12.7, 13.1, null]]
}
```

| Field | Description |
|---|---|
| `bounds` | Outer edges of the returned cells (after clipping + halo); for `point` reads it may extend beyond the dataset extent |
| `resolution_deg` | Cell size in degrees (lon, lat) |
| `center_lat` | Latitude used to convert the longitude cell size to metres: mean latitude of the **core** rows (`bbox` forms) or the row-centre latitude of the containing cell (`point` form; the request `lat` when outside the extent) |
| `core` | Slice within `cells` that a plain `bbox` read would return; equals the full array when `halo_cells = 0` or on `point` reads |
| `cells` | 2D array `rows × cols`, nodata → `null`; row 0 is the northernmost |

> Values are the raw `float32` cell values serialised without rounding. `resolution_deg` + `center_lat` are exactly the inputs of MS4's `DemWindowMapper.to_dem_window(...)`, so this payload maps 1:1 onto MS4's `DemWindow`/`HaloWindow` port. MS4 `read_window` → `bbox` request; `read_window_with_halo` → `bbox` + `halo_cells`; `read_window_around` → `point` + `radius_cells`; `ping` → `GET /health`.

### 4.5 Sample response `200`

```json
{
  "band": "rugosidad_m",
  "sample_count": 42,
  "total_distance_m": 4150.0,
  "samples": [
    { "lat": -4.60, "lon": 137.44, "distance_m": 0.0, "value": 0.31 }
  ]
}
```

> Samples on nodata cells or outside the extent report `value: null`. The request fails with `404` only when **every** sample lies outside the extent.

### 4.6 Layer response `200`

`image/png` body + `X-Raster-Bounds`, `X-Raster-CRS: IAU_2015:49900`, `X-Raster-Value-Range` headers. An all-nodata band returns a fully transparent PNG (`200`); a constant band renders the mid-ramp colour.

### 4.7 Error responses

| Code | Condition |
|---|---|
| `400` | Invalid coordinates (lat ∉ [−90, 90], lon ∉ [−180, 180]), inverted bbox or path (< 2 points), both/neither `bbox`+`point`, missing `radius_cells`, limits exceeded, unknown colormap |
| `404` | Unknown dataset or band (`detail` lists the valid names); bbox not intersecting the extent; `/point` outside the extent; `/sample` path fully outside the extent |
| `422` | Malformed request body/types (FastAPI validation) |
| `503` | Dataset file unreadable (missing, corrupt, non-geographic, rotated or not north-up) |

## 5. Business Rules

- All values are returned **verbatim** from the band — no resampling, interpolation, or recomputation. Nearest-cell lookup only.
- All coordinates and distances use the dataset CRS `IAU_2015:49900` and Mars radius **3396.19 km** (59 274.69 m/degree) — never WGS84 constants. MS3 does not reproject; requests arrive already in the dataset CRS.
- Values are serialised as the float64 representation of the stored value — never rounded — so a consumer reading through MS3 gets exactly what a local rasterio read would return.
- `null` is the only nodata representation on the wire; raw sentinel values (NaN, `-9999`, …) never leak into responses.
- Window cell counts are capped by `max_window_cells` (config, default 1 000 000; evaluated on the core window). Oversized requests → `400`, never a partial answer.
- Unknown band names are rejected with `404` and the valid list — consumers depend on the canonical 6 names.
- PNG rendering is a display concern only: nodata → transparent pixel; the numeric endpoints remain the source of truth.

## 6. Non-Functional Requirements

- Offline-capable: reads only local files; zero external calls.
- Point query p95 < 100 ms; window ≤ `max_window_cells` < 500 ms; PNG layer < 1 s (dataset is 72×105 — trivial).
- `GET /health` returning `{"status": "ok"}`, per-dataset `readable` status, and registered dataset count. Doubles as MS4's `ping()`.
- Rasterio file handles are not held across requests (open per read or a bounded read-through cache); safe under uvicorn workers.

## 7. Acceptance Criteria (2-day scope)

1. `/health`, `/raster/datasets`, `/raster/{d}/metadata`, `/raster/{d}/point`, `/raster/{d}/window` (bbox, halo, and point+radius forms), `/raster/{d}/sample`, `/raster/{d}/layer/{band}` implemented and tested.
2. Reading `rejilla_ruta_90m.tif` returns 72×105 and all 6 canonical band names; a known cell returns the file's raw value verbatim; nodata surfaces as `null` (band `fraccion_oscura` has exactly one nodata cell).
3. Window endpoint semantics verified against a small synthetic GeoTIFF fixture: centre-inclusion selection, sub-cell fallback, clipping at edges, `halo_cells` expansion, `core` slice correctness, `center_lat`, and `(2r+1)²` shape with `null` padding for point reads.
4. Contract tests validate request/response schemas and error codes above.
5. MS4 runs with an `HttpRasterDatasource` against MS3 and returns the same `/terrain/point` and `/terrain/area` bodies as its local `rejilla` mode (parity test with exact equality).

## 8. Out of Scope (v0.1)

- XYZ/WMTS tiling, COG overviews, arbitrary client-side bounding boxes on the PNG layer.
- Writes: derived-layer persistence, dataset upload/mutation, catalog versioning (that belongs to MS2 Data Management).
- Serving non-raster data (`.xlsx`, GeoJSON routes, `modelos_por_suelo.json`) — consumers read those directly.
- Auth, rate limiting, multi-body negotiation beyond the registered dataset set.
