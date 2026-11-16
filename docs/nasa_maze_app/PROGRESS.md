# nasa-maze-app — Progress & Handoff

Plan: [`IMPLEMENTATION_PLAN_APP.md`](IMPLEMENTATION_PLAN_APP.md). Branch: `feature/frontend`. PR target: `development`.
The orchestrator updates this file in the same commit as each WP and before every checkpoint (plan §9).

## Status

| WP | Title | Status | Commit | Notes |
|---|---|---|---|---|
| WP0 | Bootstrap (plan, profiles, merge development) | done | see `git log` (`docs(app): WP0 ...`) | |
| WP1 | Scaffold | in_progress | | |
| WP2 | API client | pending | | |
| WP3 | Domain | done | `feat(app): WP3 domain` | 47 domain tests (64 total) |
| ◆A | Checkpoint | done | `docs(app): checkpoint A` | handoff written in WP3 commit 36408c4 |
| WP4 | Map shell | pending | | |
| WP5 | Route panel | pending | | |
| ◆B | Checkpoint | pending | | |
| WP6 | Route rendering | pending | | |
| ◆C | Checkpoint | pending | | |
| WP7 | Docker + compose | pending | | |
| WP8 | E2E + review + docs | pending | | |
| ◆D | Final checkpoint / PR | pending | | |

## Resume here

- **Branch:** `feature/frontend` (not pushed). **Last completed:** WP3 + checkpoint ◆A (see `git log --oneline`).
- **Next:** WP4 ∥ WP5 (background, max 2 concurrent, disjoint dirs), then the orchestrator wires both into `src/App.tsx` and runs ◆B (`npm run dev` against Core shows Gale with sites, overlay and working form).
- **WP4 prompt** (profile `app-tdd-developer-plus`):

  ```
  WP4 — Map shell. Root: nasa-maze-app/. Windows: run npm via PowerShell.
  Read: docs/nasa_maze_app/IMPLEMENTATION_PLAN_APP.md §1, §2 (D3, D5, D9), §3 + §3.1, §4 rows F6, F7, §5, §6 row WP4, §11; nasa-maze-app/AGENTS.md.
  Files to create/modify (exhaustive): src/components/map/{MarsMap,Basemap,RasterOverlay,SitesLayer,Legend}.tsx,
  src/hooks/{useHealth,useBaseLayers,useRasterBand}.ts + one test file each.
  Existing modules you may import: src/api/{types,coreClient}.ts, src/domain/{labels,capabilities,mission,sites,routeView}.ts, src/test/handlers.ts (loadFixture, MSW server).
  Do NOT edit App.tsx (the orchestrator wires it). MarsMap accepts children (other layers/handlers are passed in by App).
  Done when: typecheck, lint, test, build green; F6–F7 rows green. Do not commit.
  ```

- **WP5 prompt** (profile `app-tdd-developer`):

  ```
  WP5 — Route panel. Root: nasa-maze-app/. Windows: run npm via PowerShell.
  Read: docs/nasa_maze_app/IMPLEMENTATION_PLAN_APP.md §1, §2 (D1, D2, D4, D11), §3 + §3.1, §4 row F8, §5, §6 row WP5; nasa-maze-app/AGENTS.md.
  Files to create/modify (exhaustive): src/components/panel/{RoutePanel,OriginPicker,MineralPicker,MissionSettings,StatusBadge,LayerControls}.tsx,
  src/hooks/useRoute.ts, src/components/map/OriginClickHandler.tsx + one test file each.
  Existing modules you may import: src/api/{types,coreClient}.ts, src/domain/*.ts, src/test/handlers.ts. Do NOT touch WP4 files (MarsMap etc., useHealth/useBaseLayers/useRasterBand) — receive health/capabilities/sites as props.
  Mission settings in fallback: inputs rendered but disabled (read-only), not hidden. Do NOT edit App.tsx.
  Done when: typecheck, lint, test, build green; F8 row green. Do not commit.
  ```

- **WP6 note:** expose `factor_scores` / `local_time_hour` in `RiskSegmentView` (src/domain/routeView.ts) if popups need them, instead of reading raw `riesgo`.
- **Open review findings / minors (batched for WP8):**
  - WP1: pin `@types/node` to 24.x; add `engines.node`; consider `eslint-plugin-jsx-a11y`; eslint 9 deprecation warning (eslint 10 optional).
  - WP2: `handlers.ts` `BANDAS` should be typed `RasterBand[]`; raster test should assert the `cmap` query; consumers must not switch exhaustively on `fuente`/`risk_level` without a default.
  - WP3: add explicit pinned `@types/geojson` devDependency (currently transitive via @types/leaflet); `mission.ts:42` float step check (use rounding); document `originOptions` 4-decimal dedupe precision.
- **Environment notes:** Node 24 available. Core for manual checks: from `core/`, `python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"` then `.venv/Scripts/uvicorn app.main:app --port 8000` (fallback-only routes work without MS6), or `docker compose up --build` from the root.
- **Known issues:** none. Generating fixtures with system Python needs `pandas` + `openpyxl`; stub `app.settings` if `pydantic_settings` is missing.

## Deviations

1. Plan updated during WP0: `development` (merged into `feature/frontend`) added `riesgo` (MS5 evaluation, nullable) to `POST /api/ruta` and `ms5` to `/api/health`. Plan §1/§2 D8/D9/§4 now use it (risk badge, MS5 warnings, color-by Risk).
2. WP1 version deviations: jsdom 29.1.1 (31 needs node >= 24.15; local is 24.10), msw 2.15.0 (not v3), eslint 9.39.5, typescript 5.9.3 (typescript-eslint peer), `vite/client` types via tsconfig instead of `vite-env.d.ts`.
3. Windows shell note: in this environment bash pipes/`&&` chains to npm hit a WSL shim error; run npm commands via PowerShell.
4. WP2: fixtures loaded via `import.meta.glob` in `src/test/handlers.ts` (`loadFixture`) because tsconfig lacks `resolveJsonModule`; keep it that way. `baseLayers.json` generated by the orchestrator from `core/app/datasources/base_layers.py` over `data/gale` (traverse decimated 1/5). Precalc routes may have `control_calidad: null` and null `tramos` cells.
