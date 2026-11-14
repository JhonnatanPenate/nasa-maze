# features/area_analysis

Area analysis feature: aggregate elevation/slope statistics over a bounding
box (`POST /terrain/area`, plan F4).

## Contents

- `domain/value_stats.py` — `ValueStats`: min/max/mean aggregate over the
  valid cells of one quantity (finite values, `min <= max` enforced).
- `domain/area_stats.py` — `AreaStats`: feature result entity holding
  `elevation_m: ValueStats`, `slope_deg: ValueStats`, and
  `steep_fraction: float` (validated to `[0, 1]`).
- `application/analyze_area.py` — `AnalyzeArea` use case: fetches the DEM
  window via `TerrainRepository.window_for_with_halo(bbox, 1)` — the
  1-cell halo of real DEM cells lets `SlopeCalculator` compute border-cell
  slopes from true neighbours (identical to an interior computation)
  instead of mirror extrapolation. All statistics are then computed on
  the **core** slices only, so the halo never enters the results.
- `presentation/area_schemas.py` — `AreaRequest` (`body` accepted but
  ignored for the MVP; `bbox` must hold exactly 4 floats — other lengths
  are 422), `ValueStatsResponse`, `AreaResponse`.
- `presentation/area_mapper.py` — `AreaMapper`: bbox list → `BoundingBox`
  (order min_lon, min_lat, max_lon, max_lat) and `AreaStats` →
  `AreaResponse`.
- `presentation/area_router.py` — `APIRouter(prefix="/terrain")` exposing
  `POST /area`; the use case is injected via
  `Depends(get_analyze_area)` from `app/composition/area_dependencies.py`
  (Depends-chained so `get_raster_datasource` overrides work in tests).

## Behaviour notes

- `steep_fraction` counts cells with slope `>= steep_min_deg`, where
  `steep_min_deg` is the lower bound of the `steep` terrain class
  (`TerrainClassifier.steep_min_deg`, i.e. `Settings.slope_moderate_max_deg`,
  15 deg by default). It therefore covers `steep` **and** `hazardous`
  cells.
- **Differing denominators:** `elevation_m` stats are computed over all
  cells with valid elevation in the bbox window, while `slope_deg` stats
  and `steep_fraction` are computed over only the cells whose slope is
  computable (non-NaN) — a valid cell surrounded entirely by nodata has
  elevation but no slope.
- `window_for` on an all-nodata bbox returns an all-NaN window without
  raising; the use case checks `core().is_all_nodata()` and raises
  `NoCoverageError` (404) itself.
- A window whose valid elevation cells have no computable slope (e.g. an
  isolated valid cell surrounded by nodata, halo included) also yields
  `NoCoverageError`.
- Nodata cells are excluded from every statistic (nanmin/nanmax/nanmean
  over elevation; valid-slope cells only for slope stats).

## Layer rules

`presentation → application → domain`. The use case depends on the
`TerrainRepository` port only; window-size enforcement
(`max_window_cells`) and non-intersecting-bbox detection live in the
datasource. Inverted/degenerate/out-of-range bbox → `DomainValidationError`
(400, raised by `BoundingBox`); nodata-only → 404; datasource failure →
502.
