"""Catalog validation (README section 9.1). Fails the build on errors."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

from location_service.domain.models import Place, Region
from location_service.domain.text import normalize_text

_SCHEMA_VERSION = 1

# known-feature convention check (section 9.1): Olympus Mons center
_OLYMPUS_NAME_NORMS = {"olympus mons"}
_OLYMPUS_LAT = 18.65
_OLYMPUS_LON = 226.2
_OLYMPUS_TOLERANCE_DEG = 1.0

_ROUTE_DESTINATION_IDS = (
    "mars:msl:oudam",
    "mars:msl:glen-etive",
    "mars:msl:buckskin",
)


def validate_catalog(
    places: list[Place],
    regions: tuple[Region, ...] | list[Region],
    report: dict[str, Any],
) -> list[str]:
    """Return a list of validation errors (empty = catalog is valid)."""
    errors: list[str] = []

    for p in places:
        lat, lon = p.center.lat, p.center.lon
        if not (math.isfinite(lat) and math.isfinite(lon)):
            errors.append(f"{p.id}: non-finite coordinates")
            continue
        if not -90.0 <= lat <= 90.0:
            errors.append(f"{p.id}: lat {lat} outside [-90, 90]")
        if not 0.0 <= lon < 360.0:
            errors.append(f"{p.id}: lon {lon} outside [0, 360)")

    ids = Counter(p.id for p in places)
    for pid, count in ids.items():
        if count > 1:
            errors.append(f"duplicate place id: {pid} ({count} rows)")

    aoi = next((r for r in regions if r.id == "aoi:gale-90m"), None)
    if aoi is not None and aoi.bbox is not None:
        for p in places:
            if p.source == "mission_msl" and not aoi.bbox.contains(
                p.center.lat, p.center.lon
            ):
                errors.append(
                    f"mission place {p.id} ({p.name}) is outside aoi:gale-90m"
                )
    else:
        report.setdefault("warnings", []).append(
            "region aoi:gale-90m not configured; POI containment check skipped"
        )

    if not any(p.id == "mars:msl:bradbury-landing" for p in places):
        errors.append("Bradbury Landing (mars:msl:bradbury-landing) is missing")

    known_ids = {p.id for p in places}
    for pid in _ROUTE_DESTINATION_IDS:
        if pid not in known_ids:
            errors.append(f"route destination missing: {pid}")

    # convention sanity check - only meaningful when Gazetteer data is present
    gazetteer_places = [p for p in places if p.source == "iau_gazetteer"]
    if gazetteer_places:
        olympus = [
            p
            for p in gazetteer_places
            if (p.name_norm or normalize_text(p.name)) in _OLYMPUS_NAME_NORMS
        ]
        if not olympus:
            report.setdefault("warnings", []).append(
                "Olympus Mons not found in gazetteer; convention check skipped"
            )
        else:
            for p in olympus:
                if (
                    abs(p.center.lat - _OLYMPUS_LAT) > _OLYMPUS_TOLERANCE_DEG
                    or abs(p.center.lon - _OLYMPUS_LON) > _OLYMPUS_TOLERANCE_DEG
                ):
                    errors.append(
                        f"convention check failed for {p.name}: center "
                        f"({p.center.lat}, {p.center.lon}) is not near "
                        f"({_OLYMPUS_LAT}, {_OLYMPUS_LON}); possible "
                        "longitude/latitude convention or sign error"
                    )
    return errors


def schema_version() -> int:
    return _SCHEMA_VERSION
