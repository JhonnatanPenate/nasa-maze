# app/core/domain

Value objects and pure grid/spherical math for the Raster Service.

## Key classes

- `GeoPoint`, `BoundingBox` — validated coordinates (lat [-90, 90],
  lon [-180, 180]; strict min < max; inclusive `contains`).
- `GridGeometry` — cell/geo index math for a north-up lon/lat grid.
  Cell selection semantics are identical to MS4 (centre-inclusion with
  eps 1e-9, sub-cell fallback, floor+clamp `cell_at`, clipped halo,
  `padded_slices`, `row_center_lat`, `rows_mean_lat`).
- `CellWindow` — outer cell range plus the core range inside it (halo
  offsets, read/core slices, `outer_bounds`); feeds the `/window` response.
- `BandInfo`, `DatasetMetadata` — band table and dataset description;
  `band()` lookup raises `UnknownBandError` listing valid names.
- `DistanceCalculator` — haversine + interpolation (Mars R = 3396.19 km).
- `PathSampler`, `PathSample` — arc-length sampling identical to MS4.
- `ColorRamp` — named ramps (`slope`, `viridis`, `grayscale`) mapping a
  float array + (min, max) to uint8 RGBA; NaN -> alpha 0.

## Layer rules

Stdlib + numpy only. No web-framework, DTO-schema or raster-driver imports.
All failures raise exceptions from `app.core.errors.exceptions`.
