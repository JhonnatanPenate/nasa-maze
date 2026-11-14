"""Prepara, en la nube, los insumos reales transferidos desde el navegador del usuario.

Entradas (en este directorio, transferidas con verificación CRC/hash):
  grid.b64        rejilla 90 m (72 x 105) derivada del DEM HiRISE de Trek a 10 m y del ortomosaico:
                  pendiente*4, rugosidad*50 (m), fracción de píxeles oscuros*200 (255 = nulo)
  wp.b64          851 waypoints MSL dentro de la rejilla (delta-codificados)
  rad_raw.txt     RAD RDR, sols 1360/2140/3290/4710: hora LMST, dosis B, dosis E (uGy/h)
  rems_raw.txt    REMS MODRDR, sols 1360/2140: resumen horario
TES TI y albedo: 42 muestras PDS (8 px/grado) sobre Gale, transcritas abajo.

Salidas (estructura del proyecto):
  planetary-explorer/data/raw/ambiental/rad_dosis_observaciones.csv
  planetary-explorer/data/raw/ambiental/rems_resumen_horario.csv
  planetary-explorer/data/processed/rejilla_ruta_90m.tif   (bandas: pendiente, rugosidad, fraccion_oscura,
                                                             inercia_termica, albedo, distancia_duna_m)
  planetary-explorer/data/processed/gale_puntos_quimica.csv
  planetary-explorer/data/processed/gale_matriz_calibracion.csv
"""
import base64
import gzip
import os
import sys

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import distance_transform_edt

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/claude")
from construir_dataset_estadistico import INCIDENTES, unir_ambiental  # noqa: E402
from marte_crs import CRS_MARTE_PROJ4, METROS_POR_GRADO  # noqa: E402

RAIZ = os.path.join(AQUI, "planetary-explorer", "data")
AMB = os.path.join(RAIZ, "raw", "ambiental")
PROC = os.path.join(RAIZ, "processed")
os.makedirs(AMB, exist_ok=True)
os.makedirs(PROC, exist_ok=True)

# ---------------------------------------------------------------- rejilla 90 m
G = (137.345, -4.740, 137.455, -4.580)   # oeste, sur, este, norte
GW, GH, CELDA_M = 72, 105, 90.0
CDEG = CELDA_M / METROS_POR_GRADO
UMBRAL_DUNA = 0.5                         # fracción de píxeles oscuros (ortomosaico < 45 DN) => arena oscura

a = np.frombuffer(gzip.decompress(base64.b64decode(open(os.path.join(AQUI, "grid.b64")).read())), np.uint8)
a = a.reshape(3, GH, GW).astype(float)
a[a == 255] = np.nan
pend, rug, osc = a[0] / 4.0, a[1] / 50.0, a[2] / 200.0
lat_c = G[3] - (np.arange(GH) + 0.5) * CDEG
lon_c = G[0] + (np.arange(GW) + 0.5) * CDEG

# ---------------------------------------------------------------- TES (PDS mgs-m-tes-special-v1)
TES_LAT = [-4.3, -4.425, -4.55, -4.675, -4.8, -4.925, -5.05]
TES_LON = [137.1, 137.225, 137.35, 137.475, 137.6, 137.725]
TES_TI = [335, 335, 276, 276, 359, 359, 446, 446, 397, 397, 511, 511, 446, 446, 397, 397, 511, 511,
          520, 520, 443, 443, 415, 415, 520, 520, 443, 443, 415, 415, 514, 514, 272, 272, 179, 179,
          514, 514, 272, 272, 179, 179]
TES_ALB = [0.23, 0.225, 0.223, 0.251, 0.246, 0.247, 0.222, 0.218, 0.244, 0.244, 0.249, 0.243, 0.21, 0.231,
           0.233, 0.231, 0.238, 0.245, 0.231, 0.232, 0.229, 0.228, 0.232, 0.239, 0.226, 0.231, 0.232, 0.226,
           0.226, 0.229, 0.219, 0.22, 0.225, 0.227, 0.221, 0.222, 0.201, 0.214, 0.215, 0.221, 0.217, 0.22]


def interp_tes(vals):
    z = np.array(vals, float).reshape(len(TES_LAT), len(TES_LON))
    return RegularGridInterpolator((np.array(TES_LAT[::-1]), np.array(TES_LON)), z[::-1], method="linear")


f_ti, f_alb = interp_tes(TES_TI), interp_tes(TES_ALB)
LL = np.stack(np.meshgrid(lat_c, lon_c, indexing="ij"), -1)
ti = f_ti(LL)
alb = f_alb(LL)

