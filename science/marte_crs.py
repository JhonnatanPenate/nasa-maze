# -*- coding: utf-8 -*-
"""
marte_crs.py - Sistema de referencia de Marte para Planetary Explorer
=====================================================================

Problema que resuelve
---------------------
Los GeoJSON que entrega el servidor ArcGIS de Mars Trek vienen marcados como
EPSG:4326 (WGS 84, la Tierra) porque ese formato no admite otro sistema. Si
GeoPandas o Shapely los leen así, cualquier distancia, área o buffer se calcula
sobre el elipsoide terrestre (6 378 km) en lugar del marciano (3 396 km): las
distancias salen ~1.88 veces más grandes.

Además, los GeoTIFF de Trek declaran GCS_Mars_2000 con un elipsoide achatado
(a = 3 396 190 m, 1/f = 169.894). Formalmente eso indica latitud planetográfica,
pero los valores reales son planetocéntricos (Curiosity en Bradbury Landing está en
-4.5895 tanto en Trek como en el JSON oficial de JPL). Si se dejara que PROJ
convirtiera "ográfica -> océntrica", a la latitud de Gale el error sería de
~0.055 grados, unos 3.3 km. Por eso aquí NUNCA se transforma entre esos datums:
se reasigna el CRS.

Convención del proyecto
-----------------------
* Coordenadas geográficas: IAU_2015:49900 = "Mars (2015) - Sphere / Ocentric",
  esfera de radio 3 396 190 m, latitud planetocéntrica, longitud este (-180 a 180).
  Equivale a "+proj=longlat +R=3396190 +no_defs".
* Cálculos métricos (distancias, pendientes, buffers): proyección azimutal
  equidistante local centrada en el recorrido de Curiosity, sobre la misma esfera.
  En un radio de 20 km el error de escala es < 0.002 %.
"""

import json
import math

RADIO_MARTE_M = 3396190.0
METROS_POR_GRADO = 2 * math.pi * RADIO_MARTE_M / 360.0   # 59 274.69 m

CRS_MARTE_CODIGO = "IAU_2015:49900"
CRS_MARTE_PROJ4 = f"+proj=longlat +R={RADIO_MARTE_M:.0f} +no_defs +type=crs"
CRS_MARTE_WKT = (
    'GEOGCS["Mars (2015) - Sphere / Ocentric",DATUM["Mars (2015) - Sphere",'
    f'SPHEROID["Mars (2015) - Sphere",{RADIO_MARTE_M:.0f},0]],PRIMEM["Reference Meridian",0],'
    'UNIT["degree",0.0174532925199433]]')

# Centro del recorrido de Curiosity (Bradbury Landing -> región boxwork)
LON0, LAT0 = 137.40, -4.71
CRS_METRICO_LOCAL = (f"+proj=aeqd +lat_0={LAT0} +lon_0={LON0} +R={RADIO_MARTE_M:.0f} "
                     "+x_0=0 +y_0=0 +units=m +no_defs +type=crs")

# Proyección del JSON de JPL (MMGIS) y de las tablas APXS: equirectangular, esfera R, lon_0=0
CRS_MSL_EQC = f"+proj=eqc +lat_ts=0 +lon_0=0 +R={RADIO_MARTE_M:.0f} +units=m +no_defs +type=crs"


def crs_marte():
    """Devuelve el CRS geográfico de Marte (pyproj.CRS), con respaldo por proj4."""
    from pyproj import CRS
    try:
        return CRS.from_user_input(CRS_MARTE_CODIGO)
    except Exception:  # PROJ < 8.2 no trae la autoridad IAU_2015
        return CRS.from_proj4(CRS_MARTE_PROJ4)


def fijar_crs_marte(gdf):
    """Reasigna (sin transformar) el CRS marciano a un GeoDataFrame en grados."""
    return gdf.set_crs(crs_marte(), allow_override=True)


def a_metrico(gdf):
    """GeoDataFrame en grados marcianos -> metros (azimutal equidistante local)."""
    return fijar_crs_marte(gdf).to_crs(CRS_METRICO_LOCAL)


def corregir_geojson(ruta):
    """Reescribe el miembro 'crs' de un GeoJSON para que GDAL/GeoPandas lo lean como Marte.

    Las coordenadas no cambian: solo se corrige la etiqueta EPSG:4326 que pone ArcGIS.
    """
    with open(ruta, "r", encoding="utf-8") as f:
        datos = json.load(f)
    if not isinstance(datos, dict) or datos.get("type") != "FeatureCollection":
        return False
    datos["crs"] = {"type": "name", "properties": {"name": CRS_MARTE_CODIGO}}
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f)
    return True


def crs_raster_efectivo(crs_raster):
    """CRS que se usará para un raster marciano, forzado a la esfera de 3 396 190 m.

    * Raster geográfico (Trek, USGS en grados): se trata como IAU_2015:49900.
    * Raster proyectado (HRSC equidistante, CRISM, THEMIS): se conserva la proyección
      pero sobre la esfera, porque así fueron generados esos productos.
    """
    from pyproj import CRS
    if crs_raster is None:
        return crs_marte()
    c = CRS.from_user_input(crs_raster.to_wkt() if hasattr(crs_raster, "to_wkt") else crs_raster)
    if c.is_geographic:
        return crs_marte()
    params = c.to_dict()
    for k in ("a", "b", "rf", "f", "ellps", "datum", "towgs84", "R"):
        params.pop(k, None)
    params["R"] = RADIO_MARTE_M
    params["no_defs"] = True
    return CRS.from_dict(params)


def transformador_desde_marte(crs_raster):
    """Transformer lon/lat marcianos -> coordenadas del raster (sin desplazamiento de datum)."""
    from pyproj import Transformer
    return Transformer.from_crs(crs_marte(), crs_raster_efectivo(crs_raster), always_xy=True)


def eqc_a_lonlat(easting, northing):
    """Easting/Northing de JPL (MMGIS, APXS) -> lon/lat planetocéntricos."""
    return easting / METROS_POR_GRADO, northing / METROS_POR_GRADO
