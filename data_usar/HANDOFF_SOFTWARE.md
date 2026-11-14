# Planetary Explorer — Handoff para equipo de software

Paquete de datos y lógica científica listo para construir **API + interfaz**.  
CRS obligatorio: **`IAU_2015:49900`** (esfera marciana R = 3 396 190 m).  
Escala: **59 274.69 m/grado**. No usar EPSG:4326/3857 para distancias.

Origen de misión por defecto: **Bradbury Landing** `(lon=137.4416, lat=-4.5895)`.  
Bounds del AOI: `[137.345, -4.740, 137.455, -4.580]`.

---

## Mapa de la carpeta

```
data_usar/
├── HANDOFF_SOFTWARE.md          ← este documento
├── LEEME.txt
├── processed/                   ← salidas listas para API / UI / Excel
├── raw/                         ← insumos ambientales e históricos
└── scripts/                     ← motor científico (importar, no reescribir)
```

---

## 1. `processed/` — lo que consume la API y la UI

| Archivo | Ubicación | Qué es | Uso sugerido en software |
|---|---|---|---|
| `Bitacora_Calidad_Marte.xlsx` | `processed/` | Libro consolidado (4 hojas) | Endpoint de auditoría / descarga de reporte |
| `gale_matriz_calibracion.csv` | `processed/` | 851 waypoints calibrados (tilt, pendiente, rugosidad, albedo, RAD, REMS, riesgo) | Dataset de entrenamiento / tablas de telemetría |
| `gale_puntos_quimica.csv` | `processed/` | 21 puntos CheMin (minerales %) | Capa de objetivos científicos + selector de mineral |
| `modelos_por_suelo.json` | `processed/` | Coeficientes β, R², σ, p-valores, VIF, supuestos por suelo | `GET /api/modelos` / panel de auditoría estadística |
| `rejilla_ruta_90m.tif` | `processed/` | Raster 6 bandas, 72×105 celdas | Capas de mapa (pendiente, rugosidad, dunas, etc.) |
| `mapa_rutas_gale.png` | `processed/` | Preview de las 3 rutas | Imagen estática / README / demo |
| `_rejilla_suelo_tilt.npy` | `processed/` | Array auxiliar suelo/tilt/bloqueo | Cache interno del motor (opcional) |

### Bandas del GeoTIFF (`rejilla_ruta_90m.tif`)
1. `pendiente_grados`  
2. `rugosidad_m`  
3. `fraccion_oscura`  
4. `inercia_termica_tiu`  
5. `albedo`  
6. `distancia_duna_m`

### Rutas precalculadas (3 objetivos)

| Prefijo | Objetivo | Mineral | Archivos |
|---|---|---|---|
| `ruta_hematita_*` | Oudam | hematita | `.geojson` + `_tramos.csv` + `_resumen.json` |
| `ruta_esmectitas_*` | Glen Etive | esmectitas | `.geojson` + `_tramos.csv` + `_resumen.json` |
| `ruta_tridimita_*` | Buckskin | tridimita (sílice) | `.geojson` + `_tramos.csv` + `_resumen.json` |

- **`.geojson`** → geometría para MapLibre/Leaflet/QGIS  
- **`_tramos.csv`** → tabla tramo a tramo (distancia, tilt, dosis μGy, T suelo, tipo de suelo)  
- **`_resumen.json`** → KPIs (km, llegada LMST, dosis, espera nocturna, Bagnold)

---

## 2. `processed/Bitacora_Calidad_Marte.xlsx` — hojas

| Hoja | Contenido |
|---|---|
| `Auditoria_Estadistica` | n, método (OLS/GLS), R² aj., σ, p-valores de supuestos, VIF |
| `Pesos_Calibrados` | coeficientes β + parámetros operativos |
| `Catalogo_Minerales` | mismos puntos que `gale_puntos_quimica.csv` |
| `Rutas_Simuladas` | resumen tramo a tramo de las 3 rutas |

---

## 3. `raw/` — datos de entrada ambiental / históricos

| Archivo | Ubicación | Qué es | Uso sugerido |
|---|---|---|---|
| `pe_msl_vectores.json` | `raw/` | Traza Curiosity (`MSL_traverse`, `MSL_waypoints`) | Capa histórica en el mapa |
| `rad_dosis_observaciones.csv` | `raw/ambiental/` | Dosis RAD por sol/hora (μGy/h) | Perfil horario de radiación |
| `rems_resumen_horario.csv` | `raw/ambiental/` | Temp. suelo/aire, presión, UV por hora LMST | Perfil térmico REMS |

