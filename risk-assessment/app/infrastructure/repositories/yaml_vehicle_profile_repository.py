"""YAML-backed vehicle profile repository (config/vehicle_profiles.yaml)."""

from app.core.config.risk_config import load_vehicle_profiles
from app.core.domain.vehicle_profile import VehicleProfile
from app.core.errors.exceptions import VehicleProfileNotFoundError


class YamlVehicleProfileRepository:
    def __init__(self, config_dir: str) -> None:
        self._profiles = {profile.name: profile for profile in load_vehicle_profiles(config_dir)}

    def list(self) -> tuple[VehicleProfile, ...]:
        return tuple(self._profiles.values())

    def get(self, name: str) -> VehicleProfile:
        try:
            return self._profiles[name]
        except KeyError as exc:
            raise VehicleProfileNotFoundError(
                f"Unknown vehicle profile '{name}'; available: {', '.join(sorted(self._profiles))}"
            ) from exc
