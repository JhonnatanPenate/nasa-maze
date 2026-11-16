# nasa-maze-app — Frontend Implementation Plan

**Version:** 1.0.0 | **Status:** Approved | **Date:** 2026-11-15
**Audience:** Orchestrator (manager) agent coordinating implementation subagents.
**System context:** [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) v2.1 · Core: [`core/README.md`](../../core/README.md) · Contract sample: [`docs/data/EJEMPLO_API_RESPUESTA.json`](../data/EJEMPLO_API_RESPUESTA.json)
**Progress / handoff:** [`PROGRESS.md`](PROGRESS.md) (source of truth for status — read it first)

Build an independent, Core-only, offline-capable, Waze-like web app in `nasa-maze-app/` (React + TypeScript + Vite + Tailwind v4 + Leaflet), test-first, driven by an orchestrator + TDD developer + read-only reviewer subagents, with mandatory user checkpoints and a versioned handoff file so another orchestrator can resume.

## 0. Bootstrap (WP0 — done by the planning orchestrator)

1. This plan saved as `docs/nasa_maze_app/IMPLEMENTATION_PLAN_APP.md`.
2. `docs/nasa_maze_app/PROGRESS.md` created (status table + "Resume here" handoff block, §9).
3. Subagent profiles `.devin/agents/app-tdd-developer.md`, `app-tdd-developer-plus.md`, `app-code-reviewer.md` created; latest `development` merged into `feature/frontend`; committed.
4. **Mandatory pause:** profiles only load at session start → the user restarts the session (§9.4) BEFORE any app code is written.

## 1. Context (facts the developer must not re-discover)

- Frontend talks **only to Core** (`/api/*`, Core on :8000). Never to MS1/MS3/MS4/MS5/MS6 directly. All calls use the relative base `/api` (Vite dev proxy / nginx proxy) → no CORS, no hardcoded hosts.
- Core endpoints used:

  | Endpoint | Use in UI |
  |---|---|
  | `GET /api/health` | `{status, servicios:{ms6,ms5,ms4,ms1: "ok"\|"down"\|"no_configurado"}, fallback_precalculado, aoi:[w,s,e,n], sols:[1360,2140,3290,4710], bounds_rejilla}` → capability gating (always 200) |
  | `GET /api/capas/base` | FeatureCollection: `capa=puntos_quimica` (21 CheMin sites; props `nombre`, `sol`, `elevacion_m`, `hematita_pct`, `esmectitas_pct`, `tridimita_pct`, `sulfatos_pct`, … — nulls allowed), `capa=traza_msl` (MultiLineString), `capa=origen` (Bradbury) |
  | `GET /api/capas/raster/{banda}?cmap=viridis\|gray` | PNG + header `X-Bounds: w,s,e,n` (bands: `pendiente_grados, rugosidad_m, fraccion_oscura, inercia_termica_tiu, albedo, distancia_duna_m`); 502 if data unreadable |
  | `POST /api/ruta` | body `{lon,lat,material,sol,hora,vmax}` → `{geojson, resumen, tramos, control_calidad, fuente: "ms6"\|"precalculada", riesgo: object\|null}`; errors: 400/404 forwarded from MS6 (`detail`), 422 validation (`detail` is a list), 503 no backend |
  | `GET /api/lugares/buscar?q=&limit=` | origin search (only when `servicios.ms1 == "ok"`); proxied MS1 `/v1/places/search` payload (see `docs/api-contracts/location-service.md`) |

