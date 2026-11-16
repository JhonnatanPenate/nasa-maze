# Upstream requests (frontend to Core)

Gaps found while building `nasa-maze-app`. The frontend works around each one; none blocks it.

| # | Gap | Frontend workaround |
|---|---|---|
| 1 | `riesgo` in `POST /api/ruta` is nullable (MS5 may be down) | Warnings derived client-side from `tramos`/`resumen`; Risk color mode hidden |
| 2 | `riesgo.segments` are straight from/to pairs, not aligned with `ruta_optima` segments | Risk mode draws its own segments from `riesgo.segments` |
| 3 | `control_calidad` may be null and `tramos` may contain null cells on precalculated routes | Fields treated as optional |
| 4 | Route calculation takes ~6 s or more (MS4 profiling) | Loading state with Cancel; nginx `proxy_read_timeout` 180 s |
