# tests/unit

Unit tests for domain classes, ports and (in later work packages) use
cases, repository, datasources and the PNG encoder. No HTTP, no real
raster files: datasource behaviour is exercised through in-memory or
generated fixtures from `tests/fixtures/` and `tests/fakes/`.

## Current coverage

- `test_geo_point.py`, `test_bounding_box.py` — coordinate validation.
- `test_grid_geometry.py` — MS4-parity cases: centre inclusion (eps),
  sub-cell fallback, `cell_at` max-edge clamp, padded slices, caps.
- `test_cell_window.py` — halo clipping, core offsets, `outer_bounds`.
- `test_band_info.py`, `test_dataset_metadata.py` — band table and the
  `UnknownBandError` listing valid names.
- `test_distance_calculator.py`, `test_path_sampler.py`,
  `test_path_sample.py` — haversine + arc-length sampling (R 3396.19 km).
- `test_color_ramp.py` — named ramps, NaN -> alpha 0, constant range.
- `test_exceptions.py`, `test_ports.py` — taxonomy + port contracts.