- **Route semantics:** the destination is a **mineral** (`hematita|esmectitas|tridimita|sulfatos`); MS6 picks the best outcrop and returns it as `capa=objetivo` (`nombre`, e.g. "Oudam", `material`). Response geojson features: `ruta_optima` LineStrings (props `tipo_suelo`, `modelo_usado`, `inclinacion_grados`), `contrafactual` LineString (`nombre: ruta_modelo_global`), `objetivo` Point, `origen` Point.
- `resumen`: `distancia_km, hora_llegada ("S+1 08:15"), dosis_rad_acum_uGy, horas_espera_nocturna, costo_objetivo, nodos_expandidos, objetivo, material, comparativa_bagnold{celdas_duna_ruta_optima, celdas_duna_contrafactual, horas_ahorradas_en_arena, distancia_minima_a_duna_m}`.
- `tramos[]`: `tramo, hora_lmst_inicio, hora_lmst_fin, tipo_suelo, modelo_usado, r2_ajustado, distancia_m, inclinacion_media_grados, inclinacion_max_grados, dosis_tramo_uGy, dosis_acumulada_uGy, temp_suelo_K ("240-253")`.
- `riesgo` (MS5 `POST /risk/evaluate` passthrough, **null** when MS5 is not configured or fails — never breaks the route; see `docs/api-contracts/risk-assessment-service.md`): `overall_risk (0..1|null), risk_level ("low"|"medium"|"high"|"unknown"…), segments[{from{lat,lon}, to{lat,lon}, distance_m, risk, factor_scores, warnings[], local_time_hour}], warnings_summary[], dominant_factor, restrictions[{segment, code, blocking, message, factor, value, limit}], hotspots[{segment, risk, level, distance_m}], blocking_segments[], confidence`. Dose still comes from MS6 (`resumen`/`tramos`), never from MS5.
- **Fallback (MS6 down):** only `hematita|esmectitas|tridimita`, origin Bradbury (137.4416, -4.5895), `sol=1360, hora=9, vmax=1000`.
- **Mars rules** (skill `mars-geodata`): CRS `IAU_2015:49900`. Leaflet's Web-Mercator view is **display only** (acceptable for an 18×11 km equatorial AOI); every metric (distance, dose, time, risk) comes from Core — never compute distances with Leaflet. AOI `[137.345, -4.740, 137.455, -4.580]`.
- JSON field names stay in Spanish (contract); everything else (code identifiers, UI text, docs) is English. A single `domain/labels.ts` maps contract values → English labels.

## 2. Decisions (from user Q&A)

| # | Decision |
|---|---|
| D1 | Destination = **mineral target** picker; candidate outcrops (sites with `<material>_pct > 0`) highlighted; reached site (`objetivo`) shown after routing |
| D2 | Origin is **health-driven**: MS6 ok → Bradbury + named CheMin sites + click-on-map inside AOI (+ search box if MS1 ok). Only fallback → locked to Bradbury. Nothing → route button disabled with message, map still works |
| D3 | **Hybrid basemap**: online OpenPlanetaryMap Mars tiles (`VITE_MARS_TILE_URL`, default `https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-mars-basemap-v0-2/all/{z}/{x}/{y}.png`, EPSG:3857, attribution "OpenPlanetaryMap"); auto-fallback to offline mode (dark canvas + Core raster overlay, slope by default) when a probe tile fails/times out. Manual toggle too |
| D4 | Mission params in a collapsed **"Mission settings"** panel: sol (from `health.sols`), start hour (0–23.5, step 0.5), vmax (m/h, >0). Defaults = reference request (1360, 9, 1000). Locked read-only in fallback mode |
| D5 | **Leaflet + react-leaflet** |
| D6 | **Vitest + React Testing Library + MSW** test-first; **Playwright** smoke e2e in the final WP |
| D7 | Docker image for the app (multi-stage node → nginx) added as a service to the **existing** root `docker-compose.yml` |
| D8 | **Frontend only**: Core is not modified. Risk info uses `riesgo` when present; when `riesgo` is null, warnings are derived client-side from `tramos`/`resumen`. Gaps logged in `docs/nasa_maze_app/UPSTREAM_REQUESTS.md` |
| D9 | Waze-like route UX: **alternative routes** (bold optimal + faded dashed counterfactual, clickable to compare) and **route colored by soil, slope or risk** (toggle; "Risk" only when `riesgo` has segments) with legend. No itinerary list, no playback |
| D10 | Models: orchestrator `opus`, developer `swe` (`sonnet` via `-plus` profile for WP4/WP6), reviewer `sonnet` read-only |
| D11 | Minimal state: React `useState` + small hooks; no Redux/zustand/react-query (ponytail). Tailwind v4 via `@tailwindcss/vite`; no component library |

## 3. Architecture of `nasa-maze-app/`

