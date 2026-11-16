from pydantic import BaseModel


class FactorInfoSchema(BaseModel):
    """One entry of the SPEC factor catalog (SPEC §3.3)."""

    id: str
    name: str
    unit: str | None
    weight: float
    available: bool
    sources: list[str]
    note: str | None = None


class FactorsResponse(BaseModel):
    """Contract for `GET /risk/factors`."""

    factors: list[FactorInfoSchema]
    weights: dict[str, float]
    model_version: str
    default_sol: int
    environmental_sols: dict[str, list[int]]
