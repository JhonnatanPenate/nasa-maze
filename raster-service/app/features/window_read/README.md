# window_read

`POST /raster/{dataset}/window` — cell window read with MS4 parity
(plan F4, spec §3.4/§4.4). Three forms: `bbox`, `bbox` + `halo_cells`
(MS4 `read_window` / `read_window_with_halo`), and `point` +
`radius_cells` (MS4 `read_window_around`).

## Contents

- `domain/window_request.py` — `WindowRequest`: validated request;
  exactly one of `bbox`/`point`, `radius_cells` required with `point`,
  counts are ints >= 0, `halo_cells` normalised to 0 on point reads.
- `application/read_window.py` — `ReadWindow(repository,
  max_window_cells)`: reproduces MS4 `GridBackedRasterDatasource`
  semantics — centre-inclusion selection with single-cell fallback,
  cap checked on core cells / `(2r+1)^2` before any read, point reads
  pad out-of-extent cells with NaN and never raise `NoCoverageError`.
  Returns `(metadata, CellWindow, cells, center_lat)`; `center_lat`
  mirrors `rows_mean_lat` (bbox) / `row_center_lat` (point; request lat
  outside the extent).
- `presentation/window_schemas.py` — `WindowRequestSchema` body DTO
  (malformed JSON -> 422) and `WindowResponse` (`band`, `bounds`,
  `rows`, `cols`, `resolution_deg`, `center_lat`, `core`, `cells`).
- `presentation/window_mapper.py` — `WindowMapper`: schema -> domain and
  domain -> `WindowResponse`; NaN -> `None` (D5), floats verbatim (D4).
- `presentation/window_router.py` — body -> `WindowRequest` -> use
  case; `settings.max_window_cells` caps the window.

## Layer rules

`domain/` and `application/` import only `core/*` — never fastapi,
pydantic or rasterio. `presentation/` owns the DTO serialisation.
Error mapping (error taxonomy §3.3): invalid form/coordinates/counts
and cap -> 400; bbox outside extent -> 404; unknown dataset/band ->
404; unreadable dataset -> 503.
