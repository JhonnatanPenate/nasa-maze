# AGENTS.md

## MS4 Terrain Analysis Service (`terrain-analysis/`)

- Execution plan: `docs/terrain_analysis/IMPLEMENTATION_PLANMS4_1.md` (source of truth; update §8 WP status as work proceeds).
- Contract: `docs/SPEC_MS4_TERRAIN_ANALYSIS.md`.
- Subagent profiles: `.devin/agents/tdd-developer.md` (model `swe`) for WPs, `.devin/agents/code-reviewer.md` (model `opus`) for review.

### Decisions (confirmed by user)
- Python: use **3.12** for the venv (rasterio wheel safety on Windows): `py -3.12 -m venv .venv`.
- Commits: one conventional commit per WP on `feature/terrain-analysis` after green tests + clean review. Do not push.

### Commands
```bash
cd terrain-analysis
py -3.12 -m venv .venv && source .venv/Scripts/activate
pip install -e ".[dev]"
pytest -v
uvicorn app.main:app --port 8004
```
