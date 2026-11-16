# MS5 upstream requests

Tracked needs MS5 has for other services. **None open.**

- **MS3 Raster (`:8003`)** — consumed via `/raster/rejilla/point`,
  `/sample`, `/dataset` as specified; no changes requested. MS5 never reads
  GeoTIFFs directly.
- **MS4 Terrain (`:8004`)** — consumed via `/terrain/point` and
  `/terrain/profile`; no changes requested. MS4's `slope_deg` is reused as
  the soil/tilt predictor (`pendiente_grados`); MS3's own
  `pendiente_grados` band is deliberately not fetched.
- **MS6 Routing (`:8006`)** — no contract change needed to consume MS5
  (see `HANDOFF_ROUTING_CORE.md`). Possible future additive asks (richer
  per-segment diagnostics, `POST /risk/path/batch`) are Phase-7
  extensions requiring SPEC/contract review first.
- **Root `docker-compose.yml`** — does not exist yet; MS5 ships a
  standalone `risk-assessment/docker-compose.yml` with root-relative paths
  ready to merge (see HANDOFF §7). No other service needs modification.
