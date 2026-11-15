# Core (Orquestador) — Plan de implementación

**Versión:** 1.0.0 | **Estado:** Propuesto | **Fecha:** 2026-11-15
**Contexto del sistema:** [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) v2.1
**Contrato de respuesta:** [`docs/data/EJEMPLO_API_RESPUESTA.json`](../data/EJEMPLO_API_RESPUESTA.json)
**API sugerida por datos:** [`docs/data/HANDOFF_SOFTWARE.md`](../data/HANDOFF_SOFTWARE.md) §"API sugerida"

---

## 1. Contexto y rol del Core

El Core es el **único punto de entrada del frontend**. Su trabajo es orquestar: recibe solicitudes, llama a los microservicios configurados, integra resultados y entrega al frontend GeoJSON + tramos + KPIs en el formato de `EJEMPLO_API_RESPUESTA.json`.

**Lo que el Core NO hace** (regla de oro v2, igual que en MS6):

- No calcula ciencia. La función objetivo vive en `science/optimizador_rutas.py`, envuelta por MS6.
- No duplica datasets. Los lee del paquete compartido `data/gale/` o los proxea por HTTP.
- No reescribe contratos de otros servicios. Si MS6 cambia, se toca el cliente del Core, no el dominio.

**Dato clave para el alcance:** MS5 (Risk) y MS3 (Raster) **no existen**. MS1 y MS6 existen solo en ramas (`feature/location-service`, `feature/ms6-routing-engine`). El Core debe funcionar **con lo que hay hoy**: MS6 (si está levantado) + lectura local de `data/gale/` como respaldo. Degradación elegante es requisito, no lujo — en el demo no puede haber un servicio caído que tumbe todo.

## 2. Alcance

### 2.1 Objetivos (in scope)

| # | Objetivo |
|---|------|
| G1 | `GET /api/health` — estado del Core + ping de servicios configurados + bounds del AOI |
| G2 | `POST /api/ruta` — proxy a MS6 `POST /route`; fallback a rutas precalculadas; respuesta en formato del contrato |
| G3 | `GET /api/capas/base` — FeatureCollection GeoJSON: puntos CheMin, traza Curiosity, origen Bradbury |
| G4 | `GET /api/capas/raster/{banda}` — banda de `rejilla_ruta_90m.tif` como PNG + bounds (overlay del mapa) |
| G5 | `GET /api/modelos` — `modelos_por_suelo.json` tal cual |
| G6 | Config por env vars (`CORE_*`): rutas de datos y URLs de servicios **nunca hardcodeadas** |
| G7 | Dockerfile + tests (mínimo 3 por feature: happy / edge / expected-failure) |

### 2.2 Fuera de alcance (este MVP)

- Orquestación de MS5/MS3 (no existen). Si aparecen, se agregan como clientes nuevos sin tocar lo anterior.
- Llamadas a MS4 (la respuesta de ruta ya trae pendiente por tramo; MS4 queda para enriquecimiento futuro, p.ej. perfil bajo demanda).
- Búsqueda de lugares vía MS1 (origen fijo en Bradbury para el MVP; `capas/base` ya da los objetivos).
- Auth, rate limiting, websockets, caché distribuida, docker-compose multi-servicio, frontend.

## 3. Arquitectura

### 3.1 Estilo

A diferencia de MS4 (Clean Architecture completa), el Core **no tiene dominio propio**: es I/O — leer archivos y llamar HTTP. Se adopta una estructura **plana por responsabilidad** (ponytail: la más simple que funcione):

```
routers ──▶ clients (HTTP a servicios)      ──▶ respuesta al frontend
        ──▶ datasources (archivos data/gale) ──┘
```

Reglas:

- Los `clients` devuelven el JSON del servicio **sin transformarlo** (salvo añadir `fuente`).
- Los `datasources` convierten `data/gale/` → DTOs de respuesta en el borde; ningún tipo crudo de rasterio/pandas sale por la API.
- El fallback de ruta se decide en un solo lugar (`datasources/precalculated_routes.py`).

### 3.2 Árbol de directorios (raíz del servicio: `core/`)

