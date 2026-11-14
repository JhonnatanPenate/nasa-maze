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
