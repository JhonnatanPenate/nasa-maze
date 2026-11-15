# Spec: Terrain Analysis Service (MS4)
**Version:** 0.2.1 | **Status:** Draft — realigned with `data/gale/` package | **Date:** 2026-11-14 | **Effort target:** 2 days (spec-driven development)

> **v0.2 changes:** the delivered data package provides slope **pre-computed** (`pendiente_grados`, band 1 of `data/gale/processed/rejilla_ruta_90m.tif`) and no elevation band. MS4 keeps its API contract but gains a second mode: read slope directly from the delivered grid when no DEM is available. Mars radius fixed to 3396.19 km (IAU_2015:49900). See `docs/terrain_analysis/REALIGNMENT_PLANMS4_1.md`.
>
> **v0.2.1:** data package relocated to `data/gale/` (tabular data is `.xlsx`-only, no CSV — irrelevant to MS4, which only reads the GeoTIFF). Dataset path via `MS4_REJILLA_PATH`; default `data/gale/processed/rejilla_ruta_90m.tif`.

## 1. Service Identity

| Field | Value |
|---|---|
| Name | Terrain Analysis Service |
| ID | MS4 |
| Stack | Python + FastAPI, Rasterio/GDAL |
| Depends on | Raster Service (MS3) for access to geospatial files (MVP: local datasource, swappable) |
| Consumed by | Core, Routing Engine (MS6), Risk Assessment Service (MS5) |

## 2. Purpose

Analyzes the physical characteristics of the terrain along a point, path, or area on a planetary body (MVP: Mars, Gale crater AOI). It converts terrain data into navigation-relevant products: slope, elevation profile (when a DEM is available), and terrain classification (flat, moderate, steep, hazardous).

Two data modes, selected by configuration:

- **DEM mode** (original): slope computed from elevation via Horn's method.
- **Grid mode** (delivered package): slope read from band `pendiente_grados` of `rejilla_ruta_90m.tif`; `elevation_m` is reported as `null` until the source DEM is delivered.

All heavy raster access goes through a swappable `RasterDatasource`; this service only computes derived values and may optionally persist derived layers back into shared storage.

## 3. Inputs (API Contract)

Base URL: `/terrain`

### 3.1 `GET /terrain/point` — Point analysis

| Param | Type | Required | Description |
|---|---|---|---|
| `lat` | float | yes | Planetocentric latitude |
| `lon` | float | yes | Planetocentric longitude |
| `body` | string | no | Celestial body, default `mars` |

### 3.2 `POST /terrain/profile` — Elevation/slope profile along a path

```json
{
  "body": "mars",
  "path": [ {"lat": 18.4, "lon": 77.5}, {"lat": 18.5, "lon": 77.6} ],
  "sample_distance_m": 100
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `path` | array of {lat, lon} | yes | Polyline, min 2 points |
| `sample_distance_m` | number | no | Sampling interval, default 100 m |

### 3.3 `POST /terrain/area` — Aggregate stats over a bounding box / polygon

```json
{
  "body": "mars",
  "bbox": [min_lon, min_lat, max_lon, max_lat]
}
```

### Data dependencies (what the service needs)

- **Grid mode (delivered):** `data/gale/processed/rejilla_ruta_90m.tif` band `pendiente_grados` (and optionally other bands for future enrichment), CRS `IAU_2015:49900`, bounds `[137.345, -4.740, 137.455, -4.580]`.
- **DEM mode (pending):** elevation DEM (GeoTIFF) exposed via Raster Service / datasource — requested from the data team; spec assumes it will arrive with the same CRS/extent family.
- Configuration: slope thresholds (see §5), sampling limits, `planet_radius_km = 3396.19` (mandatory IAU_2015:49900).

## 4. Outputs (API Contract)

### 4.1 Point analysis response `200`

```json
{
  "lat": -4.6,
  "lon": 137.44,
  "elevation_m": -2540.3,
  "slope_deg": 12.7,
  "terrain_class": "moderate"
}
```

> `elevation_m` is `null` when the active datasource is the delivered grid (no elevation band). `slope_deg` and `terrain_class` are always populated.

### 4.2 Profile response `200`

```json
{
  "sample_count": 42,
  "total_distance_m": 4150.0,
  "elevation_gain_m": 120.5,
  "elevation_loss_m": 80.2,
  "max_slope_deg": 28.4,
  "samples": [
    { "lat": 18.4, "lon": 77.5, "distance_m": 0.0, "elevation_m": -2540.3, "slope_deg": 12.7 }
  ]
}
```

### 4.3 Area response `200`

```json
{
  "elevation_m": { "min": -2600.0, "max": -2100.0, "mean": -2350.4 },
  "slope_deg": { "min": 0.0, "max": 45.0, "mean": 9.8 },
  "steep_fraction": 0.12
}
```

### 4.4 Error responses

| Code | Condition |
|---|---|
| `400` | Invalid coordinates, bbox, or path (< 2 points, limits exceeded) |
| `404` | No raster coverage at requested location (nodata) |
| `502` | Raster Service unavailable or returned error |

## 5. Business Rules

- Slope is computed from DEM using Horn's method (or GDAL `gdaldem slope` equivalent), in degrees — **or** read directly from the `pendiente_grados` band when operating on the delivered grid. The service must not recompute slope differently than the delivered band when that band is the source of truth.
- `terrain_class` mapping (configurable): `flat` < 5°, `moderate` 5–15°, `steep` 15–30°, `hazardous` ≥ 30°.
- All output coordinates echo the input CRS (planetocentric lat/lon, `IAU_2015:49900`).
- Distances use Mars radius **3396.19 km** (59 274.69 m/degree) — never WGS84 constants.

## 6. Non-Functional Requirements

- Offline-capable once datasets are prepared (no external calls except Raster Service).
- Point query p95 < 200 ms; profile of 100 samples < 2 s.
- `GET /health` endpoint returning `{"status": "ok"}` and raster connectivity status.

## 7. Acceptance Criteria (2-day scope)

1. `/health`, `/terrain/point`, `/terrain/profile`, `/terrain/area` implemented and tested.
2. Derived slope computed correctly against a known test DEM fixture (DEM mode) **and** slope read correctly from `rejilla_ruta_90m.tif` band 1 (grid mode).
3. Service runs offline against the delivered data package (datasource selected via `MS4_DATASOURCE_KIND`; `rejilla` | `synthetic` | `geotiff`; `http` reserved for MS3).
4. Contract tests validate request/response schemas above, including `elevation_m: null` in grid mode.

## 8. Out of Scope (v0.2)

- Rock/crater detection from imagery; real-time derived-layer persistence; multi-body support.
- Recomputing slope/roughness science already produced by the data team (bands 2–6 belong to MS5/MS6 consumers).
