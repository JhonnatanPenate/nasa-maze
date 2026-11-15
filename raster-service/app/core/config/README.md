# config

Env-driven configuration (prefix `MS3_`). Only place where dataset paths are defined.

- `Settings` — radius, CRS label, caps and the dataset registry. `MS3_DATASETS` (JSON) replaces the
  registry; `MS3_REJILLA_PATH` only changes the default `rejilla` path. `MS3_DATASETS='{}'` = no datasets.
- `DatasetConfig` — per-dataset `path`, `kind` (`geotiff` | `memory`), fallback `band_names`,
  `band_units`, `colormaps` (+ `default_colormap`), PNG `value_ranges`.

Layer rule: pydantic allowed here; domain/ports must not import this package's pydantic models.
