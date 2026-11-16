"""Shared [0, 1] normalization helpers for factor scoring (plan §4.2).

Every SPEC factor normalizes to ``score ∈ [0, 1]``; these helpers implement
the two shapes used: a linear ramp between a floor and a ceiling, and a
simple ratio clipped to the unit interval.
"""


def clamp01(value: float) -> float:
    """Clamp ``value`` into the closed interval [0, 1]."""
    return min(1.0, max(0.0, value))


def linear_ramp(value: float, floor: float, ceil: float) -> float:
    """Linear normalization: 0 at ``value <= floor``, 1 at ``value >= ceil``.

    ``floor`` must be < ``ceil``; the result is always inside [0, 1].
    """
    if ceil <= floor:
        raise ValueError(f"linear_ramp requires floor < ceil, got {floor} >= {ceil}")
    if value <= floor:
        return 0.0
    if value >= ceil:
        return 1.0
    return (value - floor) / (ceil - floor)