duna = np.nan_to_num(osc) >= UMBRAL_DUNA
dist_duna = distance_transform_edt(~duna) * CELDA_M

perfil = {"crs": CRS_MARTE_PROJ4, "transform": from_origin(G[0], G[3], CDEG, CDEG), "width": GW, "height": GH,
          "count": 6, "dtype": "float32", "driver": "GTiff", "nodata": np.nan}
ruta_tif = os.path.join(PROC, "rejilla_ruta_90m.tif")
with rasterio.open(ruta_tif, "w", **perfil) as dst:
    for k, (arr, nom) in enumerate([(pend, "pendiente_grados"), (rug, "rugosidad_m"), (osc, "fraccion_oscura"),
                                    (ti, "inercia_termica_tiu"), (alb, "albedo"),
                                    (dist_duna, "distancia_duna_m")], 1):
        dst.write(arr.astype("float32"), k)
        dst.set_band_description(k, nom)

# ---------------------------------------------------------------- RAD / REMS a CSV del proyecto
filas = []
for linea in open(os.path.join(AQUI, "rad_raw.txt")):
    sol, cuerpo = linea.strip().split(":")
    for i, obs in enumerate(cuerpo.split(";")):
        h, b, e = map(float, obs.split(","))
        filas.append({"sol": int(sol), "observacion": f"OBS{i:03d}", "hora_lmst": h,
                      "dosis_b_uGy_h": b, "dosis_e_uGy_h": e, "unidad_original": "uGy/hour"})
pd.DataFrame(filas).to_csv(os.path.join(AMB, "rad_dosis_observaciones.csv"), index=False)

filas = []
for linea in open(os.path.join(AQUI, "rems_raw.txt")):
    sol, cuerpo = linea.strip().split(":")
    for obs in cuerpo.split(";"):
        c = obs.split(",")
        num = lambda x: float(x) if x != "" else np.nan  # noqa: E731
        filas.append({"sol": int(sol), "hora_lmst": int(c[0]), "n": int(c[1]), "temp_suelo_K_media": num(c[2]),
                      "temp_suelo_K_min": num(c[3]), "temp_suelo_K_max": num(c[4]),
                      "temp_aire_K_media": num(c[5]), "presion_Pa_media": num(c[6]),
                      "uv_abc_W_m2_media": num(c[7])})
pd.DataFrame(filas).to_csv(os.path.join(AMB, "rems_resumen_horario.csv"), index=False)

# ---------------------------------------------------------------- puntos de química (CheMin RDR5)
# % cristalino del RDR5; base de muestra total = cristalino * (100 - arcilla - amorfo) / 100 cuando el LBL
# publica arcilla y amorfo. Arcilla (esmectitas) ya está en base de muestra total.
Q = pd.DataFrame([
    # nombre, sol, lon, lat, elev, hem_crist, arcilla, amorfo, tridimita_crist, sulfatos_crist
    ("Rocknest", 79, 137.4483, -4.5900, -4518, None, None, None, None, None),
    ("John Klein", 196, 137.4491, -4.5895, -4520, None, None, None, None, None),
    ("Cumberland", 283, 137.4491, -4.5895, -4520, None, None, None, None, None),
    ("Windjana", 624, 137.4020, -4.6388, -4479, None, None, None, None, None),
    ("Confidence Hills", 766, 137.3775, -4.6627, -4461, 13.4, None, None, None, None),
    ("Mojave2", 885, 137.3774, -4.6629, -4460, None, None, None, None, 7.6),
    ("Telegraph Peak", 923, 137.3775, -4.6635, -4454, None, None, None, None, None),
    ("Buckskin", 1062, 137.3703, -4.6680, -4447, None, None, None, 34.1, None),
    ("Big Sky", 1122, 137.3686, -4.6731, -4435, None, None, None, None, None),
    ("Greenhorn", 1140, 137.3686, -4.6731, -4435, None, None, None, None, None),
    ("Gobabeb", 1236, 137.3671, -4.6790, -4424, None, None, None, None, None),
    ("Okoruso", 1335, 137.3592, -4.6782, -4429, None, None, None, None, None),
    ("Oudam", 1363, 137.3577, -4.6787, -4436, 26.0, 3.0, 36.0, None, None),
    ("Quela", 1472, 137.3546, -4.6971, -4373, 20.0, 16.0, 52.0, None, None),
    ("Ogunquit Beach", 1834, 137.3735, -4.7251, -4185, None, None, None, None, None),
    ("Stoer", 2142, 137.3781, -4.7256, -4170, 28.3, 10.0, 35.0, None, None),
    ("Highfield", 2227, 137.3776, -4.7285, -4147, 20.2, 5.0, 49.0, None, None),
    ("Rock Hall", 2265, 137.3782, -4.7284, -4144, None, None, None, None, None),
    ("Kilmarie", 2389, 137.3837, -4.7261, -4158, None, None, None, None, None),
    ("Glen Etive", 2492, 137.3835, -4.7303, -4133, None, 34.0, None, None, 34.0),
    ("Mary Anning", 2842, 137.3911, -4.7293, -4128, None, 28.0, None, None, None),
], columns=["nombre", "sol", "lon", "lat", "elevacion_m", "hematita_crist_pct", "arcilla_pct", "amorfo_pct",
            "tridimita_crist_pct", "sulfatos_crist_pct"])
