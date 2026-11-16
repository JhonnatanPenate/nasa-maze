"""RAD reader tests: filtering, hourly means, fallback, rejections."""

from pathlib import Path

import openpyxl
from app.ingest.config_loader import load_environment_columns
from app.ingest.rad import (
    PROVENANCE_HOURLY_MEAN,
    PROVENANCE_SOL_MEAN_FALLBACK,
    read_rad,
)

RAD_HEADER = [
    "sol",
    "observacion",
    "hora_lmst",
    "dosis_b_uGy_h",
    "dosis_e_uGy_h",
    "unidad_original",
]


def _config():
    config_path = Path(__file__).resolve().parents[2] / "config" / "environment_columns.yaml"
    return load_environment_columns(config_path).rad


def _write_rad(path: Path, rows: list[list[object]]) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "RAD"
    ws.append(RAD_HEADER)
    for row in rows:
        ws.append(row)
    wb.save(path)


def _obs(
    sol: int,
    obs_id: str,
    hora: float,
    dose_e: float | None,
    dose_b: float | None = None,
) -> list[object]:
    return [sol, obs_id, hora, dose_b, dose_e, "uGy/hour"]


def test_hourly_means_and_filter(tmp_path: Path) -> None:
    xlsx = tmp_path / "rad.xlsx"
    _write_rad(
        xlsx,
        [
            # sol 100: unsorted on purpose; one low outlier filtered out.
            # dose_e = [30, 10, 1, 20, 12] -> median 12, threshold 8.4;
            # the 1.0 observation is filtered, the rest are kept.
            _obs(100, "A", 2.5, 30.0, 25.0),
            _obs(100, "B", 1.2, 10.0, 8.0),
            _obs(100, "C", 5.0, 1.0, 0.5),  # below 0.7*median -> filtered
            _obs(100, "D", 1.8, 20.0, 18.0),
            _obs(100, "G", 3.5, 12.0, 11.0),
            # sol 200: single bin.
            _obs(200, "E", 0.5, 5.0, 4.0),
            _obs(200, "F", 0.9, 7.0, 6.0),
        ],
    )
    rows, report = read_rad(xlsx, _config())

    sol100 = {r.hora: r for r in rows if r.sol == 100}
    assert len(sol100) == 24  # complete hourly profile per sol
    # bin 1: mean(10, 20) = 15 hourly_mean; bin 2: 30; bin 3: 12;
    # fallback = mean(10, 20, 30, 12) = 18.
    assert sol100[1].dose_e_uGy_h == 15.0
    assert sol100[1].provenance == PROVENANCE_HOURLY_MEAN
    assert sol100[1].dose_b_uGy_h == 13.0
    assert sol100[2].dose_e_uGy_h == 30.0
    assert sol100[3].dose_e_uGy_h == 12.0
    assert sol100[0].dose_e_uGy_h == 18.0
    assert sol100[0].provenance == PROVENANCE_SOL_MEAN_FALLBACK
    assert sol100[23].dose_e_uGy_h == 18.0
    assert sol100[23].provenance == PROVENANCE_SOL_MEAN_FALLBACK

    sol200 = {r.hora: r for r in rows if r.sol == 200}
    assert sol200[0].dose_e_uGy_h == 6.0
    assert sol200[0].provenance == PROVENANCE_HOURLY_MEAN
    assert sol200[5].dose_e_uGy_h == 6.0  # fallback = sol mean
    assert sol200[5].provenance == PROVENANCE_SOL_MEAN_FALLBACK

    # filter stats recorded per sol.
    assert report.extras["filtered"]["100"]["kept_after_filter"] == 4
    assert report.extras["filtered"]["100"]["observations"] == 5
    assert report.extras["fallback_hours"]["100"] == [h for h in range(24) if h not in (1, 2, 3)]
    assert report.rejected == {}
    assert report.rows_in == 7
    assert report.rows_kept == 48


def test_duplicate_timestamp_tolerated(tmp_path: Path) -> None:
    xlsx = tmp_path / "rad.xlsx"
    _write_rad(
        xlsx,
        [
            _obs(100, "A", 1.20, 10.0),
            _obs(100, "B", 1.20, 14.0),  # same (sol, hora) -> both in mean
            _obs(100, "C", 2.0, 12.0),
        ],
    )
    rows, report = read_rad(xlsx, _config())
    sol100 = {r.hora: r for r in rows if r.sol == 100}
    assert sol100[1].dose_e_uGy_h == 12.0  # mean(10, 14)
    assert report.extras["duplicate_timestamps"] == 1
    assert any("duplicate" in f["note"] for f in report.flags)


def test_rejections_counted(tmp_path: Path) -> None:
    xlsx = tmp_path / "rad.xlsx"
    _write_rad(
        xlsx,
        [
            _obs(100, "A", 1.0, 10.0),
            _obs(100, "B", 2.0, 12.0),
            _obs(-5, "C", 1.0, 10.0),  # sol not positive
            _obs(100, "D", 24.5, 10.0),  # hora >= 24
            _obs(100, "E", 3.0, -1.0),  # negative dose
            _obs(100, "F", 4.0, None),  # dose_e missing
            ["abc", "G", 5.0, 1.0, 10.0, "uGy/hour"],  # sol not int
        ],
    )
    rows, report = read_rad(xlsx, _config())
    assert report.rejected == {
        "sol_not_positive": 1,
        "hora_out_of_range": 1,
        "dose_negative": 1,
        "dose_e_missing": 1,
        "sol_not_int": 1,
    }
    # Only sol 100 survives -> 24 hourly rows.
    assert report.rows_kept == 24
    assert {r.sol for r in rows} == {100}


def test_fractional_hora_floors_into_bin(tmp_path: Path) -> None:
    xlsx = tmp_path / "rad.xlsx"
    _write_rad(
        xlsx,
        [
            _obs(100, "A", 0.08, 8.0),
            _obs(100, "B", 0.95, 12.0),  # both floor to hour 0
        ],
    )
    rows, _ = read_rad(xlsx, _config())
    hour0 = next(r for r in rows if r.sol == 100 and r.hora == 0)
    assert hour0.dose_e_uGy_h == 10.0
    assert hour0.provenance == PROVENANCE_HOURLY_MEAN
