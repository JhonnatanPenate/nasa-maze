# core

Cross-cutting layers shared by all features.

## Contents

- `config/` — `settings.py`: `Settings` (pydantic-settings), env prefix `MS4_`.
- `domain/` — pure computation: `geo_point.py` (GeoPoint), `dem_window.py`
  (DemWindow), `halo_window.py` (HaloWindow: window + core slices),
  `slope_calculator.py` (Horn's method), `terrain_classifier.py`
  (TerrainClassifier + TerrainClass), `distance_calculator.py` (haversine),
  `path_sampler.py` (polyline interpolation).
- `application/` — application services shared across features:
  `TerrainPointSampler` (one window read → elevation + slope at a point).
- `errors/` — `exceptions.py` (DomainError + subclasses) and
  `error_handlers.py` (`register_exception_handlers(app)`).
- `ports/` — abstract contracts: `terrain_repository.py` (TerrainRepository)
  and `raster_datasource.py` (RasterDatasource).

## Layer rules

Everything under `core/` is inner-layer code. `domain` may import only stdlib
and numpy — never FastAPI, pydantic DTOs, rasterio, or httpx. `ports` may
import `domain` but no implementation. `errors` maps domain exceptions to
HTTP responses via handlers registered once in `app/main.py`.
