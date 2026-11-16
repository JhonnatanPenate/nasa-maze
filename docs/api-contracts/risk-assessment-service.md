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
  "risk": 0.347, "risk_level": "medium",
  "factor_scores": {
    "slope":      {"score": 0.423, "available": true},
    "roughness":  {"score": 0.275, "available": true},
    "dunes":      {"score": 0.473, "available": true},
    "temperature":{"score": 0.0,   "available": true},
    "radiation":  {"score": 0.417, "available": true}
  },
  "warnings": ["STEEP_SLOPE_16DEG"],
  "sol": 1360, "hora": 9,
  "confidence": "high",
  "provenance": {"reference_sol": 1360, "rems_sol": 1360, "rad_sol": 1360,
                 "scoring": "ms5-risk-v0.1", "include_hourly": false},
  "data_quality_notes": [],
  "assumptions": ["..."]
}
```

- `sol` is echoed as the *reference* sol; `provenance` reports the
  nearest available sol actually used **per dataset** (REMS and RAD cover
  different sol sets).
- `hora` omitted → all 24 LMST hours evaluated, worst result returned;
  add `include_hourly=true` for the per-hour breakdown (`by_hour`).
- `factors=slope,temperature` restricts the catalog subset.
- `score`/`risk` are real normalized values (Phase 4 wiring); a factor
  with no coverage reports `available: false`, `score: null` and is
  excluded from the weighted mean — never scored as safe (SPEC §5).

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
  "overall_risk": 0.515,
  "risk_level": "high",
  "segments": [
    {
      "from": {"lat": -4.60, "lon": 137.44},
      "to":   {"lat": -4.604, "lon": 137.4396},
      "distance_m": 90.0,
      "risk": 0.592,
      "factor_scores": {"slope": {"score": 0.964, "available": true}, "...": "..."},
      "warnings": ["STEEP_SLOPE_29DEG"],
      "local_time_hour": 9
    }
  ],
  "warnings_summary": ["STEEP_SLOPE_29DEG", "..."],
  "sol": 1360, "hora": 9, "total_distance_m": 3190.6,
  "max_level": "high", "mean_score": 0.513, "p95_score": 0.588,
  "dominant_factor": "slope",
  "total_duration_s": 17200.8, "end_local_time_hours": 13.78,
  "confidence": "high",
  "provenance": {"reference_sol": 1360, "rems_sol": 1360, "rad_sol": 1360,
                 "scoring": "ms5-risk-v0.1",
                 "vehicle_profile": "baseline_mars_rover",
                 "sampling_step_m": 90.0,
                 "thermal_excess_Kh": 0.0},
  "data_quality_notes": [],
  "assumptions": ["..."],
  "restrictions": [{"segment": 0, "code": "SLOPE_BLOCK", "blocking": true,
                    "message": "Slope 29.1 deg >= profile block limit 25.0 deg",
                    "factor": "slope", "value": 29.09, "limit": 25.0}],
  "hotspots": [{"segment": 0, "risk": 0.592, "level": "high", "distance_m": 90.0}],
  "blocking_segments": [0, 1, 2]
}
```

- Segments are the intervals between arc-length samples (~`sampling_step_m`,
  default 90 m — the rejilla grid pitch). MS4 `/terrain/profile` is called
  once per path and MS3 `/sample` once per required band (SPEC §6 NFR).
- `overall_risk` is the distance-weighted mean of segment risks; all
  unscored → `null` + `"unknown"` (SPEC §5 — never a silent zero).
- `hora` is the **departure** LMST bin; each segment's `local_time_hour`
  advances by `distance / effective_speed` hours with mod-24 wrap
  (Javi's 24-bin convention). `end_local_time_hours` is the wrapped
  arrival time. `speed_mps` overrides the vehicle effective speed.
- Radiation is a per-segment **rate** only — MS5 never accumulates route
  dose (that is MS6's job, SPEC §8).
- Additive plan fields: `sampling_step_m`, `vehicle_profile`, `speed_mps`
  (request); `total_distance_m`, `max_level`, `mean_score`, `p95_score`,
  `dominant_factor`, `total_duration_s`, `end_local_time_hours`,
  `confidence` (`high|medium|low`), `provenance`, `data_quality_notes`,
  `assumptions`, `restrictions`, `hotspots`, `blocking_segments`,
  per-segment `local_time_hour` (response). None alter the SPEC formula;
  restrictions never force `critical`.

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

`/risk/area` evaluates the SPEC weighted risk on a regular ~90 m grid
covering the bbox (one MS4 slope read + one MS3 point read per cell) and
returns aggregate statistics only — `level_counts`, `blocked_fraction`,
`mean_score`/`p95_score`, per-factor `factor_stats`, `hotspots` (capped at
100), plus additive `confidence`/`uncovered_cells`/`provenance`/
`data_quality_notes`. It never returns a per-cell raster. The request
`max_cells`/`RISK_MAX_AREA_CELLS` cap still applies (422
`AREA_TOO_LARGE`); cells outside coverage count as `unknown`. Cost is
O(2·cells) upstream point reads — keep bboxes modest.

## 6. Modes

`RISK_DATASOURCE_MODE` selects the upstream adapters for **both** MS3 and
MS4: `synthetic` (deterministic in-process fakes, default), `http`
(`RISK_RASTER_BASE_URL`/`RISK_TERRAIN_BASE_URL`), `unavailable` (all reads
fail → factors `available: false`, `/health` degraded, reads → 502).
The REMS/RAD climatology is always the local SQLite catalog built by
`python -m app.ingest` (Phase 2); absent → temperature/radiation report
`available: false`.