```
core/
├── README.md                          # setup, run, endpoints
├── pyproject.toml
├── Dockerfile
├── .env.example
├── app/
│   ├── __init__.py
│   ├── main.py                        # create_app: routers + CORS + handlers
│   ├── settings.py                    # Settings (pydantic-settings), prefix CORE_
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── routing_client.py          # httpx → MS6 POST /route + GET /health
│   │   └── service_registry.py        # URLs configuradas + ping() por servicio
│   ├── datasources/
│   │   ├── __init__.py
│   │   ├── base_layers.py             # xlsx/json → features GeoJSON (CheMin, traza MSL, Bradbury)
│   │   ├── raster_layers.py           # banda de rejilla → PNG + bounds
│   │   ├── precalculated_routes.py    # ruta_*.geojson + tramos.xlsx + resumen.json → contrato
│   │   └── soil_models.py             # modelos_por_suelo.json → dict
│   └── routers/
│       ├── __init__.py
│       ├── health.py                  # GET /api/health
│       ├── routes.py                  # POST /api/ruta
│       ├── layers.py                  # GET /api/capas/base, /api/capas/raster/{banda}
│       └── models.py                  # GET /api/modelos
└── tests/
    ├── __init__.py
    ├── conftest.py                    # TestClient + httpx MockTransport + data/gale real
    ├── api/
    │   ├── test_health.py
    │   ├── test_ruta.py
    │   └── test_layers_models.py
    └── unit/
        ├── test_base_layers.py
        ├── test_raster_layers.py
        └── test_precalculated_routes.py
```

- Un archivo por responsabilidad, nombres `snake_case`.
- `__init__.py` vacíos (sin barrels), igual que MS4.
- `data/` y `science/` se montan por volumen/env var; el servicio no los copia.

## 4. Especificación de features

### F1 — `GET /api/health`

- `200` siempre: `{"status": "ok"|"degraded", "servicios": {"ms6": "ok"|"down"|"no_configurado", ...}, "aoi": [137.345,-4.740,137.455,-4.580], "sols": [1360,2140,3290,4710], "bounds_rejilla": {...}}`.
- `status="ok"` si al menos un backend de ruta está disponible (MS6 `ok` **o** fallback precalculado habilitado con los 3 archivos presentes); `"degraded"` en caso contrario.
- Ping con timeout corto (`CORE_HEALTH_TIMEOUT_S`, default 2 s); un servicio caído no tumba el health.

### F2 — `POST /api/ruta`

Request **idéntico al de MS6** (mismos nombres de campo — el frontend no distingue capas):

```json
{"lon": 137.4416, "lat": -4.5895, "material": "hematita", "sol": 1360, "hora": 9.0, "vmax": 1000}
```

`material`: `hematita | esmectitas | tridimita | sulfatos` (Literal; `sulfatos` solo vía MS6 — no hay ruta precalculada).

Flujo:

1. Validación Pydantic (422 si mal formado).
2. Si `CORE_MS6_URL` configurado → `routing_client.post_route()`. Respuesta `2xx` → passthrough + `"fuente": "ms6"`. Error 4xx de MS6 (sol inválido, fuera de AOI, sin ruta) → **se reenvía tal cual** (mismo status + detail).
3. MS6 no configurado / timeout / 5xx → fallback precalculado si `material ∈ {hematita, esmectitas, tridimita}` **y** `sol == 1360`, `hora == 9`, `vmax == 1000` **y** origen ≈ Bradbury (tolerancia 1 celda ≈ 0.0015°; los precálculos solo valen para esa solicitud de referencia); respuesta armada desde `ruta_{material}.geojson` + `ruta_{material}_tramos.xlsx` + `ruta_{material}_resumen.json` + `"fuente": "precalculada"`.
4. Si ninguna vía aplica → `503 {"detail": "sin backend de ruta disponible para esta solicitud"}`.

Respuesta (contrato `EJEMPLO_API_RESPUESTA.json`): `{geojson, resumen, tramos, control_calidad, fuente}`.

