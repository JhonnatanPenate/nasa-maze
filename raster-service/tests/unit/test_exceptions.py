import pytest

from app.core.errors.exceptions import (
    DatasetUnavailableError,
    NoCoverageError,
    NotFoundError,
    RasterServiceError,
    RasterValidationError,
    UnknownBandError,
    UnknownDatasetError,
)


class TestTaxonomy:
    @pytest.mark.parametrize(
        "error_cls",
        [
            RasterValidationError,
            NotFoundError,
            UnknownDatasetError,
            UnknownBandError,
            NoCoverageError,
            DatasetUnavailableError,
        ],
    )
    def test_all_errors_derive_from_base(self, error_cls):
        assert issubclass(error_cls, RasterServiceError)

    @pytest.mark.parametrize(
        "error_cls", [UnknownDatasetError, UnknownBandError, NoCoverageError]
    )
    def test_not_found_family(self, error_cls):
        assert issubclass(error_cls, NotFoundError)

    def test_message_is_preserved(self):
        assert str(UnknownBandError("bad band")) == "bad band"

    def test_subclass_caught_as_base(self):
        with pytest.raises(RasterServiceError):
            raise NoCoverageError("outside extent")
