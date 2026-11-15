# Implementation Plan — Microservice 01: Location Service (Mars)

> **Audience:** development agent (LLM or human) that will autonomously build this service.
> **Project:** Planetary Explorer (microservices monorepo).
> **Celestial body scope:** **Mars** only. The design leaves room for the Moon, but it is not implemented.
> **MVP demo area:** Gale crater (routes from Bradbury Landing to Oudam, Glen Etive, and Buckskin).

---

## 0. Agent working rules

1. **Do not invent data.** Never use memory for coordinates of a global Martian feature: obtain them from the official Gazetteer (section 3) or project files. If data is missing, report it in the ingestion log and continue.
2. **Do not touch other services.** Write only under `location-service/` and `data/processed/mars/location/`. Do not read other services' databases.
3. **Contracts first.** Write and validate the OpenAPI contract (section 6) before implementing logic. Other contributors depend on it.
4. **Offline first.** At runtime, the service makes no Internet requests. Only optional ingestion reads local files.
5. **Fixed conventions** (section 3.2). Resolve any longitude/latitude questions using that section.
6. **Every task in section 11 has acceptance criteria.** Do not move to the next task until they pass and `pytest` has run.
7. **Open decisions** (section 13): if a decision is needed, use its stated default and document it in `docs/DECISIONS.md`.

---

## 1. Service responsibilities and boundaries

**Mission:** convert human references (names, IDs, coordinates) into **validated planetary coordinates** on Mars, and return context (what is nearby and which region contains the point).

### In scope
| Function | Description |
|---|---|
| Name search | Exact, prefix, accent/case-insensitive, typo-tolerant, and alias search |
| Lookup by ID | Retrieve a place by stable identifier |
| Reverse geocoding | Given `lat/lon`, return the nearest feature and containing features |
| Origin/destination resolution | Endpoint for Core: accepts a name, ID, or coordinates |
| POI and region listing | By type, tag, bbox, and region |
| Catalog metadata | Version, sources, counts, and feature types |

### Out of scope (do not implement)
| Do not | Owner |
|---|---|
| Download datasets from the Internet | 02 Data Management |
| Read GeoTIFFs or sample pixels (elevation, slope, soil) | 03 Raster Service |
| Calculate slopes, risks, costs, or routes | 04, 05, 06 |
| Convert coordinates to 90 m grid cells (*snapping*) | 03/06 |
| Handle sols, LMST, radiation, or tilt | 05/06 (`sol` is only an informational POI attribute here) |

> **Important boundary:** the service reports whether a point falls within a known region (AOI), but this is **indicative only** (a static configured bbox). The Raster Service defines actual data coverage.

---

## 2. Existing project data (verified findings)

The following existing files were inspected. These findings constrain the design:

### 2.1 Working grid (`data/gale/processed/rejilla_ruta_90m.tif`)
- 72 × 105 pixels, 6 bands: `pendiente_grados, rugosidad_m, fraccion_oscura, inercia_termica_tiu, albedo, distancia_duna_m`.
- Geographic CRS, **sphere radius 3,396,190 m**, axes *Latitude NORTH / Longitude EAST*.
- Resolution ≈ 0.0015184° (≈ 90 m).
- **BBox:** lon `137.345 → 137.45432`, lat `-4.739427 → -4.58`.
- `data/gale/processed/ruta_hematita.geojson`, `data/gale/processed/ruta_esmectitas.geojson`, and `data/gale/processed/ruta_tridimita.geojson` declare `"crs": "IAU_2015:49900"` (Mars 2015).

→ This bbox will be region `aoi:gale-90m` (section 3.4).

### 2.2 Points of interest (`data/gale/processed/gale_puntos_quimica.xlsx`, sheet `Objetivos_Minerales`)

21 rover targets with columns `nombre, sol, lon, lat, elevacion_m` plus mineral percentages (`hematita_pct`, `esmectitas_pct`, `tridimita_pct`, `sulfatos_pct`, `*_crist_pct`, `arcilla_pct`, `amorfo_pct`) and `base_hematita`.

The 21 names: Rocknest, John Klein, Cumberland, Windjana, Confidence Hills, Mojave2, Telegraph Peak, Buckskin, Big Sky, Greenhorn, Gobabeb, Okoruso, Oudam, Quela, Ogunquit Beach, Stoer, Highfield, Rock Hall, Kilmarie, Glen Etive, Mary Anning.

**Special cases the service must handle:**
- **Exact duplicate coordinates:** *John Klein* and *Cumberland* (`137.4491, -4.5895`); *Big Sky* and *Greenhorn* (`137.3686, -4.6731`). They are distinct places with the same point: use distinct IDs and return both in reverse searches.
- **Nearly coincident points** (tens of meters apart, less than one 90 m cell): *Confidence Hills / Mojave2 / Telegraph Peak*; *Stoer / Highfield / Rock Hall*. They may snap to the same grid cell; this is not this service's concern, but the `CO_LOCATED_PLACES` warning helps Core.
- **Precision:** 4 decimal places (≈ 6 m on Mars; 1° ≈ 59.27 km).
- Only some POIs have mineral data (the others are NaN) → do not assume every column is populated.
- All 21 lie inside the grid bbox (mandatory test).

