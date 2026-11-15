# app/core

Core of the Raster Service: everything that knows nothing about HTTP or
files-on-disk drivers.

## Contents

- `config/` — `Settings` (env prefix `MS3_`) and `DatasetConfig` registry entries.
- `domain/` — value objects and pure math: `GeoPoint`, `BoundingBox`,
  `GridGeometry`, `CellWindow`, `BandInfo`, `DatasetMetadata`,
  `DistanceCalculator`, `PathSampler`, `PathSample`, `ColorRamp`.
- `ports/` — ABCs consumed by use cases: `RasterRepository`,
  `RasterDatasource`, `ImageEncoder`, plus the `RawRasterMetadata` dataclass.
- `errors/` — exception taxonomy (`RasterServiceError` family) plus the
  FastAPI handlers that map it to HTTP statuses.

## Layer rules

- `domain` may import stdlib + numpy only — never a web framework,
  DTO schema, raster driver or HTTP client.
- `ports` may import `domain` but no infrastructure implementation.
- `errors/exceptions.py` is stdlib-only; `errors/error_handlers.py` is
  the only fastapi import allowed in `core/`.
