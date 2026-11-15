# layer_render

`GET /raster/{dataset}/layer/{band}[?colormap=]` — renders one whole
band as an RGBA 8-bit PNG over the full dataset extent, one pixel per
cell, row 0 = north (plan F6, spec §3.6/§4.6).

## Contents

- `domain/rendered_layer.py` — `RenderedLayer`: PNG bytes + `BoundingBox`
  extent + CRS label + the `(min, max)` value range used for the colour
  stretch (`min == max` allowed for constant bands).
- `application/render_layer.py` — `RenderLayer`: `metadata` → `band` →
  whole-band `read_cells` → `ColorRamp.render` → `ImageEncoder.encode`.
  Depends only on the `RasterRepository` and `ImageEncoder` ports.
  The `colormap` argument overrides `BandInfo.colormap` (empty →
  `viridis`); unknown names raise `RasterValidationError` (400).
  The value range is `BandInfo.value_range` when configured, else the
  band's finite min/max; a band with no finite cells renders fully
  transparent and reports the defined fallback range `(0.0, 1.0)`.
- `presentation/layer_router.py` — returns `Response` with media type
  `image/png` and headers `X-Raster-Bounds`
  (`min_lon,min_lat,max_lon,max_lat`), `X-Raster-CRS` and
  `X-Raster-Value-Range` (`min,max`).

## Layer rules

`domain/` and `application/` import only `core/*` — never fastapi,
pydantic or rasterio. `presentation/` owns the HTTP response and
header formatting. Errors: unknown dataset/band → 404, unknown
colormap → 400, unreadable dataset → 503.
