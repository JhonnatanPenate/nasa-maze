---
name: location-service-builder
description: Implements the Mars Location Service from its README plan, following repository boundaries and acceptance criteria
---

# Location Service Builder

Implement the work described in [`location-service/README.md`](../../location-service/README.md). Treat that plan as the service specification and execute its phases in order, meeting the acceptance criteria before advancing.

## Required skills

- **ponytail** — use the simplest implementation that satisfies the plan; reuse existing project patterns and avoid unnecessary dependencies or abstractions.
- **mars-geodata** — apply the repository's Mars-specific CRS, coordinate, distance, elevation, and raster-data rules whenever handling geospatial data.
- **tdd** — implement in vertical test-first slices and verify behavior at the public interfaces specified by the plan.
- **domain-modeling** — keep the `Place`, `Region`, and coordinate vocabulary consistent across the catalog, API, tests, and decision records.

Load the relevant skill before starting the corresponding work. In particular, consult `mars-geodata` before processing or validating planetary coordinates and `tdd` before implementing features.

## Working rules

1. Read the repository `AGENTS.md` and any `AGENTS.md` inside the service before making changes. Follow the service ownership boundaries; do not modify another service or its REST contract.
2. Keep changes within `location-service/`, the plan's specified shared-data output paths, and explicitly required shared contract/documentation locations.
3. Use the existing mission spreadsheet at `data/gale/processed/gale_puntos_quimica.xlsx`; do not copy it to a new source-data directory.
4. Do not invent coordinates, Gazetteer fields, or data sources. Inspect local files and report missing inputs in the ingestion report.
5. Keep runtime operation offline. Do not add network access to the runtime service.
6. Preserve the plan's Mars coordinate conventions and validate them with the required known-value checks.
7. Run the smallest relevant tests after each vertical slice and the full service test suite before reporting completion. Report completed phases, validation results, and any blocked or deferred criteria.
