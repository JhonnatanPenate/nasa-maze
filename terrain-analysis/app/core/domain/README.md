# core/domain

Innermost layer: entities, value objects, and pure geospatial computation.

## Contents

- `geo_point.py` — `GeoPoint(lat, lon)` frozen value object; validates
  lat ∈ [-90, 90], lon ∈ [-180, 180], finite values only.
- `bounding_box.py` — `BoundingBox(min_lon, min_lat, max_lon, max_lat)`;
  rejects inverted/degenerate boxes and out-of-range values;
  `contains(point)` is inclusive on all edges.
- `dem_window.py` — `DemWindow(elevation, cell_size_x_m, cell_size_y_m)`;
  a 2-D float64 elevation array with metric cell sizes.
  Helpers: `is_all_nodata()`, `center_value()`.
- `slope_calculator.py` — `SlopeCalculator.compute(window)` → slope in
  degrees via Horn's method on the 3×3 neighbourhood (vectorized numpy);
  `compute_at_center(window)` → centre-cell slope as a float.
- `terrain_class.py` — `TerrainClass` StrEnum:
  `flat | moderate | steep | hazardous`.
- `terrain_classifier.py` — `TerrainClassifier` maps slope degrees to a
  `TerrainClass` using configurable, strictly-increasing thresholds
  (defaults 5 / 15 / 30 deg).
- `distance_calculator.py` — `DistanceCalculator(radius_m)`; haversine
  `distance_m(a, b)` and linear `interpolate(a, b, fraction)` in lat/lon.
- `path_sample.py` — `PathSample(point, distance_m)`; cumulative distance
  from the path start.
- `path_sampler.py` — `PathSampler.sample(path, step_m, max_samples)` →
  evenly spaced `PathSample`s along the whole polyline plus the final
  point; enforces the `max_samples` cap arithmetically before generating.

## Decisions

- **Nodata convention:** nodata is always represented as `NaN` inside
  `DemWindow`. Infrastructure mappers convert raw nodata values to NaN at
  the boundary, so the domain never sees sentinel numbers.
- **Neighbour extrapolation (slope):** the window is padded with NaN so
  out-of-array cells are treated like nodata. Each NaN neighbour is
  replaced by linear extrapolation through the centre from its
  point-mirrored opposite (`n = 2*e - opposite`), falling back to the
  centre value when the opposite is missing too. This is exact for planar
  terrain wherever the mirrored opposite exists, so slopes next to nodata
  or DEM edges are not attenuated. Exception: at corners of the valid
  region a diagonal neighbour pair is mutually missing, so those two
  corner cells use the centre fallback and are approximate. A NaN centre
  cell yields NaN slope; a cell whose 8 neighbours are all NaN also
  yields NaN (unknown terrain must not report 0°).
- **Degenerate path:** a path whose total length is 0 (all identical
  points) yields exactly one sample at distance 0. Zero-length segments
  in the middle of a path are skipped without division by zero.
- **Endpoint dedup:** the final path point is not duplicated when the
  total length is an exact multiple of `step_m`; decided via
  `math.isclose(n_full*step, total_m, rel_tol=1e-12, abs_tol=1e-6)` and
  the last sample distance is always clamped to `total_m`.

## Known MVP limitations

- `DistanceCalculator.interpolate` and `PathSampler` use **linear lat/lon
  interpolation**, not great-circle interpolation; adequate for MVP
  segment lengths but **antimeridian-crossing paths are not supported**.
- An **antimeridian-crossing bbox is rejected as inverted** (min_lon >
  max_lon → `DomainValidationError` → HTTP 400).
- `DemWindow` carries **no origin/transform**: geolocation stays inside
  the datasource; the domain only knows cell sizes in metres.
- `RasterDatasource` has **no `read_metadata()`**: each datasource's
  mapper converts its native resolution (degrees → metres using the
  configured planet radius) into `DemWindow.cell_size_x_m` /
  `cell_size_y_m`.

## Layer rules

May import only the standard library and numpy. Must NOT import FastAPI,
pydantic DTOs, rasterio, or httpx. No I/O; everything is deterministic pure
computation that can be unit-tested in isolation.
