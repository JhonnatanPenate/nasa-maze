# Setup rápido — equipo de software

## 1. Archivos canónicos (usar estos)

| Rol | Archivo |
|---|---|
| Optimizador (función objetivo) | `02_optimizacion_rutas/optimizador_rutas.py` |
| Modelos de inclinación | `02_optimizacion_rutas/modelos_inclinacion_por_suelo.R` |
| CRS marciano | `02_optimizacion_rutas/crs_marte.py` |

Los archivos `motor_rutas_adaptativo.py`, `modelos_adaptativos_suelo.R` y `marte_crs.py` son **wrappers de compatibilidad**. No reinventar lógica ahí.

## 2. Dependencias

Python:

```text
numpy
pandas
rasterio
scipy
openpyxl
matplotlib
fastapi
uvicorn
```

```bat
pip install numpy pandas rasterio scipy openpyxl matplotlib fastapi "uvicorn[standard]"
```

R (modelos de inclinación):

```r
install.packages(c("dplyr","car","lmtest","sandwich","nlme","jsonlite","readxl"))
```

**Tablas de entrada/salida en este paquete = Excel (`.xlsx` / `.xlsm`). No hay CSV.**

## 3. CRS (obligatorio)

- Código: `IAU_2015:49900`
- Escala: **59 274.69 m/grado**
- **No** usar EPSG:4326 / EPSG:3857 para distancias o pendientes
- Mapa offline: proyección plana sobre bounds Gale `[137.345, -4.740, 137.455, -4.580]`

## 4. Cómo regenerar rutas (opcional)

El optimizador espera una carpeta con `processed/` y `raw/` (como en el repo raíz `data/`).

```bat
python 02_optimizacion_rutas\optimizador_rutas.py --datos <carpeta_data> --batch --sol 1360 --hora 9
```

Para solo servir el MVP **sin recalcular**, lean directo `03_salidas/`.

## 5. Contrato API

- Request/response de ejemplo real: `EJEMPLO_API_RESPUESTA.json`
- Endpoint sugerido: `POST /api/ruta`
- Función a llamar: `calcular_ruta_optima(mapa, lon, lat, material, hora)`

## 6. Origen por defecto

Bradbury Landing: `(137.4416, -4.5895)` · sol `1360` · hora LMST `9`
