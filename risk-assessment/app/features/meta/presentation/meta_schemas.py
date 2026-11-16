from typing import Any

from pydantic import BaseModel


class MetaResponse(BaseModel):
    """Plan extension `GET /risk/meta`: thresholds, weights, model version,
    provenance and coverage snapshot."""

    service: str
    model_version: str
    weights: dict[str, float]
    thresholds: dict[str, Any]
    default_sol: int
    default_vehicle_profile: str
    datasource_mode: str
    upstream: dict[str, str]
    catalog: dict[str, Any]
    coordinate_system: dict[str, Any]
