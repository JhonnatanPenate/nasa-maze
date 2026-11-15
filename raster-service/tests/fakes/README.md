# fakes

Hand-written test doubles implementing core ports.

## Contents

- `failing_raster_datasource.py` — `FailingRasterDatasource`: every call
  raises `OSError`, `ping()` False; used for the repository 503 mapping
  and API failure-path tests.
