# features/area_analysis

Area analysis feature: aggregate elevation/slope statistics over a bounding
box (`POST /terrain/area`, plan F4).

## Contents (planned)

- `domain/area_stats.py` — `AreaStats` entity.
- `application/analyze_area.py` — `AnalyzeArea` use case: bbox validation,
  repository DEM window, `SlopeCalculator`, stats incl. `steep_fraction`.
- `presentation/area_router.py` — router for `POST /terrain/area`.
- `presentation/area_schemas.py` — request/response pydantic DTOs.
- `presentation/area_mapper.py` — domain → DTO adapter.

## Layer rules

`presentation → application → domain`. The use case depends on the
`TerrainRepository` port only and enforces `max_window_cells`. Inverted or
degenerate bbox → 400; fully nodata window → 404; datasource failure → 502.
