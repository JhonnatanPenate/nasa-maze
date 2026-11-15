"""Pure geodesy helpers for Mars.

Conventions (README section 3.2): planetocentric latitude in [-90, 90],
east-positive longitude normalized to [0, 360), reference sphere radius
3,396,190 m (matches the project .tif grid). NEVER use Earth geodesy libs.
"""

from __future__ import annotations

import math

MARSV_RADIUS_M = 3_396_190

# bbox tuple order: (west, south, east, north), longitudes in [0, 360)
BboxTuple = tuple[float, float, float, float]


def normalize_lon(lon: float) -> float:
    """Normalize any east-positive longitude to [0, 360)."""
    if not math.isfinite(lon):
        raise ValueError(f"lon must be finite; got {lon}")
    return lon % 360.0


def validate_lat_lon(lat: float, lon: float) -> tuple[float, float]:
    """Validate and normalize a coordinate. Returns (lat, lon in [0,360))."""
    if not math.isfinite(lat):
        raise ValueError(f"lat must be finite; got {lat}")
    if not math.isfinite(lon):
        raise ValueError(f"lon must be finite; got {lon}")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat must be within [-90, 90]; got {lat}")
    return lat, normalize_lon(lon)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters on the Mars reference sphere."""
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2.0 * MARSV_RADIUS_M * math.asin(math.sqrt(min(1.0, a)))


def bbox_contains(bbox: BboxTuple, lat: float, lon: float) -> bool:
    """True if (lat, lon) is inside bbox=(west, south, east, north).

    Handles bboxes that cross the antimeridian (west > east).
    """
    west, south, east, north = bbox
    lon_n = normalize_lon(lon)
    if not south <= lat <= north:
        return False
    if west <= east:
        return west <= lon_n <= east
    return lon_n >= west or lon_n <= east


# Canonical coordinate system advertised in every response (section 3.2)
CANONICAL_BODY = "mars"
CANONICAL_CRS = "IAU_2015:49900"
CANONICAL_LAT_TYPE = "planetocentric"
CANONICAL_LON_CONVENTION = "east_positive_0_360"


def canonical_coordinate_system() -> dict[str, object]:
    return {
        "body": CANONICAL_BODY,
        "crs": CANONICAL_CRS,
        "lat_type": CANONICAL_LAT_TYPE,
        "lon_convention": CANONICAL_LON_CONVENTION,
        "radius_m": MARSV_RADIUS_M,
    }
