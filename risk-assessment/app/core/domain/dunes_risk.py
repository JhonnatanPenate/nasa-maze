"""``dunes`` factor scoring (SPEC §3.1/§5, plan §4.2).

Sources: MS3 bands ``distancia_duna_m`` and ``fraccion_oscura``.

Score = max of the available components (placeholder normalization,
DECISIONS MS5-D15):

- proximity: ``1 - distancia_duna_m / proximity_warning_m`` clipped to
  [0, 1] — 1 on the dune (distance 0), 0 at or beyond the warning range;
- dark fraction: ``fraccion_oscura / dark_fraction_threshold`` clipped —
  1.0 at Javi's ``arena_dunas`` calibration label (``>= 0.5``).

``BAGNOLD_DUNES_NEARBY`` fires on Javi's mapped-dune rule
(``distancia_duna_m == 0`` or ``fraccion_oscura >= 0.5``) and on the
configurable proximity distance; Javi defines no broader proximity
threshold, so ``proximity_warning_m`` is a ``placeholder``.
"""

from dataclasses import dataclass

from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.factor_catalog import FACTOR_DUNES
from app.core.domain.normalization import clamp01


@dataclass(frozen=True)
class DunesThresholds:
    dark_fraction_threshold: float = 0.5  # Javi regla_suelo arena_dunas
    proximity_warning_m: float = 100.0  # placeholder (DECISIONS MS5-D15)


def assess_dunes(
    distancia_duna_m: float | None,
    fraccion_oscura: float | None,
    thresholds: DunesThresholds | None = None,
) -> FactorAssessment:
    """Score dune proximity/dark-sand fraction; both inputs nodata ->
    unavailable."""
    t = thresholds or DunesThresholds()
    observed: dict[str, float | str | None] = {
        "distancia_duna_m": distancia_duna_m,
        "fraccion_oscura": fraccion_oscura,
    }
    if distancia_duna_m is None and fraccion_oscura is None:
        return FactorAssessment(
            factor_id=FACTOR_DUNES,
            available=False,
            observed=observed,
        )

    components: list[float] = []
    if distancia_duna_m is not None and t.proximity_warning_m > 0:
        components.append(clamp01(1.0 - distancia_duna_m / t.proximity_warning_m))
    if fraccion_oscura is not None and t.dark_fraction_threshold > 0:
        components.append(clamp01(fraccion_oscura / t.dark_fraction_threshold))
    score = max(components) if components else 0.0

    warnings: tuple[str, ...] = ()
    near = (
        distancia_duna_m is not None
        and t.proximity_warning_m > 0
        and distancia_duna_m <= t.proximity_warning_m
    )
    dark = (
        fraccion_oscura is not None
        and t.dark_fraction_threshold > 0
        and fraccion_oscura >= t.dark_fraction_threshold
    )
    if near or dark:
        warnings = ("BAGNOLD_DUNES_NEARBY",)

    return FactorAssessment(
        factor_id=FACTOR_DUNES,
        available=True,
        score=score,
        warnings=warnings,
        observed=observed,
    )
