from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine, from_bounds

from app.core.domain.bounding_box import BoundingBox

TEST_ROWS = 10
TEST_COLS = 8
TEST_EXTENT = BoundingBox(
    min_lon=137.40, min_lat=-4.70, max_lon=137.48, max_lat=-4.60
)
TEST_BAND_NAMES = ("slope_deg", "roughness_m", "dark_fraction")
TEST_NODATA = -9999.0
TEST_NODATA_BAND = 1
TEST_NODATA_CELL = (1, 1)
TEST_NAN_BAND = 3
TEST_NAN_CELL = (8, 6)


def test_bands() -> np.ndarray:
    """(3, TEST_ROWS, TEST_COLS) float32 grid with known plane values.

    Band b (1-based) holds b*100 + row*10 + col at cell (row, col).
    Band TEST_NODATA_BAND carries the numeric sentinel TEST_NODATA at
    TEST_NODATA_CELL; band TEST_NAN_BAND carries a real NaN at
    TEST_NAN_CELL.
    """
    row_idx, col_idx = np.meshgrid(
        np.arange(TEST_ROWS, dtype=np.float32),
        np.arange(TEST_COLS, dtype=np.float32),
        indexing="ij",
    )
    cells = np.stack(
        [
            index * 100.0 + row_idx * 10.0 + col_idx
            for index in range(len(TEST_BAND_NAMES))
        ]
    ).astype(np.float32)
    cells[TEST_NODATA_BAND - 1, *TEST_NODATA_CELL] = TEST_NODATA
    cells[TEST_NAN_BAND - 1, *TEST_NAN_CELL] = np.nan
    return cells


test_bands.__test__ = False  # helper, not a test function


def write_test_raster(path) -> Path:
    """Write the canonical 3-band 10x8 geographic float32 GeoTIFF.

    Band descriptions carry TEST_BAND_NAMES; file nodata is the numeric
    sentinel TEST_NODATA. Generated at test time only — never committed.
    """
    return _write(path, test_bands(), crs="EPSG:4326", transform=_transform())


def write_test_raster_projected(path) -> Path:
    """Same grid under a projected (non-geographic) CRS."""
    return _write(path, test_bands(), crs="EPSG:32632", transform=_transform())


def write_test_raster_rotated(path) -> Path:
    """Same grid with a sheared (rotated) affine transform."""
    transform = Affine(
        0.01, 0.002, TEST_EXTENT.min_lon,
        0.002, -0.01, TEST_EXTENT.max_lat,
    )
    return _write(path, test_bands(), crs="EPSG:4326", transform=transform)


def write_test_raster_nan_nodata(path) -> Path:
    """Same grid with the nodata sentinel declared as NaN, like the
    delivered rejilla file."""
    return _write(
        path,
        test_bands(),
        crs="EPSG:4326",
        transform=_transform(),
        nodata=float("nan"),
    )


def _transform() -> Affine:
    return from_bounds(
        west=TEST_EXTENT.min_lon,
        south=TEST_EXTENT.min_lat,
        east=TEST_EXTENT.max_lon,
        north=TEST_EXTENT.max_lat,
        width=TEST_COLS,
        height=TEST_ROWS,
    )


def _write(
    path,
    cells: np.ndarray,
    crs: str,
    transform: Affine,
    nodata: float | None = TEST_NODATA,
) -> Path:
    path = Path(path)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=cells.shape[1],
        width=cells.shape[2],
        count=cells.shape[0],
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=nodata,
    ) as dst:
        for index, name in enumerate(TEST_BAND_NAMES, start=1):
            dst.write(cells[index - 1], index)
            dst.set_band_description(index, name)
    return path
