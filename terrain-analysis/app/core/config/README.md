# core/config

Service configuration.

## Contents

- `settings.py` — `Settings(BaseSettings)`, env prefix `MS4_`: body label,
  planet radius, datasource selection (`synthetic` | `geotiff` | `http`),
  DEM path, slope class thresholds, sampling and window limits.

## Layer rules

Config is consumed inward by `application`/`domain` defaults and outward by
`composition` for wiring. It must not import feature or infrastructure code.
