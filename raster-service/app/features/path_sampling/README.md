# path_sampling

`POST /raster/{dataset}/sample` — nearest-cell band values along a
polyline, sampled at regular arc-length positions `0, step, 2*step, …`
plus the final vertex (haversine, R = 3396.19 km; plan F5/A5, spec
§3.5/§4.5). Default `sample_distance_m` is the dataset `resolution_m`.

## Contents

- `domain/path_profile.py` — `PathProfile`: band + `PathSample` tuple +
  parallel value tuple; NaN is the in-domain nodata/out-of-extent
  marker.
- `application/sample_path.py` — `SamplePath`: `metadata` →
  `PathSampler.sample` (caps `max_path_points`/`max_samples`) →
  `GridGeometry.cell_at` → `read_cells` 1×1 per in-extent sample.
  Raises `UnknownBandError` (404, lists valid names) and
  `NoCoverageError` (404 only when *every* sample is outside the
  extent); out-of-extent or nodata samples keep `value: NaN` → `null`.
- `presentation/sample_schemas.py` — `SampleRequest` (`band`, `path`,
  `sample_distance_m?`), `SampleEntryResponse`, `SampleResponse`
  (`sample_count`, `total_distance_m`, `samples`). Range/limit rules
  stay in the domain so they surface as 400, not 422.
- `presentation/sample_mapper.py` — `SampleMapper`: NaN → `None` (JSON
  cannot carry NaN, D5); floats serialised verbatim, never rounded (D4).
- `presentation/sample_router.py` — body → `GeoPoint` list → use case;
  `max_path_points`/`max_samples`/`planet_radius_km` come from
  `Settings`.

## Layer rules

`domain/` and `application/` import only `core/*` — never fastapi,
pydantic or rasterio. `presentation/` owns the DTO serialisation.