### 2.3 Origin and destinations of existing routes
| Route | Material | Destination (`objetivo_mineral`) |
|---|---|---|
| `data/gale/processed/ruta_hematita.geojson` | hematite | **Oudam** |
| `data/gale/processed/ruta_esmectitas.geojson` | smectites | **Glen Etive** |
| `data/gale/processed/ruta_tridimita.geojson` | tridymite | **Buckskin** |

All three start at **Bradbury Landing** (the star in `data/gale/processed/mapa_rutas_gale.png`), which is **not** in the target spreadsheet. Add it manually:
- Default value: `lat -4.5895, lon 137.4417`.
- Note: `data/gale/processed/gale_matriz_calibracion.xlsx` uses `137.4416` on sol 3, and the route snaps to cell center `137.4414, -4.5899`. See decision D1 (section 13).

### 2.4 Data that is not useful to this service

`data/gale/processed/modelos_por_suelo.json`, `data/gale/processed/Bitacora_Calidad_Marte.xlsx`, `data/gale/processed/*_resumen.json`, `data/gale/processed/*_tramos.xlsx`, and `data/gale/processed/gale_matriz_calibracion.xlsx` (except to validate Bradbury Landing's coordinate and the bbox). These belong to Terrain/Risk/Routing.

---

## 3. Required data

### 3.1 Sources (three layers)

| Layer | Source | Content | Provider | Local file |
|---|---|---|---|---|
| **A. Global Mars Gazetteer** | USGS *Gazetteer of Planetary Nomenclature* (IAU WGPSN), <https://planetarynames.wr.usgs.gov/> | Approved Martian feature names with center, diameter, type, approval status, and name origin | 02 Data Management (or manual download for the MVP) | `data/raw/mars/gazetteer/` |
| **B. Mission POIs (Gale)** | `data/gale/processed/gale_puntos_quimica.xlsx` + Bradbury Landing added manually | 21 targets + landing site | Team (already available) | `data/gale/processed/gale_puntos_quimica.xlsx` |
| **C. Curated configuration** | YAML in the repo | Aliases, route tags, regions/AOIs | This service | `location-service/config/` |

**About layer A (verified):** the Gazetteer provides CSV/TSV downloads (with coordinate-system selection on its website) and Mars shapefile/KML downloads (MDIM 2.1 base), as well as a `MARS_nomenclature` package (zip/kmz). Some download pages may temporarily be unavailable; exact URLs change, so **the agent must not hard-code URLs**. Work with a file present in `data/raw/mars/gazetteer/` and detect its format by extension (`.csv`, `.tsv`, `.shp`, `.geojson`).

> **Download recommendation (for the human):** CSV with **east longitude 0–360** and **planetocentric latitude**, including center, bounds, diameter, feature type, approval status, and name origin. Save the original file and a `SOURCE.txt` containing the download date and URL.

**Inspect the Gazetteer's actual column names:** create a *column mapping* in `location-service/config/gazetteer_columns.yaml` (source name → canonical field), rather than assuming them.

### 3.2 Coordinate conventions (mandatory)

| Aspect | Canonical value |
|---|---|
| Body | `mars` |
| Latitude | **Planetocentric**, degrees, `[-90, 90]`, positive north |
| Longitude | **East-positive**, degrees, normalized to `[0, 360)` |
| Reference sphere | Radius **3,396,190 m** (matches the `.tif` grid) |
| CRS reference | `IAU_2015:49900` (already declared by the project's GeoJSONs) |
| Distances | Great-circle (haversine) using that radius |
| Array order | `[lon, lat]` (as in GeoJSON). JSON objects use named `lat`, `lon` fields |

Input rules:
- Accept `lon` in `[-180, 180]` or `[0, 360)`; normalize with `lon % 360`.
- **Do not** support west-positive longitude or planetographic latitude in the MVP (return `UNSUPPORTED_COORDINATE_SYSTEM` if the client declares another convention).
- The Gazetteer notes that historical Mars maps used planetographic latitude and west longitude, while current convention is planetocentric and east-positive. **When ingesting, verify the downloaded file's convention** and convert if needed. This is the most likely cause of silent errors.

### 3.3 Canonical `Place` schema

`places` table in SQLite (and equivalent Pydantic model):

| Field | Type | Notes |
|---|---|---|
| `id` | TEXT PK | Stable. `mars:iau:<feature_id>` if the Gazetteer provides an ID; otherwise `mars:iau:<slug(name)>-<type>`. POIs: `mars:msl:<slug>` |
| `body` | TEXT | Always `mars` |
| `name` | TEXT | Full name (e.g. “Gale”) |
| `name_clean` | TEXT | Name without descriptor if the Gazetteer separates it |
| `name_norm` | TEXT | Normalized (section 7.1), indexed |
| `kind` | TEXT | `feature` (Gazetteer) \| `poi` (mission) \| `landing_site` |
| `feature_type` | TEXT | Descriptor (crater, mons, vallis, planitia…) or `mission_target` / `landing_site` |
| `source` | TEXT | `iau_gazetteer` \| `mission_msl` \| `config` |
| `lat`, `lon` | REAL | Center, convention from 3.2 |
| `bbox_west/south/east/north` | REAL NULL | Bounds, if available |
| `diameter_km` | REAL NULL | Approximate feature size |
| `elevation_m` | REAL NULL | Informational only (available for POIs). Raster provides authoritative elevation |
| `approval_status` | TEXT NULL | Gazetteer status |
| `origin` | TEXT NULL | Name origin, if available |
| `tags_json` | TEXT | List, e.g. `["target_route:smectite"]` |
| `properties_json` | TEXT | Extra attributes (sol, mineral percentages, etc.); include only non-null values |

Auxiliary tables: `aliases(place_id, alias, alias_norm)`, `regions(id, name, kind, bbox…, source, note)`, `catalog_meta(key, value)` (schema version, build date, sha256 of each source, counts, verified convention).

### 3.4 Curated configuration data (YAML)

**`location-service/config/aliases.yaml`** (extensible):
```yaml
aliases:
  "mars:iau:<Aeolis Mons feature ID>": ["Mount Sharp"]
  "mars:msl:bradbury-landing": ["Curiosity landing site", "Bradbury"]
```
> Resolve IAU IDs **by name** during ingestion (`resolve_by_name: "Aeolis Mons"`); do not hard-code them.

**`location-service/config/mission_points.yaml`**
```yaml
landing_sites:
  - slug: bradbury-landing
    name: Bradbury Landing
    lat: -4.5895
    lon: 137.4417
    note: "Origin of the 3 MVP routes. Confirm the official value (decision D1)."
tags:
  target_route:hematite: [Oudam]
  target_route:smectite: [Glen Etive]
  target_route:tridymite: [Buckskin]
```

**`location-service/config/regions.yaml`**
```yaml
regions:
  - id: "aoi:gale-90m"
    name: "Gale — route area (90 m grid)"
    kind: aoi
    bbox: { west: 137.345, south: -4.739427, east: 137.454322, north: -4.58 }
    note: "Indicative only. Actual data coverage is determined by the Raster Service."
```

### 3.5 Ingestion pipeline (offline CLI, run before starting the service)

```sh
python -m location_service.ingest build \
  --gazetteer data/raw/mars/gazetteer/<file> \
  --mission   data/gale/processed/gale_puntos_quimica.xlsx \
  --config    location-service/config \
  --out       data/processed/mars/location/location_catalog.sqlite
```

Steps:
1. **Read** the Gazetteer (CSV/TSV/shp/geojson) and apply `gazetteer_columns.yaml`.
2. **Filter** to `body == mars`. Exclude records without coordinates (report them).
3. **Normalize coordinates** (3.2): detect whether the file uses east longitude 0–360, −180–180, or west longitude; convert as needed. If it cannot be detected, abort with a clear message.
4. **Read mission POIs** from the XLSX with `pandas + openpyxl`; convert `lon/lat`; discard columns that are 100% empty per row; put `sol` and percentages into `properties`; map `elevacion_m` to `elevation_m`.
5. **Add** Bradbury Landing and aliases from YAML. Apply `tags`.
6. **Validate** (section 9.1) and **write** SQLite in a transaction to a temporary file; rename atomically.
7. **Emit report** `ingest_report.json`: counts by source/type, discarded records with reasons, name collisions, duplicate coordinates, and source SHA-256 values.

**Seed mode (no Gazetteer):** if `--gazetteer` is omitted, build a catalog containing only mission POIs + Bradbury Landing. The service must work in this mode (useful for development and a minimal offline demo). Save the result as `data/seed/location_catalog_seed.sqlite` or regenerate it when the container starts if no catalog exists.

---

## 4. Internal architecture

Use **lightweight hexagonal architecture** (ports and adapters) so the domain does not depend on FastAPI or SQLite. This is a small service: do not add extra layers.

```text
location-service/
├── pyproject.toml
├── Dockerfile
├── README.md
├── config/
│   ├── aliases.yaml
│   ├── mission_points.yaml
│   ├── regions.yaml
│   └── gazetteer_columns.yaml
├── src/location_service/
│   ├── main.py                  # create_app(), lifespan: load catalog
│   ├── settings.py              # pydantic-settings (environment variables)
│   ├── api/                     # LAYER 1: HTTP
│   │   ├── routers/{places,resolve,regions,meta,health}.py
│   │   ├── schemas.py           # Pydantic input/output models
│   │   ├── errors.py            # exceptions → application/problem+json
│   │   └── deps.py              # service dependency injection
│   ├── application/             # LAYER 2: use cases
│   │   ├── search_places.py
│   │   ├── get_place.py
│   │   ├── reverse_lookup.py
│   │   ├── resolve_endpoints.py
│   │   └── list_places.py
│   ├── domain/                  # LAYER 3: pure rules (no I/O)
│   │   ├── models.py            # Place, Region, Coordinate (frozen dataclasses)
│   │   ├── geo.py               # normalize_lon, validate, haversine, bbox_contains
│   │   ├── text.py              # text normalization, tokenization
│   │   └── ranking.py           # score, match_type, ambiguity
│   ├── ports.py                 # Protocols: CatalogRepository
│   ├── adapters/
│   │   ├── sqlite_catalog.py    # read-only access to location_catalog.sqlite
│   │   └── memory_index.py      # in-memory indexes (name, tokens, coordinates)
│   └── ingest/                  # build CLI (NOT imported at runtime)
│       ├── __main__.py
│       ├── gazetteer.py
│       ├── mission_points.py
│       ├── config_loader.py
│       ├── validate.py
│       └── writer.py
├── tests/
│   ├── unit/            # geo, text, ranking
│   ├── integration/     # seed catalog + API (TestClient)
│   ├── contract/        # validate responses against openapi.yaml
│   └── fixtures/        # mini-gazetteer.csv, mini-mission.xlsx
└── data/seed/           # optional seed catalog
```

### Design decisions
1. **Read-only catalog at runtime.** Build it offline and load it **fully into memory on startup** (the Mars Gazetteer has thousands of names, not millions). No R-tree or FTS is needed: a brute-force vectorized search over a few thousand points responds in milliseconds.
2. **Service-owned SQLite** (`location_catalog.sqlite`). Do **not** use or read Data Management's `catalog.sqlite` (service-independence rule). If 02 publishes the Gazetteer in the future, consume it as a file under `data/raw/`.
3. **Pure domain.** `domain/` does not import FastAPI, sqlite3, or pandas. It is testable without infrastructure.
4. **Separate ingestion.** `pandas`/`openpyxl` are dependencies of the `ingest` extra **only**; they are not included in the runtime image.
5. **No mutable state or external cache.** `POST /v1/admin/reload` (internal network only) reopens SQLite to reload after ingestion.
6. **Versioning:** routes live under `/v1`. Pass the celestial body as `body` (defaults to `mars`; any other value → `UNSUPPORTED_BODY`).

---

## 5. Stack

| Need | Tool | Note |
|---|---|---|
| Language | Python 3.12 | Aligned with the other services |
| API | **FastAPI** + **Uvicorn** | Generates OpenAPI automatically |
| Validation | **Pydantic v2** | Contract schemas |
| Configuration | `pydantic-settings` | Environment variables |
| Persistence | `sqlite3` (stdlib) | Read-only catalog |
| Fuzzy matching | **RapidFuzz** | Typo tolerance |
| Geodesic calculation | Own implementation (haversine with R = 3,396,190 m) | **Do not** use `pyproj`/`geopy`: they assume Earth |
| Ingestion | `pandas`, `openpyxl`, optionally `pyshp`/`fiona` | `ingest` extra only |
| YAML | `PyYAML` | Curated configuration |
| Testing | `pytest`, `httpx`, `pytest-cov`; optionally `schemathesis` for contract fuzzing | |
| Quality | `ruff` (lint + format), `mypy` | |
| Container | Docker (`python:3.12-slim` image) + Docker Compose | |
| Dependency manager | `uv` or `pip` with `pyproject.toml` | Pin exact versions when creating the project (check current releases; do not make them up) |

> Classic pitfall: Earth geospatial libraries (`geopy`, `pyproj` with EPSG:4326) calculate distances using the WGS84 ellipsoid. On Mars they would be off by ~88%. Always use the Martian radius.

---

## 6. API contract

Source of truth: `packages/contracts/location-service/openapi.yaml` (generated and reviewed; Core and other services consume **this** file). Common header: `X-Request-ID` (accept or generate it, return it, and log it).

### 6.1 Endpoints

| Method | Route | Use |
|---|---|---|
| GET | `/health` | Liveness (always 200 while the process is alive) |
| GET | `/ready` | Readiness: 200 only after the catalog is loaded |
| GET | `/v1/places/search` | Text search |
| GET | `/v1/places/{place_id}` | Place by ID |
| GET | `/v1/places/reverse` | Reverse geocoding |
| GET | `/v1/places` | Filtered, paginated listing |
| POST | `/v1/resolve` | Resolve origin and destination (used by Core) |
| GET | `/v1/regions` | Known regions/AOIs |
| GET | `/v1/meta/catalog` | Version, sources, counts |
| GET | `/v1/meta/feature-types` | Feature types and counts |
| POST | `/v1/admin/reload` | Reload the catalog (internal) |

### 6.2 `Place` object
```json
{
  "id": "mars:msl:glen-etive",
  "name": "Glen Etive",
  "body": "mars",
  "kind": "poi",
  "feature_type": "mission_target",
  "source": "mission_msl",
  "center": { "lat": -4.7303, "lon": 137.3835 },
  "bbox": null,
  "diameter_km": null,
  "elevation_m": -4133,
  "approval_status": null,
  "aliases": [],
  "tags": ["target_route:smectite"],
  "properties": { "sol": 2492, "esmectitas_pct": 34.0 },
  "in_regions": ["aoi:gale-90m"]
}
```
All responses containing coordinates include this object at the root:
```json
"coordinate_system": { "body": "mars", "crs": "IAU_2015:49900", "lat_type": "planetocentric",
                       "lon_convention": "east_positive_0_360", "radius_m": 3396190 }
```

### 6.3 `GET /v1/places/search`

Parameters: `q` (required, 1–100 characters), `limit` (1–50, default 10), `kind`, `feature_type`, `source`, `near_lat` + `near_lon` (distance tie-breaker), `region` (region ID), `body` (default `mars`).

```json
{
  "query": "glen etive",
  "normalized_query": "glen etive",
  "total": 1,
  "results": [
    { "score": 1.0, "match_type": "exact_name", "place": { "...": "Place" } }
  ],
  "catalog_version": "2026-11-14.1",
  "coordinate_system": { "...": "..." }
}
```
`match_type` ∈ `exact_name | exact_alias | prefix | tokens | fuzzy`. No matches → **200** with `results: []` (not an error).

### 6.4 `GET /v1/places/reverse`

Parameters: `lat`, `lon` (required), `radius_m` (default 5000, max 500000), `limit` (default 5), `kind`, `body`.
```json
{
  "point": { "lat": -4.668, "lon": 137.3703 },
  "nearest": [
    { "distance_m": 0.0, "place": { "...": "Buckskin" } },
    { "distance_m": 612.4, "place": { "...": "Big Sky" } }
  ],
  "containing": [
    { "place": { "...": "Gale (crater)" }, "containment": "approximate_circle" }
  ],
  "regions": ["aoi:gale-90m"],
  "coordinate_system": { "...": "..." }
}
```
`containing`: features with `diameter_km` where `distance(point, center) ≤ diameter/2`. This is an **approximate circular containment** and is labeled as such. `nearest` includes all coincident POIs (John Klein and Cumberland appear together at the same distance).

### 6.5 `POST /v1/resolve` (main contract for Core)

Provide **exactly one** of `query`, `place_id`, or `coordinates` for each endpoint.
```json
{
  "body": "mars",
  "origin":      { "query": "Bradbury Landing" },
  "destination": { "place_id": "mars:msl:glen-etive" },
  "options": { "ambiguity_gap": 0.05, "max_alternatives": 3 }
}
```
Response (always **200** for business results; 4xx only for malformed requests):
```json
{
  "status": "resolved",
  "origin": {
    "status": "resolved",
    "input": { "query": "Bradbury Landing" },
    "point": { "lat": -4.5895, "lon": 137.4417 },
    "place": { "...": "Place" },
    "alternatives": []
  },
  "destination": { "status": "resolved", "...": "..." },
  "straight_line_distance_m": 14420.3,
  "shared_regions": ["aoi:gale-90m"],
  "warnings": [],
  "catalog_version": "2026-11-14.1",
  "coordinate_system": { "...": "..." }
}
```
- Per-endpoint `status`: `resolved | ambiguous | not_found | invalid`.
- Global `status`: `resolved` only if both endpoints are resolved; otherwise `partial` (one is resolved) or the worse endpoint status (`ambiguous`, `not_found`, `invalid`).
- For `ambiguous`, return `alternatives` (up to `max_alternatives`, each with a `score`) and `point: null`. **The service never chooses for the user** when there is ambiguity.
- For `coordinates` input: `place: null` and include `nearest_place` (the nearest place within 5 km, if any).

**`warnings` codes:**
| Code | When |
|---|---|
| `OUTSIDE_KNOWN_AOI` | An endpoint is outside every known region (probably no local data) |
| `ENDPOINTS_IN_DIFFERENT_REGIONS` | Origin and destination are in different AOIs |
| `SAME_POINT` | Distance < 1 m |
| `CO_LOCATED_PLACES` | Other places have identical coordinates or are < 10 m away |
| `LOW_CONFIDENCE_MATCH` | Resolved by fuzzy matching with score < 0.9 |

### 6.6 Errors (RFC 7807, `application/problem+json`)
```json
{
  "type": "https://planetary-explorer.local/errors/out-of-range",
  "title": "Coordinate out of range",
  "status": 422,
  "code": "OUT_OF_RANGE",
  "detail": "lat must be within [-90, 90]; got 95",
  "request_id": "7f1c..."
}
```
| `code` | HTTP | Cause |
|---|---:|---|
| `INVALID_PARAMETER` | 422 | Missing or malformed parameter |
| `OUT_OF_RANGE` | 422 | `lat` outside [-90, 90], or non-finite values |
| `UNSUPPORTED_BODY` | 422 | `body` is not `mars` |
| `UNSUPPORTED_COORDINATE_SYSTEM` | 422 | Convention differs from the canonical one |
| `NOT_FOUND` | 404 | Unknown `place_id` |
| `CATALOG_UNAVAILABLE` | 503 | Catalog is not loaded |
| `INTERNAL_ERROR` | 500 | Unhandled error (no traceback in the response) |

---

## 7. Search logic

### 7.1 Text normalization (`domain/text.py`)

Apply to indexed names and queries, in this order:
1. Unicode NFKD and remove diacritical marks.
2. `casefold()`.
3. Replace `-`, `_`, `'`, `.`, `,` with spaces.
4. Collapse spaces and trim.

`"Glén-Etive "` → `"glen etive"`.

### 7.2 Type words (descriptors)

Gazetteer descriptors (crater, mons, vallis, planitia, chasma, fossae, patera, tholus, dorsa, terra, mensa, labyrinthus, catena, colles, planum, rupes…) are **derived from the data** (distinct `feature_type` values) and translated using a small ES→EN dictionary in config (`cráter→crater`, `monte→mons`, `valle→vallis`, `llanura→planitia`…). If a query token matches a descriptor:
- it does not have to appear in the name;
- add a **+0.05 bonus** to candidates of that `feature_type`.

Thus “Gale crater”, “cráter Gale”, and “Gale” reach the same feature.

### 7.3 Ranking (deterministic)

For each candidate, compute the best match against `name_norm` and aliases:

| Type | Base score |
|---|---:|
| `exact_name` | 1.00 |
| `exact_alias` | 0.97 |
| `prefix` (query is a prefix of the name or one of its words) | 0.90 |
| `tokens` (all query tokens appear, in any order) | 0.85 |
| `fuzzy` (RapidFuzz `WRatio`/100 × 0.80; discard < 0.60) | 0.48–0.80 |

Adjustments: `+0.05` type bonus (7.2); `+0.02` if `source = mission_msl` and the candidate is inside an AOI; `+0.02` if `near_*` was provided and the candidate is < 50 km away. Cap at 1.0.

**Final order:** score ↓ → source priority (`mission_msl` > `iau_gazetteer`) → `diameter_km` ↓ → `name` ↑ (for reproducibility).

### 7.4 Ambiguity

A `/resolve` endpoint is **ambiguous** if, after sorting, the second candidate is a **different place** and `score_1 − score_2 < ambiguity_gap` (default 0.05). Exception: resolve if there is exactly one `exact_name` match from source `mission_msl`.

### 7.5 Reverse geocoding
- Vectorized haversine distance (NumPy optional; pure Python or NumPy is sufficient for a few thousand points).
- `nearest`: sort by distance, filter by `radius_m`, return up to `limit`.
- `containing`: see 6.4.
- `regions`: each region whose bbox contains the point.

---

## 8. Configuration (environment variables)

| Variable | Default | Description |
|---|---|---|
| `LOCATION_CATALOG_PATH` | `/app/data/processed/mars/location/location_catalog.sqlite` | Catalog |
| `LOCATION_CONFIG_DIR` | `/app/config` | Curated YAML files |
| `LOCATION_DEFAULT_BODY` | `mars` | Only supported value |
| `LOCATION_FUZZY_MIN_SCORE` | `0.60` | Fuzzy threshold |
| `LOCATION_AMBIGUITY_GAP` | `0.05` | Ambiguity gap |
| `LOCATION_MAX_LIMIT` | `50` | Maximum result limit |
| `LOCATION_ADMIN_ENABLED` | `false` | Enables `/v1/admin/reload` |
| `LOG_LEVEL` | `INFO` | Structured JSON logging |
| `PORT` | `8001` | Internal port |

Document all variables in `.env.example`.

---

## 9. Validation and tests

### 9.1 Ingestion validation (fail the build if any check fails)
- `lat ∈ [-90, 90]`, `lon ∈ [0, 360)`, no NaN.
- `id` is unique.
- All mission POIs are inside the `aoi:gale-90m` bbox.
- Bradbury Landing is present.
- Every `target_route:*` destination exists (Oudam, Glen Etive, Buckskin).
- Verify longitude convention (a known feature's center, e.g. Olympus Mons, should be around `lat ≈ +18.65`, `lon ≈ 226.2`; tolerance ±1° — **failure indicates a convention/sign error**).

*(Note: the example `lat=-18.5&lon=226.2` in the project data document is illustrative; Olympus Mons is in the northern hemisphere. Do not use it as a fixture.)*

### 9.2 Required test cases (golden tests)

| # | Input | Expected result |
|---:|---|---|
| 1 | `search?q=Glen Etive` | First result `mars:msl:glen-etive`, `lat -4.7303`, `lon 137.3835`, `exact_name` |
| 2 | `q=glen   etive`, `q=GLEN-ETIVE`, `q=Glén Etive` | Same result as #1 |
| 3 | `q=Glen Ettive` | `mars:msl:glen-etive` by `fuzzy`, score ≥ 0.8 |
| 4 | `q=Buckskin`, `q=Oudam` | `lat -4.668/lon 137.3703` and `lat -4.6787/lon 137.3577` |
| 5 | `q=Bradbury` | Bradbury Landing by `prefix` or alias |
| 6 | `q=Curiosity landing site` | Bradbury Landing by alias |
| 7 | `q=Mount Sharp` *(requires Gazetteer)* | Aeolis Mons |
| 8 | `q=Gale crater` and `q=cráter Gale` *(requires Gazetteer)* | Gale (IAU crater) ranks first; center ≈ `lat -5.4, lon 137.8` (±0.5°) |
| 9 | `q=xyzzy` | 200 with `results: []` |
| 10 | `reverse?lat=-4.668&lon=137.3703` | `nearest[0]` = Buckskin at ≈ 0 m; `regions` contains `aoi:gale-90m` |
| 11 | `reverse?lat=-4.5895&lon=137.4491` | John Klein **and** Cumberland, same distance |
| 12 | `reverse` at Big Sky's coordinates | Big Sky **and** Greenhorn |
| 13 | `resolve` Bradbury Landing → Glen Etive | `resolved`, distance ≈ 14–15 km, `shared_regions = [aoi:gale-90m]` |
| 14 | `resolve` with `coordinates` outside the bbox | `OUTSIDE_KNOWN_AOI` in `warnings` |
| 15 | `resolve` with origin = destination | `SAME_POINT` |
| 16 | `resolve` with two endpoints, one ambiguous | `status = partial` or `ambiguous`, non-empty `alternatives`, `point = null` for the ambiguous endpoint |
| 17 | `lat=95` | 422 `OUT_OF_RANGE` |
| 18 | `lon=-222.6` | Normalized to `137.4` |
| 19 | `body=moon` | 422 `UNSUPPORTED_BODY` |
| 20 | `places/mars:msl:no-existe` | 404 `NOT_FOUND` |
| 21 | `places?tag=target_route:hematite` | Oudam only |
| 22 | All 21 POIs | All inside `aoi:gale-90m` |
| 23 | Bradbury→Glen Etive haversine distance | Matches an independent calculation (R = 3,396,190 m) with error < 0.1% |
| 24 | Contract | All responses validate against `openapi.yaml` |

Tests marked *“requires Gazetteer”* use `pytest.mark.skipif` if no file is present in `data/raw/mars/gazetteer/`; all other tests must pass with only the seed catalog and fixtures.

### 9.3 Quality targets
- Line coverage ≥ 85% in `domain/` and `application/`.
- `ruff` and `mypy --strict` pass without errors in `src/`.
- Local p95 latency: search < 50 ms, reverse < 50 ms, resolve < 100 ms.
- Startup with the full catalog < 3 s.

---

## 10. Container and integration

**`Dockerfile`** (summary): `python:3.12-slim` base, non-root user, install runtime dependencies only, `CMD uvicorn location_service.main:app --host 0.0.0.0 --port 8001`, `HEALTHCHECK` against `/ready`.

**`docker-compose.yml` snippet:**
```yaml
location-service:
  build: ./location-service
  ports: ["8001:8001"]
  environment:
    LOCATION_CATALOG_PATH: /app/data/processed/mars/location/location_catalog.sqlite
  volumes:
    - ./data/processed/mars/location:/app/data/processed/mars/location:ro
    - ./location-service/config:/app/config:ro
  healthcheck:
    test: ["CMD", "python", "-c", "import urllib.request;urllib.request.urlopen('http://localhost:8001/ready')"]
    interval: 10s
    retries: 5
```
If the catalog does not exist at startup, the container exits with an explicit message (including the exact ingestion command to run) instead of appearing healthy but empty.

**What this service provides to others:**
| Consumer | Use |
|---|---|
| **Core** | `POST /v1/resolve` (main flow), `GET /v1/places/search` (UI autocomplete), `GET /v1/regions` |
| **Routing Engine / Raster** | They do not call it directly: Core passes them already resolved `lat/lon` |
| **UI** | `search` + `reverse` through Core |

Also deliver `docs/api-contracts/location-service.md` with 3–4 real `curl` examples.

---

## 11. Phased work plan (tasks with acceptance criteria)

### Phase 0 — Skeleton and contract
- **T0.1** Create the directory structure (section 4), `pyproject.toml`, `ruff`, `mypy`, and `pytest`.
  *Acceptance:* `pytest` runs (0 tests); `ruff` and `mypy` pass.
- **T0.2** Write the complete `openapi.yaml` (6.1–6.6) and place it in `packages/contracts/location-service/`.
  *Acceptance:* the file validates with an OpenAPI validator; this document's examples are included.
- **T0.3** Add Pydantic models in `api/schemas.py` consistent with the contract.
  *Acceptance:* FastAPI-generated OpenAPI matches the authored contract (test route and schema equivalence).

### Phase 1 — Pure domain
- **T1.1** `domain/geo.py`: `normalize_lon`, `validate_lat_lon`, `haversine_m` (R = 3,396,190), `bbox_contains`.
  *Acceptance:* tests for cases 17, 18, and 23; property: `haversine(a,b) == haversine(b,a)`; 1° latitude ≈ 59,274.7 m.
- **T1.2** `domain/text.py`: normalization (7.1) and tokenization.
  *Acceptance:* textual part of case 2.
- **T1.3** `domain/ranking.py`: scores, bonuses, ambiguity (7.3–7.4).
  *Acceptance:* parameterized tests with an in-memory mini-catalog.

### Phase 2 — Data and ingestion
- **T2.1** Use the existing `data/gale/processed/gale_puntos_quimica.xlsx` (do not copy it to a new source location). Create the YAML configuration files (3.4).
- **T2.2** Implement `ingest/mission_points.py` + `config_loader.py` + `writer.py` + `validate.py` (seed mode, no Gazetteer).
  *Acceptance:* generates `location_catalog.sqlite` with 22 places (21 + Bradbury); `ingest_report.json` reports 2 pairs of duplicate coordinates; validation 9.1 passes.
- **T2.3** Implement `ingest/gazetteer.py` with configurable column mapping and convention conversion.
  *Acceptance:* using `tests/fixtures/mini-gazetteer.csv` (≈ 20 rows, including longitudes in −180–180 and west-positive) yields correct `[0,360)` longitudes and a report of discarded records.
- **T2.4** *(Once the human puts the real Gazetteer in `data/raw/mars/gazetteer/`)* run full ingestion.
  *Acceptance:* Olympus Mons validation (9.1) and cases 7–8 pass.

### Phase 3 — Adapters and use cases
- **T3.1** Implement `adapters/sqlite_catalog.py` (read-only) and `memory_index.py`.
- **T3.2** Implement use cases: `search_places`, `get_place`, `reverse_lookup`, `list_places`, `resolve_endpoints`.
  *Acceptance:* cases 1–6, 9–16, and 21 pass against the seed catalog.

### Phase 4 — API
- **T4.1** Implement routers, `problem+json` error handling, `X-Request-ID`, `/health`, `/ready`, `/v1/meta/*`, `/v1/regions`, and `/v1/admin/reload`.
  *Acceptance:* cases 17–20 and 24 pass; `schemathesis` (if available) reports no schema failures.

### Phase 5 — Packaging and delivery
- **T5.1** Add `Dockerfile`, compose snippet, `.env.example`, and service README (how to run ingestion and tests, plus `curl` examples).
  *Acceptance:* `docker compose up location-service` and `curl localhost:8001/v1/places/search?q=Glen%20Etive` return case 1's result.
- **T5.2** Add `docs/DECISIONS.md` with the decisions in section 13 and their status.
- **T5.3** **Offline test:** with the network disabled, the service starts and responds to cases 1, 10, and 13.

---

## 12. Definition of Done

- [ ] `openapi.yaml` is published in `packages/contracts/` and followed by the implementation.
- [ ] All cases in 9.2 pass (Gazetteer cases pass or have a justified skip).
- [ ] Coverage, `ruff`, and `mypy` meet 9.3.
- [ ] Works **without Internet** and without a Gazetteer (seed mode).
- [ ] Does not read databases or directories belonging to other services.
- [ ] README contains exact ingestion, run, and test commands.
- [ ] `ingest_report.json` has been generated and reviewed (duplicates, discarded records, convention).
- [ ] Docker image runs as a non-root user and has a working healthcheck.

---

## 13. Open decisions (use the default if no one responds)

| ID | Decision | Default |
|---|---|---|
| **D1** | Canonical Bradbury Landing coordinate (`137.4417` vs `137.4416` in the matrix vs route cell center `137.4414`) | `lat -4.5895, lon 137.4417`; snapping to the grid belongs to Raster/Routing |
| **D2** | Who downloads the Gazetteer: Data Management or manual MVP download? | Manual for the MVP; 02 automates it later without changing this service |
| **D3** | Include unapproved/provisional Gazetteer features in search? | Approved only (`approval_status` approved); omit others and count them in the report |
| **D4** | Alias and descriptor languages? | Spanish + English; official names remain in the Gazetteer's language |
| **D5** | Expose mineral `properties` for each POI? | Yes, as informational attributes; this service does not treat them as an official scientific source |
| **D6** | UI autocomplete? | Use `search` with a small `limit` and prefix matching; no separate endpoint |
| **D7** | Future Moon support? | `body` field and ID prefixes already allow it; do not implement now |

---

## 14. Known risks

| Risk | Mitigation |
|---|---|
| **Longitude/latitude convention misinterpreted** (planetographic/west-positive vs planetocentric/east-positive) | Detect during ingestion + validate with Olympus Mons + explicitly include `coordinate_system` in every response |
| Duplicate names (multiple features with the same name) | Explicit ambiguity in `/resolve`; never choose silently |
| Gazetteer fields differ or version changes | Configurable column mapping + ingestion report + source hash |
| Mission POIs have identical coordinates | Distinct IDs and responses that return all coincident places |
| Data coverage differs from configured bbox | `OUTSIDE_KNOWN_AOI` is only a warning; Raster Service is authoritative |
| Informal name (Mount Sharp) confused with official name (Aeolis Mons) | Configure and test aliases |

---

## 15. Operations runbook

All commands run from the repo root (`/work`) unless noted. The service is
fully offline at runtime: no outbound network calls, catalog is a local
read-only SQLite file.

### Environment setup

```bash
cd location-service
python3.13 -m venv .venv          # requires-python >=3.12
.venv/bin/pip install -e ".[dev,ingest]"
```

(`ingest` extra = pandas + openpyxl, needed only to rebuild the catalog;
never required at runtime.)

### Build the catalog

Seed mode (mission POIs + Bradbury Landing + Gale AOI, no Gazetteer):

```bash
.venv/bin/python -m location_service.ingest build \
    --mission ../data/gale/processed/gale_puntos_quimica.xlsx \
    --config config \
    --out data/seed/location_catalog_seed.sqlite \
    --report data/seed/ingest_report.json
```

Full mode (once `data/raw/mars/gazetteer/` exists):

```bash
.venv/bin/python -m location_service.ingest build \
    --gazetteer ../data/raw/mars/gazetteer/<gazetteer-file> \
    --mission ../data/gale/processed/gale_puntos_quimica.xlsx \
    --config config \
    --out ../data/processed/mars/location/location_catalog.sqlite \
    --report ../data/processed/mars/location/ingest_report.json
```

The build fails (non-zero exit) if validation 9.1 fails — including the
Olympus Mons longitude-convention check.

### Run locally

```bash
cd location-service
LOCATION_CATALOG_PATH=$PWD/data/seed/location_catalog_seed.sqlite \
LOCATION_CONFIG_DIR=$PWD/config \
LOCATION_CATALOG_REQUIRED=false \
.venv/bin/uvicorn location_service.main:app --port 8001
```

`LOCATION_CATALOG_REQUIRED=false` is only for local dev; the default `true`
makes the process exit with the exact ingestion command when no catalog is
found (this is what the container relies on).

### Test

```bash
cd location-service
.venv/bin/pytest                 # unit + integration + contract
.venv/bin/pytest --cov           # coverage report (target >=85%)
.venv/bin/ruff check .
.venv/bin/mypy src
```

### curl examples

```bash
# case 1: exact name search
curl -s 'http://localhost:8001/v1/places/search?q=Glen%20Etive' | jq '.results[0].id'

# case 10: reverse lookup at Buckskin
curl -s 'http://localhost:8001/v1/places/reverse?lat=-4.668&lon=137.3703' | jq '.nearest[0].place.name'

# case 13: resolve Bradbury Landing -> Glen Etive
curl -s -X POST http://localhost:8001/v1/resolve \
    -H 'Content-Type: application/json' \
    -d '{"origin":{"query":"Bradbury Landing"},"destination":{"place_id":"mars:msl:glen-etive"}}' \
    | jq '{status, distance_m: .straight_line_distance_m}'
```

More examples: `docs/api-contracts/location-service.md` (repo root).

### Docker

```bash
docker compose -f location-service/docker-compose.yml up location-service
```

The image runs as non-root user `location`, healthchecks `/ready`, and exits
at startup with the ingestion command if the mounted catalog is missing.
