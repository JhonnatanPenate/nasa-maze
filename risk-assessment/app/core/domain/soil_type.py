"""Javi's 4-class soil regime precedence (plan §3.1/§4.2).

Mirrors ``clasificar_tipo_suelo`` in ``science/optimizador_rutas.py``
(lines 73-85): start at ``regolito_compacto`` and let each later rule
overwrite — ``rocoso_fracturado``, then ``lecho_rocoso_firme``, then
``arena_dunas`` on top. ``pendiente_grados`` is the MS4 slope reused as
Javi's slope input (plan §4.2); predicted tilt is NOT a substitute for the
SPEC ``slope`` factor.

All five raster inputs are required: any nodata -> ``None`` (the soil
regime is unknown, never guessed).
"""

from enum import StrEnum


class SoilType(StrEnum):
    ARENA_DUNAS = "arena_dunas"
    LECHO_ROCOSO_FIRME = "lecho_rocoso_firme"
    ROCOSO_FRACTURADO = "rocoso_fracturado"
    REGOLITO_COMPACTO = "regolito_compacto"


# Javi regla_suelo thresholds (optimizador_rutas.py + modelos_por_suelo.json
# "reglas_suelo"). Sources are the delivered calibration, not placeholders.
ROCKY_ROUGHNESS_MIN_M = 1.10
ROCKY_SLOPE_MIN_DEG = 8.0
ROCKY_ALBEDO_MAX = 0.2291
FIRM_ROUGHNESS_MAX_M = 0.60
FIRM_SLOPE_MAX_DEG = 7.0
FIRM_ALBEDO_MIN = 0.2294
DUNE_DARK_FRACTION = 0.5


def classify_soil(
    *,
    rugosidad_m: float | None,
    pendiente_grados: float | None,
    albedo: float | None,
    distancia_duna_m: float | None,
    fraccion_oscura: float | None,
) -> SoilType | None:
    """Classify the soil regime; ``None`` when any input is nodata."""
    inputs = (
        rugosidad_m,
        pendiente_grados,
        albedo,
        distancia_duna_m,
        fraccion_oscura,
    )
    if any(v is None for v in inputs):
        return None
    assert rugosidad_m is not None and pendiente_grados is not None
    assert albedo is not None and distancia_duna_m is not None
    assert fraccion_oscura is not None

    soil = SoilType.REGOLITO_COMPACTO
    if (
        rugosidad_m >= ROCKY_ROUGHNESS_MIN_M
        or pendiente_grados >= ROCKY_SLOPE_MIN_DEG
        or albedo < ROCKY_ALBEDO_MAX
    ):
        soil = SoilType.ROCOSO_FRACTURADO
    if (
        rugosidad_m <= FIRM_ROUGHNESS_MAX_M
        and pendiente_grados <= FIRM_SLOPE_MAX_DEG
        and albedo >= FIRM_ALBEDO_MIN
    ):
        soil = SoilType.LECHO_ROCOSO_FIRME
    if distancia_duna_m == 0 or fraccion_oscura >= DUNE_DARK_FRACTION:
        soil = SoilType.ARENA_DUNAS
    return soil
