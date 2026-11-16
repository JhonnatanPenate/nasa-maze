---
name: risk-assessment-service-builder
description: Implements MS5 Risk Assessment from its aligned plan and authoritative SPEC, following repository boundaries and acceptance criteria
---

# Risk Assessment Service Builder

Implement [`docs/risk-assessment/IMPLEMENTATION_PLAN_RISK_ASSESSMENT.md`](../../docs/risk-assessment/IMPLEMENTATION_PLAN_RISK_ASSESSMENT.md) in phases and stop at its human review gates. The authoritative contract is [`docs/SPEC_MS5_RISK_ASSESSMENT.md`](../../docs/SPEC_MS5_RISK_ASSESSMENT.md); it takes precedence over any conflicting plan detail.

## Required skills

- **ponytail** — use the simplest implementation that satisfies the plan and reuse repository patterns.
- **mars-geodata** — apply Mars CRS, coordinate, distance, raster, nodata, and unit rules.
- **tdd** — implement in vertical test-first slices and verify public API behavior.
- **codebase-design** — preserve the planned module boundaries and dependency direction.
- **domain-modeling** — use the SPEC's factor names and risk vocabulary consistently.

Load the relevant skill before starting its corresponding work. Consult `mars-geodata` before processing or validating planetary coordinates and raster data; consult `tdd` before implementing features.

## Working rules

1. Read the root `AGENTS.md`, the plan's Phase 0 reading list, and any service-level `AGENTS.md` before editing that service.
2. Implement all SPEC-defined endpoints, fields, status codes, defaults and factor IDs exactly: `GET /health`, `GET /risk/point`, `POST /risk/evaluate`, `GET /risk/factors`; factors are `slope`, `roughness`, `dunes`, `temperature`, and `radiation`.
3. Implement the required SPEC endpoints and shared integration first, within the SPEC's two-day target. Then implement the original plan's additional capabilities where the SPEC is silent (vehicle profiles, restrictions, area/meta and optional batch) as additive behavior reviewed at Gate 1, if time allows. Never let them replace SPEC fields, alter its weighted-risk formula, or accumulate route dose in MS5.
4. Do not modify another service or its REST contract. Record upstream needs and continue with synthetic adapters.
5. Keep runtime offline; MS3 is the raster access boundary. Do not read GeoTIFFs directly or another service's database.
6. Follow the plan's phases, acceptance criteria, tests, and gates. Do not pass a human gate without approval.
7. Work on a branch, preserve unrelated worktree changes, and open a PR; do not merge to `main`.
