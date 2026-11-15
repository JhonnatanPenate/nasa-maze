# Architecture decisions log

Cross-service decisions and per-service defaults. Each entry records the
decision, the status, and where it is implemented.

## Location Service (`location-service/`)

| ID | Decision | Status | Notes |
|---|---|---|---|
| D1 | Canonical Bradbury Landing coordinate: `lat -4.5895, lon 137.4417` | **accepted (default)** | Route-cell snapping belongs to Raster/Routing, not this service. Seed catalog uses `mars:msl:bradbury-landing`. |
| D2 | Gazetteer acquisition: manual MVP download into `data/raw/mars/gazetteer/` | **done (MVP)** | Delivered file: USGS `MARS_nomenclature_center_pts.shp` (2055 POINT features, GCS_Mars_2000 sphere). Linked into `data/raw/mars/gazetteer/`; full catalog built at `data/processed/mars/location/location_catalog.sqlite` (2077 places). |
| D3 | Gazetteer `approval_status`: approved features only by default | **accepted (default)** | Unapproved/provisional features are excluded from the catalog and counted in `ingest_report.json`. |
| D4 | Alias/descriptor languages: Spanish + English | **accepted (default)** | `config/aliases.yaml` + `type_word_translations` in `config/gazetteer_columns.yaml`. Official names stay in the Gazetteer's language. |
| D5 | Mineral `properties` exposed per POI | **accepted (default)** | Informational attributes only; not an official scientific source. |
| D6 | UI autocomplete via `GET /v1/places/search` (small `limit`, prefix matching) | **accepted (default)** | No separate autocomplete endpoint. |
| D7 | Future Moon support | **deferred** | `body` field and ID prefixes already allow it; not implemented. |

### Implementation notes

- Python `>=3.12` (`requires-python`), developed on 3.13.5 — the only
  interpreter available in the build environment.
- Runtime is fully offline: no outbound calls; the catalog is a read-only
  SQLite file loaded once at startup (with optional `/v1/admin/reload`).
- Ingestion-only dependencies (`pandas`, `openpyxl`) live in the `ingest`
  extra, never in runtime dependencies.
- Mars geodesy is implemented locally (`domain/geo.py`, haversine with
  R = 3,396,190 m); no Earth geodesy library is used.
- Gazetteer-dependent golden cases 7–8 run unskipped once a file is
  present in `data/raw/mars/gazetteer/` (currently a symlink to the
  delivered `data/gale/raw/gazzeter/MARS_nomenclature_center_pts.shp`;
  the directory itself is git-ignored data, so fresh clones skip again).
- Golden case 13 (Bradbury Landing → Glen Etive): the spec's "≈ 14–15 km"
  appears to be an estimate; the haversine straight-line distance with
  R = 3,396,190 m is 9,026 m (the delivered route metadata reports a 10.3 km
  path). The test asserts the computed value (8–11 km) and case 23 verifies
  the formula against an independent calculation.
