# composition

Composition root: dependency-injection wiring for FastAPI `Depends`.

## Contents (planned)

- `dependencies.py` — providers that build the `Settings`, select the
  `RasterDatasource` implementation from `Settings.datasource_kind`
  (`synthetic` | `geotiff`; `http` reserved), construct the
  `DemTerrainRepository`, and expose them to routers.

## Layer rules

This is the only layer allowed to import everything (presentation,
application, domain, infrastructure). All outward knowledge converges here so
inner layers stay free of concrete dependencies.
