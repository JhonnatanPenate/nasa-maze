# nasa-maze — Planetary Explorer

**A "Waze for Mars":** a map-based tool that helps an astronaut plan a safe, science-driven Marswalk in Gale Crater, combining terrain, radiation, temperature and mineral targets from NASA missions.

Built for the **NASA International Space Apps Challenge 2026** — challenge [*Interplanetary Survival Guide: Martian Map*](https://www.spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/).

> 🔗 **Live demo:** _coming soon_ · 📄 License: [Apache 2.0](LICENSE) · 📊 Data sources: [DATA_SOURCES.md](DATA_SOURCES.md)

---

## The problem

NASA has decades of Mars data, but it is not layered together at the scale of a single surface excursion. An astronaut walking from the landing site to a mineral target needs to know, along the route: how steep and rough the ground is, where sand dunes slow them down, how much radiation they accumulate and how cold the surface gets.

## What it does

- Picks a **science target** (hematite, smectites, tridymite) and computes the **lowest-cost route** from Bradbury Landing (Curiosity's landing site).
- Route cost combines time, terrain uncertainty, night waits, soil changes, **radiation dose (RAD)**, **thermal stress (REMS)** and mineral interest.
- Returns the route as GeoJSON plus **segment-by-segment telemetry** (slope, predicted tilt, soil type, dose, ground temperature, local solar time).
- Avoids the **Bagnold Dunes**: the adaptive route is compared against a counterfactual global model.

| Target | Site | Distance | Dose (sol 1360, 09:00 LMST) |
|---|---|---:|---:|
| Hematite | Oudam | 7.73 km | 247.8 μGy |
| Smectites | Glen Etive | 10.3 km | 289.7 μGy |
| Tridymite | Buckskin | 6.71 km | 85.1 μGy |

## NASA data used

| Data | Mission / instrument | Use |
|---|---|---|
| HiRISE DEM (via Mars Trek) | Mars Reconnaissance Orbiter | Slope and roughness |
| Thermal inertia and albedo | Mars Global Surveyor — TES | Soil and surface layers |
| Radiation dose | Curiosity — RAD | Dose along the route |
| Ground temperature | Curiosity — REMS | Thermal stress |
| Mineralogy | Curiosity — CheMin | Science targets |
| Traverse and waypoints | Curiosity (MSL) | Historical layer and calibration |

Full citations and terms of use: **[DATA_SOURCES.md](DATA_SOURCES.md)**. All data is projected on the Mars sphere `IAU_2015:49900` (59 274.69 m per degree), never on Earth CRSs.

## Architecture

Monorepo of Python/FastAPI microservices (see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)):

```
Frontend (map) ──▶ Core ──▶ MS6 Routing Engine ──▶ science/optimizador_rutas.py
                     ├────▶ MS4 Terrain Analysis ──▶ data/gale/processed/rejilla_ruta_90m.tif
                     └────▶ MS5 Risk Assessment ──▶ RAD / REMS tables
```

| Folder | What | Status |
|---|---|---|
| `science/` | Route optimizer (A*, mission cost function) and soil models | ✅ |
| `data/gale/` | Processed Gale Crater dataset (90 m grid, 6 bands; routes; RAD/REMS) | ✅ |
| `location-service/` | **MS1** — place search → planetocentric coordinates | ✅ |
| `raster-service/` | **MS3** — raster access API (bands, point/sample) | ✅ |
| `terrain-analysis/` | **MS4** — slope, profile and area analysis API | ✅ |
| `risk-assessment/` | **MS5** — normalized point/path/area risk (SPEC_MS5 + extensions) | ✅ code + 293 tests; 🐳 docker run pending |
| `routing-engine/` | **MS6** — wraps `science/optimizador_rutas.py` | ✅ |
| Core, frontend, Data Management (MS2) | Orchestration, map UI, dataset registry | 🚧 in progress |

**Tech:** Python 3.12 · FastAPI · rasterio/GDAL · numpy/pandas/scipy · R (soil models) · Docker · GitHub Actions · Google Cloud.

## Run it locally

Requirements: Python 3.12+.

```bash
git clone https://github.com/JhonnatanPenate/nasa-maze.git
cd nasa-maze

# Compute a route with the scientific optimizer
pip install numpy pandas rasterio scipy openpyxl matplotlib
python science/optimizador_rutas.py --datos data/gale --material hematita --sol 1360 --hora 9 --salida /tmp/route

# MS4 Terrain Analysis API (Docker)
cd terrain-analysis
docker build -t ms4-terrain-analysis .
docker run --rm -p 8004:8004 -v "$(pwd)/../data:/data:ro" ms4-terrain-analysis
# → http://localhost:8004/docs
```

## Team

| Member | Role |
|---|---|
| Javier Galdámez ([@JavyGG04](https://github.com/JavyGG04)) | Science & data: optimizer, soil models, Gale dataset |
| Armando Salgado ([@Armando-J-Salgado](https://github.com/Armando-J-Salgado)) | MS4 Terrain Analysis |
| Alex Alas ([@Alex-Alas](https://github.com/Alex-Alas)) | AI agents setup & docs |
| Jhonnatan Peñate ([@JhonnatanPenate](https://github.com/JhonnatanPenate)) | Repository, CI/CD, cloud deployment, MS6 Routing Engine |

## Contributing

`feature/*`, `fix/*` or `docs/*` branch from `development` → PR to `development` (the `tests` check must pass) → release PR `development` → `main`. Conventional commits (`feat:`, `fix:`, `docs:`).

## Use of AI

AI coding assistants were used and are declared in [docs/ai/USO-DE-IA.md](docs/ai/USO-DE-IA.md).

## License and disclaimer

Code: [Apache License 2.0](LICENSE) — see also [NOTICE](NOTICE) and [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). Data keeps its own terms ([DATA_SOURCES.md](DATA_SOURCES.md)).

**This project is not endorsed, sponsored or approved by NASA.** "NASA" refers only to the Space Apps Challenge; no NASA logos are used.
