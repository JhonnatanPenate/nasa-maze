# MS5 Phase 6 notes — integration, offline verification, DoD status

Phase 6 of `IMPLEMENTATION_PLAN_RISK_ASSESSMENT.md`. Everything verifiable
without docker/network was verified in this environment (Python 3.13.5 venv,
no docker daemon, MS3/MS4 not running); docker-dependent items are marked
**deferred** below and in the final report.

## 1. Offline run verification (T5.3-style)

Booted the real app with `uvicorn app.main:app` and exercised every
endpoint — no network upstreams involved:

- `RISK_DATASOURCE_MODE=synthetic` (default): `/health` → ok with
  terrain/raster/environment ok; `/risk/point` → real scores from the
  **real REMS/RAD SQLite catalog** (`data/processed/mars/risk/`); `/risk/evaluate`
  → 36 segments, restrictions populated; `/risk/factors`, `/risk/meta`,
  `/risk/vehicle-profiles`, `/risk/area` (540 cells) all 200; point outside
  coverage → 404 `{"detail": ...}`.
- `RISK_DATASOURCE_MODE=unavailable`: `/health` → `degraded`
  (terrain/raster unavailable, environment ok — catalog still local);
  `/risk/point` → **502**; `/risk/factors` → slope/roughness/dunes
  `available:false`, temperature/radiation still `true`.

**No runtime network proof (code review):** `httpx` is imported only by
`app/infrastructure/datasources/http_*.py` and `app/composition/
dependencies.py` (client construction for `datasource_mode=http`).
`core/domain`, `core/application`, `core/ports`, `features/*/application`
import no httpx/fastapi/sqlite3 (enforced by
`tests/unit/test_architecture.py`). The SQLite catalog is opened read-only;
the only runtime file reads are `config/*.yaml|json` and the catalog.
Golden-route + API tests run fully offline (synthetic adapters + fake env
repo).

## 2. Compose / docker status

- No root `docker-compose.yml` exists in the repo — each service ships a
  standalone snippet (`location-service`, `risk-assessment`). MS5's
  `risk-assessment/docker-compose.yml` uses repo-root-relative paths
  (`build: ./risk-assessment`, `./data/...`, `./risk-assessment/...`
  volumes) so it merges cleanly into a future root compose; standalone
  invocation documented in the file header and `risk-assessment/README.md`:
  `docker compose --project-directory . -f risk-assessment/docker-compose.yml up`.
- `risk-assessment/Dockerfile` reviewed by inspection: `python:3.13-slim`,
  runtime deps only (ingest extras excluded), non-root user `risk` (uid
  10005), `EXPOSE 8005`, uvicorn CMD, HEALTHCHECK on `/health`. Data is
  **not** baked into the image — catalog/config arrive via compose
  volumes (seed fallback `data/seed/risk_catalog_seed.sqlite` is committed).
- **Deferred:** `docker build`, compose up, and the live MS3/MS4
  integration run — no docker in this environment. The live-upstream
  pytest module (`tests/integration/test_live_upstream.py`) auto-skips
  when :8003/:8004 are unreachable and will exercise the `http` adapters
  once the stack is up.

## 3. Handoff & docs

- `docs/risk-assessment/HANDOFF_ROUTING_CORE.md` — endpoints, request/
  response shapes, error table, SPEC vs additive fields, radiation-rate
  boundary (MS6 owns dose), env config, deployment notes.
- `docs/risk-assessment/UPSTREAM_REQUESTS.md` — no open upstream needs.
- Root `README.md` status table now lists every service folder with
  honest status (MS5 marked code+tests done, docker run pending).
- `docs/ARCHITECTURE.md` §3 component table gained an `Estado (2026-11)`
  column.
- `risk-assessment/README.md` phase status updated (was stale "Phase 1").

## 4. Definition of Done (§12) — verified status

| Item | Status |
|---|---|
| `docs/risk-assessment/{PHASE0_NOTES,DATA_INVENTORY_MS5,HANDOFF_ROUTING_CORE}.md` exist & current | ✅ (+ UPSTREAM_REQUESTS, PHASE6_NOTES) |
| `AGENTS.md` + `CLAUDE.md` from template; README per package | ✅ (verified: every `app/**` dir with .py has README.md) |
| Contract in `docs/api-contracts/` + `packages/contracts/.../openapi.yaml`; contract test green | ✅ |
| `python -m app.ingest` builds catalog; report reviewed; seed committed | ✅ Phase 2 (`data/seed/risk_catalog_seed.sqlite` + `ingest_report.json` committed) |
| SPEC endpoints exactly as specified | ✅ point/evaluate/factors/health |
| Extensions additive, SPEC fields/scores untouched | ✅ vehicle-profiles, meta, area, confidence/provenance/notes/restrictions |
| Missing data never safe; no factors → unknown | ✅ |
| synthetic/http/unavailable modes; upstream failure → 502 | ✅ tested (respx + unavailable mode) |
| No runtime Internet/other-service DB/direct GeoTIFF | ✅ architecture test + review |
| Suite green offline; coverage targets; arch test | ✅ 293 passed/3 skipped; cov 95% total, 98% domain+application |
| Docker image builds; compose with MS3/MS4 | ⏸ **deferred** — no docker in env |
| Thresholds/weights/limits in DECISIONS.md | ✅ MS5-D1…D24 |
| No files outside allowed paths modified | ✅ see §5 |

## 5. Files touched outside `risk-assessment/`

- `docs/DECISIONS.md`, `docs/api-contracts/risk-assessment-service.md`,
  `docs/ARCHITECTURE.md`, `docs/risk-assessment/*` — docs (allowed).
- `packages/contracts/risk-assessment/openapi.yaml` — allowed.
- `data/processed/mars/risk/risk_catalog.sqlite` + `ingest_report.json` —
  allowed output path (gitignored data, not committed).
- `README.md` (root) — Phase-6 task explicitly requires the status-table
  update; flagged here for Gate 2 transparency.
- No other service's code or REST contract was modified.

## 6. Deferred items (Gate 2 follow-ups)

1. `docker build -t ms5-risk-assessment ./risk-assessment` + compose run.
2. `RISK_DATASOURCE_MODE=http` live run against MS3 :8003 / MS4 :8004 and
   re-run `tests/integration/test_live_upstream.py` unskipped.
3. Merge `risk-assessment` service block into a root `docker-compose.yml`
   when the stack lands (paths already root-relative).
