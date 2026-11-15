# rendering

`ImageEncoder` port implementations for the `/layer/{band}` endpoint.

## Contents

- `png_encoder.py` — `PngEncoder`: encodes an H×W×4 uint8 RGBA array as
  PNG using only stdlib `zlib` + `struct` (no Pillow). Filter byte 0 per
  row; rejects non-RGBA shapes and non-uint8 dtypes with `ValueError`.

## Key classes

`PngEncoder`.

## Layer rules

May import: `core/ports`, numpy, stdlib. Must NOT import fastapi,
rasterio, or domain raster math.