```
nasa-maze-app/
├── AGENTS.md  README.md  .env.example  .dockerignore  Dockerfile  nginx/default.conf.template
├── package.json  package-lock.json  vite.config.ts (incl. vitest config)  tsconfig*.json  eslint.config.js
├── playwright.config.ts  e2e/smoke.spec.ts
├── index.html
└── src/
    ├── main.tsx  App.tsx  index.css            # @import "tailwindcss"; leaflet css
    ├── api/
    │   ├── types.ts                            # Core contract types (Spanish field names)
    │   └── coreClient.ts                       # getHealth, getBaseLayers, getRasterBand, postRoute(signal), searchPlaces; CoreError{status,detail}
    ├── domain/                                 # pure TS, no React/Leaflet/fetch
    │   ├── labels.ts                           # minerals, soils, bands, risk levels → English labels + colors
    │   ├── capabilities.ts                     # Health → {routing:'live'|'fallback'|'none', originMode, materials, missionEditable, searchEnabled, riskEnabled}
    │   ├── mission.ts                          # defaults, validation, buildRouteRequest, isInsideAoi
    │   ├── sites.ts                            # base layers → sites, candidate sites per mineral, Bradbury, traverse
    │   └── routeView.ts                        # RouteResponse → {segments, riskSegments, alternative, target, origin, bounds, kpis, warnings}; slope/soil/risk color scales
    ├── hooks/  useHealth.ts  useBaseLayers.ts  useRasterBand.ts  useRoute.ts  (abort + loading + error)
    ├── components/
    │   ├── map/   MarsMap.tsx  Basemap.tsx  RasterOverlay.tsx  SitesLayer.tsx  RouteLayer.tsx  OriginClickHandler.tsx  Legend.tsx
    │   └── panel/ RoutePanel.tsx  OriginPicker.tsx  MineralPicker.tsx  MissionSettings.tsx  RouteSummary.tsx  LayerControls.tsx  StatusBadge.tsx
    └── test/  setup.ts  server.ts (MSW)  handlers.ts  fixtures/{route.json, health.live.json, health.fallback.json, health.none.json, baseLayers.json}
```

Rules: `domain/` imports nothing from React/Leaflet/api runtime (types only); components call hooks, hooks call `coreClient`; only `coreClient` knows URLs; one component per file; English only; no comments unless non-obvious.

### 3.1 Layout (minimalist, map-first)

- Full-screen map. Floating top-left card (≈360 px, becomes a bottom sheet on small screens): **From** (origin), **To** (mineral), "Mission settings" (collapsed), big **Find route** button (spinner + Cancel while routing; MS6 can take ~1–15 s, Core timeout 120 s).
- After routing the same card shows **RouteSummary**: target name, distance km, arrival LMST, RAD dose µGy, night wait h, source badge (`Live` / `Precalculated`), risk badge (`riesgo.risk_level` + `overall_risk`, or "Risk unavailable"), warnings (MS5 `warnings_summary` + blocking `restrictions` messages when present; otherwise client-derived: max slope ≥15°, dune cells crossed, night wait > 0), and an alternatives row "Optimal (soil-aware)" vs "Global model" with the Bagnold comparison. Clicking the faded route on the map selects it in the card. "New route" button returns to the form.
- Top-right: StatusBadge (Routing: Live / Fallback / Unavailable; Basemap: Online / Offline). Bottom-right: LayerControls (basemap toggle, raster band select + opacity, Curiosity traverse toggle, color-by Soil | Slope | Risk) and Legend.
- Route styling: white casing + 6 px colored line per `ruta_optima` segment (Risk mode: per `riesgo.segments` from/to). Slope scale <5° green, 5–10 yellow, 10–15 orange, ≥15 red; soil palette and risk-level palette from `labels.ts`; blocking segments outlined red. Alternative: 4 px gray dashed, 60 % opacity. Segment click → popup (soil, model, slope / risk, warnings). Fit bounds to route on success. Origin and target markers distinct (Waze-like pin for target).

## 4. Feature specs & test matrix (≥3 tests per feature: happy / edge / failure)

