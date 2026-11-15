# repositories

`RasterRepository` port implementation and its error-wrapping helper.

## Contents

- `registry_raster_repository.py` — `RegistryRasterRepository`: maps
  dataset names to `RasterDatasource` instances; adapts
  `RawRasterMetadata` into `DatasetMetadata`, merging registry config
  (units, CRS label, per-band `colormap`/`value_range`); band names from
  file descriptions → config `band_names` → `band_<i>`; converts the
  numeric nodata sentinel to NaN and cells to float64; caches metadata
  per dataset (D8).
- `guarded_call.py` — logs the original datasource failure and re-raises
  a generic `DatasetUnavailableError` (→ HTTP 503) so internal errors and
  paths never leak into responses.

## Key classes

`RegistryRasterRepository` (infrastructure impl of the
`RasterRepository` port), `guarded_call` (function).

## Layer rules

May import: `core/ports`, `core/domain`, `core/errors`, `core/config`,
numpy. Must NOT import fastapi, rasterio, or concrete datasource
classes — the registry is injected by the composition root.
