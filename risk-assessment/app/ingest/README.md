# app/ingest — offline ingestion pipeline

`python -m app.ingest` builds `risk_catalog.sqlite` from the delivered
REMS/RAD `.xlsx` workbooks (plan §8). **Phase 2 scope** — currently a stub.

Planned modules: `config_loader.py` (environment_columns.yaml), `rems.py`,
`rad.py`, `validate.py`, `writer.py` (atomic sqlite write + ingest_report.json).
