# Spec: Terrain Analysis Service (MS4)
**Version:** 0.1.0 | **Status:** Draft | **Date:** 2026-11-14 | **Effort target:** 2 days (spec-driven development)

## 1. Service Identity

| Field | Value |
|---|---|
| Name | Terrain Analysis Service |
| ID | MS4 |
| Stack | Python + FastAPI, Rasterio/GDAL |
| Depends on | Raster Service (MS3) for access to geospatial files |
| Consumed by | Core, Routing Engine (MS6), Risk Assessment Service (MS5) |

## 2. Purpose

Analyzes the physical characteristics of the terrain along a point, path, or area on a planetary body (MVP: single body, e.g. Mars). It converts raw elevation data into navigation-relevant derived products: slope, elevation profile, and terrain classification (flat, moderate, steep, crater rim, rocky).

All heavy raster access goes through the Raster Service; this service only computes derived values and may optionally persist derived layers (e.g., a slope GeoTIFF) back into shared storage.

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

- Elevation DEM (GeoTIFF) exposed via Raster Service query endpoints.
- Dataset metadata (CRS, resolution, nodata value) from Raster Service catalog.
- Configuration: slope thresholds (see §5), sampling limits (max path length, max samples).

## 4. Outputs (API Contract)

### 4.1 Point analysis response `200`

```json
{
  "lat": 18.4,
  "lon": 77.5,
  "elevation_m": -2540.3,
  "slope_deg": 12.7,
  "terrain_class": "moderate"
}
```

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

- Slope is computed from DEM using Horn's method (or GDAL `gdaldem slope` equivalent), in degrees.
- `terrain_class` mapping (configurable): `flat` < 5°, `moderate` 5–15°, `steep` 15–30°, `hazardous` ≥ 30°.
- All output coordinates echo the input CRS (planetocentric lat/lon for MVP).

## 6. Non-Functional Requirements

- Offline-capable once datasets are prepared (no external calls except Raster Service).
- Point query p95 < 200 ms; profile of 100 samples < 2 s.
- `GET /health` endpoint returning `{"status": "ok"}` and raster connectivity status.

## 7. Acceptance Criteria (2-day scope)

1. `/health`, `/terrain/point`, `/terrain/profile` implemented and tested (`/terrain/area` is stretch).
2. Derived slope computed correctly against a known test DEM fixture.
3. Service runs via Docker Compose and queries Raster Service for DEM data.
4. Contract tests validate request/response schemas above.

## 8. Out of Scope (v0.1)

- Rock/crater detection from imagery; real-time derived-layer persistence; multi-body support.
