# nasa-maze-app — Progress & Handoff

Plan: [`IMPLEMENTATION_PLAN_APP.md`](IMPLEMENTATION_PLAN_APP.md). Branch: `feature/frontend`. PR target: `development`.
The orchestrator updates this file in the same commit as each WP and before every checkpoint (plan §9).

## Status

| WP | Title | Status | Commit | Notes |
|---|---|---|---|---|
| WP0 | Bootstrap (plan, profiles, merge development) | done | see `git log` (`docs(app): WP0 ...`) | |
| WP1 | Scaffold | pending | | |
| WP2 | API client | pending | | |
| WP3 | Domain | pending | | |
| ◆A | Checkpoint | pending | | |
| WP4 | Map shell | pending | | |
| WP5 | Route panel | pending | | |
| ◆B | Checkpoint | pending | | |
| WP6 | Route rendering | pending | | |
| ◆C | Checkpoint | pending | | |
| WP7 | Docker + compose | pending | | |
| WP8 | E2E + review + docs | pending | | |
| ◆D | Final checkpoint / PR | pending | | |

## Resume here

- **Last completed:** WP0. Session restart required so `.devin/agents/app-*.md` profiles load.
- **Next:** WP1 Scaffold, developer profile `app-tdd-developer`. Prompt:

  ```
  WP1 — Scaffold. Root: nasa-maze-app/ (create it at the repo root; run commands there).
  Read: docs/nasa_maze_app/IMPLEMENTATION_PLAN_APP.md §1, §2, §3, §5, §6 row WP1.
  Files to create/modify (exhaustive): nasa-maze-app/** config files (package.json, package-lock.json,
  vite.config.ts with vitest config + /api proxy to CORE_URL, tsconfig*.json, eslint.config.js, index.html, .gitignore),
  src/main.tsx, src/App.tsx, src/index.css, src/App.test.tsx, src/test/{setup,server,handlers}.ts,
  AGENTS.md, README.md, .env.example.
  Existing modules you may import: none.
  Done when: npm ci && npm run typecheck && npm run lint && npm test && npm run build are green;
  App.test.tsx (written first) asserts a full-screen map container and a route panel placeholder render.
  ```

- **Open review findings / minors:** none.
- **Environment notes:** Node 24 available. Core for manual checks: from `core/`, `python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"` then `.venv/Scripts/uvicorn app.main:app --port 8000` (fallback-only routes work without MS6), or `docker compose up --build` from the root.
- **Known issues:** none.

## Deviations

1. Plan updated during WP0: `development` (merged into `feature/frontend`) added `riesgo` (MS5 evaluation, nullable) to `POST /api/ruta` and `ms5` to `/api/health`. Plan §1/§2 D8/D9/§4 now use it (risk badge, MS5 warnings, color-by Risk).
