---
name: mars-geodata
description: Reglas para datos geoespaciales de Marte (DEM, pendiente, CRS, GeoTIFF/COG, rasterio/GDAL). Usar al leer, reproyectar o analizar rásters de Marte, calcular pendientes o distancias, o elegir CRS y unidades.
---

# Datos geoespaciales de Marte

Marte no es la Tierra: casi todos los bugs vienen de asumir defaults terrestres. Revisa estas reglas antes de tocar un ráster.

## CRS

- **Nunca** uses EPSG:4326 / 3857 ni nada terrestre. Lee el CRS del archivo (`src.crs`) y respétalo.
- Si hay que fijar uno, usa los códigos IAU de PROJ (PROJ >= 8.2), comprobados con `pyproj.CRS(...)`:
  - `IAU_2015:49900` geográfico planetocéntrico, esfera de radio 3 396 190 m.
  - `IAU_2015:49910` equirectangular (clon = 0), en metros. Bueno para regiones chicas cerca del ecuador.
- Para pendientes y distancias reproyecta a un CRS métrico local de la región del MVP; no midas en grados.
- Latitud planetocéntrica (ocentric) vs planetográfica (ographic) no son lo mismo. Longitud puede venir 0 a 360 Este o -180 a 180: normaliza en un solo lugar.

## Elevación y pendiente

- Un grado en Marte mide ~59 274.7 m en el ecuador (no 111 120 m). Si usas `gdaldem slope` sobre un DEM en grados, pasa `-s 59274.7`; mejor aún, reproyecta antes.
- Pendiente en grados: `degrees(arctan(hypot(dz/dx, dz/dy)))` con `dx, dy` = tamaño de pixel en metros (`src.res`).
- Las alturas de MOLA son relativas al areoide; las de DTM HiRISE/CTX suelen ser metros sobre la esfera de referencia. No mezcles fuentes sin revisar el datum vertical.
- Respeta `nodata` (los DTM de USGS usan a menudo `-3.4028227e+38`). Enmascara antes de calcular.

## Archivos

- Lee con ventanas (`src.read(window=...)`) o `WarpedVRT`; no cargues mosaicos globales completos en memoria.
- Salida: GeoTIFF Cloud Optimized (`driver="COG"`) con el CRS y nodata explícitos.
- Los datos viven en el almacenamiento compartido (`data/`, ignorado por git). Nunca subas `.tif`/`.img` al repo.
- Cita cada dataset (misión, instrumento, URL) en la documentación del servicio que lo usa.

## Antes de dar por bueno un resultado

Comprueba un valor conocido a mano (una pendiente o distancia que puedas estimar) y deja ese check como test.
