# MS6 Routing Engine

FastAPI service (port `8006`) that computes the **lowest-cost Marswalk** from an origin in Gale Crater to the best outcrop of a requested mineral. It wraps the team's scientific optimizer (`science/optimizador_rutas.py`, A* over a 90 m grid) without changing it.

The route cost combines walking time, terrain uncertainty, night waits, soil changes, accumulated radiation dose (Curiosity RAD), thermal stress (Curiosity REMS) and mineral interest. Distances use the Mars sphere `IAU_2015:49900` (59 274.69 m per degree).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness, available sols and the Gale AOI |
| POST | `/route` | Compute a route (body below) |
| GET | `/docs` | Interactive OpenAPI docs |

### `POST /route`

```json
{ "lon": 137.4416, "lat": -4.5895, "material": "hematita", "sol": 1360, "hora": 9, "vmax": 1000 }
```

All fields are optional; the defaults above are Bradbury Landing (Curiosity's landing site) at sol 1360, 09:00 local mean solar time, 1000 m/h. JSON field names are in Spanish because they are the contract shared with the science package and Core.

| Field | Meaning |
|---|---|
| `lon`, `lat` | Origin (degrees), must be inside the Gale AOI `[137.345, -4.740, 137.455, -4.580]` |
| `material` | `hematita` (hematite), `esmectitas` (smectites), `tridimita` (tridymite), `sulfatos` (sulfates) |
| `sol` | RAD/REMS reference sol: `1360`, `2140`, `3290`, `4710` |
| `hora` | Departure time, LMST hours `[0, 24)` |
| `vmax` | Nominal walking speed (m/h) |

Response `200`: `{geojson, resumen, tramos, control_calidad}`

- `geojson`: FeatureCollection with layers `ruta_optima` (route segments), `contrafactual` (global-model route), `objetivo` (target) and `origen` (origin).
- `resumen`: KPIs (distance in km, arrival LMST, RAD dose in μGy, night wait hours, Bagnold Dunes comparison).
- `tramos`: segment-by-segment telemetry (soil type, tilt, dose, ground temperature, LMST).
- `control_calidad`: grid quality-control report.

Full real example: [`docs/data/EJEMPLO_API_RESPUESTA.json`](../docs/data/EJEMPLO_API_RESPUESTA.json).

Errors: `400` sol not supported or origin outside the AOI · `422` invalid body (e.g. unknown material) or failed quality check · `404` no feasible route.

Reference results (Bradbury, sol 1360, 09:00):

| Target | Site | Distance | Dose |
|---|---|---:|---:|
| Hematite | Oudam | 7.73 km | 247.8 μGy |
| Smectites | Glen Etive | 10.3 km | 289.7 μGy |
| Tridymite | Buckskin | 6.71 km | 85.1 μGy |

## Performance

An uncached route takes ~1–15 s, and requests are serialized by a lock because the optimizer uses module globals. Results are cached in memory (64 entries), and the three reference routes are pre-computed at startup, so startup takes a few seconds (~5 s locally) and the default demo routes answer in ~0.2 s.

## Run locally

Python 3.12+:

```bash
cd routing-engine
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash; use .venv/bin/activate on Linux/macOS
pip install -e ".[dev]"
pytest -q
uvicorn app.main:app --port 8006
# → http://localhost:8006/docs
```

## Docker

Build from the repository root (the image needs `science/` and `data/gale/`, which are baked in):

```bash
docker build -f routing-engine/Dockerfile -t ms6 .
docker run --rm -p 8006:8006 ms6
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `MS6_DATA_DIR` | `data/gale` (image: `/data/gale`) | Gale data package; relative paths resolve from the repo root |
| `MS6_SCIENCE_DIR` | `science` (image: `/app/science`) | Folder containing `optimizador_rutas.py` |

## Data

Processed Gale Crater package (90 m grid, soil models, CheMin targets, RAD/REMS). Sources and terms: [`DATA_SOURCES.md`](../DATA_SOURCES.md).
