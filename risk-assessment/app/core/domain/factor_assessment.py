"""Per-factor assessment result (SPEC §4.1 ``factor_scores`` entries).

``available`` reports whether the factor's dataset has coverage at the
sampled location/time. ``score`` is the normalized [0, 1] value; it stays
``None`` until the Phase 3 scoring rules land — an available factor with a
``None`` score is simply not weightable yet and never counts as safe.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FactorAssessment:
    factor_id: str
    available: bool
    score: float | None = None
    # Observed raw inputs kept for provenance/explainability (additive fields).
    observed: dict[str, float | str | None] | None = None
