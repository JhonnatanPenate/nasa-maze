# features/point_analysis

Point analysis feature: elevation, slope, and terrain class at a coordinate
(`GET /terrain/point`, plan F2).

## Contents

- `domain/point_analysis.py` — `PointAnalysis` frozen result entity
  (`lat`, `lon`, `elevation_m`, `slope_deg`, `terrain_class`).
- `application/analyze_point.py` — `AnalyzePoint` use case: delegates the
  sampling to the shared `TerrainPointSampler` (`core/application`, one
  `window_around(point, 1)` read feeding elevation + slope); the slope is
  classified by `TerrainClassifier`.
- `presentation/point_router.py` — router for `GET /terrain/point`
  (`lat`, `lon`, `body` query params; `body` is accepted and ignored by the
  MVP).
- `presentation/point_schemas.py` — `PointAnalysisResponse` pydantic DTO;
  `terrain_class` is typed as the `TerrainClass` domain enum (serializes
  to its plain string value).
- `presentation/point_mapper.py` — `PointMapper` domain → DTO adapter.

The use case is wired in `app/composition/point_dependencies.py`
(`get_analyze_point`), built from the Depends-chained providers
`get_terrain_point_sampler` and `get_terrain_classifier`, so test
`dependency_overrides` on `get_raster_datasource` or `get_settings`
propagate.

## Behaviour notes

- Out-of-range `lat`/`lon` returns **400** on every endpoint (spec §4.4):
  the query params carry no range constraints, so `GeoPoint` raises
  `DomainValidationError`. Missing or non-numeric params stay **422**
  (Pydantic request validation).
- A valid elevation cell whose slope is undefined (all neighbours nodata)
  raises `NoCoverageError("Slope undefined at ...")` → 404.

## Layer rules

`presentation → application → domain`. The use case depends on the
`TerrainRepository` port only. Presentation must not import rasterio or
datasource internals; errors map to 422 (Pydantic), 404 (nodata), 502
(datasource failure).
