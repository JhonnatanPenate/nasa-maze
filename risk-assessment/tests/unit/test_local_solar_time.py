"""LMST helpers: integer hour bins 0-23 and sol wrap-around."""

import pytest
from app.core.domain.local_solar_time import advance, normalize_hour, validate_hour


@pytest.mark.parametrize("hora", [0, 1, 12, 23])
def test_validate_hour_accepts(hora: int) -> None:
    assert validate_hour(hora) == hora


@pytest.mark.parametrize("hora", [-1, 24, 25, 1.5, "9", True])
def test_validate_hour_rejects(hora: object) -> None:
    with pytest.raises(ValueError):
        validate_hour(hora)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "raw,expected",
    [(0, 0), (23, 23), (24, 0), (-1, 23), (25, 1), (47, 23)],
)
def test_normalize_hour_wraps(raw: int, expected: int) -> None:
    assert normalize_hour(raw) == expected


def test_advance_within_sol() -> None:
    assert advance(1360, 9, 2.0) == (1360, 11)


def test_advance_wraps_sol() -> None:
    assert advance(1360, 23, 2.0) == (1361, 1)


def test_advance_fractional_floors() -> None:
    assert advance(1360, 9, 1.9) == (1360, 10)


def test_advance_backward_wraps() -> None:
    assert advance(1360, 0, -1.0) == (1359, 23)
