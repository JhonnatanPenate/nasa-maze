# app

MS3 Raster Service application package — the single HTTP access point to
the Mars raster files (`data/gale/`). FastAPI surface over a Clean
Architecture core: presentation → application → domain, with
infrastructure behind ports and `composition` wiring everything.

## Contents

- `main.py` — `create_app()`: registers the exception handlers and the
  feature routers; `app = create_app()` is the uvicorn entrypoint.
- `core/` — `config` (`Settings`, `DatasetConfig`), `domain` (value
  objects + grid math), `ports` (ABCs), `errors` (exception taxonomy +
  FastAPI handlers; the only fastapi import under `core/`).
- `features/` — one folder per endpoint feature: `health`, `datasets`,
  `point_query`, `window_read`, `path_sampling`, `layer_render`.
- `infrastructure/` — `RasterDatasource` implementations (rasterio /
  in-memory / unavailable), `RegistryRasterRepository`, `PngEncoder`.
- `composition/` — `dependencies.py`: `get_settings`, `get_repository`,
  `get_image_encoder` providers for `Depends`.

## Layer rules

Dependencies point inward only: routers depend on use cases, use cases
on `RasterRepository`; `domain`/`ports`/`application` never import
fastapi, pydantic, rasterio or httpx. See each package's README.