| Feature | Happy | Edge | Failure |
|---|---|---|---|
| F1 coreClient | each call parses fixture; raster returns objectURL + parsed `X-Bounds` | `postRoute` aborted → AbortError, not CoreError; `riesgo: null` accepted | non-2xx → `CoreError` with `status` + `detail` (string detail for 400/404/503; 422 list joined) |
| F2 capabilities | ms6 ok → live, 4 materials, free origin, editable mission | ms1 ok toggles search; ms5 ok sets riskEnabled; fallback only → Bradbury locked, 3 materials, mission locked | all down + no fallback → routing `none` |
| F3 mission | defaults = reference request; buildRouteRequest | hour 23.5 ok, 24 invalid; click outside AOI rejected | sol not in `health.sols` invalid; vmax ≤ 0 invalid |
| F4 sites | 21 sites parsed; candidates for hematita include Oudam | coincident coords deduped for origin list | null/missing pct columns → no candidates, no crash |
| F5 routeView | segments/alternative/target/origin split; KPIs mapped; bounds; riskSegments from `riesgo.segments` | slope colors at 5/10/15 thresholds; no contrafactual → no alternative; `riesgo` null → client-derived warnings | malformed geojson → typed error shown as banner |
| F6 MarsMap/Basemap | online tiles rendered when probe ok | manual toggle; offline enables slope overlay | probe error/timeout → offline mode + badge |
| F7 Raster/Sites layers | overlay drawn with X-Bounds; sites + traverse + Bradbury | candidate highlight changes with mineral | raster 502 → layer control shows error, map stays |
| F8 RoutePanel | select mineral + Find route → POST body correct | live: map click sets origin; search result sets origin | fallback disables sulfates (tooltip "Requires live routing engine"); 503/400 detail shown; health refetched on 503 |
| F9 RouteLayer + RouteSummary | segments colored, KPIs + risk badge shown, source badge | color-by toggle (Risk hidden when no riesgo); clicking alternative selects it | cancel during loading → no route, button re-enabled |
| F10 Docker/compose | image builds; `/` serves SPA; `/api/health` proxied | SPA deep-link fallback to index.html | core down → app loads, badge "Unavailable" |
| E2E (Playwright) | stack up: choose Hematite → route drawn + "Oudam" + distance | tile host blocked (`page.route` abort) → Offline badge | — |

Mocks: MSW handlers built from `docs/data/EJEMPLO_API_RESPUESTA.json` (copied, trimmed, into `src/test/fixtures/route.json`, plus a `riesgo` sample from the MS5 contract doc), health variants (live / fallback / none), base layers snapshot (generated once from Core: `curl localhost:8000/api/capas/base` or Core `TestClient`). Leaflet in jsdom: assert via RTL on Leaflet DOM (`.leaflet-interactive` paths, markers by `title`/`aria-label`); panel tests may mock `MarsMap`.

## 5. Tooling

- Node 24 (installed), Vite `react-ts` template, React 19, TypeScript strict, Tailwind v4 (`tailwindcss` + `@tailwindcss/vite`), `leaflet` + `react-leaflet` + `@types/leaflet`; dev: `vitest`, `jsdom`, `@testing-library/{react,user-event,jest-dom}`, `msw`, `@playwright/test`, eslint from the template.
- **Exact versions pinned** (`npm i -E`), each published ≥ 7 days ago (check `npm view <pkg> time --json` in WP1); no `latest` / `^` ranges for added deps.
- Scripts: `dev`, `build` (`tsc -b && vite build`), `preview`, `test` (`vitest run`), `test:watch`, `typecheck` (`tsc -b --noEmit` or equivalent), `lint`, `e2e` (`playwright test`).
- Env: `CORE_URL` (Vite dev proxy target, default `http://localhost:8000`), `VITE_MARS_TILE_URL` (build-time; empty = offline only). Nginx: `CORE_UPSTREAM` (default `http://core:8000`) via the official nginx image `templates/` envsubst; `proxy_read_timeout 180s` (Core route 120 s + MS5 evaluation).

## 6. Work Packages

```
WP0 → [RESTART SESSION] → WP1 → WP2 → WP3 → ◆A → WP4 ∥ WP5 → ◆B → WP6 → ◆C → WP7 → WP8 → ◆D
```

◆ = user checkpoint (§9). WP4 and WP5 may run in parallel (disjoint dirs: `components/map` + map hooks vs `components/panel` + `useRoute`); the orchestrator merges both into `App.tsx`. WP6 needs both.

