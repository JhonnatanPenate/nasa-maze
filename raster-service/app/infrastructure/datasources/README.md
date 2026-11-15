# datasources

`RasterDatasource` port implementations — one instance per dataset file.
Datasources do I/O only on already-clipped slices; coordinate→cell math
lives in `core/domain/GridGeometry`. Slices are normalised via
`slice.indices(n)`; stepped slices are rejected (`ValueError`).

## Contents

- `geotiff_raster_datasource.py` — `GeoTiffRasterDatasource`: opens the
  file lazily per call (no handles held), reports extent/shape/band
  descriptions/nodata plus geographic and north-up flags, serves
  `float32` cell values verbatim.
- `in_memory_raster_datasource.py` — `InMemoryRasterDatasource`: wraps a
  3-D numpy array (bands × rows × cols); `synthetic()` is a deterministic
  stand-in for the rejilla grid used when `DatasetConfig.kind == "memory"`.
- `unavailable_raster_datasource.py` — `UnavailableRasterDatasource`:
  build-failure placeholder; `ping()` False, reads raise
  `DatasetUnavailableError`.

## Key classes

`GeoTiffRasterDatasource` (production), `InMemoryRasterDatasource`
(dev/tests/swap proof), `UnavailableRasterDatasource` (503 fallback).

## Layer rules

May import: `core/ports`, `core/domain`, `core/errors`, rasterio, numpy.
Must NOT import fastapi or repositories. Errors propagate raw; the
repository wraps them via `guarded_call`.
