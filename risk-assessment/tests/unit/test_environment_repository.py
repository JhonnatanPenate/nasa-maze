"""SqliteEnvironmentRepository against a temp catalog (Phase 2 schema)."""

import sqlite3
from pathlib import Path

import pytest
from app.infrastructure.repositories.sqlite_environment_repository import (
    SqliteEnvironmentRepository,
)
from app.infrastructure.repositories.unavailable_environment_repository import (
    UnavailableEnvironmentRepository,
)


def _make_catalog(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE thermal_climatology(
            sol INTEGER, hora INTEGER, air_temp_mean_K REAL,
            ground_temp_mean_K REAL, ground_temp_min_K REAL,
            ground_temp_max_K REAL, pressure_mean_Pa REAL,
            uv_abc_mean_W_m2 REAL);
        CREATE TABLE radiation_climatology(
            sol INTEGER, hora INTEGER, dose_e_uGy_h REAL,
            dose_b_uGy_h REAL, unit TEXT);
        INSERT INTO thermal_climatology VALUES
            (1360, 9, 250.0, 255.0, 240.0, 265.0, 700.0, 1.5),
            (2140, 9, 260.0, 265.0, 250.0, 275.0, 650.0, 1.2);
        INSERT INTO radiation_climatology VALUES
            (1360, 9, 12.5, 3.0, 'uGy/h'),
            (4710, 9, 20.0, 4.0, 'uGy/h');
        """
    )
    conn.commit()
    conn.close()


def test_ping_and_sols(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.sqlite"
    _make_catalog(catalog)
    repo = SqliteEnvironmentRepository(str(catalog))
    assert repo.ping() is True
    assert repo.available_sols("rems") == (1360, 2140)
    assert repo.available_sols("rad") == (1360, 4710)


def test_nearest_sol_tie_prefers_lower(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.sqlite"
    _make_catalog(catalog)
    repo = SqliteEnvironmentRepository(str(catalog))
    # midpoint between 1360 and 2140 is 1750; 1749 -> 1360, 1751 -> 2140
    assert repo.nearest_sol("rems", 1749) == 1360
    assert repo.nearest_sol("rems", 1751) == 2140
    assert repo.nearest_sol("rems", 3000) == 2140


def test_lookups(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.sqlite"
    _make_catalog(catalog)
    repo = SqliteEnvironmentRepository(str(catalog))
    temp = repo.temperature_at(1360, 9)
    assert temp is not None and temp.air_temp_mean_K == 250.0
    rad = repo.radiation_at(1360, 9)
    assert rad is not None and rad.dose_e_uGy_h == 12.5
    assert repo.temperature_at(1360, 10) is None
    assert repo.radiation_at(2140, 9) is None


def test_missing_file_reports_no_coverage(tmp_path: Path) -> None:
    repo = SqliteEnvironmentRepository(str(tmp_path / "missing.sqlite"))
    assert repo.ping() is False
    assert repo.available_sols("rems") == ()
    assert repo.nearest_sol("rad", 1360) is None
    assert repo.temperature_at(1360, 9) is None


def test_empty_catalog_no_tables(tmp_path: Path) -> None:
    catalog = tmp_path / "empty.sqlite"
    sqlite3.connect(catalog).close()
    repo = SqliteEnvironmentRepository(str(catalog))
    assert repo.ping() is True
    assert repo.available_sols("rems") == ()
    assert repo.temperature_at(1360, 9) is None


def test_catalog_opened_read_only(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.sqlite"
    _make_catalog(catalog)
    repo = SqliteEnvironmentRepository(str(catalog))
    assert repo.ping() is True
    conn = repo._connect()
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        conn.execute("INSERT INTO thermal_climatology VALUES (1, 0, 0, 0, 0, 0, 0, 0)")


def test_unavailable_repository_is_empty() -> None:
    repo = UnavailableEnvironmentRepository()
    assert repo.ping() is False
    assert repo.available_sols("rems") == ()
    assert repo.temperature_at(1360, 9) is None
