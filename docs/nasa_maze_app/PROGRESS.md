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
| WP6 | Route rendering | done (verified) | uncommitted | 139 tests green; typecheck, lint, build green (F9) |
| ◆C | Checkpoint | pending | | |
| WP7 | Docker + compose | done, docker build not run (no docker in sandbox) | uncommitted | Dockerfile, .dockerignore, nginx template, compose `app` service |
| WP8 | E2E + review + docs | partial: code/docs done, offline-badge E2E passed; route-flow E2E pending | uncommitted | see "Pending" below |
| ◆D | Final checkpoint / PR | pending | | |

## Resume here

- **Branch:** `feature/frontend` (not pushed). **Last commit:** `docs(app): checkpoint B`. WP6, WP7 and most of WP8 are written and **uncommitted** in the working tree.
- **Verified (Node 24 locally):** `npm run typecheck`, `lint`, `test` (144 passing) and `build` all green; offline-basemap Playwright smoke passes against local production preview.
- **Done in WP6-WP8:** RouteLayer, RouteSummary, App integration (RoutePanel stays mounted but hidden while a route is shown, so mission settings survive "New route"); Dockerfile, `.dockerignore`, `nginx/default.conf.template`, compose `app` service; `playwright.config.ts` + `e2e/smoke.spec.ts` (vitest excludes `e2e/`); `.env.example`; offline basemap probe now controls initial status while manual selection remains authoritative; minors fixed (`@types/node` 24.19.2, `engines.node >=24`, `@types/geojson` pinned, `BANDAS: RasterBand[]`, float-safe hour step, Legend soils from `labels.ts`, `cmap` query asserted, `originOptions` dedupe documented, `eslint-plugin-jsx-a11y` 6.10.2 enabled with zero findings); extra tests for RouteLayer popups, alternative selection and App risk-to-slope fallback; READMEs, root `README.md` and `docs/ARCHITECTURE.md` status, `UPSTREAM_REQUESTS.md`, `USO-DE-IA.md` line. Independent review by `app-code-reviewer` done: nginx timeout fixed to 180 s, warning list keys, offline-basemap e2e test added, `.git` in `.dockerignore`. Reviewer noted (accepted): `eslint-plugin-jsx-a11y` and `@types/node` 24 are intentional; hidden RoutePanel stays mounted by design.

## Pending (what is left; needs Docker, a browser or the user)

1. **Docker never run** (no docker in the sandbox): `docker compose up --build`, then open http://localhost:3000. Generate the location-service seed catalog first (see compose header). If the `app` image fails, run `docker compose build app`.
2. **Route-flow Playwright smoke (1 test) not run:** requires the stack up (`E2E_BASE_URL` to override). Offline-basemap smoke passed against the local production preview.
3. **Manual check against live Core:** route over live MS6, fallback-only, and no-backend states (DoD §8); online/offline basemap switch; visual check of route casing/colors and fitBounds.
4. ~~Independent review~~ done, findings applied.
5. **Commits:** nothing from WP6-WP8 is committed. Suggested: `feat(app): WP6 route rendering`, `feat(app): WP7 docker + compose`, `feat(app): WP8 e2e + docs`, then `docs(app): checkpoint D`.
6. **Minors not done:** eslint 10 upgrade (optional); `npm audit` reports 7 moderate issues (minimatch via dev tooling; not fixed to avoid breaking upgrades); site markers are `span` (use buttons if they become interactive); MarsMap wrapper div only for aria-label/test id.
7. **Final step (◆D):** open PR `feature/frontend` to `development` (only with user approval); tick the DoD in plan §8.

- **Environment notes:** Node >= 24. Core for manual checks: from `core/`, `python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"` then `.venv/Scripts/uvicorn app.main:app --port 8000` (fallback-only routes work without MS6), or `docker compose up --build` from the root.
- **Known issues:** none known. Generating fixtures with system Python needs `pandas` + `openpyxl`; stub `app.settings` if `pydantic_settings` is missing.

## Deviations

1. Plan updated during WP0: `development` (merged into `feature/frontend`) added `riesgo` (MS5 evaluation, nullable) to `POST /api/ruta` and `ms5` to `/api/health`. Plan §1/§2 D8/D9/§4 now use it (risk badge, MS5 warnings, color-by Risk).
2. WP1 version deviations: jsdom 29.1.1 (31 needs node >= 24.15; local is 24.10), msw 2.15.0 (not v3), eslint 9.39.5, typescript 5.9.3 (typescript-eslint peer), `vite/client` types via tsconfig instead of `vite-env.d.ts`.
3. Windows shell note: in this environment bash pipes/`&&` chains to npm hit a WSL shim error; run npm commands via PowerShell.
4. WP2: fixtures loaded via `import.meta.glob` in `src/test/handlers.ts` (`loadFixture`) because tsconfig lacks `resolveJsonModule`; keep it that way. `baseLayers.json` generated by the orchestrator from `core/app/datasources/base_layers.py` over `data/gale` (traverse decimated 1/5). Precalc routes may have `control_calidad: null` and null `tramos` cells.
