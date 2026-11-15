# AGENTS.md

## MS4 Terrain Analysis Service (`terrain-analysis/`)

- Execution plan: `docs/terrain_analysis/IMPLEMENTATION_PLANMS4_1.md` (WPs WP0–WP7 done). Current direction: `docs/terrain_analysis/REALIGNMENT_PLANMS4_1.md` (R0–R5 implemented — realignment to the delivered `data/gale/` grid; update §8 status if work resumes).
- Contract: `docs/SPEC_MS4_TERRAIN_ANALYSIS.md`.
- Subagent profiles: `.devin/agents/tdd-developer.md` (model `swe`) for WPs, `.devin/agents/code-reviewer.md` (model `opus`) for review.

### Decisions (confirmed by user)
- Python: use **3.12** for the venv (rasterio wheel safety on Windows): `py -3.12 -m venv .venv`.
- Commits: one conventional commit per WP on the current working branch (`fix/terrain-analysis-api`) after green tests + clean review. Do not push.

### Commands
```bash
cd terrain-analysis
py -3.12 -m venv .venv && source .venv/Scripts/activate
pip install -e ".[dev]"
pytest -v
uvicorn app.main:app --port 8004
# run against the delivered Gale grid (slope verbatim, elevation_m null):
MS4_DATASOURCE_KIND=rejilla uvicorn app.main:app --port 8004
# run via the MS3 Raster Service (must be up on :8003):
MS4_DATASOURCE_KIND=http MS4_RASTER_SERVICE_URL=http://localhost:8003 uvicorn app.main:app --port 8004
# parity test vs a live MS3 (skipped when unreachable):
MS4_RASTER_SERVICE_URL=http://localhost:8003 pytest tests/integration -v
```
