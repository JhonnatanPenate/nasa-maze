from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Contract for `GET /health` — always 200 while the process is alive;
    upstream failures degrade the status instead of erroring (MS4 pattern)."""

    status: Literal["ok", "degraded"]
    datasource_mode: str
    terrain: Literal["ok", "unavailable"]
    raster: Literal["ok", "unavailable"]
    environment: Literal["ok", "unavailable"]