- El `resumen` del fallback se normaliza a las mismas claves que MS6 (`distancia_km`, `hora_llegada`, `dosis_rad_acum_uGy`, `horas_espera_nocturna`, `costo_objetivo`, `nodos_expandidos`, `objetivo`, `material`, `comparativa_bagnold`) desde `resumen.json` (que trae alias `llegada_lmst`, `dosis_uGy`, … y `comparativa_dunas`).
- En fallback `control_calidad` sale de `ruta_*_resumen.json`; el GeoJSON precalculado se normaliza al de MS6 (se descarta `ruta_optima_completa`; se agregan `objetivo` y `origen` desde los extremos de la ruta). El frontend puede mostrar el badge "datos precalculados" vía `fuente`.
- Endpoint real de MS6: `POST {CORE_MS6_URL}/route` (el prefijo `/api/ruta` es solo del Core).
- Timeout MS6 configurable (`CORE_ROUTE_TIMEOUT_S`, default 120 — el A* expande ~30k nodos).

### F3 — `GET /api/capas/base`

- `200`: FeatureCollection `IAU_2015:49900` con:
  - `capa: "puntos_quimica"` — un Point por fila de `gale_puntos_quimica.xlsx` (21 puntos CheMin, properties = columnas del Excel, incl. `material` objetivo).
  - `capa: "traza_msl"` — LineString desde `raw/pe_msl_vectores.json` (traza histórica Curiosity).
  - `capa: "origen"` — Point Bradbury `(137.4416, -4.5895)`.
- Dunas: **no** se poligonizan; se exponen como banda raster (`distancia_duna_m` / `fraccion_oscura` vía F4). Decisión documentada: menos código, mismo resultado visual.
- Archivos pequeños: se leen una vez (lazy singleton); fallo de lectura → `502`.

### F4 — `GET /api/capas/raster/{banda}`

- `banda` ∈ whitelist canónica: `pendiente_grados | rugosidad_m | fraccion_oscura | inercia_termica_tiu | albedo | distancia_duna_m` → bandas 1–6 de `processed/rejilla_ruta_90m.tif`. Nombre inválido → `422`.
- `200`: `image/png` (banda normalizada a 0–255, nodata → alfa 0). Bounds en header `X-Bounds: "min_lon,min_lat,max_lon,max_lat"` (también disponibles vía F1).
- Query `?cmap=gray|viridis` opcional (default `viridis`); colormap simple vía Pillow/matplotlib — sin tiles ni pirámides en el MVP (la rejilla es 72×105, un PNG basta).

### F5 — `GET /api/modelos`

- `200`: contenido de `processed/modelos_por_suelo.json` tal cual (β, R², σ por tipo de suelo — el frontend lo usa para la ficha de cada tramo).

## 5. Configuración (`app/settings.py`)

`Settings(BaseSettings)`, prefijo `CORE_`:

| Campo | Default | Propósito |
|---|---|---|
| `data_dir` | `data/gale` (relativo a raíz del repo) | paquete de datos compartido |
| `ms6_url` | `""` | base URL del Routing Engine; vacío = solo fallback |
| `ms4_url` / `ms1_url` | `""` | solo para ping en health (reservado orquestación futura) |
| `route_timeout_s` | `120.0` | timeout del POST a MS6 |
| `health_timeout_s` | `2.0` | timeout de pings |
| `precalc_fallback` | `true` | habilita servir rutas precalculadas |
| `bradbury_lon` / `bradbury_lat` | `137.4416` / `-4.5895` | origen fijo del MVP |

## 6. Dependencias (`pyproject.toml`)

- Runtime: `fastapi`, `uvicorn[standard]`, `pydantic-settings`, `httpx`, `pandas`, `openpyxl`, `rasterio`, `pillow`.
- Dev: `pytest`, `respx` (o `httpx.MockTransport`) para simular MS6.
- Versiones mínimas pineadas, sin rangos abiertos (misma política que MS4).
- Instalación: `pip install -e ".[dev]"` desde `core/`.

## 7. Matriz de tests (mínimo 3 por feature)

