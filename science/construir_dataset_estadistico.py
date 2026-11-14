#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Planetary Explorer - Matriz de calibración estadística de Gale Crater
=====================================================================

Cruza los waypoints reales de Curiosity (msl_waypoints_todos.geojson, 1 389 puntos)
con los rasters locales y con los puntos de química de superficie (CheMin, APXS,
ChemCam) que dejó `descargar_datos_gale.py`. Exporta:

  data/processed/gale_puntos_quimica.csv / .gpkg
      Tabla georreferenciada de objetivos analizados: instrumento, objetivo, sol,
      lon, lat, elevación, minerales clave (CheMin) y óxidos (APXS, ChemCam).

  data/processed/gale_matriz_calibracion.csv / .gpkg
      Una fila por waypoint con:
        coordenadas   lon, lat, elevacion_m
        predictoras X pendiente_grados, rugosidad, inercia_termica_tiu, albedo,
                      indice_polvo, distancia_duna_m (+ índices CRISM)
        respuestas Y  tilt_real_grados, velocidad_efectiva_m_sol, mineral_dominante,
                      abundancia_mineral_pct, indice_interes_cientifico, nivel_riesgo_real

  data/processed/gale_matriz_calibracion_diccionario.json
      Definición, unidad y fuente de cada columna.

Uso:
    python construir_dataset_estadistico.py               # usa ./planetary-explorer/data
    python construir_dataset_estadistico.py --datos RUTA  # otra carpeta de datos

