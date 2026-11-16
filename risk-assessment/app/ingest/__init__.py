"""Offline ingestion CLI (plan §8, Phase 2).

`python -m app.ingest` builds `risk_catalog.sqlite` from the delivered
REMS/RAD workbooks. This package is never imported by the runtime app;
pandas/openpyxl live only in the reader modules (`rems.py`, `rad.py`).
"""
