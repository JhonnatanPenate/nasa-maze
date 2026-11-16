"""REMS reader tests: fixture workbook -> thermal_climatology rows."""

from pathlib import Path

import openpyxl
import pytest
from app.ingest.config_loader import WorkbookConfig
from app.ingest.rems import read_rems

REMS_HEADER = [
    "sol",
    "hora_lmst",
    "n",
    "temp_suelo_K_media",
    "temp_suelo_K_min",
    "temp_suelo_K_max",
    "temp_aire_K_media",
    "presion_Pa_media",
    "uv_abc_W_m2_media",
]


def _config() -> WorkbookConfig:
    return WorkbookConfig(
        name="rems",
        source="fixture.xlsx",
        sheet="REMS",
        key_columns={},
        value_columns={},
    )


def _real_config() -> WorkbookConfig:
    """Use the shipped environment_columns.yaml rems section."""
    from app.ingest.config_loader import load_environment_columns

    config_path = Path(__file__).resolve().parents[2] / "config" / "environment_columns.yaml"
    return load_environment_columns(config_path).rems


def _write_rems(path: Path, rows: list[list[object]]) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "REMS"
    ws.append(REMS_HEADER)
    for row in rows:
        ws.append(row)
    wb.save(path)


def _valid_row(sol: int, hora: int, **overrides: object) -> list[object]:
    row: list[object] = [
        sol,
        hora,
        300,
        220.0,
        210.0,
        230.0,
        225.0,
        750.0,
        1.5,
    ]
    for index, value in overrides.items():
        row[REMS_HEADER.index(index)] = value
    return row


def test_valid_rows_kept_with_nulls(tmp_path: Path) -> None:
    xlsx = tmp_path / "rems.xlsx"
    _write_rems(
        xlsx,
        [
            _valid_row(1360, 0),
            _valid_row(1360, 1, uv_abc_W_m2_media=None),
            _valid_row(2140, 0),
        ],
    )
    rows, report = read_rems(xlsx, _real_config())
    assert report.rows_in == 3
    assert report.rows_kept == 3
    assert report.rejected == {}
    assert len(rows) == 3
    uv_null = next(r for r in rows if r.hora == 1)
    assert uv_null.uv_abc_mean_W_m2 is None
    assert uv_null.air_temp_mean_K == 225.0
    assert any("uv_abc" in f["note"] for f in report.flags)


def test_sanity_band_rejects_impossible_temp(tmp_path: Path) -> None:
    xlsx = tmp_path / "rems.xlsx"
    _write_rems(
        xlsx,
        [
            _valid_row(1360, 0),
            _valid_row(1360, 1, temp_suelo_K_media=400.0),  # > 323.15 K
            _valid_row(1360, 2, presion_Pa_media=-5.0),
        ],
    )
    rows, report = read_rems(xlsx, _real_config())
    assert len(rows) == 1
    assert report.rejected == {"sanity_band": 2}


def test_duplicate_and_bad_keys_rejected(tmp_path: Path) -> None:
    xlsx = tmp_path / "rems.xlsx"
    _write_rems(
        xlsx,
        [
            _valid_row(1360, 0),
            _valid_row(1360, 0),  # duplicate (sol, hora)
            _valid_row(1360, 25),  # hora out of range
            _valid_row(-3, 0),  # sol not positive
            _valid_row(1360, "x"),  # type: ignore[list-item]
        ],
    )
    rows, report = read_rems(xlsx, _real_config())
    assert len(rows) == 1
    assert report.rejected == {
        "duplicate_key": 1,
        "hora_out_of_range": 1,
        "sol_not_positive": 1,
        "hora_not_int": 1,
    }


def test_missing_required_mapping_fails(tmp_path: Path) -> None:
    xlsx = tmp_path / "rems.xlsx"
    _write_rems(xlsx, [_valid_row(1360, 0)])
    with pytest.raises(ValueError, match="required key columns"):
        read_rems(xlsx, _config())
