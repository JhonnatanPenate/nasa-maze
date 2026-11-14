# science/ — scripts científicos (dueño: Javi)

Lógica de rutas y modelos. **No reescribir**: importar desde los servicios.

| Archivo | Rol |
|---|---|
| `optimizador_rutas.py` | **Canónico.** A*/función de costo: `MapaMision`, `calcular_ruta_optima`, `minimizar_costo_ruta`, `tabla_tramos_ruta` |
| `modelos_inclinacion_por_suelo.R` | **Canónico.** Ajusta modelos por tipo de suelo → `modelos_por_suelo.json` |
| `crs_marte.py` | **Canónico.** CRS `IAU_2015:49900`, 59 274.69 m/grado |
| `motor_rutas_adaptativo.py`, `marte_crs.py`, `modelos_adaptativos_suelo.R` | Alias de compatibilidad |
| `construir_dataset_estadistico.py`, `preparar_datos_reales.py`, `exportar_tablas_excel.py`, `verificar_envio.py` | Pipeline de preparación de datos |

Datos: `data/gale/` (`processed/` + `raw/`, tablas en Excel). Fuentes: `DATA_SOURCES.md`. Integración: `docs/data/`.

```bash
# Ruta de prueba (sol 1360, 9:00 LMST, hematita ≈ 7.7 km, 247.8 μGy)
python science/optimizador_rutas.py --datos data/gale --material hematita --sol 1360 --hora 9 --salida /tmp/ruta
```

Nota: `modelos_inclinacion_por_suelo.R` busca `<raiz>/data/processed/`, que no coincide con `data/gale/processed/` de este repo. Solo hace falta si se recalibran los modelos; `modelos_por_suelo.json` ya viene generado. Ajuste pendiente con Javi.
