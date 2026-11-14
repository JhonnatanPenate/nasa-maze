# infrastructure

Outer layer: concrete implementations of the `core/ports` contracts.

## Contents

- `datasources/` — `RasterDatasource` implementations
  (`SyntheticDemDatasource`, `GeoTiffRasterDatasource`) plus the
  raw-payload → `DemWindow` mapper.
- `repositories/` — `DemTerrainRepository`: `TerrainRepository`
  implementation backed by a `RasterDatasource`.

## Layer rules

May import `ports`, `domain`, rasterio, and numpy. Must NOT import FastAPI
routers or presentation code. Datasource failures are raised as
`UpstreamDatasourceError`; nodata coverage gaps as `NoCoverageError`. Swapping
the data source must only change code in this layer plus its mapper.