| WP | Scope | Files | Acceptance | Model |
|---|---|---|---|---|
| **WP0 Bootstrap** (orchestrator) | plan + PROGRESS + profiles; merge `development` into `feature/frontend` | `docs/nasa_maze_app/{IMPLEMENTATION_PLAN_APP,PROGRESS}.md`, `.devin/agents/app-*.md` | committed; user told to restart session | orchestrator |
| **WP1 Scaffold** | Vite react-ts, Tailwind v4, Vitest+RTL+MSW setup, Vite proxy, scripts, pinned deps; first red→green test "App renders map container + panel placeholder" | `nasa-maze-app/**` config files, `src/main.tsx`, `src/App.tsx`, `src/index.css`, `src/test/{setup,server,handlers}.ts`, `AGENTS.md`, `README.md`, `.env.example`, `.gitignore` | `npm ci && npm run typecheck && npm run lint && npm test && npm run build` green | swe |
| **WP2 API client** | F1 + contract types + fixtures | `src/api/**`, `src/test/fixtures/**`, `src/test/handlers.ts`, tests | F1 rows green | swe |
| **WP3 Domain** | F2–F5 | `src/domain/**` + tests | F2–F5 rows green; `domain/` has no react/leaflet/fetch imports | swe |
| ◆A | checkpoint | | | |
| **WP4 Map shell** | F6, F7 + hooks `useHealth/useBaseLayers/useRasterBand` | `src/components/map/{MarsMap,Basemap,RasterOverlay,SitesLayer,Legend}.tsx`, `src/hooks/{useHealth,useBaseLayers,useRasterBand}.ts` + tests | F6–F7 green | swe-plus (sonnet) |
| **WP5 Route panel** | F8 + `useRoute` + `OriginClickHandler` | `src/components/panel/{RoutePanel,OriginPicker,MineralPicker,MissionSettings,StatusBadge,LayerControls}.tsx`, `src/hooks/useRoute.ts`, `src/components/map/OriginClickHandler.tsx` + tests | F8 green | swe |
| ◆B | checkpoint (after orchestrator wires WP4+WP5 into `App.tsx`; `npm run dev` shows Gale with sites, overlay and working form) | | | |
| **WP6 Route rendering** | F9: RouteLayer (casing, soil/slope/risk coloring, popups, alternative), RouteSummary, fit bounds, App integration | `src/components/map/RouteLayer.tsx`, `src/components/panel/RouteSummary.tsx`, `src/App.tsx` + tests | F9 green; manual: route over live Core | swe-plus (sonnet) |
| ◆C | checkpoint | | | |
| **WP7 Docker + compose** | F10 | `nasa-maze-app/{Dockerfile,.dockerignore,nginx/default.conf.template}`, root `docker-compose.yml` (add `app` service: `build: ./nasa-maze-app`, `ports: ["3000:80"]`, `environment: CORE_UPSTREAM: http://core:8000`, `depends_on: [core]`) | `docker compose up --build` → http://localhost:3000 works; existing services untouched | swe |
| **WP8 E2E + review + docs** | Playwright smoke vs compose stack; full-diff review; minors fixed; docs | `playwright.config.ts`, `e2e/smoke.spec.ts`, READMEs, `docs/nasa_maze_app/UPSTREAM_REQUESTS.md`, root `README.md` + `docs/ARCHITECTURE.md` status row (frontend), `docs/ai/USO-DE-IA.md` line | DoD §8 all checked | swe + reviewer |
| ◆D | final checkpoint: offer PR to `development` | | | |

## 7. Agent orchestration

### 7.1 Roles

| Role | Profile / model | Duty |
|---|---|---|
| Orchestrator (root) | current session, `opus` | owns this plan + PROGRESS.md, sequences WPs, runs verification itself, commits, runs checkpoints |
| Developer | `app-tdd-developer` (`swe`) / `app-tdd-developer-plus` (`sonnet`, WP4/WP6) | one WP, test-first, only listed files |
| Reviewer | `app-code-reviewer` (`sonnet`, read-only) | reviews one WP diff |
| Explore | `subagent_explore` only for unexpected questions | |

### 7.2 Profiles

Created in WP0 under `.devin/agents/` (`app-tdd-developer.md`, `app-tdd-developer-plus.md`, `app-code-reviewer.md`). Read them there; they encode the rules of §1–§3 for subagents. If a new session does not list them as available profiles, fall back to `subagent_general` (developer) / `subagent_explore` (reviewer) and paste the profile body at the top of the prompt; record it as a deviation.

### 7.3 Prompt template (subagents are stateless — paths, not pasted content)

```
WP<n> — <title>. Root: nasa-maze-app/ (run commands there).
Read: docs/nasa_maze_app/IMPLEMENTATION_PLAN_APP.md §1, §2, §3, §4 rows <..>, §5, §6 row WP<n>.
Files to create/modify (exhaustive): <list from §6>.
Existing modules you may import: <paths from earlier WPs>.
Done when: <acceptance column of §6>.
```

### 7.4 Loop per WP

