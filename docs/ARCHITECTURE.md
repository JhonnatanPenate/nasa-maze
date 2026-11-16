# Planetary Explorer
### Propuesta de proyecto y arquitectura de software

**Versión:** 2.1 | **Fecha:** 2026-11-14 | **Estado:** Alineada con el paquete de datos `data/gale/` (handoff actual: `docs/data/HANDOFF_SOFTWARE.md` + `docs/data/SETUP_EQUIPO_SOFTWARE.md`)

> **Cambio clave en v2:** el equipo de datos entregó un **optimizador de rutas calibrado** (`optimizador_rutas.py`, minimiza una función objetivo de costo de misión), un raster multibanda de transitabilidad (`rejilla_ruta_90m.tif`, 6 bandas sobre el cráter Gale) y perfiles ambientales por hora (RAD/REMS). Los microservicios pasan de "construir la ciencia" a **envolver la ciencia existente en APIs** y añadir análisis ad-hoc que las rutas precalculadas no cubren.
>
> **v2.1:** la data aterrizó en `data/gale/{processed,raw}/`. **Todas las tablas son Excel (`.xlsx`) — no hay CSV** (leer con `openpyxl`/`pandas`). Nombres canónicos nuevos: `MapaMision`, `calcular_ruta_optima`, `minimizar_costo_ruta`, `tabla_tramos_ruta` (los antiguos `motor_rutas_adaptativo.py`/`marte_crs.py` quedan como wrappers). `data_usar/` queda **obsoleto**.

## 1. Descripción del proyecto

Planetary Explorer es una herramienta de navegación geoespacial inteligente que permite calcular rutas entre dos ubicaciones sobre la superficie de cuerpos celestes, inicialmente Marte o la Luna.

Inspirado en herramientas como Waze, el sistema permitirá buscar ubicaciones mediante nombres de referencia, seleccionar un origen y un destino, y obtener rutas optimizadas considerando las características físicas, geológicas y ambientales del terreno.

A diferencia de un navegador convencional, Planetary Explorer no se limita a encontrar el camino más corto, sino que evalúa las condiciones de transitabilidad y los posibles riesgos asociados al desplazamiento.

## 2. Funcionamiento general

El usuario introduce una ubicación de origen y otra de destino. El sistema convierte ambas referencias en coordenadas planetarias y consulta los conjuntos de datos geoespaciales disponibles localmente.

Posteriormente, analiza diferentes variables:

- **Geográficas:** elevación, pendientes, cráteres, formaciones rocosas y características del terreno.
- **Ambientales:** temperatura, radiación y otras condiciones que puedan afectar el desplazamiento.

Con esta información, el motor de navegación calcula rutas alternativas y presenta distancia, tiempo estimado, advertencias y riesgos relevantes.

El resultado será un mapa interactivo que permita identificar la ubicación, visualizar los trayectos y consultar información específica de cada ruta.

## 3. Arquitectura basada en microservicios

El proyecto se desarrollará utilizando una arquitectura de microservicios dentro de un único repositorio (Monorepo). Cada integrante será responsable de desarrollar un servicio independiente, con una responsabilidad específica y una API propia.

La arquitectura estará compuesta por seis microservicios y un componente central denominado **Core**, encargado de coordinar su comunicación.

| Componente | Responsabilidad | Fuente de datos principal (`data/gale/`) | Estado (2026-11) |
|---|---|---|---|
| **1. Location Service** | Buscar ubicaciones planetarias y convertir nombres en coordenadas. | `processed/gale_puntos_quimica.xlsx` (21 puntos CheMin), `raw/pe_msl_vectores.json` (waypoints Curiosity), Bradbury Landing como origen fijo. | ✅ `location-service/` |
| **2. Data Management Service** | Registrar, versionar y validar los datasets entregados por el equipo de datos (en el MVP los datos ya están locales; no hay descarga externa). | Todo `data/`; catálogo SQLite opcional. | 🚧 sin servicio dedicado (catálogos SQLite por servicio) |
| **3. Raster Service** | Administrar el acceso a archivos geoespaciales y proporcionar consultas sobre sus valores y bandas. | `processed/rejilla_ruta_90m.tif` (6 bandas; ver §4). | ✅ `raster-service/` (:8003) |
| **4. Terrain Analysis Service** | Analizar elevación, pendientes y características físicas del terreno (punto, perfil, área). | Banda 1 `pendiente_grados` del GeoTIFF + DEM de elevación *pendiente de entrega* (ver plan de realineación). | ✅ `terrain-analysis/` (:8004) |
| **5. Risk Assessment Service** | Evaluar riesgos ambientales y geográficos (pendiente, rugosidad, dunas, térmico, radiación) sobre un tramo o punto. | Bandas del GeoTIFF + `raw/ambiental/rad_dosis_observaciones.xlsx` + `raw/ambiental/rems_resumen_horario.xlsx`. | ✅ `risk-assessment/` (:8005 — SPEC + extensiones; handoff en `docs/risk-assessment/HANDOFF_ROUTING_CORE.md`; corrida docker pendiente) |
| **6. Routing Engine** | Calcular y optimizar rutas; **envuelve el optimizador existente** (`MapaMision`, `calcular_ruta_optima`, `tabla_tramos_ruta`) sin reescribir la función objetivo. | `optimizador_rutas.py` (canónico; pendiente de incluirse en el repo) + `processed/modelos_por_suelo.json` + rejilla + RAD/REMS. | ✅ `routing-engine/` (:8006) |
| **Core** | Recibir solicitudes, coordinar los microservicios e integrar sus resultados para entregarlos al usuario. | Orquesta todo lo anterior; entrega GeoJSON + tramos + KPIs al frontend (formato de respuesta: `docs/data/EJEMPLO_API_RESPUESTA.json`). | 🚧 Core sin implementar aún; frontend en `nasa-maze-app/` ✅ (docker/e2e por verificar) |

