# infrastructure/repositories

Concrete `TerrainRepository` implementations.

## Contents (planned)

- `dem_terrain_repository.py` — `DemTerrainRepository`: implements the
  `TerrainRepository` port on top of a `RasterDatasource`; exposes
  `elevation_at(point)` and DEM-window queries returning domain objects.

## Layer rules

Implements `core/ports` and returns `core/domain` types only. Translates
datasource failures into `UpstreamDatasourceError` and nodata coverage gaps
into `NoCoverageError`. Contains no FastAPI or presentation code.