1. Mark WP `in_progress` in PROGRESS.md.
2. Spawn developer (foreground; WP4 ∥ WP5 background, max 2 concurrent) with the §7.3 prompt.
3. Orchestrator runs `npm run typecheck && npm run lint && npm test && npm run build` itself (never trust the report).
4. Spawn reviewer with `git diff <wp-base>..HEAD -- <wp paths>` (or the working-tree diff before commit).
5. Blockers/majors → `resume` the same developer with the findings → back to 3.
6. One conventional commit `feat(app): WP<n> <title>`; PROGRESS.md updated in the same commit. Branch `feature/frontend`; no push without user approval. Minors batched into WP8.

## 8. Definition of Done

- [ ] `npm ci && npm run typecheck && npm run lint && npm test && npm run build` green in `nasa-maze-app/`; ≥ 3 tests per feature.
- [ ] App works in all three backend states: live MS6 (free origin, 4 minerals, settings), fallback only (Bradbury, 3 minerals, locked settings), none (map + layers, routing disabled with message).
- [ ] Route displayed Waze-style: optimal colored by soil/slope/risk + alternative; KPIs, risk and source badges; errors readable.
- [ ] Online basemap with automatic offline fallback; fully usable with no internet once images are built.
- [ ] Only Core is called, via relative `/api`; no hardcoded hosts; config via env.
- [ ] `docker compose up --build` serves the app on :3000 alongside the existing stack; Playwright smoke green.
- [ ] READMEs/AGENTS.md written; PROGRESS.md final; UPSTREAM_REQUESTS.md lists gaps; `docs/ai/USO-DE-IA.md` entry.

## 9. Token-budget checkpoints & handoff (mandatory)

### 9.1 When to pause

The AI token quota is low → the orchestrator **must stop and ask** the user (`ask_user_question`: "Continue with WP<n+1>" / "Stop and save handoff") at: after WP0 (forced session restart), ◆A (after WP3), ◆B (after WP4+WP5), ◆C (after WP6), ◆D (end). Also pause early whenever the remaining budget is unlikely to finish the next WP. Never start a WP that cannot be finished and committed.

### 9.2 Before every checkpoint

All green work committed; PROGRESS.md updated and committed (`docs(app): checkpoint <X>`). No uncommitted or half-done WP left.

### 9.3 If the user says stop → handoff

Update the "Resume here" block of `docs/nasa_maze_app/PROGRESS.md` and commit (`docs(app): handoff after WP<n>`): branch + last commit SHA, WP status table, next WP and its exact prompt, open review findings/minors, deviations, environment notes (how to run Core), known issues. Offer to push the branch (only with explicit approval).

### 9.4 How to resume (shown to the user at every stop and after WP0)

Open a new Devin session in the repo root (so `.devin/agents/app-*.md` load), `git checkout feature/frontend`, and prompt:

> You are the orchestrator for nasa-maze-app. Read docs/nasa_maze_app/IMPLEMENTATION_PLAN_APP.md and continue from the "Resume here" section of docs/nasa_maze_app/PROGRESS.md, following §7 and §9.

## 10. Verification commands

```bash
cd nasa-maze-app && npm ci && npm run typecheck && npm run lint && npm test && npm run build
# dev against Core (fallback-only is enough), from core/:
#   .venv/Scripts/uvicorn app.main:app --port 8000
npm run dev                 # http://localhost:5173, /api proxied to CORE_URL
# full stack, from repo root:
docker compose up --build   # app http://localhost:3000, core http://localhost:8000/docs
npx playwright test         # with stack up (BASE_URL=http://localhost:3000)
```

## 11. Risks

| Risk | Mitigation |
|---|---|
| OPM tile service down / slow / coarse at Gale zoom | probe + auto offline; URL configurable; offline overlays always available |
| Leaflet in jsdom (sizes, canvas) | SVG renderer, assert DOM; mock map in panel tests; Playwright covers real render |
| MS6 slow (1–15 s, ≤ 120 s) + MS5 evaluation (~6 s) | spinner + Cancel (AbortController); nginx timeout 180 s |
| Contract drift in Core/MS6/MS5 | types in one file; MSW fixtures from contract docs; reviewer checks contract; `riesgo` treated as optional |
| Profiles not loaded mid-session | WP0 forces restart before WP1; §7.2 fallback |
| Token exhaustion mid-WP | checkpoints + commit-per-WP + PROGRESS.md handoff |
| New deps supply chain | exact pins, ≥ 7-day-old versions |

---

**Deviations recorded during execution:** see `PROGRESS.md` → "Deviations".
