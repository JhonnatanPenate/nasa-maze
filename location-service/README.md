# Location Service

FastAPI microservice that resolves Martian place names, stable IDs, and
coordinates into validated locations and nearby geographic context. It serves
the Planetary Explorer Core and runs offline using a local, read-only SQLite
catalog.

The full implementation requirements, data model, API behavior, test cases,
phases, and acceptance criteria are in the
[Location Service implementation plan](../docs/location-service/IMPLEMENTATION_PLAN_LOCATION_SERVICE.md).
For request examples, see the [API usage guide](../docs/api-contracts/location-service.md).

## Architecture

The service uses lightweight hexagonal architecture. Dependencies point inward:

```text
HTTP API  →  application use cases  →  domain
                  ↑                    ↑
             adapters / ports ─────────┘
```

- **API:** FastAPI routers, Pydantic request/response schemas, and RFC 7807
  error handlers.
- **Application:** place search, ID lookup, reverse lookup, listing, and
  origin/destination resolution.
- **Domain:** Mars coordinates and distance calculations, place/region models,
  text normalization, and deterministic matching/ranking.
- **Adapters:** read-only SQLite catalog loader and an in-memory search index.
- **Ingestion:** offline CLI that builds the service-owned SQLite catalog from
  local mission data, optional Gazetteer data, and curated YAML configuration.

The catalog is loaded into memory when the application starts. Runtime API
requests do not access the network or modify the SQLite catalog.

## Project layout

```text
location-service/
├── config/                  # aliases, mission POIs, regions, Gazetteer mapping
├── data/seed/               # generated seed catalog and ingestion report
├── src/location_service/
│   ├── api/                 # HTTP routers, schemas, errors, dependencies
│   ├── application/         # search, lookup, reverse, list, resolve use cases
│   ├── adapters/            # SQLite reader and memory index
│   ├── domain/              # pure Mars geography, text, and ranking rules
│   ├── ingest/              # offline catalog builder
│   ├── main.py              # FastAPI app factory and lifespan
│   └── settings.py          # environment-based configuration
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── fixtures/
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Requirements

- Python 3.12 or newer
- The project data file `data/gale/processed/gale_puntos_quimica.xlsx` for
  building the Gale seed catalog
- Optional: a local Mars Gazetteer under `data/raw/mars/gazetteer/` for global
  features

## Local setup

From the repository root:

```bash
cd location-service
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,ingest]"
```

On Windows, create the environment with `py -3.12 -m venv .venv` and activate
it with `.venv\Scripts\activate`.

The `ingest` extra provides the spreadsheet and shapefile readers needed only
to build catalogs. The runtime image installs runtime dependencies only.

## Build the catalog

Build a seed catalog from the 21 Gale mission targets, Bradbury Landing, and
the configured Gale AOI. Run from the `location-service/` directory:

```bash
python -m location_service.ingest build \
  --mission ../data/gale/processed/gale_puntos_quimica.xlsx \
  --config config \
  --out data/seed/location_catalog_seed.sqlite \
  --report data/seed/ingest_report.json
```

To include the global Gazetteer, provide its local file and choose a separate
output path:

```bash
python -m location_service.ingest build \
  --gazetteer ../data/raw/mars/gazetteer/<gazetteer-file> \
  --mission ../data/gale/processed/gale_puntos_quimica.xlsx \
  --config config \
  --out ../data/processed/mars/location/location_catalog.sqlite \
  --report ../data/processed/mars/location/ingest_report.json
```

The builder validates input coordinates and the Gale POIs before writing the
catalog. It reports source counts, discarded records, duplicate coordinates,
and source hashes.

## Run locally

Start the API from `location-service/` after building the seed catalog:

```bash
LOCATION_CATALOG_PATH="$PWD/data/seed/location_catalog_seed.sqlite" \
LOCATION_CONFIG_DIR="$PWD/config" \
uvicorn location_service.main:app --host 0.0.0.0 --port 8001
```

The application uses `LOCATION_CATALOG_PATH` first and falls back to
`LOCATION_SEED_CATALOG_PATH` if the primary catalog is missing. By default,
startup fails with an ingestion command if neither catalog is available.

## Docker

Build and run the image (the versioned seed catalog in `data/seed` and
`config/` are baked in, so no mounts are needed):

```bash
docker build -t planetary-location-service ./location-service
docker run --rm -p 8001:8001 planetary-location-service
```

The image runs as the non-root `location` user. It exposes port `8001` and
checks readiness at `/ready`. Mount a catalog at `LOCATION_CATALOG_PATH` (or
`/app/data/seed`) to override the baked-in one. The standalone
[`docker-compose.yml`](./docker-compose.yml) documents the equivalent service
mounts for integration into the project stack.

## Tests and quality checks

Run from `location-service/`:

```bash
pytest
pytest --cov
ruff check .
mypy src
```

Tests cover pure domain behavior, ingestion, API golden cases, and the API
contract.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness; requires a loaded catalog |
| GET | `/v1/places/search` | Search by name, alias, or feature |
| GET | `/v1/places/{place_id}` | Retrieve a place by stable ID |
| GET | `/v1/places/reverse` | Find nearby and containing places |
| GET | `/v1/places` | Filter and page through places |
| POST | `/v1/resolve` | Resolve origin and destination for Core |
| GET | `/v1/regions` | List configured regions/AOIs |
| GET | `/v1/meta/catalog` | Catalog version, sources, and counts |
| GET | `/v1/meta/feature-types` | Feature types and counts |
| POST | `/v1/admin/reload` | Reload the catalog when enabled |

Coordinate-bearing responses specify the Mars coordinate system
(`IAU_2015:49900`, planetocentric latitude, east-positive longitude,
reference radius 3,396,190 m). The API returns `X-Request-ID` and uses
`application/problem+json` for errors.

## Configuration

Settings are read from environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `LOCATION_CATALOG_PATH` | `/app/data/processed/mars/location/location_catalog.sqlite` | Primary SQLite catalog |
| `LOCATION_SEED_CATALOG_PATH` | `/app/data/seed/location_catalog_seed.sqlite` | Seed catalog fallback |
| `LOCATION_CONFIG_DIR` | `/app/config` | Curated YAML configuration |
| `LOCATION_DEFAULT_BODY` | `mars` | Default supported body |
| `LOCATION_FUZZY_MIN_SCORE` | `0.60` | Minimum fuzzy-match score |
| `LOCATION_AMBIGUITY_GAP` | `0.05` | Score gap used to flag ambiguity |
| `LOCATION_MAX_LIMIT` | `50` | Maximum list/search page size |
| `LOCATION_ADMIN_ENABLED` | `false` | Enables `POST /v1/admin/reload` |
| `LOCATION_CATALOG_REQUIRED` | `true` | Fail startup if no catalog is available |
| `LOG_LEVEL` | `INFO` | Application log level |
| `PORT` | `8001` | Service port |

## Consumers

- **Core:** uses `POST /v1/resolve`, place search, and region listing.
- **Routing Engine / Raster:** receive resolved coordinates through Core; they
  do not call this service directly.
- **UI:** search and reverse lookup are exposed through Core.
