import pytest

from app.core.domain.band_info import BandInfo
from app.core.domain.bounding_box import BoundingBox
from app.core.domain.dataset_metadata import DatasetMetadata
from app.core.errors.exceptions import RasterValidationError, UnknownBandError

BANDS = (
    BandInfo(index=1, name="pendiente_grados", unit="deg", nodata=None),
    BandInfo(index=2, name="rugosidad_m", unit="m", nodata=None),
)


def make_metadata(**overrides) -> DatasetMetadata:
    kwargs = {
        "name": "rejilla",
        "crs": "IAU_2015:49900",
        "bounds": BoundingBox(
            min_lon=137.345, min_lat=-4.739427215909189,
            max_lon=137.45432151948057, max_lat=-4.58,
        ),
        "width": 72,
        "height": 105,
        "resolution_m": 90.0,
        "bands": BANDS,
    }
    kwargs.update(overrides)
    return DatasetMetadata(**kwargs)


class TestBandLookup:
    def test_band_by_name_returns_band(self):
        band = make_metadata().band("rugosidad_m")

        assert band.index == 2
        assert band.unit == "m"

    def test_unknown_band_raises_listing_valid_names(self):
        with pytest.raises(UnknownBandError) as excinfo:
            make_metadata().band("elevation_m")

        assert "pendiente_grados" in str(excinfo.value)
        assert "rugosidad_m" in str(excinfo.value)

    def test_band_names_property(self):
        assert make_metadata().band_names() == [
            "pendiente_grados",
            "rugosidad_m",
        ]


class TestGridGeometryBridge:
    def test_grid_geometry_uses_bounds_and_shape(self):
        grid = make_metadata().grid_geometry()

        assert grid.rows == 105
        assert grid.cols == 72
        assert grid.res_lat_deg == pytest.approx(0.0015183544372303697)

    def test_resolution_is_derived_from_extent_and_shape(self):
        meta = make_metadata()

        assert meta.res_lon_deg == pytest.approx(
            (meta.bounds.max_lon - meta.bounds.min_lon) / meta.width
        )
        assert meta.res_lat_deg == pytest.approx(
            (meta.bounds.max_lat - meta.bounds.min_lat) / meta.height
        )


class TestValidation:
    @pytest.mark.parametrize(("width", "height"), [(0, 105), (72, -1), (1.5, 5)])
    def test_invalid_shape_raises(self, width, height):
        with pytest.raises(RasterValidationError):
            make_metadata(width=width, height=height)

    def test_empty_bands_raises(self):
        with pytest.raises(RasterValidationError):
            make_metadata(bands=())

    def test_duplicate_band_names_raise(self):
        bands = (
            BandInfo(index=1, name="dup", unit="m", nodata=None),
            BandInfo(index=2, name="dup", unit="m", nodata=None),
        )
        with pytest.raises(RasterValidationError, match="dup"):
            make_metadata(bands=bands)

    @pytest.mark.parametrize("bad_res", [0.0, -1.0, float("nan")])
    def test_invalid_resolution_raises(self, bad_res):
        with pytest.raises(RasterValidationError):
            make_metadata(resolution_m=bad_res)
