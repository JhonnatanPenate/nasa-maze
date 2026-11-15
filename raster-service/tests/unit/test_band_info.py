import pytest

from app.core.domain.band_info import BandInfo
from app.core.errors.exceptions import RasterValidationError


class TestBandInfo:
    def test_valid_band_stores_fields(self):
        band = BandInfo(
            index=1, name="pendiente_grados", unit="deg", nodata=None
        )

        assert band.index == 1
        assert band.name == "pendiente_grados"
        assert band.unit == "deg"
        assert band.nodata is None

    def test_numeric_nodata_is_stored(self):
        band = BandInfo(index=2, name="rugosidad_m", unit="m", nodata=-9999.0)

        assert band.nodata == -9999.0

    def test_nan_nodata_is_normalized_to_none(self):
        band = BandInfo(index=3, name="b", unit="fraction", nodata=float("nan"))

        assert band.nodata is None

    @pytest.mark.parametrize("bad_index", [0, -2, 1.5, "1", True])
    def test_invalid_index_raises(self, bad_index):
        with pytest.raises(RasterValidationError):
            BandInfo(index=bad_index, name="b", unit="m", nodata=None)

    @pytest.mark.parametrize("bad_name", ["", None, 3])
    def test_invalid_name_raises(self, bad_name):
        with pytest.raises(RasterValidationError):
            BandInfo(index=1, name=bad_name, unit="m", nodata=None)

    def test_infinite_nodata_raises(self):
        with pytest.raises(RasterValidationError):
            BandInfo(index=1, name="b", unit="m", nodata=float("inf"))

    def test_render_fields_default_to_unset(self):
        band = BandInfo(index=1, name="b", unit="m", nodata=None)

        assert band.colormap == ""
        assert band.value_range is None

    def test_render_fields_are_stored(self):
        band = BandInfo(
            index=1,
            name="b",
            unit="m",
            nodata=None,
            colormap="slope",
            value_range=(0.0, 35.0),
        )

        assert band.colormap == "slope"
        assert band.value_range == (0.0, 35.0)

    @pytest.mark.parametrize("bad_colormap", [None, 3, True])
    def test_invalid_colormap_raises(self, bad_colormap):
        with pytest.raises(RasterValidationError):
            BandInfo(
                index=1, name="b", unit="m", nodata=None,
                colormap=bad_colormap,
            )

    @pytest.mark.parametrize(
        "bad_range",
        [(35.0, 0.0), (0.0, float("nan")), (1.0,), "wide", 35.0],
    )
    def test_invalid_value_range_raises(self, bad_range):
        with pytest.raises(RasterValidationError):
            BandInfo(
                index=1, name="b", unit="m", nodata=None,
                value_range=bad_range,
            )
