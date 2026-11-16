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

Phase status: Phase 1 skeleton — SPEC endpoints and additive stubs are wired;
factor scoring lands in Phase 3, ingestion in Phase 2. See
`docs/risk-assessment/IMPLEMENTATION_PLAN_RISK_ASSESSMENT.md`.
