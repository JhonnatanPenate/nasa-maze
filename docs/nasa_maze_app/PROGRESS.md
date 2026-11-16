# nasa-maze-app — Progress & Handoff

Plan: [`IMPLEMENTATION_PLAN_APP.md`](IMPLEMENTATION_PLAN_APP.md). Branch: `feature/frontend`. PR target: `development`.
The orchestrator updates this file in the same commit as each WP and before every checkpoint (plan §9).

## Status

| WP | Title | Status | Commit | Notes |
|---|---|---|---|---|
| WP0 | Bootstrap (plan, profiles, merge development) | done | see `git log` (`docs(app): WP0 ...`) | |
| WP1 | Scaffold | done | `feat(app): WP1 scaffold` (49b8295) | 3 tests |
| WP2 | API client | done | `feat(app): WP2 api client` (cd757ed) | 14 F1 tests |
| WP3 | Domain | done | `feat(app): WP3 domain` | 47 domain tests (64 total) |
| ◆A | Checkpoint | done | `docs(app): checkpoint A` | handoff written in WP3 commit 36408c4 |
| WP4 | Map shell | done | `feat(app): WP4 map shell` (24a2353) | 98 tests (F6, F7 green) |
| WP5 | Route panel | done | `feat(app): WP5 route panel` (40e2a3f) | 130 tests (F8 green) |
| ◆B | Checkpoint | done | `docs(app): checkpoint B` | wired WP4+WP5 into App.tsx (130 tests green) |
| WP6 | Route rendering | pending | | |
| ◆C | Checkpoint | pending | | |
| WP7 | Docker + compose | pending | | |
| WP8 | E2E + review + docs | pending | | |
| ◆D | Final checkpoint / PR | pending | | |

## Resume here

- **Branch:** `feature/frontend` (not pushed). **Last commit:** `docs(app): checkpoint B` (see `git log --oneline`). WP1–WP5 + ◆B done.
- **Checkpoint ◆B reached:**
  - WP4 (`MarsMap`, `Basemap`, `RasterOverlay`, `SitesLayer`, `Legend`, `OriginClickHandler`) and WP5 (`RoutePanel`, `OriginPicker`, `MineralPicker`, `MissionSettings`, `StatusBadge`, `LayerControls`, `useRoute`) are fully implemented, tested (130 tests passing across 23 test suites), and integrated into `src/App.tsx`.
  - All verification checks (`typecheck`, `lint`, `test`, `build`) are completely green.
- **Next:** WP6 (Route rendering).
  - When the user approves: spawn `app-tdd-developer-plus` with the prompt below.
  - WP6 scope: `RouteLayer.tsx`, `RouteSummary.tsx`, integration in `App.tsx` (casing, soil/slope/risk coloring, alternatives comparison, popup inspection, fitBounds on route calculated).
- **WP6 prompt** (profile `app-tdd-developer-plus`, after ◆B is approved):

  ```
  WP6 — Route rendering. Root: nasa-maze-app/. Windows: run npm via PowerShell.
  Read: docs/nasa_maze_app/IMPLEMENTATION_PLAN_APP.md §1, §2 (D8, D9), §3 + §3.1, §4 row F9, §5, §6 row WP6; nasa-maze-app/AGENTS.md.
  Files to create/modify (exhaustive): src/components/map/RouteLayer.tsx, src/components/panel/RouteSummary.tsx, src/App.tsx + their test files.
  Existing modules you may import: src/api/{types,coreClient}.ts, src/domain/*.ts, src/test/handlers.ts, WP4 map components, WP5 panel components.
  Route styling: white casing + 6px colored line per ruta_optima segment (soil/slope/risk modes). Alternative: dashed gray line. RouteSummary: KPIs, source badge, risk badge, Bagnold comparison, warnings, "New route" button. Fit bounds to route on calculation.
  Done when: typecheck, lint, test, build green; F9 row green. Do not commit.
  ```

