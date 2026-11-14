# core/domain

Innermost layer: entities, value objects, and pure geospatial computation.

## Contents (planned)

- `geo_point.py` — `GeoPoint` value object (lat/lon validation).
- `dem_window.py` — `DemWindow`: elevation array + `cell_size_m` + origin + nodata.
- `slope_calculator.py` — `SlopeCalculator`: Horn's method on 3x3 neighborhoods → slope in degrees.
- `terrain_classifier.py` — `TerrainClassifier` + `TerrainClass` enum (thresholds from config).
- `distance_calculator.py` — `DistanceCalculator`: haversine on a sphere with configurable body radius.
- `path_sampler.py` — `PathSampler`: interpolate a polyline into sample points every N meters.

## Layer rules

May import only the standard library and numpy. Must NOT import FastAPI,
pydantic DTOs, rasterio, or httpx. No I/O; everything is deterministic pure
computation that can be unit-tested in isolation.
