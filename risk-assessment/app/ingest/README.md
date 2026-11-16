# app/ingest — offline ingestion pipeline

`python -m app.ingest` builds `risk_catalog.sqlite` from the delivered
REMS/RAD `.xlsx` workbooks (plan §8, Phase 2).

- `config_loader.py` — `config/environment_columns.yaml` -> typed mappings.
- `rems.py` — REMS hourly summaries -> `thermal_climatology` rows (K/Pa/W·m⁻²
  preserved as delivered; no humidity invented).
- `rad.py` — RAD observations -> `radiation_climatology`: dose-E channel only,
  per-sol `0.7 * median` background filter, `floor(hora_lmst)` hourly means,
  per-sol-mean fallback for empty bins (`provenance` column).
- `validate.py` — sanity bands, finite checks, reject/flag accounting.
- `writer.py` — atomic temp-file + `os.replace` SQLite write, `meta` +
  `data_quality` tables, `ingest_report.json`.

pandas/openpyxl live only in the `ingest` optional extra; the runtime image
does not include them. Outputs: `data/processed/mars/risk/` plus a committed
seed copy under `data/seed/` (`--seed-dir`).
