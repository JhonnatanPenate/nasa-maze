# Risk Assessment Service

Dueño: Risk Assessment builder. Puerto: 8005.

## Qué hace
Evalúa riesgo normalizado [0,1] de terreno (pendiente vía MS4) y ambiental
(rugosidad, dunas, temperatura REMS, radiación RAD) en puntos y rutas del
cráter Gale. MS5 reporta tasas por segmento; la dosis acumulada de ruta es de MS6.

## Contrato
- `GET /health` -> estado + conectividad MS3/MS4/catálogo
- `GET /risk/point?lat&lon[&sol&hora&include_hourly&factors]` -> evaluación puntual
- `POST /risk/evaluate` body `{path, factors?, sol?, hora?, sampling_step_m?, vehicle_profile?, speed_mps?}` -> evaluación por ruta
- `GET /risk/factors` -> catálogo de factores y cobertura
- Extensiones aditivas (plan, no SPEC): `GET /risk/vehicle-profiles`, `GET /risk/meta`, `POST /risk/area`
- Consume: MS3 `:8003` (`/raster/rejilla/*`), MS4 `:8004` (`/terrain/profile`, `/terrain/point`)

## Datos
- `data/gale/processed/rejilla_ruta_90m.tif` vía MS3 (6 bandas); REMS/RAD `.xlsx`
  vía catálogo SQLite (`python -m app.ingest`, Phase 2). CRS `IAU_2015:49900`,
  lat/lon planetocéntricas en grados, lon +este [-180,180].

## Comandos
- Correr: `uvicorn app.main:app --port 8005` (desde `risk-assessment/`)
- Tests: `pip install -e ".[dev]" && pytest -q` (+ `ruff check .`, `mypy`)
- Modos: `RISK_DATASOURCE_MODE=synthetic|http|unavailable`

## Trampas conocidas
- Factores no disponibles NUNCA puntúan como seguros: `available:false` y se
  excluyen de la media ponderada; sin factores -> `risk_level:"unknown"`.
- `sol`/`hora` seleccionan perfiles ambientales horarios; el sol más cercano
  disponible se elige por dataset y se reporta en `provenance`.
- No leer GeoTIFF ni SQLite de otros servicios: MS3 es la frontera de rasters.