| Target | Happy | Edge | Expected failure |
|---|---|---|---|
| `POST /api/ruta` | MS6 mockeado → passthrough `200` + `fuente:"ms6"` | MS6 devuelve 400/404 → se reenvía igual | MS6 down + request no elegible → `503` |
| Fallback precalculado | material=hematita, sol=1360, origen Bradbury → `200` + `fuente:"precalculada"` | origen desplazado >1 celda → no aplica | `material="sulfatos"` sin MS6 → `503` |
| `GET /api/capas/base` | FeatureCollection con 21 CheMin + traza + origen | properties preservan columnas del xlsx | xlsx ilegible → `502` |
| `GET /api/capas/raster/{banda}` | PNG válido + header `X-Bounds` | banda 6 (distancia_duna) renderiza | banda inexistente → `422` |
| `GET /api/modelos` | JSON con 4 tipos de suelo | — | archivo faltante → `502` |
| `GET /api/health` | MS6 ok → `status:"ok"` | MS6 down + fallback on → `"ok"`; todo down → `"degraded"` (siempre 200) | — |

`conftest.py`: `TestClient`, `httpx.MockTransport` para clientes, y `data/gale` real del repo (ya está en disco; no se commitean fixtures binarios nuevos).

## 8. Paquetes de trabajo (WPs)

```
WP0 → WP1 → ┬─ WP2 (capas + modelos)  → WP4 → WP5
            └─ WP3 (ruta/orquestación)
```

> **Estado (2026-11-15):** WP0–WP4 implementados en `feature/Core` (23 tests verdes, Dockerfile incluido, imagen sin construir aún). Pendiente: WP5 review y prueba e2e contra MS6 real cuando se mergee. Desviación del árbol: `app/routers/deps.py` (inyección de transporte para tests).

| WP | Alcance | Archivos | Aceptación |
|---|---|---|---|
| **WP0 Bootstrap** | skeleton + settings | `pyproject.toml`, `app/settings.py`, dirs + `__init__.py`, `tests/conftest.py`, `.env.example` | `pip install -e ".[dev]"` ok; `Settings` importa |
| **WP1 Datasources** | lectura de `data/gale/` | `datasources/*.py` + unit tests | xlsx→features, banda→PNG, precalc→contrato; tests verdes contra datos reales |
| **WP2 Capas + modelos** | F3, F4, F5 | `routers/layers.py`, `routers/models.py` + tests api | 3 endpoints responden contrato; errores mapeados |
| **WP3 Ruta** | F2 + cliente MS6 + fallback | `clients/routing_client.py`, `clients/service_registry.py`, `routers/routes.py` + tests | passthrough, reenvío de errores, fallback y 503 verdes con MS6 mockeado |
| **WP4 Wiring** | F1 + app + Docker | `routers/health.py`, `app/main.py` (CORS `*`), `Dockerfile`, `README.md` | `uvicorn app.main:app` sirve todo; `/api/health` agrega pings; imagen construye |
| **WP5 Review** | DoD | fixes de review, README completo | checklist §9 completo |

WP2 y WP3 son disjuntos → pueden correr en paralelo tras WP1.

## 9. Definition of Done

- [ ] `pytest` verde completo desde `core/`
- [ ] `POST /api/ruta` responde el contrato de `EJEMPLO_API_RESPUESTA.json` tanto vía MS6 como vía fallback
- [ ] Frontend puede levantar un mapa con solo: `capas/base` + `capas/raster/{banda}` + `ruta`
- [ ] Ninguna ruta de datos ni URL hardcodeada (todo por `CORE_*` env vars)
- [ ] Servicio levanta **aunque MS6/MS4/MS1 estén caídos** (degraded ≠ down)
- [ ] `README.md` con run local + Docker + tabla de endpoints

## 10. Notas de integración

- **Puerto sugerido:** `8000` (MS4=8004; MS6 expone `/route` y `/health`).
- **MS6 no está mergeado:** para e2e local, levantarlo desde `origin/feature/ms6-routing-engine` (`uvicorn app.main:app` en `routing-engine/` con `MS6_DATA_DIR` apuntando a `data/gale`) o correr Core solo con fallback.
- **CRS:** todo es passthrough `IAU_2015:49900`; el Core no transforma coordenadas.
- **CORS abierto** (`*`) — el frontend es local/file para el hackathon.
