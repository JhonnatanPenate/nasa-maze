# point_query

`GET /raster/{dataset}/point?lat&lon[&band]` — nearest-cell band
value(s) at one coordinate, verbatim (no resampling), nodata → `null`
(plan F3, spec §4.3).

## Contents

- `domain/point_values.py` — `PointValues`: `GeoPoint` + band→float
  mapping; NaN is the in-domain nodata marker.
- `application/query_point.py` — `QueryPoint`: `metadata` →
  `GridGeometry.cell_at` → `read_cells` 1×1 per band. Raises
  `UnknownBandError` (404, lists valid names) and `NoCoverageError`
  (404 outside the extent); out-of-range coordinates fail in `GeoPoint`
  as `RasterValidationError` (400).
- `presentation/point_schemas.py` — `PointResponse` (`lat`, `lon`,
  `values`).
- `presentation/point_mapper.py` — `PointMapper`: NaN → `None` (JSON
  cannot carry NaN, D5); floats serialised verbatim, never rounded (D4).
- `presentation/point_router.py` — query params → `GeoPoint` → use case.

## Layer rules

`domain/` and `application/` import only `core/*` — never fastapi,
pydantic or rasterio. `presentation/` owns the DTO serialisation.
