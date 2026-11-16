# MS5 Risk Assessment Service (`risk-assessment/`)

Evaluates normalized terrain + environmental risk for Mars paths in the Gale
crater AOI. Contract: `docs/SPEC_MS5_RISK_ASSESSMENT.md` (authoritative) +
plan extensions documented in `docs/api-contracts/risk-assessment-service.md`
and `packages/contracts/risk-assessment/openapi.yaml`.

## Layout

```
app/
  main.py                     # create_app(), routers, error handlers
  composition/dependencies.py # settings -> adapters -> use cases
  core/
    config/settings.py        # pydantic-settings, RISK_ env prefix
    domain/                   # pure: geo, sampling, solar time, risk math
    errors/                   # DomainError -> {"detail": ...} (MS3/MS4 format)
    ports/                    # terrain_source, raster_source, environment_repository, vehicle_profile_repository
  features/                   # health, point_assessment, path_assessment,
                              # factors, vehicle_profiles, meta, area_assessment
  infrastructure/
    datasources/              # http / synthetic / unavailable MS3+MS4 adapters
    repositories/             # sqlite environment catalog, yaml vehicle profiles
  ingest/                     # offline workbook -> catalog CLI (Phase 2)
tests/                        # unit, api, contract, integration, fakes, fixtures
config/                       # vehicle_profiles, risk_thresholds, risk_weights, environment_columns
```

## Run

```bash
pip install -e ".[dev]"
uvicorn app.main:app --port 8005            # synthetic mode (default)
RISK_DATASOURCE_MODE=http \
RISK_RASTER_BASE_URL=http://localhost:8003 \
RISK_TERRAIN_BASE_URL=http://localhost:8004 \
uvicorn app.main:app --port 8005            # against real MS3/MS4
pytest -q && ruff check . && mypy
```

Docker (no root compose yet — standalone snippet, repo-root relative paths):

```bash
# from the repo root
docker compose --project-directory . -f risk-assessment/docker-compose.yml up risk-assessment
# or merge the service block into a future root docker-compose.yml
```

Phase status: **all phases complete (Gate 2 pending)** — SPEC endpoints,
environmental catalog ingestion, pure-domain risk model, ports/adapters,
plan extensions (`vehicle-profiles`, `meta`, `area`), golden-route
validation. See `docs/risk-assessment/` (PHASE0_NOTES, DATA_INVENTORY_MS5,
HANDOFF_ROUTING_CORE, UPSTREAM_REQUESTS) and
`docs/DECISIONS.md` (MS5-D*). Deferred: docker build/compose run and live
MS3/MS4 integration (no docker in the dev environment).