Cada microservicio tendrá independencia lógica y podrá desarrollarse, ejecutarse y probarse individualmente. La comunicación entre ellos se realizará principalmente mediante APIs REST.

**Regla de oro (v2):** el optimizador científico se **importa, no se reescribe**. Si la organización de archivos del paquete de datos cambia, solo se actualiza la capa de acceso a datos (datasource/config) de cada servicio — nunca el dominio ni los contratos de API. **Las rutas a datasets se resuelven por configuración** (variables de entorno), nunca hardcodeadas — la reorganización ya ocurrió una vez (`data_usar/` → `data/gale/`) y puede repetir.

## 4. Gestión y disponibilidad de los datos

**Fuente de verdad del MVP:** el paquete `data/gale/` entregado por el equipo de datos (cfr. `docs/data/HANDOFF_SOFTWARE.md` y `docs/data/SETUP_EQUIPO_SOFTWARE.md`). Datos originales provienen de fuentes oficiales (NASA/USGS: MSL/Curiosity, RAD, REMS, CheMin) ya procesados y calibrados.

**Formato tabular:** **Excel únicamente** (`.xlsx`/`xlsm`; leer con `pandas.read_excel`/`openpyxl`). El paquete **no incluye CSV**. Servicios que consumen tablas (MS1, MS5, MS6, Core) deben añadir `openpyxl` a sus dependencias.

**CRS obligatorio:** `IAU_2015:49900` (esfera marciana, R = 3 396 190 m; 59 274.69 m/grado). No usar EPSG:4326/3857 para distancias. Todos los servicios deben usar `planet_radius_km = 3396.19`.

**AOI del MVP:** cráter Gale, bounds `[137.345, -4.740, 137.455, -4.580]` (min_lon, min_lat, max_lon, max_lat). Origen por defecto: Bradbury Landing `(lon=137.4416, lat=-4.5895)`.

**Raster principal** — `processed/rejilla_ruta_90m.tif`, 72×105 celdas, 6 bandas:

| # | Banda | Consumidor principal |
|---|---|---|
| 1 | `pendiente_grados` | MS4 (pendiente pre-calculada), MS5, MS6 |
| 2 | `rugosidad_m` | MS5, MS6 |
| 3 | `fraccion_oscura` | MS5 (proxy de arena/dunas), MS6 |
| 4 | `inercia_termica_tiu` | MS5, MS6 |
| 5 | `albedo` | MS5, capas de mapa |
| 6 | `distancia_duna_m` | MS5 (riesgo Bagnold), MS6 |

> ⚠️ El raster **no incluye banda de elevación**. La pendiente ya viene calculada por el equipo de datos; el DEM fuente está pendiente de entrega. MS4 debe poder operar leyendo la banda de pendiente directamente (ver `docs/terrain_analysis/REALIGNMENT_PLANMS4_1.md`).

**Rutas precalculadas** (hematita→Oudam, esmectitas→Glen Etive, tridimita→Buckskin) disponibles como `ruta_*.geojson` + `ruta_*_tramos.xlsx` + `ruta_*_resumen.json` bajo `data/gale/processed/` — útiles para demo offline y como fixtures de referencia. Sus columnas de tramos (17) incluyen `tipo_suelo`, `modelo_usado`, `dosis_acumulada_uGy`, `temp_suelo_K`, horas LMST inicio/fin.

**Función objetivo del optimizador** (referencia para MS5/MS6): `min g = Σ c_ij`, con `c_ij = tiempo·(1+incertidumbre) + espera_nocturna + cambio_de_suelo + radiación + estrés_térmico + (1−interés_mineral)·distancia`. Pesos canónicos en `optimizador_rutas.py` (`PESO_*`, `PENALIZACION_CAMBIO_SUELO`).

Los datos se organizan en almacenamiento local compartido. El Raster Service es el punto de acceso común a la información geoespacial, evitando que cada microservicio duplique archivos.

Los servicios de análisis podrán generar nuevas capas derivadas, que también quedarán disponibles localmente. La consulta, el análisis y el cálculo de rutas funcionan **sin conexión** una vez presente el paquete de datos.

## 5. Tecnologías y organización

Se propone utilizar Python y FastAPI para desarrollar los microservicios, Rasterio/GDAL para el procesamiento geoespacial, SQLite para el catálogo de datasets y Docker Compose para ejecutar e integrar los componentes.

El repositorio único contendrá los seis microservicios, el Core, los paquetes compartidos, la configuración de infraestructura y la documentación técnica.

## 6. Alcance inicial

El MVP se enfocará en un único cuerpo celeste y una región geográfica delimitada. Deberá demostrar la búsqueda de ubicaciones, consulta de datos offline, análisis topográfico, evaluación básica de riesgos y generación de rutas alternativas.

El objetivo principal es construir una plataforma modular y extensible que demuestre la viabilidad de la navegación inteligente sobre superficies planetarias, dejando abierta la incorporación de nuevas variables, fuentes científicas y cuerpos celestes en futuras versiones.

---

**Principio del proyecto:** transformar datos científicos geoespaciales en información útil para tomar decisiones de navegación sobre superficies extraterrestres.

For more information: [Chat GPT Conversation GPT-4](https://chatgpt.com/share/6af895f4-de94-83e8-9d60-52998ca71e0e)