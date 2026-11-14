# core/ports

Abstract interfaces that keep inner layers independent of infrastructure.

## Contents (planned)

- `terrain_repository.py` — `TerrainRepository` ABC: `elevation_at(point)`,
  `window_for(point/bbox)`, etc. Domain-facing contract used by use cases.
- `raster_datasource.py` — `RasterDatasource` ABC: `read_window(...)`,
  `read_metadata()`, `ping()`. Data-access contract implemented by
  `SyntheticDemDatasource`, `GeoTiffRasterDatasource`, and a reserved
  `HttpRasterDatasource`.

## Layer rules

Ports may import `core/domain` types but no concrete implementation, no
FastAPI, and no rasterio. Use cases depend on `TerrainRepository`, never on a
datasource directly — this is what makes the datasource swappable.
