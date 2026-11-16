# nasa-maze-app

Waze-like Mars route planner frontend for the NASA Space Apps "Interplanetary
Survival Guide: Martian Map" challenge. React + TypeScript + Vite + Tailwind v4
+ Leaflet. Talks **only** to the Core service through the relative `/api` base
(Vite dev proxy to `CORE_URL`, nginx proxy in Docker) — never to another
microservice and never to an absolute host.

## Commands

- `npm ci` — install (exact pinned versions, no `^` ranges)
- `npm run dev` — dev server (proxies `/api` → `CORE_URL`, default `http://localhost:8000`)
- `npm run typecheck` — `tsc -b`
- `npm run lint` — ESLint flat config
- `npm test` — Vitest + React Testing Library + MSW
- `npm run build` — `tsc -b && vite build`

## Rules

- Test-first: failing Vitest/RTL test before any implementation; >=3 tests per
  feature (happy / edge / failure). MSW handlers in `src/test/` mock Core.
- `src/domain/` is pure TypeScript: no react, no leaflet, no fetch. Components
  call hooks, hooks call `src/api/coreClient.ts`; only `coreClient` knows URLs.
- Never compute Mars metrics (distance, dose, time, risk) with Leaflet or
  client-side math — display the values returned by Core. Leaflet's Web
  Mercator view is display-only for the Gale crater AOI.
- JSON contract field names stay in Spanish (`resumen`, `tramos`, `riesgo`…);
  everything else — code identifiers, UI text, docs — is English. User-facing
  labels for contract values go through `src/domain/labels.ts`.
- Tailwind classes only; one component per file; no state libraries; no
  comments unless non-obvious. No new dependencies — they are pre-installed;
  ask the orchestrator if something is missing.
- Env vars: `CORE_URL` (dev proxy), `VITE_MARS_TILE_URL` (basemap; empty =
  offline-only). Copy `.env.example` to `.env` to override.
