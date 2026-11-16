"""Distance-weighted path aggregation (SPEC §4.1/§4.4, plan §4.4)."""

import pytest
from app.core.domain.risk_aggregator import aggregate_path
from app.core.domain.risk_level import RiskLevel


def test_distance_weighted_mean() -> None:
    # (0.5 * 100 + 1.0 * 300) / 400 = 0.875 -> critical
    risk, level = aggregate_path([(0.5, 100.0), (1.0, 300.0)])
    assert risk == pytest.approx(0.875)
    assert level is RiskLevel.CRITICAL


def test_unscored_segments_do_not_contribute() -> None:
    risk, level = aggregate_path([(None, 100.0), (0.5, 100.0), (None, 50.0)])
    assert risk == pytest.approx(0.5)
    assert level is RiskLevel.HIGH  # 0.5 is the medium/high SPEC boundary


def test_zero_length_segments_skipped() -> None:
    risk, _ = aggregate_path([(0.2, 0.0), (0.8, 100.0)])
    assert risk == pytest.approx(0.8)


def test_all_unscored_returns_unknown_never_zero() -> None:
    risk, level = aggregate_path([(None, 100.0), (None, 200.0)])
    assert risk is None
    assert level is RiskLevel.UNKNOWN


def test_empty_path_returns_unknown() -> None:
    risk, level = aggregate_path([])
    assert risk is None
    assert level is RiskLevel.UNKNOWN


def test_out_of_range_segment_risk_rejected() -> None:
    with pytest.raises(ValueError, match="outside"):
        aggregate_path([(1.5, 100.0)])
