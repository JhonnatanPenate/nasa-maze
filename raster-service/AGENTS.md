# AGENTS.md — MS3 Raster Service (`raster-service/`)

Single HTTP access point to Mars raster files (port 8003). Owns all
raster I/O — open, coordinate->cell math, clipping, nodata — and serves
JSON/PNG so consumers never import rasterio.

- Contract: `docs/SPEC_MS3_RASTER.md` (v0.1.1).
- Plan: `docs/raster_service/IMPLEMENTATION_PLANMS3_1.md`.
- Subagent profiles: `.devin/agents/ms3-*.md`.

## Architecture (plan §3.1-§3.2)

Feature-first Clean Architecture: presentation -> application ->
domain, dependencies point inward. `core/domain`, `core/ports`,
`features/*/application`, `features/*/domain` never import fastapi,
pydantic, rasterio or httpx (`tests/unit/test_architecture.py`);
rasterio lives only in `app/infrastructure`. Swap: use cases depend on
the `RasterRepository` port; the repository takes `RasterDatasource`
instances by constructor — new format = new datasource + config entry.

## Commands

```bash
cd raster-service
py -3.12 -m venv .venv && source .venv/Scripts/activate
pip install -e ".[dev]"
pytest -q                  # or .venv/Scripts/python -m pytest -q
uvicorn app.main:app --port 8003
docker build -t ms3-raster .
docker run --rm -p 8003:8003 -v "<repo>/data:/data:ro" ms3-raster
```

## Data rules and consumers

- Paths only from `MS3_*` env vars; never commit data. Values verbatim
  (float32 cell -> same float64); NaN/±inf -> null. Mars: planetocentric
  deg, R=3396.19 km, CRS `IAU_2015:49900`.
- MS4 calls this service via `HttpRasterDatasource`; parity pinned by
  `terrain-analysis/tests/integration/test_ms3_parity.py` — keep green.