Sols de referencia típicos: `1360`, `2140`, `3290`, `4710`.

---

## 4. `scripts/` — lógica científica (backend)

| Archivo | Ubicación | Qué hace | Cómo integrarlo |
|---|---|---|---|
| `marte_crs.py` | `scripts/` | Define CRS marciano y `METROS_POR_GRADO` | Importar siempre para distancias/pendientes |
| `modelos_adaptativos_suelo.R` | `scripts/` | Ajusta regresiones por tipo de suelo → escribe `modelos_por_suelo.json` | Solo re-ejecutar si cambian datos de calibración |
| `motor_rutas_adaptativo.py` | `scripts/` | Clases/funciones A*: `Entorno`, `a_estrella`, `tramos`, `calcular_ruta` | **Importar desde FastAPI**; no reescribir la física |

### Funciones clave del motor
```text
Entorno(datos, sol_ref)
a_estrella(env, origen, destino, hora_inicio, I, usar_suelo=True)
tramos(env, ruta)
calcular_ruta(env, lon, lat, material, hora)
```

Materiales válidos: `hematita` | `esmectitas` | `tridimita` | `sulfatos`.

---

## 5. Dónde se agrega o quita data

| Acción | Archivo a editar |
|---|---|
| Sumar/quitar waypoints de calibración | `processed/gale_matriz_calibracion.csv` |
| Sumar/quitar objetivos minerales | `processed/gale_puntos_quimica.csv` |
| Cambiar perfiles RAD | `raw/ambiental/rad_dosis_observaciones.csv` |
| Cambiar perfiles REMS | `raw/ambiental/rems_resumen_horario.csv` |
| Actualizar traza Curiosity | `raw/pe_msl_vectores.json` |

Tras editar entradas científicas, regenerar:
```bat
Rscript scripts\modelos_adaptativos_suelo.R .
python scripts\motor_rutas_adaptativo.py --datos . --batch
```
(Ajustar `--datos` a la raíz que contenga `processed/` y `raw/`.)

No editar a mano: `modelos_por_suelo.json`, GeoJSON de rutas, Excel ni PNG (se regeneran).

---

## 6. Contratos sugeridos para la API

| Endpoint | Fuente de datos |
|---|---|
| `GET /api/health` | bounds + sols + QC de `rejilla_ruta_90m.tif` |
| `GET /api/capas/base` | dunas (raster/`distancia_duna_m`), CheMin CSV, `pe_msl_vectores.json` |
| `GET /api/capas/raster/{banda}` | `rejilla_ruta_90m.tif` |
| `GET /api/modelos` | `modelos_por_suelo.json` |
| `POST /api/ruta` | llama `calcular_ruta` / `a_estrella` del motor |

Body sugerido de `POST /api/ruta`:
```json
{
  "lon": 137.4416,
  "lat": -4.5895,
  "material": "hematita",
  "sol": 1360,
  "hora": 9,
  "vmax": 1000
}
```

---

## 7. Resultados de referencia (sol=1360, hora=9, Bradbury)

| Material | Objetivo | Distancia | Dosis RAD |
|---|---|---|---|
| hematita | Oudam | 7.73 km | 247.8 μGy |
| esmectitas | Glen Etive | 10.3 km | 289.7 μGy |
| tridimita | Buckskin | 6.71 km | 85.1 μGy |

La ruta a esmectitas evita Bagnold Dunes frente al modelo global (ahorro ~8.4 h en arena).

---

## 8. Stack recomendado (alineado al proyecto)

- **Backend:** FastAPI + Uvicorn, importando `scripts/motor_rutas_adaptativo.py`
- **Frontend:** React + MapLibre (proyección plana sobre bounds de Gale, sin tiles terrestres)
- **Dependencias Python clave:** `numpy`, `pandas`, `rasterio`, `scipy`, `openpyxl`

---

## Contacto de datos

Todo el contenido de esta carpeta es el paquete operativo para el MVP.  
La fuente de verdad tabular para demo/auditoría es `processed/Bitacora_Calidad_Marte.xlsx`.  
La fuente de verdad para navegación en vivo es el motor en `scripts/motor_rutas_adaptativo.py` + `processed/modelos_por_suelo.json` + `processed/rejilla_ruta_90m.tif`.