fac = (100 - Q["arcilla_pct"].fillna(0) - Q["amorfo_pct"].fillna(0)) / 100
conocido = Q["arcilla_pct"].notna() & Q["amorfo_pct"].notna()
Q["hematita_pct"] = np.where(conocido, Q["hematita_crist_pct"] * fac, Q["hematita_crist_pct"]).round(2)
Q["esmectitas_pct"] = Q["arcilla_pct"]
Q["tridimita_pct"] = Q["tridimita_crist_pct"]
Q["sulfatos_pct"] = Q["sulfatos_crist_pct"]
Q["base_hematita"] = np.where(conocido, "muestra_total", np.where(Q["hematita_crist_pct"].notna(), "cristalina", ""))
Q.to_csv(os.path.join(PROC, "gale_puntos_quimica.csv"), index=False)

# ---------------------------------------------------------------- matriz de calibración
t = gzip.decompress(base64.b64decode(open(os.path.join(AQUI, "wp.b64")).read())).decode()
r = np.array([list(map(int, l.split(","))) for l in t.split("\n")])
r[:, :4] = np.cumsum(r[:, :4], axis=0)
M = pd.DataFrame({"sol": r[:, 0], "lon": 137.345 + r[:, 1] / 1e4, "lat": -4.58 - r[:, 2] / 1e4,
                  "elevacion_m": r[:, 3], "tilt_real_grados": np.abs(r[:, 4] / 10), "dist_m": r[:, 5] / 10})
M = M.sort_values(["sol"], kind="stable").reset_index(drop=True)
fi = np.clip(((G[3] - M["lat"]) / CDEG).astype(int), 0, GH - 1)
fj = np.clip(((M["lon"] - G[0]) / CDEG).astype(int), 0, GW - 1)
M["pendiente_grados"] = pend[fi, fj]
M["rugosidad"] = rug[fi, fj]
M["fraccion_oscura"] = osc[fi, fj]
M["distancia_duna_m"] = dist_duna[fi, fj]
M["inercia_termica_tiu"] = f_ti(np.column_stack([M["lat"], M["lon"]])).round(1)
M["albedo"] = f_alb(np.column_stack([M["lat"], M["lon"]])).round(4)
M["indice_polvo"] = np.nan            # DCI no transferido en esta ejecución
dsol = M["sol"].diff()
M["velocidad_efectiva_m_sol"] = np.where(dsol > 0, M["dist_m"] / dsol, np.nan)
M = unir_ambiental(M, AMB)


def riesgo(row):
    nivel = "bajo"
    for a_, b_, n_, _ in INCIDENTES:
        if a_ <= row.sol <= b_ and n_ == "alto":
            nivel = "alto"
        elif a_ <= row.sol <= b_ and nivel == "bajo":
            nivel = "medio"
    if row.tilt_real_grados >= 20:
        nivel = "alto"
    elif nivel == "bajo" and (row.tilt_real_grados >= 12 or row.pendiente_grados >= 15 or row.distancia_duna_m == 0):
        nivel = "medio"
    return nivel


M["nivel_riesgo_real"] = M.apply(riesgo, axis=1)
M.to_csv(os.path.join(PROC, "gale_matriz_calibracion.csv"), index=False)
print(f"rejilla: {ruta_tif}  celdas duna={int(duna.sum())}  TI {np.nanmin(ti):.0f}-{np.nanmax(ti):.0f}")
print(f"matriz: {len(M)} waypoints, sols {M.sol.min()}-{M.sol.max()}")
print(M[["pendiente_grados", "rugosidad", "inercia_termica_tiu", "albedo", "distancia_duna_m", "dosis_rad_uGy_h",
         "temp_suelo_K_media", "tilt_real_grados", "velocidad_efectiva_m_sol"]].describe().round(2).T)
print(M["nivel_riesgo_real"].value_counts())
