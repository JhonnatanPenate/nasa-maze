# infrastructure

Concrete implementations of the core ports: raster datasources, the
dataset registry repository, and the PNG image encoder.

## Contents

- `datasources/` — `GeoTiffRasterDatasource` (rasterio, opens per call),
  `InMemoryRasterDatasource` (numpy, dev/tests), `UnavailableRasterDatasource`
  (build-failure placeholder).
- `repositories/` — `RegistryRasterRepository` (the `RasterRepository`
  implementation: name → datasource map, `RawRasterMetadata` →
  `DatasetMetadata` adapter, nodata → NaN, metadata cache) and
  `guarded_call` (datasource exceptions → `DatasetUnavailableError`).
- `rendering/` — `PngEncoder` (stdlib zlib + struct, `ImageEncoder` port).

## Key classes

`RegistryRasterRepository` is the only class use cases see; it receives
`RasterDatasource` instances by constructor so datasources are swappable
(`geotiff`, `memory`, or new formats) without touching application code.

## Layer rules

May import: `core/ports`, `core/domain`, `core/errors`, `core/config`,
rasterio, numpy, stdlib. Must NOT import fastapi, pydantic DTOs, or
`features/`. Raw rasterio types never leave this layer.
