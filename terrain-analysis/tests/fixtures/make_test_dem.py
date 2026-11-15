import numpy as np
import rasterio
from rasterio.transform import from_bounds

from app.core.domain.bounding_box import BoundingBox


def write_test_dem(
    path,
    elevation: np.ndarray,
    extent: BoundingBox,
    nodata: float = -32768.0,
) -> None:
    """Write a single-band float32 north-up EPSG:4326 GeoTIFF test DEM.

    Generated at test time only; the output file must never be committed.
    """
    elevation = np.asarray(elevation, dtype=np.float32)
    if elevation.ndim != 2:
        raise ValueError(f"elevation must be 2-D, got shape {elevation.shape}")
    rows, cols = elevation.shape
    transform = from_bounds(
        west=extent.min_lon,
        south=extent.min_lat,
        east=extent.max_lon,
        north=extent.max_lat,
        width=cols,
        height=rows,
    )
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=rows,
        width=cols,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(elevation, 1)


def write_test_grid(
    path,
    bands: list[np.ndarray],
    extent: BoundingBox,
    nodata: float | None = None,
) -> None:
    """Write a multi-band float32 north-up EPSG:4326 GeoTIFF test grid.

    Generated at test time only; the output file must never be committed.
    """
    arrays = [np.asarray(band, dtype=np.float32) for band in bands]
    if not arrays:
        raise ValueError("bands must be a non-empty list")
    for band in arrays:
        if band.ndim != 2 or band.shape != arrays[0].shape:
            raise ValueError(
                f"all bands must be 2-D with identical shape, "
                f"got {band.shape} vs {arrays[0].shape}"
            )
    rows, cols = arrays[0].shape
    transform = from_bounds(
        west=extent.min_lon,
        south=extent.min_lat,
        east=extent.max_lon,
        north=extent.max_lat,
        width=cols,
        height=rows,
    )
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=rows,
        width=cols,
        count=len(arrays),
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=nodata,
    ) as dst:
        for index, band in enumerate(arrays, start=1):
            dst.write(band, index)
