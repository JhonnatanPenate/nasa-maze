# Risk Assessment Service API — usage examples

Contract: `packages/contracts/risk-assessment/openapi.yaml`.
Authoritative spec: `docs/SPEC_MS5_RISK_ASSESSMENT.md` (v0.2.1).
Base URL: `http://localhost:8005`. All coordinates are planetocentric
`IAU_2015:49900`, east-positive longitude in **[-180, 180]** (the MS3/MS4
wire convention — not the 0..360 used by the location catalog).

Error bodies use the shared MS3/MS4 shape `{"detail": "..."}`; plan-named
codes are prefixed into the string (e.g. `AREA_TOO_LARGE: ...`).

| Code | Condition |
|---|---|
| 400 | Invalid path/factors/coordinates/`hora`/`sol` |
| 404 | No coverage at the requested location; unknown `vehicle_profile` (`VEHICLE_PROFILE_NOT_FOUND`) |
| 422 | `AREA_TOO_LARGE` — `/risk/area` exceeds the cell cap |
| 502 | MS3/MS4 unreachable or failing |
| 503 | Environmental catalog configured but unreadable |
| 500 | `INTERNAL_ERROR` — sanitized, never leaks internals |

## 1. Health (SPEC §6)

```bash
curl -s http://localhost:8005/health | jq
# {"status":"ok","datasource_mode":"synthetic",
#  "terrain":"ok","raster":"ok","environment":"ok"}
```

Always 200 while the process is alive; unreachable upstreams degrade the
status (`degraded` + `unavailable`) instead of erroring.

## 2. Risk at a point (SPEC §3.2/§4.2)

```bash
curl -s 'http://localhost:8005/risk/point?lat=-4.62&lon=137.40&sol=1360&hora=9' | jq
```

```json
{
  "lat": -4.62, "lon": 137.40,
  "risk": null, "risk_level": "unknown",
  "factor_scores": {
    "slope":      {"score": null, "available": true},
    "roughness":  {"score": null, "available": true},
    "dunes":      {"score": null, "available": true},
    "temperature":{"score": null, "available": true},
    "radiation":  {"score": null, "available": true}
  },
  "warnings": [],
  "sol": 1360, "hora": 9,
  "provenance": {"reference_sol": 1360, "rems_sol": 1360, "rad_sol": 1360,
                 "scoring": "pending-phase-3", "include_hourly": false}
}
```

- `sol` is echoed as the *reference* sol; `provenance` reports the
  nearest available sol actually used **per dataset** (REMS and RAD cover
  different sol sets).
- `hora` omitted → all 24 LMST hours evaluated, worst result returned;
  add `include_hourly=true` for the per-hour breakdown (`by_hour`).
- `factors=slope,temperature` restricts the catalog subset.
- Phase 1: `score`/`risk` are `null` and `risk_level` is `"unknown"` —
  scoring lands in Phase 3; `available` already reflects real coverage.

## 3. Risk along a path (SPEC §3.1/§4.1)

```bash
curl -s -X POST http://localhost:8005/risk/evaluate \
  -H 'Content-Type: application/json' \
  -d '{
    "body": "mars",
    "path": [{"lat": -4.60, "lon": 137.44}, {"lat": -4.65, "lon": 137.42}],
    "factors": ["slope", "roughness", "dunes", "temperature", "radiation"],
    "sol": 1360,
    "hora": 9
  }' | jq
```

```json
{
  "overall_risk": null,
  "risk_level": "unknown",
  "segments": [
    {
      "from": {"lat": -4.60, "lon": 137.44},
      "to":   {"lat": -4.604, "lon": 137.4396},
      "distance_m": 90.0,
      "risk": null,
      "factor_scores": {"slope": {"score": null, "available": true}, "...": "..."},
      "warnings": []
    }
  ],
  "warnings_summary": [],
  "sol": 1360, "hora": 9, "total_distance_m": 9052.3,
  "provenance": {"reference_sol": 1360, "rems_sol": 1360, "rad_sol": 1360,
                 "scoring": "pending-phase-3",
                 "vehicle_profile": "baseline_mars_rover",
                 "sampling_step_m": 90.0}
}
```

- Segments are the intervals between arc-length samples (~`sampling_step_m`,
  default 90 m — the rejilla grid pitch). MS4 `/terrain/profile` is called
  once per path and MS3 `/sample` once per required band (SPEC §6 NFR).
- `overall_risk` is the distance-weighted mean of segment risks; all
  unscored → `null` + `"unknown"` (SPEC §5 — never a silent zero).
- Additive plan fields: `sampling_step_m`, `vehicle_profile`, `speed_mps`
  (request); `total_distance_m`, `max_level`, `provenance`, `assumptions`,
  `restrictions`, `hotspots`, `blocking_segments` (response). None alter
  the SPEC formula; restrictions never force `critical`.

## 4. Factor catalog + coverage (SPEC §3.3)

```bash
curl -s http://localhost:8005/risk/factors | jq
```

Returns the five SPEC factors with `weight` (SPEC §5 defaults:
slope .4, dunes .2, roughness .15, temperature .15, radiation .1), live
`available` flags, data `sources`, and `environmental_sols` per dataset.

## 5. Plan extensions (additive — not in SPEC)

```bash
curl -s http://localhost:8005/risk/vehicle-profiles | jq   # configured profiles
curl -s http://localhost:8005/risk/meta | jq               # weights/thresholds/provenance
curl -s -X POST http://localhost:8005/risk/area \
  -H 'Content-Type: application/json' \
  -d '{"bbox": [137.345, -4.740, 137.455, -4.580], "hora": 12}' | jq
```

`/risk/area` is a Phase 1 stub: it validates the bbox, enforces
`max_cells`/`RISK_MAX_AREA_CELLS` (422 `AREA_TOO_LARGE`), and returns
`aggregation: "pending"` until Phase 5 implements per-cell evaluation.

## 6. Modes

`RISK_DATASOURCE_MODE` selects the upstream adapters for **both** MS3 and
MS4: `synthetic` (deterministic in-process fakes, default), `http`
(`RISK_RASTER_BASE_URL`/`RISK_TERRAIN_BASE_URL`), `unavailable` (all reads
fail → factors `available: false`, `/health` degraded, reads → 502).
The REMS/RAD climatology is always the local SQLite catalog built by
`python -m app.ingest` (Phase 2); absent → temperature/radiation report
`available: false`.
