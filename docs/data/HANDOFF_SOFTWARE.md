# Planetary Explorer — Handoff software

Esta guía coincide **1:1** con el contenido de `data_usar/`.

**Idea clave:** no hay un “motor misterioso”. Hay un **optimizador de rutas** que **minimiza una función objetivo de costo de misión** (horas equivalentes).

```text
min g = Σ c_ij

c_ij = tiempo·(1 + incertidumbre)
     + espera_nocturna
     + cambio_de_suelo
     + radiación
     + estrés_térmico
     + (1 − interés_mineral)·distancia
```

**CRS:** `IAU_2015:49900` · **59 274.69 m/grado**  
**Origen default:** Bradbury `(137.4416, -4.5895)`  
**AOI:** `[137.345, -4.740, 137.455, -4.580]`

---

## Estructura

```
data_usar/
├── LEEME.txt
├── 01_datos_entrada/          ← SOLO datos de entrada
├── 02_optimizacion_rutas/     ← código que calcula / minimiza el costo
├── 03_salidas/                ← resultados listos para API/UI
└── 04_documentacion/          ← este manual
```

| Carpeta | Pregunta |
|---|---|
| `01_datos_entrada` | ¿Con qué información se alimenta? |
| `02_optimizacion_rutas` | ¿Dónde está el código de la función objetivo? |
| `03_salidas` | ¿Qué resultados ya existen? |
| `04_documentacion` | ¿Cómo lo integro? |

---

## 01_datos_entrada — información

### `observaciones/`
| Archivo | Qué es |
|---|---|
| `pe_msl_vectores.json` | Traza histórica Curiosity |
| `ambiental/rad_dosis_observaciones.xlsx` | Dosis RAD (μGy/h) por sol/hora |
| `ambiental/rems_resumen_horario.xlsx` | Temperatura / presión / UV REMS |

### `calibracion/`
| Archivo | Qué es |
|---|---|
| `gale_matriz_calibracion.xlsx` | 851 waypoints (tilt real + predictores) |
| `gale_puntos_quimica.xlsx` | 21 objetivos CheMin (minerales %) |

> **Fuente canónica = Excel (`.xlsx` / `.xlsm`)** — una columna por campo.  
> R (`readxl`) y Python (`_leer_tabla` / `openpyxl`) leen Excel directamente. **Este paquete no trae CSV.**  
> Extensiones aceptadas: `.xlsx`, `.xlsm`, `.xls` (y CSV solo si alguien lo agrega después).

### `mapa_raster/`
| Archivo | Qué es |
|---|---|
| `rejilla_ruta_90m.tif` | Raster 6 bandas del corredor Gale |

**Aquí se agregan/quitan datos de entrada.**

---

## 02_optimizacion_rutas — código (función objetivo)

| Archivo canónico | Rol |
|---|---|
| `optimizador_rutas.py` | Minimiza el costo de misión (A*). Lee `.xlsx`/`.xlsm` vía `_leer_tabla` (≥2 cols) |
| `modelos_inclinacion_por_suelo.R` | Ajusta inclinación desde Excel (`readxl`); exige `ncol ≥ 2` |
| `exportar_tablas_excel.py` | Valida/reformatea `.xlsx` (una columna por campo) |
| `crs_marte.py` | CRS marciano (`METROS_POR_GRADO`) |
| `construir_dataset_estadistico.py` | Arma la matriz de calibración |
| `preparar_datos_reales.py` | Prepara insumos |

Wrappers de compatibilidad (mismo comportamiento):
- `motor_rutas_adaptativo.py` → reexporta `optimizador_rutas.py`
- `modelos_adaptativos_suelo.R` → llama `modelos_inclinacion_por_suelo.R`
- `marte_crs.py` → igual a `crs_marte.py`

### Nombres que debe usar el equipo de software

| Concepto | Nombre en código |
|---|---|
| Mapa + modelos + RAD/REMS | `MapaMision` |
| Minimizar función objetivo | `minimizar_costo_ruta(...)` |
| Calcular misión completa | `calcular_ruta_optima(...)` |
| Tabla tramo a tramo | `tabla_tramos_ruta(...)` |
| Clasificar suelo | `clasificar_tipo_suelo(...)` |

Pesos de la función objetivo (en `optimizador_rutas.py`):
- `PESO_INCERTIDUMBRE_MODELO`
- `PESO_ESPERA_NOCTURNA`
- `PENALIZACION_CAMBIO_SUELO`
- `PESO_DOSIS_RADIACION`
- `PESO_ESTRES_TERMICO`
- `PESO_ATRACCION_CIENTIFICA`

---

## 03_salidas — resultados

### `modelos_inclinacion/`
| Archivo | Qué es |
|---|---|
| `modelos_por_suelo.json` | β, R², σ, p-valores, VIF por suelo |

### `rutas_optimas/`
| Subcarpeta | Objetivo | Archivos |
|---|---|---|
| `hematita/` | Oudam | geojson + tramos.xlsx + resumen.json |
| `esmectitas/` | Glen Etive | geojson + tramos.xlsx + resumen.json |
| `tridimita_buckskin/` | Buckskin | geojson + tramos.xlsx + resumen.json |

