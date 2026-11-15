import math

import numpy as np

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.cell_window import CellWindow
from app.core.domain.dataset_metadata import DatasetMetadata
from app.core.domain.geo_point import GeoPoint
from app.features.window_read.domain.window_request import WindowRequest
from app.features.window_read.presentation.window_schemas import (
    WindowCoreSchema,
    WindowRequestSchema,
    WindowResolutionDegSchema,
    WindowResponse,
)


class WindowMapper:
    """Domain <-> DTO adapter for window reads.

    NaN becomes null on the wire (D5) and values are serialised as
    float64 without rounding (D4), so MS4 receives exactly the inputs of
    `DemWindowMapper.to_dem_window`.
    """

    @staticmethod
    def to_domain(body: WindowRequestSchema) -> WindowRequest:
        bbox = None
        if body.bbox is not None:
            bbox = BoundingBox(
                min_lon=body.bbox[0],
                min_lat=body.bbox[1],
                max_lon=body.bbox[2],
                max_lat=body.bbox[3],
            )
        point = None
        if body.point is not None:
            point = GeoPoint(lat=body.point.lat, lon=body.point.lon)
        return WindowRequest(
            band=body.band,
            bbox=bbox,
            point=point,
            halo_cells=body.halo_cells,
            radius_cells=body.radius_cells,
        )

    @staticmethod
    def to_response(
        band: str,
        metadata: DatasetMetadata,
        window: CellWindow,
        cells: np.ndarray,
        center_lat: float,
    ) -> WindowResponse:
        min_lon, min_lat, max_lon, max_lat = window.outer_bounds(
            metadata.grid_geometry()
        )
        return WindowResponse(
            band=band,
            bounds=[min_lon, min_lat, max_lon, max_lat],
            rows=window.rows,
            cols=window.cols,
            resolution_deg=WindowResolutionDegSchema(
                lon=metadata.res_lon_deg, lat=metadata.res_lat_deg
            ),
            center_lat=center_lat,
            core=WindowCoreSchema(
                row_off=window.row_off,
                col_off=window.col_off,
                rows=window.core_rows,
                cols=window.core_cols,
            ),
            cells=[
                [
                    None if not math.isfinite(value) else float(value)
                    for value in row
                ]
                for row in cells
            ],
        )
