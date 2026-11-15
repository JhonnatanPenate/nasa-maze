from typing import Literal

from pydantic import BaseModel


class DatasetHealth(BaseModel):
    name: str
    readable: bool


class HealthResponse(BaseModel):
    """Contract for `GET /health` (plan F1); doubles as MS4's ping()."""

    status: Literal["ok", "degraded"]
    dataset_count: int
    datasets: list[DatasetHealth]
