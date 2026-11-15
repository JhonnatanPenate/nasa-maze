# app/core/ports

Abstract ports (dependency-inversion boundary) for the Raster Service.

## Contents

- `RasterRepository` — domain-facing port used by use cases:
  `dataset_names`, `metadata`, `read_cells` (float64, nodata -> NaN),
  `is_readable`.
- `RasterDatasource` — raw data-access port, one instance per dataset
  file: `read_metadata`, `read_cells` (in-grid slices only), `ping`.
- `ImageEncoder` — `encode(rgba: np.ndarray) -> bytes` (PNG impl in
  infrastructure).
- `RawRasterMetadata` — dataclass: extent, rows/cols, band descriptions,
  nodata, `is_geographic`, `is_north_up`; what a datasource reports before
  the repository merges config into `DatasetMetadata`.

## Layer rules

Ports may import `app.core.domain` but never an infrastructure
implementation. Signatures are frozen by the implementation plan (§3.2).
