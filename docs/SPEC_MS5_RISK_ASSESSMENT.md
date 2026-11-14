# Spec: Risk Assessment Service (MS5)
**Version:** 0.2.0 | **Status:** Draft — realigned with `data_usar/` package | **Date:** 2026-11-14 | **Effort target:** 2 days (spec-driven development)

> **v0.2 changes:** the delivered package provides real environmental layers — `rejilla_ruta_90m.tif` bands (`rugosidad_m`, `fraccion_oscura`, `inercia_termica_tiu`, `albedo`, `distancia_duna_m`) plus hourly RAD dose and REMS thermal profiles per sol. The factor catalog expands beyond `slope/temperature/radiation`, and requests may carry `sol`/`hora` to select the environmental profile.

## 1. Service Identity

| Field | Value |
|---|---|
| Name | Risk Assessment Service |
| ID | MS5 |
| Stack | Python + FastAPI |
| Depends on | Terrain Analysis Service (MS4), Raster Service (MS3) for environmental layers |
| Consumed by | Core, Routing Engine (MS6) |

## 2. Purpose

Evaluates geographic and environmental risks that may affect traversal between two locations. Given a candidate path (or point), it produces a normalized risk score plus human-readable warnings, combining terrain hazards (slope, steep drops) with environmental factors (temperature extremes, radiation — when datasets are available).

This service is the single source of truth for "how dangerous is this segment?" so the Routing Engine can penalize risky edges and Core can display warnings.

## 3. Inputs (API Contract)

Base URL: `/risk`

### 3.1 `POST /risk/evaluate` — Risk evaluation along a path

```json
{
  "body": "mars",
  "path": [ {"lat": -4.60, "lon": 137.44}, {"lat": -4.65, "lon": 137.42} ],
  "factors": ["slope", "roughness", "dunes", "temperature", "radiation"],
  "sol": 1360,
  "hora": 9
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `path` | array of {lat, lon} | yes | Polyline, min 2 points |
| `factors` | array of string | no | Subset of the catalog below; default all available |
| `sol` | int | no | Reference sol for hourly RAD/REMS profiles (typical: `1360`, `2140`, `3290`, `4710`); nearest available sol is used, echoed in response |
| `hora` | int | no | Hour LMST (0–23) for selecting the hourly environmental profile; default `12` |
| `body` | string | no | Celestial body, default `mars` |

**Factor catalog (v0.2):**

| Factor | Source | Notes |
|---|---|---|
| `slope` | MS4 `/terrain/profile` | Slope in degrees |
| `roughness` | GeoTIFF band `rugosidad_m` | Surface roughness |
| `dunes` | GeoTIFF bands `distancia_duna_m`, `fraccion_oscura` | Proximity to Bagnold dunes / dark sand fraction |
| `temperature` | `raw/ambiental/rems_resumen_horario.csv` (+ band `inercia_termica_tiu` for terrain coupling) | Hourly ground/air temp |
| `radiation` | `raw/ambiental/rad_dosis_observaciones.csv` | Hourly dose rate μGy/h; segment dose = rate × traversal time when MS6 provides it |

### 3.2 `GET /risk/point?lat=..&lon=..` — Risk at a single point

### 3.3 `GET /risk/factors` — Lists available risk factors and which have data coverage

### Data dependencies (what the service needs)

- Slope values per sampled point — obtained by calling MS4 `/terrain/profile`.
- Terrain bands (`rugosidad_m`, `fraccion_oscura`, `inercia_termica_tiu`, `albedo`, `distancia_duna_m`) via the raster datasource (MS3 or local file behind a swappable datasource, same pattern as MS4).
- Environmental CSVs (`rad_dosis_observaciones.csv`, `rems_resumen_horario.csv`) — loaded as hourly profiles keyed by sol/hora.
- All layers **optional**: if a layer is missing, that factor is skipped with `available: false`.
- Configuration: risk weights and thresholds per factor (see §5); dataset paths via env vars (paths may change when the data team reorganizes).

## 4. Outputs (API Contract)

### 4.1 Evaluate response `200`

```json
{
  "overall_risk": 0.62,
  "risk_level": "high",
  "segments": [
    {
      "from": {"lat": 18.4, "lon": 77.5},
      "to": {"lat": 18.45, "lon": 77.55},
      "risk": 0.71,
      "factor_scores": {
        "slope": {"score": 0.8, "available": true},
        "temperature": {"score": 0.5, "available": true},
        "radiation": {"score": null, "available": false}
      },
      "warnings": ["STEEP_SLOPE_28DEG"]
    }
  ],
  "warnings_summary": ["STEEP_SLOPE_28DEG", "EXTREME_COLD_ZONE"]
}
```

| Field | Description |
|---|---|
| `overall_risk` | Weighted mean of segment risks, 0.0 (safe) – 1.0 (impassable) |
| `risk_level` | `low` < 0.25, `medium` 0.25–0.5, `high` 0.5–0.75, `critical` ≥ 0.75 |
| `factor_scores[].available` | `false` when the dataset for that factor is missing; excluded from weighting |
| `warnings` | Machine-readable warning codes for Core/UI display |

### 4.2 Point response `200`

```json
{
  "lat": 18.4, "lon": 77.5,
  "risk": 0.4, "risk_level": "medium",
  "factor_scores": { "slope": {"score": 0.4, "available": true} },
  "warnings": []
}
```

### 4.3 Error responses

| Code | Condition |
|---|---|
| `400` | Invalid path/factors |
| `404` | No coverage at requested location |
| `502` | MS4 or Raster Service unavailable |

## 5. Business Rules

- Each factor is normalized to [0, 1] via configurable thresholds (e.g., slope: 0 at ≤5°, 1 at ≥30°, linear between).
- Overall segment risk = weighted average over **available** factors; weights in config (default: slope 0.4, dunes 0.2, roughness 0.15, temperature 0.15, radiation 0.1).
- If no factors are available, return `overall_risk: null`, `risk_level: "unknown"` — never silently zero.
- Warning codes are emitted when a factor crosses its configured warning threshold. Suggested codes with delivered data: `STEEP_SLOPE_NDEG`, `BAGNOLD_DUNES_NEARBY` (distancia_duna below threshold), `HIGH_ROUGHNESS`, `EXTREME_COLD_ZONE`, `HIGH_RADIATION_RATE`.

## 6. Non-Functional Requirements

- Offline-capable; only calls other internal services.
- Evaluation of a 50-segment path < 3 s (one batched call to MS4, not per-segment).
- `GET /health` reporting MS4/raster connectivity.

## 7. Acceptance Criteria (2-day scope)

1. `/health`, `/risk/point`, `/risk/evaluate`, `/risk/factors` implemented.
2. Slope factor works end-to-end via MS4 on the test DEM; missing environmental layers degrade gracefully (`available: false`).
3. Weights/thresholds externalized in config file.
4. Contract tests validate schemas and the "unknown risk" rule in §5.

## 8. Out of Scope (v0.2)

- Weather forecasts, dust storm modeling, custom per-user risk profiles.
- Route-time-dependent accumulation (e.g., total dose over the route) remains MS6's job; MS5 scores per-segment rates using the requested `sol`/`hora` profile.
