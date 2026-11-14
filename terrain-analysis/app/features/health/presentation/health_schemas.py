from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Contract for `GET /health` (plan F1)."""

    status: Literal["ok", "degraded"]
    datasource: Literal["ok", "unavailable"]