Columnas claras en `*_tramos.xlsx` (17 cols):
`tramo`, `hora_lmst_inicio`, `hora_lmst_fin`, `tipo_suelo`, `modelo_usado`, `r2_ajustado`, `distancia_m`, `pendiente_media_grados`, `inclinacion_media_grados`, `inclinacion_max_grados`, `dosis_tramo_uGy`, `dosis_acumulada_uGy`, `temp_suelo_K`, coordenadas.

### `reportes/`
| Archivo | Qué es |
|---|---|
| `Bitacora_Calidad_Marte.xlsx` | Libro consolidado |
| `mapa_rutas_gale.png` | Mapa de las 3 rutas |

Hojas del Excel (nombres lógicos):
1. `Auditoria_Modelos`
2. `Coeficientes_Objetivo` ← incluye pesos de la función objetivo
3. `Objetivos_Minerales`
4. `Rutas_Optimas`

### `auxiliares/`
| Archivo | Qué es |
|---|---|
| `_rejilla_suelo_tilt.npy` | Cache numérico del optimizador |

---

## Resultados de referencia (sol=1360, hora=9)

| Material | Objetivo | Distancia | Dosis |
|---|---|---:|---:|
| hematita | Oudam | 7.73 km | 247.8 μGy |
| esmectitas | Glen Etive | 10.3 km | 289.7 μGy |
| tridimita | Buckskin | 6.71 km | 85.1 μGy |

---

## API sugerida

| Endpoint | Fuente |
|---|---|
| `GET /api/health` | bounds del raster |
| `GET /api/capas/base` | CheMin + dunas + traza MSL |
| `GET /api/capas/raster/{banda}` | `01_datos_entrada/mapa_raster/rejilla_ruta_90m.tif` |
| `GET /api/modelos` | `03_salidas/modelos_inclinacion/modelos_por_suelo.json` |
| `POST /api/ruta` | `calcular_ruta_optima` en `optimizador_rutas.py` |

Request mínimo:

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

**Ejemplo real de request + response:** `EJEMPLO_API_RESPUESTA.json`  
**Setup / deps / CRS / canónicos:** `SETUP_EQUIPO_SOFTWARE.md`

---

## Dónde tocar qué

| Acción | Carpeta |
|---|---|
| Agregar/quitar datos | `01_datos_entrada/` |
| Cambiar función objetivo / A* | `02_optimizacion_rutas/optimizador_rutas.py` |
| Cambiar modelos estadísticos | `02_optimizacion_rutas/modelos_inclinacion_por_suelo.R` |
| Servir resultados sin recalcular | `03_salidas/` |

No editar a mano `03_salidas/` (se regenera desde datos + optimización).

---

## Inventario 1:1 (verificado)

```
LEEME.txt
01_datos_entrada/LEEME.txt
01_datos_entrada/observaciones/pe_msl_vectores.json
01_datos_entrada/observaciones/ambiental/rad_dosis_observaciones.xlsx
01_datos_entrada/observaciones/ambiental/rems_resumen_horario.xlsx
01_datos_entrada/calibracion/LEEME.txt
01_datos_entrada/calibracion/gale_matriz_calibracion.xlsx
01_datos_entrada/calibracion/gale_puntos_quimica.xlsx
01_datos_entrada/mapa_raster/rejilla_ruta_90m.tif

02_optimizacion_rutas/LEEME.txt
02_optimizacion_rutas/optimizador_rutas.py
02_optimizacion_rutas/modelos_inclinacion_por_suelo.R
02_optimizacion_rutas/exportar_tablas_excel.py
02_optimizacion_rutas/crs_marte.py
02_optimizacion_rutas/marte_crs.py
02_optimizacion_rutas/motor_rutas_adaptativo.py
02_optimizacion_rutas/modelos_adaptativos_suelo.R
02_optimizacion_rutas/construir_dataset_estadistico.py
02_optimizacion_rutas/preparar_datos_reales.py

03_salidas/LEEME.txt
03_salidas/modelos_inclinacion/modelos_por_suelo.json
03_salidas/rutas_optimas/hematita/ruta_hematita.geojson
03_salidas/rutas_optimas/hematita/ruta_hematita_tramos.xlsx
03_salidas/rutas_optimas/hematita/ruta_hematita_resumen.json
03_salidas/rutas_optimas/esmectitas/ruta_esmectitas.geojson
03_salidas/rutas_optimas/esmectitas/ruta_esmectitas_tramos.xlsx
03_salidas/rutas_optimas/esmectitas/ruta_esmectitas_resumen.json
03_salidas/rutas_optimas/tridimita_buckskin/ruta_tridimita.geojson
03_salidas/rutas_optimas/tridimita_buckskin/ruta_tridimita_tramos.xlsx
03_salidas/rutas_optimas/tridimita_buckskin/ruta_tridimita_resumen.json
03_salidas/reportes/Bitacora_Calidad_Marte.xlsx
03_salidas/reportes/mapa_rutas_gale.png
03_salidas/auxiliares/_rejilla_suelo_tilt.npy

04_documentacion/HANDOFF_SOFTWARE.md
04_documentacion/SETUP_EQUIPO_SOFTWARE.md
04_documentacion/EJEMPLO_API_RESPUESTA.json
```
