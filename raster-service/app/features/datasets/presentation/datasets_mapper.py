from collections.abc import Mapping

from app.core.domain.dataset_metadata import DatasetMetadata
from app.features.datasets.presentation.datasets_schemas import (
    BandResponse,
    DatasetItemResponse,
    DatasetsResponse,
    MetadataResponse,
    ResolutionDegResponse,
)


class DatasetsMapper:
    """Domain -> DTO adapter for the datasets endpoints."""

    @staticmethod
    def to_datasets_response(
        entries: list[tuple[str, bool]], paths: Mapping[str, str]
    ) -> DatasetsResponse:
        return DatasetsResponse(
            datasets=[
                DatasetItemResponse(
                    name=name,
                    path=paths.get(name, ""),
                    readable=readable,
                )
                for name, readable in entries
            ]
        )

    @staticmethod
    def to_metadata_response(metadata: DatasetMetadata) -> MetadataResponse:
        bounds = metadata.bounds
        return MetadataResponse(
            name=metadata.name,
            crs=metadata.crs,
            bounds=[
                bounds.min_lon,
                bounds.min_lat,
                bounds.max_lon,
                bounds.max_lat,
            ],
            width=metadata.width,
            height=metadata.height,
            resolution_deg=ResolutionDegResponse(
                lon=metadata.res_lon_deg, lat=metadata.res_lat_deg
            ),
            resolution_m=metadata.resolution_m,
            bands=[
                BandResponse(
                    index=band.index,
                    name=band.name,
                    unit=band.unit,
                    nodata=band.nodata,
                )
                for band in metadata.bands
            ],
        )
