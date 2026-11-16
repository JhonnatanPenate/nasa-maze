"""Application use case: list configured vehicle profiles (plan ext.)."""

from app.core.domain.vehicle_profile import VehicleProfile
from app.core.ports.vehicle_profile_repository import VehicleProfileRepository


class ListVehicleProfiles:
    def __init__(self, repository: VehicleProfileRepository) -> None:
        self._repository = repository

    def execute(self) -> tuple[VehicleProfile, ...]:
        return self._repository.list()
