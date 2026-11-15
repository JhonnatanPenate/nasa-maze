# Routing Engine Service (MS6)

Dueño: Jhonnatan. Puerto: 8006.

## Qué hace
Calcula la ruta de costo mínimo (A* con tiempo, dosis RAD, estrés térmico y espera nocturna)
desde un origen en Gale hasta el mejor afloramiento del mineral pedido.

## Contrato
- `GET /health` -> `{status, sols_disponibles, aoi}`
- `POST /route` body `{lon, lat, material, sol, hora, vmax}` -> `{geojson, resumen, tramos, control_calidad}`
  (forma en `docs/data/EJEMPLO_API_RESPUESTA.json`). 400 si `sol` no es 1360/2140/3290/4710 o el
  origen sale del AOI `[137.345, -4.740, 137.455, -4.580]`; 422 si `material` no es válido; 404 sin ruta.
- Consume: nada por REST; lee `data/gale/` y usa `science/optimizador_rutas.py` (de Javier, no modificar).

## Datos
- `data/gale/` (paquete Gale de Javier, ver `DATA_SOURCES.md`): rejilla 90 m, modelos por suelo,
  química ChemCam/APXS, RAD/REMS. CRS IAU_2015:49900.
- Env: `MS6_DATA_DIR` (default `data/gale`), `MS6_SCIENCE_DIR` (default `science`), relativos a la raíz del repo.

## Comandos
- Correr: `uvicorn app.main:app --port 8006` (desde `routing-engine/`)
- Tests: `pip install -e ".[dev]" && pytest -q`
- Docker (desde la raíz): `docker build -f routing-engine/Dockerfile -t ms6 .` y
  `docker run -p 8006:8006 -v "$PWD/data/gale:/data/gale:ro" ms6`

## Trampas conocidas
- El optimizador lee globals (`VELOCIDAD_MAXIMA_M_H`) y muta `celda_bloqueada` del entorno cacheado:
  todo el cálculo va bajo un lock global. Un request tarda ~10-30 s.
