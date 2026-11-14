# Spec: Risk Assessment Service (MS5)
**Version:** 0.1.0 | **Status:** Draft | **Date:** 2026-11-14 | **Effort target:** 2 days (spec-driven development)

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
  "path": [ {"lat": 18.4, "lon": 77.5}, {"lat": 18.5, "lon": 77.6} ],
  "factors": ["slope", "temperature", "radiation"]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `path` | array of {lat, lon} | yes | Polyline, min 2 points |
| `factors` | array of string | no | Subset of `slope`, `temperature`, `radiation`; default all available |
| `body` | string | no | Celestial body, default `mars` |

### 3.2 `GET /risk/point?lat=..&lon=..` — Risk at a single point

### 3.3 `GET /risk/factors` — Lists available risk factors and which have data coverage

### Data dependencies (what the service needs)

- Slope/elevation values per sampled point — obtained by calling MS4 `/terrain/profile`.
- Environmental raster layers (temperature, radiation) via Raster Service, **optional**: if a layer is missing, that factor is skipped with `available: false`.
- Configuration: risk weights and thresholds per factor (see §5).

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
- Overall segment risk = weighted average over **available** factors; weights in config (default: slope 0.6, temperature 0.2, radiation 0.2).
- If no factors are available, return `overall_risk: null`, `risk_level: "unknown"` — never silently zero.
- Warning codes are emitted when a factor crosses its configured warning threshold.

## 6. Non-Functional Requirements

- Offline-capable; only calls other internal services.
- Evaluation of a 50-segment path < 3 s (one batched call to MS4, not per-segment).
- `GET /health` reporting MS4/raster connectivity.

## 7. Acceptance Criteria (2-day scope)

1. `/health`, `/risk/point`, `/risk/evaluate`, `/risk/factors` implemented.
2. Slope factor works end-to-end via MS4 on the test DEM; missing environmental layers degrade gracefully (`available: false`).
3. Weights/thresholds externalized in config file.
4. Contract tests validate schemas and the "unknown risk" rule in §5.

## 8. Out of Scope (v0.1)

- Weather forecasts, dust storm modeling, time-of-day-dependent risk, custom per-user risk profiles.
