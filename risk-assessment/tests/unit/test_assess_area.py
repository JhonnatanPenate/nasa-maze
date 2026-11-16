"""Unit tests for the area-assessment use case helpers (plan extension)."""

import pytest
from app.core.domain.bounding_box import BoundingBox
from app.core.errors.exceptions import (
    AreaTooLargeError,
    DomainValidationError,
)
from app.features.area_assessment.application.assess_area import (
    GRID_RES_DEG,
    AssessArea,
)


def _use_case(max_area_cells: int = 100) -> AssessArea:
    """Deps are unused by the helpers under test."""
    return AssessArea(
        terrain=None,  # type: ignore[arg-type]
        raster=None,  # type: ignore[arg-type]
        env_resolver=None,  # type: ignore[arg-type]
        vehicle_profiles=None,  # type: ignore[arg-type]
        distance_calculator=None,  # type: ignore[arg-type]
        weights={},
        thresholds=None,  # type: ignore[arg-type]
        tilt_models=None,  # type: ignore[arg-type]
        model_version="test",
        default_vehicle_profile="baseline_mars_rover",
        max_area_cells=max_area_cells,
    )


def test_cell_count_uses_grid_pitch() -> None:
    res = GRID_RES_DEG
    bbox = BoundingBox(min_lon=0.0, min_lat=0.0, max_lon=2 * res, max_lat=3 * res)
    assert _use_case().cell_count(bbox) == 6


def test_cell_count_rounds_up_partial_cells() -> None:
    res = GRID_RES_DEG
    bbox = BoundingBox(
        min_lon=0.0, min_lat=0.0, max_lon=2.5 * res, max_lat=0.5 * res
    )
    assert _use_case().cell_count(bbox) == 3  # ceil(2.5)=3 cols, ceil(0.5)=1 row


def test_check_cap_raises_area_too_large() -> None:
    res = GRID_RES_DEG
    bbox = BoundingBox(min_lon=0.0, min_lat=0.0, max_lon=10 * res, max_lat=10 * res)
    with pytest.raises(AreaTooLargeError):
        _use_case(max_area_cells=50).check_cap(bbox, None)


def test_check_cap_honors_request_max_cells() -> None:
    res = GRID_RES_DEG
    bbox = BoundingBox(min_lon=0.0, min_lat=0.0, max_lon=2 * res, max_lat=2 * res)
    use_case = _use_case(max_area_cells=1000)
    assert use_case.check_cap(bbox, max_cells=4) == 4
    with pytest.raises(AreaTooLargeError):
        use_case.check_cap(bbox, max_cells=3)


def test_axis_steps_from_min() -> None:
    res = GRID_RES_DEG
    axis = AssessArea._axis(1.0, 1.0 + 2.5 * res)
    assert axis == pytest.approx([1.0, 1.0 + res, 1.0 + 2 * res])
    assert all(v < 1.0 + 2.5 * res for v in axis)


def test_validate_hora() -> None:
    assert AssessArea._validate_hora(0) == 0
    assert AssessArea._validate_hora(23) == 23
    with pytest.raises(DomainValidationError):
        AssessArea._validate_hora(24)
