# Core — orquestador de Planetary Explorer

Único punto de entrada del frontend. Proxea al Routing Engine (MS6) y, si no está disponible,
sirve las rutas precalculadas de `data/gale/processed/`. Además expone las capas base, las bandas
del raster y los modelos de suelo. No calcula ciencia. Plan: [`docs/core/IMPLEMENTATION_PLAN_CORE.md`](../docs/core/IMPLEMENTATION_PLAN_CORE.md).

## Endpoints

| Método | Ruta | Qué devuelve |
|---|---|---|
| GET | `/api/health` | Estado de servicios, fallback, AOI, sols y bounds de la rejilla (siempre 200) |
| POST | `/api/ruta` | `{geojson, resumen, tramos, control_calidad, fuente}` — `fuente`: `ms6` \| `precalculada` |
| GET | `/api/capas/base` | FeatureCollection: puntos CheMin, traza Curiosity (en el AOI), origen Bradbury |
| GET | `/api/capas/raster/{banda}?cmap=viridis\|gray` | PNG RGBA de una banda; bounds en header `X-Bounds` |
| GET | `/api/modelos` | `modelos_por_suelo.json` |

Bandas: `pendiente_grados`, `rugosidad_m`, `fraccion_oscura`, `inercia_termica_tiu`, `albedo`, `distancia_duna_m`.

`POST /api/ruta` usa el request de MS6 (`lon, lat, material, sol, hora, vmax`). Errores 4xx de MS6 se reenvían tal cual.
Si MS6 no está configurado o falla (timeout/5xx), se usa la ruta precalculada **solo** para
`hematita|esmectitas|tridimita` con `sol=1360, hora=9, vmax=1000` y origen en Bradbury; en otro caso, `503`.

## Configuración (`CORE_*`)

Ver [`.env.example`](.env.example). Las rutas de datos y URLs nunca van hardcodeadas.

## Correr

```bash
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"   # Linux/macOS: .venv/bin/pip
.venv/Scripts/python -m pytest
CORE_MS6_URL=http://localhost:8006 .venv/Scripts/uvicorn app.main:app --port 8000   # sin MS6: omitir la variable
# http://localhost:8000/docs

# e2e contra un MS6 real (se salta si no defines la variable): levanta MS6 en :8006 y
CORE_E2E_MS6_URL=http://localhost:8006 .venv/Scripts/python -m pytest tests/api/test_e2e_ms6.py

# Stack completo (desde la raíz del repo; ver cabecera de docker-compose.yml para el catálogo de MS1)
docker compose up --build

# Docker (desde core/)
docker build -t core . && docker run --rm -p 8000:8000 -v "$(pwd)/../data:/data:ro" core
```

## Estructura

`app/routers/` endpoints · `app/clients/` HTTP hacia otros servicios · `app/datasources/` lectura de `data/gale/` ·
`app/settings.py` configuración y constantes (AOI, sols).
