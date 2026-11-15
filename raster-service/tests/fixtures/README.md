# fixtures

Raster fixtures generated at test time — binary files are never
committed.

## Contents

- `make_test_raster.py` — `test_bands()` builds the canonical (3, 10, 8)
  float32 grid (band b cell (r,c) = b·100 + r·10 + c, one numeric-nodata
  cell, one NaN cell); `write_test_raster` writes it as a geographic
  EPSG:4326 GeoTIFF with band descriptions and nodata `-9999`;
  `write_test_raster_projected` / `write_test_raster_rotated` /
  `write_test_raster_nan_nodata` produce the non-geographic, rotated and
  NaN-sentinel (like the delivered rejilla) variants. Constants
  `TEST_EXTENT`, `TEST_BAND_NAMES`, `TEST_NODATA`, cell indices.
