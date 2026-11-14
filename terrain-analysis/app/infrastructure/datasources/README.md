# infrastructure/datasources

Concrete `RasterDatasource` implementations behind the data-access port.

## Contents

- `grid_geometry.py` — `GridGeometry`: shared pixel/geo index math for a
  north-up regular lon/lat grid (row 0 = max_lat, col 0 = min_lon). Point →
  cell lookup (max-edge points clamp into the boundary cell; outside →
  `None`), bbox → clipped cell bounds, `max_window_cells` enforcement,
  window-around padding slices. Used by every datasource so the index math
  is not duplicated.
- `grid_backed_raster_datasource.py` — `GridBackedRasterDatasource`:
  template-method base holding the shared `read_window` /
  `read_window_with_halo` / `read_window_around` flow (window caps —
  including the `(2r+1)²` radius cap — clipping, NaN padding).
  `read_window_with_halo` expands the clipped bbox window by up to
  `halo_cells` real rows/columns per side and returns a `HaloWindow` whose
  core slices mark the plain-read region; `max_window_cells` caps the
  core count only. Subclasses implement only `_geometry()`
  and `_read(row_slice, col_slice)`.
- `dem_window_mapper.py` — `DemWindowMapper`: the adapter converting raw
  raster payloads into `DemWindow`. This is the only place degree cell
  sizes are converted to metres (`res * pi/180 * planet_radius_m`, with
  `cos(lat)` for longitude and a small floor near the poles). Nodata
  sentinels are compared in the array's native dtype, then sentinels and
  non-finite values become NaN.
- `synthetic_dem_datasource.py` — `SyntheticDemDatasource`: deterministic
  in-memory numpy DEM. `default()` builds the MVP Mars patch: lon 77–78,
  lat 18–19, 1200×1200 cells, elevation −2500 m + layered sinusoidal hills
  and a planar tilt (flat/moderate/steep mix). It contains a nodata hole
  at **lon 77.90–77.95, lat 18.90–18.95** so nodata/404 paths are testable;
  the smoke coordinates (18.4, 77.5) and (18.5, 77.6) hold real data.
- `unavailable_raster_datasource.py` — `UnavailableRasterDatasource`:
  fallback created by the composition root when `build_datasource` fails
  (bad `datasource_kind`, missing `dem_path`). `ping()` returns `False`
  (`/health` → `degraded`); reads raise `UpstreamDatasourceError` → 502.
- `geotiff_datasource.py` — `GeoTiffRasterDatasource`: rasterio-backed
  reader over a north-up geographic (lon/lat degrees) single-band GeoTIFF
  (`Settings.dem_path`). Each open validates: ≥1 band, geographic CRS (if a
  CRS is present), non-rotated transform, north-up (`e < 0`); violations
  raise `UpstreamDatasourceError`. `ping()` returns `False` instead of
  raising.

## Behaviour notes

- `window_for` over an all-nodata region returns an all-NaN `DemWindow`,
  it does **not** raise; callers must check `DemWindow.is_all_nodata()`.
- `GeoTiffRasterDatasource` opens the file per call (`_geometry` + `_read`
  ≈ two `rasterio.open` calls, ~2 ms each) — acceptable for the MVP; a
  cached/reader-pool variant is a future optimisation.
- `cell_size_x_m` uses a single `cos(mean_lat)` for the whole window, so
  cell sizes are slightly approximate for tall windows spanning many
  degrees of latitude — acceptable at MVP extents.
- Polar handling is out of MVP scope: `cos(lat)` is floored at `1e-6`
  merely to keep cell sizes finite.

## Layer rules

May import `core/ports`, `core/domain`, `core/config`, rasterio, and numpy.
Must NOT import FastAPI. Raw datasource types must not leak past
`dem_window_mapper` into the domain. Reserved: `HttpRasterDatasource` for a
future Raster Service (MS3) client.
