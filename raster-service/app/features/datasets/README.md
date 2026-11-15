# datasets

`GET /raster/datasets` — registered datasets with configured path and
readability. `GET /raster/{dataset}/metadata` — CRS, bounds, size,
`resolution_deg`, `resolution_m` and per-band `{index, name, unit,
nodata}` (plan F2, spec §4.1–§4.2).

## Contents

- `application/list_datasets.py` — `ListDatasets`: `(name, readable)`
  pairs without touching metadata, so a broken dataset still lists.
- `application/get_metadata.py` — `GetMetadata`: `DatasetMetadata` for
  one dataset; repository raises `UnknownDatasetError` (404) /
  `DatasetUnavailableError` (503).
- `presentation/datasets_schemas.py` — `DatasetsResponse`,
  `DatasetItemResponse`, `MetadataResponse`, `BandResponse`,
  `ResolutionDegResponse`.
- `presentation/datasets_mapper.py` — `DatasetsMapper`: domain → DTO;
  `bounds` serialised as `[min_lon, min_lat, max_lon, max_lat]`.
- `presentation/datasets_router.py` — merges the configured path from
  `Settings` into the list response (the repository port has no paths).

## Layer rules

Use cases depend on `RasterRepository` only; the router may read
`Settings` via `Depends(get_settings)` — presentation concern.
