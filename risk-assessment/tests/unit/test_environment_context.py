"""EnvironmentContextResolver: per-dataset nearest sol + default sol."""

import pytest
from app.core.application.environment_context import EnvironmentContextResolver
from app.core.errors.exceptions import DomainValidationError

from tests.fakes.fake_environment_repository import FakeEnvironmentRepository


def _repo() -> FakeEnvironmentRepository:
    from tests.conftest import full_environment

    return full_environment()


def test_nearest_sol_selected_independently_per_dataset() -> None:
    resolver = EnvironmentContextResolver(_repo(), default_sol=1360)
    ctx = resolver.resolve(5000, 9)
    # REMS only has {1360, 2140}; RAD has {1360, 2140, 3290, 4710}.
    assert ctx.rems_sol == 2140
    assert ctx.rad_sol == 4710
    assert ctx.reference_sol == 5000
    assert ctx.temperature is not None
    assert ctx.radiation is not None


def test_default_sol_used_when_none() -> None:
    resolver = EnvironmentContextResolver(_repo(), default_sol=2140)
    ctx = resolver.resolve(None, 9)
    assert ctx.reference_sol == 2140
    assert ctx.rems_sol == 2140
    assert ctx.rad_sol == 2140


def test_hora_selects_hourly_profile() -> None:
    resolver = EnvironmentContextResolver(_repo(), default_sol=1360)
    ctx = resolver.resolve(1360, 9)
    assert ctx.hora == 9
    assert ctx.temperature is not None and ctx.temperature.hora == 9
    assert ctx.radiation is not None and ctx.radiation.hora == 9


def test_missing_sol_coverage_returns_none_profiles() -> None:
    resolver = EnvironmentContextResolver(FakeEnvironmentRepository(), default_sol=1360)
    ctx = resolver.resolve(1360, 9)
    assert ctx.rems_sol is None
    assert ctx.rad_sol is None
    assert ctx.temperature is None
    assert ctx.radiation is None


@pytest.mark.parametrize("bad", ["x", 1.5, True])
def test_non_integer_sol_rejected(bad: object) -> None:
    resolver = EnvironmentContextResolver(_repo(), default_sol=1360)
    with pytest.raises(DomainValidationError):
        resolver.resolve(bad, 9)  # type: ignore[arg-type]


def test_daily_predictors_are_selected_sol_means() -> None:
    resolver = EnvironmentContextResolver(_repo(), default_sol=1360)
    ctx = resolver.resolve(5000, 9)  # rems->2140, rad->4710
    predictors = resolver.daily_predictors(ctx)
    # Fake catalog is uniform: ground mean 255 K, dose-E 12.5 uGy/h.
    assert predictors["temp_suelo_K_media"] == pytest.approx(255.0)
    assert predictors["dosis_rad_uGy_h"] == pytest.approx(12.5)


def test_daily_predictors_empty_without_catalog() -> None:
    resolver = EnvironmentContextResolver(FakeEnvironmentRepository(), default_sol=1360)
    ctx = resolver.resolve(1360, 9)
    assert resolver.daily_predictors(ctx) == {}
