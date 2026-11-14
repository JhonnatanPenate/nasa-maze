# features/point_analysis

Point analysis feature: elevation, slope, and terrain class at a coordinate
(`GET /terrain/point`, plan F2).

## Contents

- `domain/point_analysis.py` — `PointAnalysis` frozen result entity
  (`lat`, `lon`, `elevation_m`, `slope_deg`, `terrain_class`).
- `application/analyze_point.py` — `AnalyzePoint` use case: one
  `TerrainRepository.window_around(point, 1)` read feeds both the centre
  elevation and `SlopeCalculator.compute_at_center`; the slope is classified
  by `TerrainClassifier`.
- `presentation/point_router.py` — router for `GET /terrain/point`
  (`lat`, `lon`, `body` query params; `body` is accepted and ignored by the
  MVP).
- `presentation/point_schemas.py` — `PointAnalysisResponse` pydantic DTO.
- `presentation/point_mapper.py` — `PointMapper` domain → DTO adapter.

The use case is wired in `app/composition/point_dependencies.py`
(`get_analyze_point`), which builds `DemTerrainRepository` from
`Depends(get_raster_datasource)` so test `dependency_overrides` propagate.

## Layer rules

`presentation → application → domain`. The use case depends on the
`TerrainRepository` port only. Presentation must not import rasterio or
datasource internals; errors map to 422 (Pydantic), 404 (nodata), 502
(datasource failure).
