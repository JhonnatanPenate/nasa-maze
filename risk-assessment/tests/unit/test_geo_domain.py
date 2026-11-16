"""GeoPoint / BoundingBox validation (same ranges as MS3/MS4)."""

import pytest
from app.core.domain.bounding_box import BoundingBox
from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import DomainValidationError


def test_valid_point() -> None:
    p = GeoPoint(lat=-4.6, lon=137.44)
    assert p.lat == -4.6 and p.lon == 137.44


@pytest.mark.parametrize("lat,lon", [(91, 0), (-91, 0), (0, 181), (0, -181)])
def test_point_out_of_range(lat: float, lon: float) -> None:
    with pytest.raises(DomainValidationError):
        GeoPoint(lat=lat, lon=lon)


def test_point_rejects_non_finite() -> None:
    with pytest.raises(DomainValidationError):
        GeoPoint(lat=float("nan"), lon=0.0)


def test_bounding_box_valid() -> None:
    bbox = BoundingBox(min_lon=137.0, min_lat=-5.0, max_lon=138.0, max_lat=-4.0)
    assert bbox.contains(GeoPoint(lat=-4.5, lon=137.5))
    assert not bbox.contains(GeoPoint(lat=0.0, lon=0.0))


def test_bounding_box_rejects_inverted() -> None:
    with pytest.raises(DomainValidationError):
        BoundingBox(min_lon=138.0, min_lat=-5.0, max_lon=137.0, max_lat=-4.0)


def test_bounding_box_rejects_out_of_range() -> None:
    with pytest.raises(DomainValidationError):
        BoundingBox(min_lon=137.0, min_lat=-95.0, max_lon=138.0, max_lat=-4.0)
