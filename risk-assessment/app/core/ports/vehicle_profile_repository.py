"""Port: vehicle profile catalog (config/vehicle_profiles.yaml)."""

from typing import Protocol

from app.core.domain.vehicle_profile import VehicleProfile


class VehicleProfileRepository(Protocol):
    def list(self) -> tuple[VehicleProfile, ...]:
        """All configured profiles."""
        ...

    def get(self, name: str) -> VehicleProfile:
        """Profile by name; raises VehicleProfileNotFoundError."""
        ...
