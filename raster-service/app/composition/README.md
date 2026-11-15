# composition

Dependency-injection root: FastAPI `Depends` providers built from
`Settings`. No routers live here.

## Contents

- `dependencies.py` — `get_settings` (lru_cache), `build_datasource`
  (per `DatasetConfig.kind`: `geotiff` → `GeoTiffRasterDatasource`,
  `memory` → `InMemoryRasterDatasource.synthetic()`),
  `build_repository`/`get_repository` (lru_cache; build failures become
  `UnavailableRasterDatasource` so health degrades to 503),
  `get_image_encoder` (`PngEncoder`).

## Key functions

`get_settings`, `get_repository`, `get_image_encoder` — wired with
`Depends(...)` in presentation routers.

## Layer rules

May import everything (it is the wiring point). Nothing else may import
composition except `app/main.py` and routers.
