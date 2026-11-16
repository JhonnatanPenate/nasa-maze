"""Per-factor assessment result (SPEC §4.1 ``factor_scores`` entries).

``available`` reports whether the factor's dataset has coverage at the
sampled location/time. ``score`` is the normalized [0, 1] value produced by
the Phase 3 scoring rules; an unavailable factor (or a ``None`` score) never
participates in the weighted mean and never counts as safe.

``warnings`` carries the SPEC warning codes emitted by that factor's
thresholds (e.g. ``STEEP_SLOPE_15DEG``); ``observed`` keeps the raw inputs
for provenance/explainability.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FactorAssessment:
    factor_id: str
    available: bool
    score: float | None = None
    warnings: tuple[str, ...] = ()
    # Observed raw inputs kept for provenance/explainability (additive fields).
    observed: dict[str, float | str | None] | None = None