- **WP6 note:** expose `factor_scores` / `local_time_hour` in `RiskSegmentView` (src/domain/routeView.ts) if popups need them, instead of reading raw `riesgo`.
- **Open review findings / minors (batched for WP8):**
  - WP1: pin `@types/node` to 24.x; add `engines.node`; consider `eslint-plugin-jsx-a11y`; eslint 9 deprecation warning (eslint 10 optional).
  - WP2: `handlers.ts` `BANDAS` should be typed `RasterBand[]`; raster test should assert the `cmap` query; consumers must not switch exhaustively on `fuente`/`risk_level` without a default.
  - WP3: add explicit pinned `@types/geojson` devDependency (currently transitive via @types/leaflet); `mission.ts:42` float step check (use rounding); document `originOptions` 4-decimal dedupe precision.
  - WP4: derive Legend `DEFAULT_SOILS` from `domain/labels.ts`; site markers are `span` (use buttons if they become interactive); MarsMap wrapper div exists only for aria-label/test id.
- **Environment notes:** Node 24 available. Core for manual checks: from `core/`, `python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"` then `.venv/Scripts/uvicorn app.main:app --port 8000` (fallback-only routes work without MS6), or `docker compose up --build` from the root.
- **Known issues:** none. Generating fixtures with system Python needs `pandas` + `openpyxl`; stub `app.settings` if `pydantic_settings` is missing.

- **WP6 note:** expose `factor_scores` / `local_time_hour` in `RiskSegmentView` (src/domain/routeView.ts) if popups need them, instead of reading raw `riesgo`.
- **Open review findings / minors (batched for WP8):**
  - WP1: pin `@types/node` to 24.x; add `engines.node`; consider `eslint-plugin-jsx-a11y`; eslint 9 deprecation warning (eslint 10 optional).
  - WP2: `handlers.ts` `BANDAS` should be typed `RasterBand[]`; raster test should assert the `cmap` query; consumers must not switch exhaustively on `fuente`/`risk_level` without a default.
  - WP3: add explicit pinned `@types/geojson` devDependency (currently transitive via @types/leaflet); `mission.ts:42` float step check (use rounding); document `originOptions` 4-decimal dedupe precision.
  - WP4: derive Legend `DEFAULT_SOILS` from `domain/labels.ts`; site markers are `span` (use buttons if they become interactive); MarsMap wrapper div exists only for aria-label/test id.
- **Environment notes:** Node 24 available. Core for manual checks: from `core/`, `python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"` then `.venv/Scripts/uvicorn app.main:app --port 8000` (fallback-only routes work without MS6), or `docker compose up --build` from the root.
- **Known issues:** none. Generating fixtures with system Python needs `pandas` + `openpyxl`; stub `app.settings` if `pydantic_settings` is missing.

## Deviations

1. Plan updated during WP0: `development` (merged into `feature/frontend`) added `riesgo` (MS5 evaluation, nullable) to `POST /api/ruta` and `ms5` to `/api/health`. Plan §1/§2 D8/D9/§4 now use it (risk badge, MS5 warnings, color-by Risk).
2. WP1 version deviations: jsdom 29.1.1 (31 needs node >= 24.15; local is 24.10), msw 2.15.0 (not v3), eslint 9.39.5, typescript 5.9.3 (typescript-eslint peer), `vite/client` types via tsconfig instead of `vite-env.d.ts`.
3. Windows shell note: in this environment bash pipes/`&&` chains to npm hit a WSL shim error; run npm commands via PowerShell.
4. WP2: fixtures loaded via `import.meta.glob` in `src/test/handlers.ts` (`loadFixture`) because tsconfig lacks `resolveJsonModule`; keep it that way. `baseLayers.json` generated by the orchestrator from `core/app/datasources/base_layers.py` over `data/gale` (traverse decimated 1/5). Precalc routes may have `control_calidad: null` and null `tramos` cells.
