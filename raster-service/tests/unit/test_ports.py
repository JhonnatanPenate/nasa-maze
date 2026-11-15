from dataclasses import FrozenInstanceError

import pytest

from app.core.domain.bounding_box import BoundingBox
from app.core.ports.image_encoder import ImageEncoder
from app.core.ports.raster_datasource import RasterDatasource
from app.core.ports.raster_repository import RasterRepository
from app.core.ports.raw_raster_metadata import RawRasterMetadata


class TestAbstractPorts:
    @pytest.mark.parametrize(
        "port", [RasterDatasource, RasterRepository, ImageEncoder]
    )
    def test_cannot_instantiate_abc(self, port):
        with pytest.raises(TypeError):
            port()


class TestRawRasterMetadata:
    def _make(self, **overrides) -> RawRasterMetadata:
        kwargs = {
            "extent": BoundingBox(
                min_lon=137.345, min_lat=-4.74,
                max_lon=137.455, max_lat=-4.58,
            ),
            "rows": 105,
            "cols": 72,
            "band_descriptions": ("pendiente_grados", None),
            "nodata": None,
            "is_geographic": True,
            "is_north_up": True,
        }
        kwargs.update(overrides)
        return RawRasterMetadata(**kwargs)

    def test_stores_fields(self):
        meta = self._make()

        assert meta.rows == 105
        assert meta.cols == 72
        assert meta.band_descriptions == ("pendiente_grados", None)
        assert meta.is_geographic is True
        assert meta.is_north_up is True

    def test_numeric_nodata_is_kept(self):
        meta = self._make(nodata=-9999.0)

        assert meta.nodata == -9999.0

    def test_is_immutable(self):
        meta = self._make()

        with pytest.raises(FrozenInstanceError):
            meta.rows = 1
