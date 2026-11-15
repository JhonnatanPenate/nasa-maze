import math
from collections.abc import Mapping
from dataclasses import replace

import numpy as np

from app.core.config.dataset_config import DatasetConfig
from app.core.domain.band_info import BandInfo
from app.core.domain.dataset_metadata import DatasetMetadata
from app.core.errors.exceptions import (
    DatasetUnavailableError,
    UnknownDatasetError,
)
from app.core.ports.raster_datasource import RasterDatasource
from app.core.ports.raster_repository import RasterRepository
from app.core.ports.raw_raster_metadata import RawRasterMetadata
from app.infrastructure.repositories.guarded_call import guarded_call


class RegistryRasterRepository(RasterRepository):
    """RasterRepository over a name -> RasterDatasource registry.

    Adapts RawRasterMetadata into the domain DatasetMetadata, merging
    registry config (units, CRS label, colormaps, value_ranges), converts
    the numeric nodata sentinel to NaN on cell reads, and caches metadata
    per dataset after the first successful read (D8) — cells are read
    per request.
    """

    def __init__(
        self,
        datasources: Mapping[str, RasterDatasource],
        configs: Mapping[str, DatasetConfig],
        crs_label: str,
        planet_radius_km: float,
    ) -> None:
        self._datasources = dict(datasources)
        self._configs = dict(configs)
        self._crs_label = crs_label
        self._planet_radius_m = planet_radius_km * 1000.0
        self._metadata_cache: dict[str, DatasetMetadata] = {}

    def dataset_names(self) -> list[str]:
        return list(self._datasources)

    def metadata(self, dataset: str) -> DatasetMetadata:
        cached = self._metadata_cache.get(dataset)
        if cached is not None:
            return cached
        datasource = self._datasource(dataset)
        raw = guarded_call(dataset, datasource.read_metadata)
        metadata = self._adapt(dataset, raw, self._config_for(dataset))
        self._metadata_cache[dataset] = metadata
        return metadata

    def read_cells(
        self, dataset: str, band: str, rows: slice, cols: slice
    ) -> np.ndarray:
        info = self.metadata(dataset).band(band)
        datasource = self._datasources[dataset]
        raw = guarded_call(
            dataset, lambda: datasource.read_cells(info.index, rows, cols)
        )
        cells = np.asarray(raw, dtype=np.float64)
        if info.nodata is not None:
            cells = np.where(cells == info.nodata, np.nan, cells)
        return cells

    def is_readable(self, dataset: str) -> bool:
        datasource = self._datasources.get(dataset)
        if datasource is None:
            return False
        try:
            return bool(datasource.ping())
        except Exception:
            return False

    def _datasource(self, dataset: str) -> RasterDatasource:
        datasource = self._datasources.get(dataset)
        if datasource is None:
            raise UnknownDatasetError(
                f"Unknown dataset {dataset!r}. Valid datasets: "
                f"{', '.join(self._datasources)}"
            )
        return datasource

    def _config_for(self, dataset: str) -> DatasetConfig:
        return self._configs.get(dataset) or DatasetConfig(
            path="", band_units={}, colormaps={}, value_ranges={}
        )

    def _adapt(
        self,
        dataset: str,
        raw: RawRasterMetadata,
        config: DatasetConfig,
    ) -> DatasetMetadata:
        if not raw.is_geographic:
            raise DatasetUnavailableError(
                f"Dataset {dataset!r} is not in a geographic CRS "
                f"(lon/lat degrees required)"
            )
        if not raw.is_north_up:
            raise DatasetUnavailableError(
                f"Dataset {dataset!r} is rotated or not north-up"
            )
        bands = tuple(
            self._band(index, raw, config)
            for index in range(len(raw.band_descriptions))
        )
        metadata = DatasetMetadata(
            name=dataset,
            crs=self._crs_label,
            bounds=raw.extent,
            width=raw.cols,
            height=raw.rows,
            resolution_m=1.0,
            bands=bands,
        )
        # resolution_m derives only from DatasetMetadata.res_lat_deg so the
        # degree-resolution formula lives in exactly one place.
        return replace(
            metadata,
            resolution_m=metadata.res_lat_deg
            * math.pi
            / 180.0
            * self._planet_radius_m,
        )

    def _band(
        self, index: int, raw: RawRasterMetadata, config: DatasetConfig
    ) -> BandInfo:
        name = self._band_name(index, raw, config)
        return BandInfo(
            index=index + 1,
            name=name,
            unit=config.band_units.get(name, ""),
            nodata=raw.nodata,
            colormap=config.colormaps.get(name, config.default_colormap),
            value_range=config.value_ranges.get(name),
        )

    @staticmethod
    def _band_name(
        index: int, raw: RawRasterMetadata, config: DatasetConfig
    ) -> str:
        description = raw.band_descriptions[index]
        if description:
            return description
        if index < len(config.band_names):
            return config.band_names[index]
        return f"band_{index + 1}"
