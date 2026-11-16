"""Mars local solar time helpers: 24-bin LMST wrap-around and sol advance.

Javi's optimizer convention (`science/optimizador_rutas.py`): LMST hour is an
integer bin 0-23; fractional observations floor into bins; elapsed traversal
time advances the bin modulo 24 and rolls the sol over at wrap-around.
No UTC/Ls conversion exists in the delivered data (Phase 0 inventory Q2).
"""

import math

HOURS_PER_SOL = 24


def normalize_hour(hora: float | int) -> int:
    """Validate and wrap an LMST hour into the integer bin 0-23."""
    if isinstance(hora, bool) or not isinstance(hora, (int, float)):
        raise ValueError(f"hora must be numeric, got {hora!r}")
    value = float(hora)
    if value != int(value):
        raise ValueError(f"hora must be an integer LMST hour, got {hora!r}")
    return int(value) % HOURS_PER_SOL


def validate_hour(hora: float | int) -> int:
    """Strict 0-23 check for request inputs (SPEC: hora int 0-23)."""
    if isinstance(hora, bool) or not isinstance(hora, (int, float)):
        raise ValueError(f"hora must be numeric, got {hora!r}")
    value = float(hora)
    if value != int(value) or not 0 <= int(value) <= 23:
        raise ValueError(f"hora must be an integer in [0, 23], got {hora!r}")
    return int(value)


def advance(sol: int, hora: int, elapsed_hours: float) -> tuple[int, int]:
    """Advance ``(sol, LMST hour)`` by ``elapsed_hours`` with mod-24 wrap.

    The absolute LMST index is ``sol*24 + hora + elapsed_hours``; the sol is
    ``floor(index/24)`` and the hour bin is the floored remainder. Negative
    elapsed time moves backward the same way. ``hora`` is normalized into
    0-23 first so departure values like 24 wrap correctly."""
    start = normalize_hour(hora)
    index = sol * HOURS_PER_SOL + start + float(elapsed_hours)
    new_sol = math.floor(index / HOURS_PER_SOL)
    hour_index = math.floor(index - new_sol * HOURS_PER_SOL)
    return int(new_sol), int(hour_index % HOURS_PER_SOL)
