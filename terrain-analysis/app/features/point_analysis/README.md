# features/point_analysis

Point analysis feature: elevation, slope, and terrain class at a coordinate
(`GET /terrain/point`, plan F2).

## Contents (planned)

- `domain/point_analysis.py` — `PointAnalysis` result entity.
- `application/analyze_point.py` — `AnalyzePoint` use case: repository
  elevation + slope window + `TerrainClassifier`.
- `presentation/point_router.py` — router for `GET /terrain/point`.
- `presentation/point_schemas.py` — `PointAnalysisResponse` pydantic DTO.
- `presentation/point_mapper.py` — domain → DTO adapter.

## Layer rules

`presentation → application → domain`. The use case depends on the
`TerrainRepository` port only. Presentation must not import rasterio or
datasource internals; errors map to 422 (Pydantic), 404 (nodata), 502
(datasource failure).
