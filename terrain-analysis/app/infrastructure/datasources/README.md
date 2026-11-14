# infrastructure/datasources

Concrete `RasterDatasource` implementations behind the data-access port.

## Contents (planned)

- `synthetic_dem_datasource.py` — `SyntheticDemDatasource`: deterministic
  in-memory numpy DEM for dev/test and the service default.
- `geotiff_datasource.py` — `GeoTiffRasterDatasource`: rasterio-backed reader
  over a GeoTIFF file (`Settings.dem_path`).
- `dem_window_mapper.py` — adapter converting raw raster payloads into the
  `DemWindow` domain object (including angular → metric cell-size conversion
  via `Settings.planet_radius_km`).

## Layer rules

May import `core/ports`, `core/domain`, `core/config`, rasterio, and numpy.
Raw datasource types must not leak past `dem_window_mapper` into the domain.
Reserved: `HttpRasterDatasource` for a future Raster Service (MS3) client.
