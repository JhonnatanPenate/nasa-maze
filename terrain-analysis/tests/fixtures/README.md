# tests/fixtures

Helpers that generate test data at test time.

## Contents

- `make_test_dem.py` — `write_test_dem(path, elevation, extent, nodata)`:
  writes a single-band float32 north-up EPSG:4326 GeoTIFF via rasterio so
  `GeoTiffRasterDatasource` can be exercised against a real file. Used by
  the session-scoped `geotiff_datasource` fixture in `tests/conftest.py`.

## Rules

Generated `.tif` files must never be committed; they are written into
`tmp_path`/`tmp_path_factory` directories only.
