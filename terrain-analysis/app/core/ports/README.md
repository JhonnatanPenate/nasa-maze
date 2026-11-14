# core/ports

Abstract interfaces that keep inner layers independent of infrastructure.

## Contents

- `raster_datasource.py` — `RasterDatasource` ABC (data-access contract):
  - `read_window(bbox, halo_cells=0)` → `DemWindow` covering bbox clipped
    to the DEM extent, optionally expanded by `halo_cells` real rows/cols
    on every side; raises `NoCoverageError` when bbox does not intersect.
  - `read_window_with_halo(bbox, halo_cells)` → `HaloWindow`: the expanded
    window plus `core_rows`/`core_cols` slices selecting the requested
    bbox window inside it. `max_window_cells` caps the **core** cell
    count only.
  - `read_window_around(point, radius_cells)` → `DemWindow` of shape
    (2r+1, 2r+1) centred on the cell containing point; out-of-extent
    cells are NaN.
  - `ping()` → datasource reachability.
  Implementations may raise any exception on I/O failure; the repository
  wraps them into `UpstreamDatasourceError`. Implemented by
  `SyntheticDemDatasource`, `GeoTiffRasterDatasource`,
  `UnavailableRasterDatasource` (build-failure fallback), and a reserved
  `HttpRasterDatasource`. The port intentionally has no `read_metadata()`:
  each datasource's mapper converts its native resolution (degrees →
  metres using the configured planet radius) into
  `DemWindow.cell_size_x_m` / `cell_size_y_m`.
- `terrain_repository.py` — `TerrainRepository` ABC (domain-facing
  contract used by use cases):
  - `elevation_at(point)` → metres; `NoCoverageError` on nodata/outside.
  - `window_around(point, radius_cells=1)` → `DemWindow`.
  - `window_for(bbox, halo_cells=0)` → `DemWindow`.
  - `window_for_with_halo(bbox, halo_cells)` → `HaloWindow` (window plus
    core slices).
  - `is_available()` → datasource health.

## Layer rules

Ports may import `core/domain` types but no concrete implementation, no
FastAPI, and no rasterio. Use cases depend on `TerrainRepository`, never on a
datasource directly — this is what makes the datasource swappable.