Requisitos: numpy, pandas, geopandas, rasterio, pyproj, shapely (scipy opcional).
Todo el cálculo métrico se hace en una proyección azimutal equidistante local sobre la
esfera de Marte (ver marte_crs.py); nunca sobre EPSG:4326.
"""

import argparse
import glob
import json
import math
import os
import re
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from marte_crs import (CRS_METRICO_LOCAL, METROS_POR_GRADO, crs_marte, crs_raster_efectivo,  # noqa: E402
                       eqc_a_lonlat, fijar_crs_marte)

warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# Parámetros del modelo (documentados en el diccionario de salida)
# ---------------------------------------------------------------------------
VENTANA_PENDIENTE_M = 15.0        # radio de la ventana para ajustar el plano local
RADIO_QUIMICA_M = 500.0           # distancia máxima para asignar una muestra CheMin a un waypoint
ESCALA_PROXIMIDAD_M = 250.0       # decaimiento de la cercanía a sitios de perforación
UMBRAL_TILT_MEDIO, UMBRAL_TILT_ALTO = 12.0, 20.0
UMBRAL_PENDIENTE_MEDIO = 15.0

# Incidentes de movilidad documentados por JPL/NASA (rango de sols aproximado)
INCIDENTES = [
    (410, 535, "alto", "Terreno de rocas afiladas incrustadas; aceleró el daño a las ruedas (oct 2013 - ene 2014)"),
    (533, 535, "medio", "Cruce de la duna de Dingo Gap (1.34 m de alto)"),
    (672, 672, "alto", "Deslizamiento de 77 % sobre ondulitas (límite operativo 60 %)"),
    (706, 712, "alto", "Hidden Valley: deslizamiento alto en arena; retirada del valle"),
    (1190, 1240, "medio", "Campaña en Bagnold Dunes (arena activa, Namib Dune)"),
    (1268, 1330, "medio", "Naukluft Plateau: lecho tallado por el viento, vigilancia de ruedas"),
]

GRUPOS_MINERALES = {
    "esmectitas": [],  # se toma del porcentaje de arcillas modelado con FULLPAT (descripción del LBL)
    "hematita": ["HEMATITE"],
    "jarosita": ["JAROSITE", "NATROJAROSITE", "NATROJAROSIT"],
    "tridimita": ["TRIDYMITE"],
    "silice": ["OPAL-CT", "OPAL", "CRISTOBALITE", "QUARTZ"],
    "sulfatos": ["ANHYDRITE", "BASSANITE", "GYPSUM", "KIESERITE", "STARKEYITE", "JAROSITE", "NATROJAROSITE",
                 "NATROJAROSIT"],
    "carbonatos": ["SIDERITE"],
}
GRUPOS_CLAVE = ["esmectitas", "hematita", "jarosita", "tridimita", "silice", "sulfatos", "carbonatos"]


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# Lectura de rasters con el CRS de Marte forzado
# ---------------------------------------------------------------------------

def abrir_raster(ruta):
    import rasterio
    if ruta.lower().endswith(".img") and os.path.exists(ruta[:-4] + ".lbl"):
        ruta = ruta[:-4] + ".lbl"
    return rasterio.open(ruta)


def nombres_bandas(src, ruta):
    """Nombres de bandas desde el raster o desde BAND_NAME del LBL de PDS3."""
    desc = [d for d in (src.descriptions or []) if d]
    if len(desc) == src.count:
        return [d.upper() for d in desc]
    lbl = ruta[:-4] + ".lbl" if not ruta.lower().endswith(".lbl") else ruta
    if os.path.exists(lbl):
        txt = open(lbl, encoding="latin-1").read()
        m = re.search(r"BAND_NAME\s*=\s*\(([\s\S]*?)\)", txt)
        if m:
            return [n.strip().strip('"').upper() for n in m.group(1).split(",")]
    return [f"B{i+1}" for i in range(src.count)]


def coords_raster(src, lons, lats):
    """lon/lat marcianos -> x, y en el sistema del raster (sin desplazamiento de datum)."""
    from pyproj import Transformer
    if src.crs is None or src.crs.is_geographic:
        x = np.asarray(lons, float)
        # raster en 0-360
        if src.bounds.right > 180.5 and np.nanmin(x) < 0:
            x = np.where(x < 0, x + 360, x)
        return x, np.asarray(lats, float)
    t = Transformer.from_crs(crs_marte(), crs_raster_efectivo(src.crs), always_xy=True)
    return t.transform(np.asarray(lons, float), np.asarray(lats, float))


def es_nulo(v, src):
    nd = src.nodata
    return (not np.isfinite(v)) or (nd is not None and v == nd) or v in (65535.0, -3.4028226550889045e38) \
        or abs(v) > 1e30 or v <= -32000


def muestrear(ruta, lons, lats, bandas=(1,)):
    """Valor del píxel en cada punto. Devuelve dict banda -> array (NaN fuera de cobertura)."""
    out = {b: np.full(len(lons), np.nan) for b in bandas}
    with abrir_raster(ruta) as src:
        xs, ys = coords_raster(src, lons, lats)
        filas, cols = [], []
        for x, y in zip(xs, ys):
            try:
                r, c = src.index(x, y)
            except Exception:  # noqa: BLE001
                r, c = -1, -1
            filas.append(r)
            cols.append(c)
        for b in bandas:
            for i, (r, c) in enumerate(zip(filas, cols)):
                if 0 <= r < src.height and 0 <= c < src.width:
                    v = float(src.read(b, window=((r, r + 1), (c, c + 1)))[0, 0])
                    if not es_nulo(v, src):
                        out[b][i] = v
    return out


def pendiente_rugosidad(ruta_dem, lons, lats, radio_m=VENTANA_PENDIENTE_M):
    """Ajuste de plano por mínimos cuadrados en una ventana en metros reales.

    pendiente_grados = atan(|gradiente|); rugosidad = desviación estándar (m) de los
    residuos al plano (rugosidad sin tendencia, a la escala de la ventana).
    """
    from pyproj import Transformer
    pend = np.full(len(lons), np.nan)
    rug = np.full(len(lons), np.nan)
    elev = np.full(len(lons), np.nan)
    with abrir_raster(ruta_dem) as src:
        crs_r = crs_raster_efectivo(src.crs)
        a_local = Transformer.from_crs(crs_r, CRS_METRICO_LOCAL, always_xy=True)
        xs, ys = coords_raster(src, lons, lats)
        res_x, res_y = abs(src.transform.a), abs(src.transform.e)
        if src.crs is None or src.crs.is_geographic:
            px_m = res_y * METROS_POR_GRADO
        else:
            px_m = res_y
        n = max(2, int(math.ceil(radio_m / px_m)))
        for i, (x, y) in enumerate(zip(xs, ys)):
            try:
                r, c = src.index(x, y)
            except Exception:  # noqa: BLE001
                continue
            r0, c0 = r - n, c - n
            if r0 < 0 or c0 < 0 or r + n >= src.height or c + n >= src.width:
                continue
            z = src.read(1, window=((r0, r + n + 1), (c0, c + n + 1))).astype(float)
            malo = ~np.isfinite(z) | (z < -30000) | (np.abs(z) > 1e20)
            if src.nodata is not None:
                malo |= z == src.nodata
            if malo.sum() > 0.3 * z.size:
                continue
            rr, cc = np.mgrid[r0:r + n + 1, c0:c + n + 1]
            gx, gy = src.xy(rr.ravel(), cc.ravel())
            mx, my = a_local.transform(np.asarray(gx), np.asarray(gy))
            ok = ~malo.ravel()
            A = np.column_stack([mx[ok], my[ok], np.ones(ok.sum())])
            coef, *_ = np.linalg.lstsq(A, z.ravel()[ok], rcond=None)
            resid = z.ravel()[ok] - A @ coef
            pend[i] = math.degrees(math.atan(math.hypot(coef[0], coef[1])))
            rug[i] = float(np.std(resid))
            elev[i] = float(z[n, n]) if not malo[n, n] else np.nan
    return pend, rug, elev


def primero_existente(*patrones):
    for p in patrones:
        hall = sorted(glob.glob(p))
        if hall:
            return hall[0]
    return None


# ---------------------------------------------------------------------------
# Química: CheMin, APXS, ChemCam -> puntos georreferenciados
# ---------------------------------------------------------------------------

def leer_chemin(dir_q):
    filas = []
    for csvp in sorted(glob.glob(os.path.join(dir_q, "chemin_min", "*.csv"))):
        nombre = os.path.basename(csvp)[:-4]
        m = re.match(r"cm[a-z]_(\d{9})min(\d{4})(\d{3})(\d{4})ch\d+p(\d)", nombre, re.I)
        if not m:
            continue
        sol, site, drive, parte = int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
        lbl = csvp[:-4] + ".lbl"
        desc = ""
        if os.path.exists(lbl):
            t = open(lbl, encoding="latin-1").read()
            desc = re.sub(r"\s+", " ", (re.search(r'DESCRIPTION\s+=\s+"This table contains([\s\S]*?)"', t) or [None, ""])[1])
        muestra = (re.search(r"for the (.+?) (?:drill |scooped |scoop )?sample", desc, re.I) or [None, ""])[1]
        arcilla = re.search(r"clay minerals?[^~]{0,80}~\s*([\d.]+)", desc, re.I)
        amorfo = (re.search(r"~\s*([\d.]+)\s*\+/-\s*[\d.]+\s*weight\s*% of the (?:total )?sample consists of X-ray amorphous", desc, re.I)
                  or re.search(r"amorphous[^~]{0,60}~\s*([\d.]+)", desc, re.I))
        arcilla = float(arcilla.group(1)) if arcilla else np.nan
        amorfo = float(amorfo.group(1)) if amorfo else np.nan
        try:
            tabla = pd.read_csv(csvp)
        except Exception:  # noqa: BLE001
            continue
        if "MINERAL" not in [c.upper() for c in tabla.columns]:
            continue
        tabla.columns = [c.upper() for c in tabla.columns]
        tabla["MINERAL"] = tabla["MINERAL"].astype(str).str.strip().str.upper()
        tabla["PERCENT"] = pd.to_numeric(tabla["PERCENT"], errors="coerce")
        # porcentajes de la fase cristalina -> base de muestra total cuando se conocen arcilla y amorfo
        f_crist = (100 - np.nan_to_num(arcilla) - np.nan_to_num(amorfo)) / 100 if np.isfinite(amorfo) else 1.0
        fila = {"instrumento": "CheMin", "objetivo": muestra.strip() or nombre, "sol": sol, "site": site,
                "drive": drive, "analisis": parte, "producto_pds": nombre.upper(),
                "arcillas_pct": arcilla, "amorfo_pct": amorfo,
                "minerales_crudos": ";".join(f"{a}:{b}" for a, b in zip(tabla["MINERAL"], tabla["PERCENT"]))}
        for g, lista in GRUPOS_MINERALES.items():
            if g == "esmectitas":
                fila["esmectitas_pct"] = arcilla
            else:
                fila[f"{g}_pct"] = round(float(tabla.loc[tabla["MINERAL"].isin(lista), "PERCENT"].sum()) * f_crist, 2)
        clave = {g: fila[f"{g}_pct"] for g in GRUPOS_CLAVE if np.isfinite(fila[f"{g}_pct"]) and fila[f"{g}_pct"] > 0}
        if clave:
            g = max(clave, key=clave.get)
            fila["mineral_dominante"], fila["abundancia_mineral_pct"] = g, round(clave[g], 2)
        else:
            top = tabla.sort_values("PERCENT", ascending=False).iloc[0]
            fila["mineral_dominante"] = top["MINERAL"].lower()
            fila["abundancia_mineral_pct"] = round(float(top["PERCENT"]) * f_crist, 2)
        fila["agua_pct"] = np.nan  # CheMin no mide agua; ver diccionario
        filas.append(fila)
    return pd.DataFrame(filas)


def leer_apxs(dir_q):
    partes = []
    for p in sorted(glob.glob(os.path.join(dir_q, "apxs", "*.csv"))):
        t = pd.read_csv(p, encoding="latin-1")
        t.columns = [c.strip() for c in t.columns]
        ren = {"sol": "sol", "Sol": "sol", "Target": "objetivo", "Northing_m": "northing", "Northing": "northing",
               "Easting_m": "easting", "Easting": "easting", "Elevation_m": "elevacion_m", "Elevation": "elevacion_m",
               "Strat_group_formal": "grupo", "Strat_group": "grupo", "Strat_fm": "formacion", "Strat_formation": "formacion"}
        t = t.rename(columns={k: v for k, v in ren.items() if k in t.columns})
        partes.append(t)
    if not partes:
        return pd.DataFrame()
    t = pd.concat(partes, ignore_index=True)
    t = t.dropna(subset=["easting", "northing"])
    t["lon"], t["lat"] = eqc_a_lonlat(t["easting"].astype(float), t["northing"].astype(float))
    t["instrumento"] = "APXS"
    t["metodo_georref"] = "easting_northing_apxs"
    cols = [c for c in t.columns if c.endswith("_pct") and not c.endswith("_err")]
    t["suma_oxidos"] = t[cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    return t


def leer_chemcam(dir_q):
    filas = []
    for p in sorted(glob.glob(os.path.join(dir_q, "chemcam_moc", "*.csv"))):
        lineas = open(p, encoding="latin-1").read().splitlines()
        i = next((k for k, l in enumerate(lineas) if l.startswith("File,Target")), None)
        if i is None:
            continue
        df = pd.read_csv(p, skiprows=i, encoding="latin-1")
        df = df[df["File"].astype(str).str.contains("CCS_F", na=False)]
        sd = df["File"].str.extract(r"CCS_F(\d{3})(\d{4})")
        df["site"], df["drive"] = pd.to_numeric(sd[0]), pd.to_numeric(sd[1])
        filas.append(df)
    if not filas:
        return pd.DataFrame()
    df = pd.concat(filas, ignore_index=True)
    ox = ["SiO2", "TiO2", "Al2O3", "FeOT", "MgO", "CaO", "Na2O", "K2O", "MnO", "Sum of Oxides"]
    for c in ox:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    g = df.groupby(["Target", "site", "drive"], as_index=False)[ox].mean()
    g = g.rename(columns={"Target": "objetivo", "Sum of Oxides": "suma_oxidos"})
    g["volatiles_proxy_pct"] = (100 - g["suma_oxidos"]).clip(lower=0)
    g["instrumento"] = "ChemCam"
    return g


def resumen_ambiental_por_sol(dir_amb):
    """Resume RAD y REMS por sol a partir de los CSV de descargar_datos_gale.py.

    RAD: media diaria de la tasa de dosis del detector E (plástico, equivalente a tejido; si falta, B),
         descartando observaciones parciales (valor < 70 % de la mediana del sol).
    REMS: media de las medias horarias y máximo horario de la temperatura de suelo (BRIGHTNESS_TEMP).
    Devuelve (rad_df[sol, dosis_rad_uGy_h], rems_df[sol, temp_suelo_K_media, temp_suelo_K_max]).
    """
    rad, rems = pd.DataFrame(), pd.DataFrame()
    ruta_rad = os.path.join(dir_amb, "rad_dosis_observaciones.csv")
    if os.path.exists(ruta_rad):
        r = pd.read_csv(ruta_rad)
        col = "dosis_e_uGy_h" if r.get("dosis_e_uGy_h", pd.Series(dtype=float)).notna().any() else "dosis_b_uGy_h"
        r = r[pd.to_numeric(r[col], errors="coerce") > 0].copy()
        r["_med"] = r.groupby("sol")[col].transform("median")
        r = r[r[col] >= 0.7 * r["_med"]]
        rad = r.groupby("sol")[col].mean().rename("dosis_rad_uGy_h").reset_index()
    ruta_rems = os.path.join(dir_amb, "rems_resumen_horario.csv")
    if os.path.exists(ruta_rems):
        t = pd.read_csv(ruta_rems)
        t = t[pd.to_numeric(t["temp_suelo_K_media"], errors="coerce") > 0]
        rems = t.groupby("sol").agg(temp_suelo_K_media=("temp_suelo_K_media", "mean"),
                                    temp_suelo_K_max=("temp_suelo_K_max", "max")).reset_index()
    return rad, rems


def unir_ambiental(M, dir_amb):
    """Tarea 1: une RAD y REMS a cada waypoint por el sol más cercano con datos.

    Añade dosis_rad_uGy_h, temp_suelo_K_media, temp_suelo_K_max y, para trazabilidad,
    sol_ref_rad / sol_ref_rems (sol del que proviene el valor).
    """
    rad, rems = resumen_ambiental_por_sol(dir_amb)
    for df_amb, cols, ref in ((rad, ["dosis_rad_uGy_h"], "sol_ref_rad"),
                              (rems, ["temp_suelo_K_media", "temp_suelo_K_max"], "sol_ref_rems")):
        if df_amb.empty or M["sol"].isna().all():
            for c in cols + [ref]:
                M[c] = np.nan
            continue
        izq = M[["sol"]].reset_index().dropna().sort_values("sol")
        izq["sol"] = izq["sol"].astype(float)
        der = df_amb.assign(**{ref: df_amb["sol"]}).astype({"sol": float}).sort_values("sol")
        u = pd.merge_asof(izq, der, on="sol", direction="nearest").set_index("index")
        for c in cols + [ref]:
            M[c] = u[c].reindex(M.index).round(3)
    return M


def georreferenciar_por_rmc(df, wp):
    """Asigna lon/lat/elev/sol usando site/drive (RMC) de los waypoints; si no, el waypoint del sol más cercano."""
    if df.empty:
        return df
    idx = wp.set_index(["site", "drive"])
    lon, lat, ele, sol, met = [], [], [], [], []
    wp_sol = wp.sort_values("sol")
    for _, r in df.iterrows():
        k = (int(r["site"]), int(r["drive"])) if pd.notna(r.get("site")) and pd.notna(r.get("drive")) else None
        if k is not None and k in idx.index:
            w = idx.loc[k]
            w = w.iloc[0] if isinstance(w, pd.DataFrame) else w
            lon.append(w["lon"]); lat.append(w["lat"]); ele.append(w["elev_geoid"]); sol.append(w["sol"]); met.append("rmc_exacto")
            continue
        # mismo site, drive más cercano
        mismo = wp[wp["site"] == r.get("site")] if pd.notna(r.get("site")) else wp.iloc[0:0]
        if len(mismo):
            w = mismo.iloc[(mismo["drive"] - r["drive"]).abs().argmin()]
            met.append("rmc_drive_cercano")
        elif pd.notna(r.get("sol")):
            w = wp_sol.iloc[(wp_sol["sol"] - r["sol"]).abs().argmin()]
            met.append("sol_cercano")
        else:
            lon.append(np.nan); lat.append(np.nan); ele.append(np.nan); sol.append(np.nan); met.append("sin_georref")
            continue
        lon.append(w["lon"]); lat.append(w["lat"]); ele.append(w["elev_geoid"]); sol.append(w["sol"])
    df = df.copy()
    df["lon"], df["lat"], df["elevacion_m"], df["metodo_georref"] = lon, lat, ele, met
    if "sol" not in df.columns or df["sol"].isna().all():
        df["sol"] = sol
    return df


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------

def main():
    import geopandas as gpd
    from pyproj import Transformer

    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default=os.path.join(".", "planetary-explorer", "data"))
    args = ap.parse_args()
    D = os.path.abspath(args.datos)
    R, P = os.path.join(D, "raw"), os.path.join(D, "processed")
    os.makedirs(P, exist_ok=True)
    fuentes = {}

    # --- Waypoints (variable de respuesta real) -----------------------------------
    ruta_wp = os.path.join(R, "vectores", "msl_waypoints_todos.geojson")
    wp = fijar_crs_marte(gpd.read_file(ruta_wp))   # reasigna Marte aunque el archivo diga EPSG:4326
    wp["lon"], wp["lat"] = wp.geometry.x, wp.geometry.y
    for c in ("sol", "site", "drive", "elev_geoid", "tilt", "dist_m", "roll", "pitch"):
        if c in wp.columns:
            wp[c] = pd.to_numeric(wp[c], errors="coerce")
    wp = wp.sort_values(["sol", "site", "drive"]).reset_index(drop=True)
    log(f"Waypoints: {len(wp)} (sol {int(wp['sol'].min())} a {int(wp['sol'].max())})")
    lons, lats = wp["lon"].values, wp["lat"].values
    loc = Transformer.from_crs(crs_marte(), CRS_METRICO_LOCAL, always_xy=True)
    wx, wy = loc.transform(lons, lats)

    M = pd.DataFrame({"sol": wp["sol"].astype("Int64"), "rmc": wp.get("RMC"), "lon": lons, "lat": lats,
                      "elevacion_m": wp["elev_geoid"]})

    # --- Topografía ---------------------------------------------------------------
    dem = primero_existente(os.path.join(R, "dem", "gale_dem_hirise_2m_ruta.tif"),
                            os.path.join(R, "dem", "gale_dem_hirise_2m_ruta_teselas", "*.vrt"),
                            os.path.join(R, "dem", "gale_dem_hrsc_30m_ucl.tif"),
                            os.path.join(R, "dem", "gale_dem_mola_hrsc_200m_crater.tif"))
    if dem:
        radio = VENTANA_PENDIENTE_M if "hirise" in dem else (90.0 if "hrsc_30m" in dem else 600.0)
        pend, rug, ele_dem = pendiente_rugosidad(dem, lons, lats, radio)
        M["pendiente_grados"], M["rugosidad"], M["elevacion_dem_m"] = pend, rug, ele_dem
        fuentes["pendiente_grados"] = fuentes["rugosidad"] = os.path.relpath(dem, D)
        # respaldo con HRSC 30 m donde el HiRISE no cubre
        hrsc = os.path.join(R, "dem", "gale_dem_hrsc_30m_ucl.tif")
        faltan = M["pendiente_grados"].isna()
        if faltan.any() and os.path.exists(hrsc) and "hrsc" not in dem:
            p2, r2, e2 = pendiente_rugosidad(hrsc, lons[faltan], lats[faltan], 90.0)
            M.loc[faltan, "pendiente_grados"], M.loc[faltan, "rugosidad"] = p2, r2
        log(f"Pendiente y rugosidad desde {os.path.basename(dem)}: {M['pendiente_grados'].notna().sum()} puntos")
    else:
        M["pendiente_grados"] = M["rugosidad"] = M["elevacion_dem_m"] = np.nan
        log("AVISO: no hay DEM local; pendiente y rugosidad quedan vacías")

    # --- Variables térmicas y de superficie ----------------------------------------
    def capa(col, candidatas, banda=1):
        ruta = primero_existente(*[os.path.join(R, c) for c in candidatas])
        if ruta:
            M[col] = muestrear(ruta, lons, lats, (banda,))[banda]
            fuentes[col] = os.path.relpath(ruta, D)
            log(f"{col} desde {os.path.basename(ruta)}: {M[col].notna().sum()} puntos")
        else:
            M[col] = np.nan
            log(f"AVISO: {col} sin fuente local")

    capa("inercia_termica_tiu", ["termico/gale_themis_inercia_termica_100m.tif", "termico/tes_inercia_termica_8ppd.lbl"])
    capa("albedo", ["contexto/tes_albedo_bolometrico_8ppd.lbl"])
    capa("indice_polvo", ["contexto/tes_dust_cover_index_16ppd.pds"])

    # --- Distancia a dunas ----------------------------------------------------------
    ruta_dunas = os.path.join(R, "vectores", "gale_campos_dunas.geojson")
    if os.path.exists(ruta_dunas):
        dunas = fijar_crs_marte(gpd.read_file(ruta_dunas)).to_crs(CRS_METRICO_LOCAL)
        pts = gpd.GeoSeries(gpd.points_from_xy(wx, wy), crs=CRS_METRICO_LOCAL)
        union = dunas.geometry.union_all() if hasattr(dunas.geometry, "union_all") else dunas.unary_union
        M["distancia_duna_m"] = pts.distance(union).round(1).values
        fuentes["distancia_duna_m"] = os.path.relpath(ruta_dunas, D)
    else:
        M["distancia_duna_m"] = np.nan

    # --- Índices CRISM (máximo entre productos que cubren el punto) -----------------
    indices = {"BD860_2": "crism_hematita_bd860_2", "D2300": "crism_filosilicatos_d2300",
               "SINDEX2": "crism_sulfatos_sindex2", "MIN2250": "crism_silice_min2250",
               "BD1900R2": "crism_hidratacion_bd1900r2"}
    for col in indices.values():
        M[col] = np.nan
    crism = sorted(set(glob.glob(os.path.join(R, "crism", "*_su*_mtr3.lbl")) +
                       glob.glob(os.path.join(R, "crism", "*_su*_mtr3.tif"))))
    for ruta in crism:
        try:
            with abrir_raster(ruta) as src:
                nombres = nombres_bandas(src, ruta)
            bandas = {nombres.index(k) + 1: v for k, v in indices.items() if k in nombres}
            vals = muestrear(ruta, lons, lats, tuple(bandas))
            for b, col in bandas.items():
                M[col] = np.fmax(M[col].values, vals[b])
        except Exception as e:  # noqa: BLE001
            log(f"CRISM {os.path.basename(ruta)}: omitido ({e})")
    if crism:
        log(f"CRISM: {len(crism)} productos; {M['crism_hematita_bd860_2'].notna().sum()} waypoints con dato")

    # --- Respuestas de movilidad ----------------------------------------------------
    M["tilt_real_grados"] = wp["tilt"].values if "tilt" in wp.columns else np.nan
    dsol = wp["sol"].diff().clip(lower=1).fillna(1)
    M["velocidad_efectiva_m_sol"] = (wp["dist_m"] / dsol).round(2).values if "dist_m" in wp.columns else np.nan
    M.loc[0, "velocidad_efectiva_m_sol"] = np.nan  # el primer waypoint no tiene tramo previo

    # --- Puntos de química -----------------------------------------------------------
    dq = os.path.join(R, "quimica")
    wp_ref = wp[["sol", "site", "drive", "lon", "lat", "elev_geoid"]].dropna(subset=["site", "drive"]).copy()
    wp_ref[["site", "drive"]] = wp_ref[["site", "drive"]].astype(int)
    chemin = georreferenciar_por_rmc(leer_chemin(dq), wp_ref)
    chemcam = georreferenciar_por_rmc(leer_chemcam(dq), wp_ref)
    apxs = leer_apxs(dq)
    partes = [d for d in (chemin, apxs, chemcam) if not d.empty]
    if partes:
        Q = pd.concat(partes, ignore_index=True, sort=False)
        primeras = ["instrumento", "objetivo", "sol", "lon", "lat", "elevacion_m", "metodo_georref",
                    "mineral_dominante", "abundancia_mineral_pct"] + [f"{g}_pct" for g in GRUPOS_CLAVE] + \
                   ["amorfo_pct", "agua_pct", "volatiles_proxy_pct", "suma_oxidos"]
        Q = Q[[c for c in primeras if c in Q.columns] + [c for c in Q.columns if c not in primeras]]
        Q.to_csv(os.path.join(P, "gale_puntos_quimica.csv"), index=False, encoding="utf-8")
        gq = Q.dropna(subset=["lon", "lat"])
        gpd.GeoDataFrame(gq, geometry=gpd.points_from_xy(gq["lon"], gq["lat"]), crs=crs_marte()) \
            .to_file(os.path.join(P, "gale_puntos_quimica.gpkg"), driver="GPKG")
        log(f"Química: {len(chemin)} CheMin, {len(apxs)} APXS, {len(chemcam)} objetivos ChemCam")
    else:
        log("AVISO: no hay tablas de química en raw/quimica")

    # --- Asignación mineral y proximidad a sitios de perforación ---------------------
    M["mineral_dominante"], M["abundancia_mineral_pct"], M["dist_muestra_chemin_m"] = None, np.nan, np.nan
    s_quim = np.zeros(len(M))
    s_prox = np.zeros(len(M))
    if not chemin.empty and chemin["lon"].notna().any():
        cm = chemin.dropna(subset=["lon", "lat"]).reset_index(drop=True)
        cx, cy = loc.transform(cm["lon"].values, cm["lat"].values)
        try:
            from scipy.spatial import cKDTree
            d, j = cKDTree(np.column_stack([cx, cy])).query(np.column_stack([wx, wy]))
        except ImportError:
            dd = np.hypot(wx[:, None] - cx[None, :], wy[:, None] - cy[None, :])
            j, d = dd.argmin(axis=1), dd.min(axis=1)
        cerca = d <= RADIO_QUIMICA_M
        M["dist_muestra_chemin_m"] = np.round(d, 1)
        M.loc[cerca, "mineral_dominante"] = cm.loc[j[cerca], "mineral_dominante"].values
        M.loc[cerca, "abundancia_mineral_pct"] = cm.loc[j[cerca], "abundancia_mineral_pct"].values
        presentes = (cm[[f"{g}_pct" for g in GRUPOS_CLAVE]].fillna(0) > 1).sum(axis=1).values
        s_quim = np.where(cerca, presentes[j] / len(GRUPOS_CLAVE), 0.0)
        s_prox = np.exp(-d / ESCALA_PROXIMIDAD_M)

    # --- Índice de interés científico (0 a 1) ----------------------------------------
    cols_c = list(indices.values())
    if M[cols_c].notna().any().any():
        norm = []
        for c in cols_c:
            v = M[c].clip(lower=0)
            p99 = np.nanpercentile(v, 99) if v.notna().any() else np.nan
            norm.append((v / p99).clip(0, 1) if p99 and np.isfinite(p99) and p99 > 0 else v * 0)
        s_crism = pd.concat(norm, axis=1).max(axis=1).fillna(0).values
        pesos = (0.5, 0.3, 0.2)
    else:
        s_crism = np.zeros(len(M))
        pesos = (0.0, 0.6, 0.4)
    M["indice_interes_cientifico"] = np.round(pesos[0] * s_crism + pesos[1] * s_prox + pesos[2] * s_quim, 4)

    # --- Nivel de riesgo real ---------------------------------------------------------
    niveles, motivos = [], []
    orden = {"bajo": 0, "medio": 1, "alto": 2}
    for _, r in M.iterrows():
        nivel, mot = "bajo", []
        s = r["sol"]
        for a, b, n, txt in INCIDENTES:
            if pd.notna(s) and a <= int(s) <= b:
                if orden[n] > orden[nivel]:
                    nivel = n
                mot.append(txt)
        t = r["tilt_real_grados"]
        if pd.notna(t) and t >= UMBRAL_TILT_ALTO:
            nivel = "alto"; mot.append(f"tilt {t:.1f}° >= {UMBRAL_TILT_ALTO}°")
        elif pd.notna(t) and t >= UMBRAL_TILT_MEDIO and orden[nivel] < 1:
            nivel = "medio"; mot.append(f"tilt {t:.1f}° >= {UMBRAL_TILT_MEDIO}°")
        p = r["pendiente_grados"]
        if pd.notna(p) and p >= UMBRAL_PENDIENTE_MEDIO and orden[nivel] < 1:
            nivel = "medio"; mot.append(f"pendiente local {p:.1f}°")
        if pd.notna(r["distancia_duna_m"]) and r["distancia_duna_m"] == 0 and orden[nivel] < 1:
            nivel = "medio"; mot.append("dentro de un campo de dunas cartografiado")
        niveles.append(nivel)
        motivos.append("; ".join(mot))
    M["nivel_riesgo_real"], M["motivo_riesgo"] = niveles, motivos

    # --- Tarea 1: radiación (RAD) y temperatura de suelo (REMS) por sol más cercano -----
    M = unir_ambiental(M, os.path.join(D, "raw", "ambiental"))
    if M["dosis_rad_uGy_h"].notna().any():
        log(f"RAD unido desde {M['sol_ref_rad'].nunique()} sols; REMS desde {M['sol_ref_rems'].nunique()} sols")
        fuentes["dosis_rad_uGy_h"] = "raw/ambiental/rad_dosis_observaciones.csv"
        fuentes["temp_suelo_K_media"] = fuentes["temp_suelo_K_max"] = "raw/ambiental/rems_resumen_horario.csv"
    else:
        log("AVISO: sin RAD/REMS en raw/ambiental (ejecuta descargar_datos_gale.py sin --sin-ambiental)")

    # --- Exportar -------------------------------------------------------------------
    orden_cols = ["sol", "rmc", "lon", "lat", "elevacion_m",
                  "pendiente_grados", "rugosidad", "inercia_termica_tiu", "albedo", "indice_polvo", "distancia_duna_m",
                  "dosis_rad_uGy_h", "temp_suelo_K_media", "temp_suelo_K_max", "sol_ref_rad", "sol_ref_rems",
                  *cols_c, "elevacion_dem_m",
                  "tilt_real_grados", "velocidad_efectiva_m_sol", "mineral_dominante", "abundancia_mineral_pct",
                  "indice_interes_cientifico", "nivel_riesgo_real", "motivo_riesgo", "dist_muestra_chemin_m"]
    M = M[orden_cols]
    salida = os.path.join(P, "gale_matriz_calibracion.csv")
    M.to_csv(salida, index=False, encoding="utf-8")
    gpd.GeoDataFrame(M, geometry=gpd.points_from_xy(M["lon"], M["lat"]), crs=crs_marte()) \
        .to_file(os.path.join(P, "gale_matriz_calibracion.gpkg"), driver="GPKG")

    dicc = {
        "crs": "IAU_2015:49900 (Marte, esfera R=3396190 m, planetocéntrica, lon este). Métrico: " + CRS_METRICO_LOCAL,
        "columnas": {
            "lon, lat": "grados planetocéntricos del waypoint (NASA/JPL MMGIS)",
            "elevacion_m": "elevación respecto al geoide marciano (elev_geoid del waypoint), m",
            "pendiente_grados": f"pendiente del plano ajustado en radio {VENTANA_PENDIENTE_M} m sobre el DEM",
            "rugosidad": "desviación estándar de residuos al plano local, m (rugosidad sin tendencia)",
            "inercia_termica_tiu": "J m-2 K-1 s-1/2; THEMIS 100 m si existe, si no TES 8 px/grado",
            "albedo": "albedo de Lambert bolométrico TES (0-1), ~7.4 km/px",
            "indice_polvo": "TES Dust Cover Index (emisividad 1350-1400 cm-1); menor = más polvo",
            "distancia_duna_m": "distancia al campo de dunas cartografiado más cercano (0 = dentro)",
            "dosis_rad_uGy_h": "tasa de dosis media del sol (RAD detector E, equivalente a tejido), uGy/h; "
                               "sol más cercano con datos (sol_ref_rad)",
            "temp_suelo_K_media, temp_suelo_K_max": "REMS GTS: media de medias horarias y máximo horario del sol "
                                                     "más cercano con datos (sol_ref_rems), K",
            "crism_*":"parámetros espectrales CRISM MTRDR (Viviano-Beck 2014); máximo entre productos",
            "tilt_real_grados": "inclinación total del rover registrada en el waypoint",
            "velocidad_efectiva_m_sol": "distancia del tramo / sols transcurridos desde el waypoint anterior",
            "mineral_dominante, abundancia_mineral_pct": f"grupo mineral clave de la muestra CheMin más cercana "
                                                         f"(<= {RADIO_QUIMICA_M} m), % en peso de muestra total",
            "indice_interes_cientifico": "0.5*CRISM normalizado (p99) + 0.3*exp(-d/250 m) a perforación "
                                         "+ 0.2*grupos minerales clave presentes/7 (pesos se redistribuyen sin CRISM)",
            "nivel_riesgo_real": "bajo/medio/alto: incidentes documentados por sol + tilt >= 12/20° + pendiente >= 15° "
                                 "+ dentro de campo de dunas",
            "agua_pct (puntos_quimica)": "vacío: el PDS no publica % de agua por muestra en tabla; SAM EGA requiere "
                                         "procesar espectros. volatiles_proxy_pct = 100 - suma de óxidos ChemCam",
        },
        "incidentes": [{"sol_inicio": a, "sol_fin": b, "nivel": n, "descripcion": t} for a, b, n, t in INCIDENTES],
        "fuentes_locales": fuentes,
    }
    with open(os.path.join(P, "gale_matriz_calibracion_diccionario.json"), "w", encoding="utf-8") as f:
        json.dump(dicc, f, ensure_ascii=False, indent=2)
    log(f"Listo: {salida} ({len(M)} filas, {M.shape[1]} columnas)")
    log(M[["pendiente_grados", "rugosidad", "tilt_real_grados", "velocidad_efectiva_m_sol",
           "indice_interes_cientifico"]].describe().round(3).to_string())
    log(M["nivel_riesgo_real"].value_counts().to_string())


if __name__ == "__main__":
    main()
