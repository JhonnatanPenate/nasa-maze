# nasa-maze-app

A "Waze for Mars": pick an origin and a mineral target inside the Gale crater
AOI and get a terrain- and risk-aware route from the Core service, rendered on
an interactive Leaflet map that degrades gracefully to an offline raster-only
mode when the Mars basemap tiles are unreachable.

## Quickstart

```bash
npm ci
cp .env.example .env   # optional; defaults point to Core on localhost:8000
npm run dev
```

The dev server proxies `/api/*` to `CORE_URL` (default `http://localhost:8000`),
so start the Docker Compose stack first for live data. Without Core the app
still loads and reports routing as unavailable.

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Vite dev server |
| `npm test` | Vitest + React Testing Library + MSW |
| `npm run typecheck` | TypeScript project-references check |
| `npm run lint` | ESLint flat config |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Serve the production build locally |

## Layout

`src/api` — Core REST client (the only place that knows URLs).
`src/domain` — pure TypeScript: capabilities, mission params, sites, route
view-models, English labels/colors for the Spanish contract fields.
`src/hooks` — data fetching hooks wrapping the client.
`src/components/map`, `src/components/panel` — UI, one component per file.
`src/test` — Vitest setup, MSW server/handlers, contract fixtures.

See `AGENTS.md` for the working rules and
`docs/nasa_maze_app/IMPLEMENTATION_PLAN_APP.md` for the full plan.
