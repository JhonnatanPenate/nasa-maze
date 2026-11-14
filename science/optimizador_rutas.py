"""optimizador_rutas.py — Planetary Explorer

Minimiza la FUNCIÓN OBJETIVO de costo de misión (horas equivalentes)
con A* dependiente del tiempo en Gale Crater.

Función objetivo:
    min g = Σ c_ij

    c_ij = Δt·(1 + peso_incertidumbre·(1-R²))
         + peso_espera·horas_noche
         + penalizacion_cambio_suelo
         + peso_radiacion·dosis_uGy
         + peso_termico·exceso_K_h
         + peso_ciencia·(1-interes_mineral)·km

Uso:
  python optimizador_rutas.py --datos data --batch --sol 1360 --hora 9
"""
from __future__ import annotations

import argparse
import heapq
import json
import math
import os
import sys

import numpy as np
import pandas as pd
import rasterio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from crs_marte import METROS_POR_GRADO
except ImportError:
    try:
        from marte_crs import METROS_POR_GRADO
    except ImportError:
        METROS_POR_GRADO = math.pi * 3396190.0 / 180.0

# ---------------------------------------------------------------------------
# Parámetros de la función objetivo (unidad: horas equivalentes)
# ---------------------------------------------------------------------------
VELOCIDAD_MAXIMA_M_H = 1000.0          # velocidad nominal EVA (m/h)
INCLINACION_LIMITE_VELOCIDAD = 30.0    # tilt donde la velocidad cae a ~0
INCLINACION_MAXIMA_TRANSITABLE = 20.0  # celda bloqueada si tilt >= 20°
PENDIENTE_MAXIMA_TRANSITABLE = 25.0    # celda bloqueada si pendiente DEM >= 25°
FACTOR_DESLIZAMIENTO_ARENA = 0.60      # reduce velocidad en dunas

PESO_INCERTIDUMBRE_MODELO = 1.0        # w_inc en (1 + w_inc*(1-R²))
PENALIZACION_CAMBIO_SUELO = 0.25       # λ horas por cambio de régimen
PESO_ATRACCION_CIENTIFICA = 0.30       # w_ciencia por km lejos del mineral
PESO_DOSIS_RADIACION = 0.005           # w_rad por μGy
PESO_ESTRES_TERMICO = 0.05             # w_term por (K fuera de banda · h)
PESO_ESPERA_NOCTURNA = 0.5             # w_esp por hora de espera

BANDA_TERMICA_OPERATIVA_K = (230.0, 290.0)
VENTANA_SOLAR_LMST = (7.0, 17.0)       # solo se avanza de día
RADIO_INFLUENCIA_CIENCIA_M = 400.0
RADIO_LLEGADA_M = 60.0
RESOLUCION_HORARIA_BINS = 2            # 30 min por bin de estado
Z_SCORE_SEGURIDAD = 1.96               # Ŷ + 1.96·σ ≤ inclinación máxima
PORCENTAJE_CELDAS_VALIDAS_MIN = 0.90

COLUMNA_MINERAL = {
    "hematita": "hematita_pct",
    "esmectitas": "esmectitas_pct",
    "tridimita": "tridimita_pct",
    "sulfatos": "sulfatos_pct",
}


def clasificar_tipo_suelo(rugosidad, pendiente_grados, albedo, distancia_duna_m, fraccion_oscura):
    """Clasifica cada celda en un régimen de suelo (misma lógica que el script R)."""
    rugosidad = np.asarray(rugosidad, dtype=float)
    pendiente_grados = np.asarray(pendiente_grados, dtype=float)
    albedo = np.asarray(albedo, dtype=float)
    distancia_duna_m = np.asarray(distancia_duna_m, dtype=float)
    fraccion_oscura = np.asarray(fraccion_oscura, dtype=float)

    tipo = np.full(rugosidad.shape, "regolito_compacto", dtype=object)
    tipo[(rugosidad >= 1.10) | (pendiente_grados >= 8.0) | (albedo < 0.2291)] = "rocoso_fracturado"
    tipo[(rugosidad <= 0.60) & (pendiente_grados <= 7.0) & (albedo >= 0.2294)] = "lecho_rocoso_firme"
    tipo[(distancia_duna_m == 0) | (fraccion_oscura >= 0.5)] = "arena_dunas"
    return tipo


class MapaMision:
    """Mapa operativo de Gale: raster + modelos de inclinación + perfiles RAD/REMS."""

    def __init__(self, carpeta_datos: str, sol_referencia: int):
        carpeta_procesados = os.path.join(carpeta_datos, "processed")
        carpeta_ambiental = os.path.join(carpeta_datos, "raw", "ambiental")

        with rasterio.open(os.path.join(carpeta_procesados, "rejilla_ruta_90m.tif")) as src:
            bandas = {src.descriptions[k]: src.read(k + 1).astype(float) for k in range(src.count)}
            self.transformada = src.transform
            self.limites = src.bounds
            self.n_filas, self.n_columnas = src.height, src.width

        self.pendiente_grados = bandas["pendiente_grados"]
        self.rugosidad_m = bandas["rugosidad_m"]
        self.inercia_termica_tiu = bandas["inercia_termica_tiu"]
        self.albedo = bandas["albedo"]
        self.distancia_duna_m = bandas["distancia_duna_m"]
        self.fraccion_oscura = bandas["fraccion_oscura"]
        self.tamano_celda_m = abs(self.transformada.a) * METROS_POR_GRADO

        with open(os.path.join(carpeta_procesados, "modelos_por_suelo.json"), encoding="utf-8") as f:
            self.modelos_inclinacion = json.load(f)
        # Tablas: Excel (.xlsx/.xlsm) preferido; CSV opcional si existe.
        self.puntos_minerales = self._leer_tabla(
            os.path.join(carpeta_procesados, "gale_puntos_quimica.xlsx"),
            os.path.join(carpeta_procesados, "gale_puntos_quimica.xlsm"),
            os.path.join(carpeta_procesados, "gale_puntos_quimica.csv"),
        )

        self._cargar_perfiles_ambientales(carpeta_ambiental, sol_referencia)
        self._predecir_inclinacion_por_suelo()
        self.control_calidad = self._auditar_calidad_mapa()
        # Alias de atributos (compatibilidad API / código previo)
        self.bounds = self.limites
        self.transform = self.transformada
        self.h, self.w = self.n_filas, self.n_columnas
        self.pend = self.pendiente_grados
        self.rug = self.rugosidad_m
        self.ti = self.inercia_termica_tiu
        self.alb = self.albedo
        self.dduna = self.distancia_duna_m
        self.osc = self.fraccion_oscura
        self.celda_m = self.tamano_celda_m
        self.modelos = self.modelos_inclinacion
        self.quim = self.puntos_minerales
        self.auditoria_calidad = self.control_calidad
        self.rad_h = self.dosis_rad_por_hora
        self.t_med = self.temp_suelo_media_por_hora
        self.t_min = self.temp_suelo_min_por_hora
        self.t_max = self.temp_suelo_max_por_hora
        self.amb_diario = self.predictores_diarios

    @staticmethod
    def _leer_tabla(*rutas: str) -> pd.DataFrame:
        """Lee tabla columnar desde Excel (.xlsx/.xlsm/.xls) o CSV.

        Prioridad: primera ruta existente en el orden dado.
        Exige >= 2 columnas (rechaza el fallo 'todo pegado en columna A').
        """
        elegida = next((r for r in rutas if r and os.path.exists(r)), None)
        if elegida is None:
            raise FileNotFoundError(f"No se encontró tabla. Candidatos: {list(rutas)}")

        ext = os.path.splitext(elegida)[1].lower()
        if ext in {".xlsx", ".xlsm", ".xls"}:
            df = pd.read_excel(elegida, engine="openpyxl" if ext != ".xls" else None)
        elif ext == ".csv":
            df = pd.read_csv(elegida)
        else:
            raise ValueError(f"Extensión no soportada para tabla: {elegida}")

        df.columns = [str(c).strip() for c in df.columns]
        if df.shape[1] < 2:
            raise ValueError(
                f"Tabla mal formada (parece una sola columna): {elegida}. "
                "Usa el .xlsx/.xlsm con una columna por campo."
            )
        return df

    def _cargar_perfiles_ambientales(self, carpeta_ambiental: str, sol_referencia: int):
        rad = self._leer_tabla(
            os.path.join(carpeta_ambiental, "rad_dosis_observaciones.xlsx"),
            os.path.join(carpeta_ambiental, "rad_dosis_observaciones.xlsm"),
            os.path.join(carpeta_ambiental, "rad_dosis_observaciones.csv"),
        )
        rems = self._leer_tabla(
            os.path.join(carpeta_ambiental, "rems_resumen_horario.xlsx"),
            os.path.join(carpeta_ambiental, "rems_resumen_horario.xlsm"),
            os.path.join(carpeta_ambiental, "rems_resumen_horario.csv"),
        )
        self.sol_rad = int(rad["sol"].unique()[np.argmin(abs(rad["sol"].unique() - sol_referencia))])
        self.sol_rems = int(rems["sol"].unique()[np.argmin(abs(rems["sol"].unique() - sol_referencia))])

        rad_sol = rad[rad["sol"] == self.sol_rad].copy()
        rad_sol = rad_sol[rad_sol["dosis_e_uGy_h"] >= 0.7 * rad_sol["dosis_e_uGy_h"].median()]
        rad_sol["hora"] = rad_sol["hora_lmst"].astype(int) % 24
        dosis_por_hora = rad_sol.groupby("hora")["dosis_e_uGy_h"].mean()
        self.dosis_rad_por_hora = np.array(
            [dosis_por_hora.get(h, rad_sol["dosis_e_uGy_h"].mean()) for h in range(24)]
        )

        rems_sol = rems[rems["sol"] == self.sol_rems].set_index("hora_lmst")
        self.temp_suelo_media_por_hora = np.array([rems_sol.loc[h, "temp_suelo_K_media"] for h in range(24)])
        self.temp_suelo_min_por_hora = np.array([rems_sol.loc[h, "temp_suelo_K_min"] for h in range(24)])
        self.temp_suelo_max_por_hora = np.array([rems_sol.loc[h, "temp_suelo_K_max"] for h in range(24)])
        self.predictores_diarios = {
            "dosis_rad_uGy_h": float(rad_sol["dosis_e_uGy_h"].mean()),
            "temp_suelo_K_media": float(rems_sol["temp_suelo_K_media"].mean()),
        }

    def _predecir_inclinacion_por_suelo(self):
        tipo = clasificar_tipo_suelo(
            self.rugosidad_m, self.pendiente_grados, self.albedo,
            self.distancia_duna_m, self.fraccion_oscura,
        )
        self.tipo_suelo = tipo
        capas = {
            "pendiente_grados": self.pendiente_grados,
            "rugosidad": self.rugosidad_m,
            "inercia_termica_tiu": self.inercia_termica_tiu,
            "albedo": self.albedo,
        }
        forma = self.pendiente_grados.shape
        self.inclinacion_predicha = np.full(forma, np.nan)
        self.inclinacion_con_margen = np.full(forma, np.nan)
        self.sigma_modelo = np.full(forma, np.nan)
        self.r2_modelo = np.full(forma, np.nan)
        self.nombre_modelo = np.full(forma, "", dtype=object)

        for suelo in np.unique(tipo):
            modelo = self.modelos_inclinacion["modelos"].get(suelo, {})
            etiqueta = suelo
            if modelo.get("estado") != "ajustado":
                modelo = self.modelos_inclinacion["modelo_global"]
                etiqueta = "global"
            mascara = tipo == suelo
            y = np.full(mascara.sum(), modelo["coeficientes"]["(Intercept)"])
            for predictor in modelo["predictores"]:
                lo, hi = modelo["rango_predictores"][predictor]
                if predictor in capas:
                    x = capas[predictor][mascara]
                else:
                    x = np.full(mascara.sum(), self.predictores_diarios.get(predictor, 0.0))
                y = y + modelo["coeficientes"][predictor] * np.clip(x, lo, hi)
            sigma = float(modelo.get("sigma_residual", 0.0) or 0.0)
            y = np.maximum(y, 0)
            self.inclinacion_predicha[mascara] = y
            self.sigma_modelo[mascara] = sigma
            self.inclinacion_con_margen[mascara] = y + Z_SCORE_SEGURIDAD * sigma
            self.r2_modelo[mascara] = max(modelo["r2_ajustado"], 0)
            self.nombre_modelo[mascara] = f"{etiqueta}:{modelo['metodo']}"

        global_m = self.modelos_inclinacion["modelo_global"]
        y_global = np.full(forma, global_m["coeficientes"]["(Intercept)"])
        for predictor in global_m["predictores"]:
            lo, hi = global_m["rango_predictores"][predictor]
            if predictor in capas:
                x = capas[predictor]
            else:
                x = np.full(forma, self.predictores_diarios.get(predictor, 0.0))
            y_global = y_global + global_m["coeficientes"][predictor] * np.clip(x, lo, hi)
        self.inclinacion_modelo_global = np.maximum(y_global, 0)

        self.celda_bloqueada = (
            np.isnan(self.pendiente_grados)
            | (self.pendiente_grados >= PENDIENTE_MAXIMA_TRANSITABLE)
            | (self.inclinacion_predicha >= INCLINACION_MAXIMA_TRANSITABLE)
            | (self.inclinacion_con_margen > INCLINACION_MAXIMA_TRANSITABLE)
        )
        # Alias de capas predichas
        self.suelo = self.tipo_suelo
        self.tilt = self.inclinacion_predicha
        self.tilt_seguro = self.inclinacion_con_margen
        self.sigma = self.sigma_modelo
        self.r2 = self.r2_modelo
        self.modelo_usado = self.nombre_modelo
        self.tilt_global = self.inclinacion_modelo_global
        self.bloqueo = self.celda_bloqueada

    def _auditar_calidad_mapa(self):
        total = self.n_filas * self.n_columnas
        validas = int(np.sum(~np.isnan(self.pendiente_grados)))
        pct = validas / total
        conteo = {k: int(v) for k, v in zip(*np.unique(self.tipo_suelo, return_counts=True))}
        return {
            "celdas_totales": total,
            "celdas_validas": validas,
            "pct_celdas_validas": round(100 * pct, 2),
            "pct_validas": round(100 * pct, 2),
            "umbral_pct_celdas_validas": 100 * PORCENTAJE_CELDAS_VALIDAS_MIN,
            "umbral_pct_validas": 100 * PORCENTAJE_CELDAS_VALIDAS_MIN,
            "cobertura_ok": pct >= PORCENTAJE_CELDAS_VALIDAS_MIN,
            "margen_seguridad": (
                f"inclinacion + {Z_SCORE_SEGURIDAD}*sigma <= {INCLINACION_MAXIMA_TRANSITABLE}"
            ),
            "celdas_bloqueadas_por_margen": int(
                np.sum((self.inclinacion_con_margen > INCLINACION_MAXIMA_TRANSITABLE) & ~np.isnan(self.pendiente_grados))
            ),
            "conteo_tipos_suelo": conteo,
            "suelos": conteo,
        }

    def indice_celda(self, lon: float, lat: float):
        col, fila = ~self.transformada * (lon, lat)
        return int(fila), int(col)

    def celda(self, lon: float, lat: float):
        return self.indice_celda(lon, lat)

    def centro_celda(self, fila: int, col: int):
        return self.transformada * (col + 0.5, fila + 0.5)

    def centro(self, fila: int, col: int):
        return self.centro_celda(fila, col)

    def mapa_interes_cientifico(self, material: str):
        """Campo de atracción científica I(x,y) hacia el mineral objetivo."""
        return self.campo_ciencia(material)

    def campo_ciencia(self, material: str):
        columna = COLUMNA_MINERAL[material]
        puntos = self.puntos_minerales.dropna(subset=[columna])
        puntos = puntos[puntos[columna] > 0]
        interes = np.zeros(self.pendiente_grados.shape)
        ii, jj = np.indices(self.pendiente_grados.shape)
        lon, lat = self.transformada * (jj + 0.5, ii + 0.5)
        for _, p in puntos.iterrows():
            dist = np.hypot((lon - p.lon) * math.cos(math.radians(p.lat)), lat - p.lat) * METROS_POR_GRADO
            interes = np.maximum(
                interes,
                (p[columna] / puntos[columna].max()) * np.exp(-dist / RADIO_INFLUENCIA_CIENCIA_M),
            )
        objetivo = puntos.loc[puntos[columna].idxmax()]
        return interes, objetivo


def velocidad_efectiva(mapa: MapaMision, fila: int, col: int) -> float:
    v = VELOCIDAD_MAXIMA_M_H * max(0.1, 1 - mapa.inclinacion_predicha[fila, col] / INCLINACION_LIMITE_VELOCIDAD)
    if mapa.tipo_suelo[fila, col] == "arena_dunas":
        v *= (1 - FACTOR_DESLIZAMIENTO_ARENA)
    return v


def integrar_exposicion(mapa: MapaMision, hora_inicio: float, duracion_h: float):
    """Integra dosis RAD (μGy) y exceso térmico (K·h) en un intervalo."""
    dosis = exceso_termico = 0.0
    t = hora_inicio
    while t < hora_inicio + duracion_h - 1e-9:
        hora = int(t) % 24
        paso = min(math.floor(t) + 1, hora_inicio + duracion_h) - t
        dosis += mapa.dosis_rad_por_hora[hora] * paso
        temp = mapa.temp_suelo_media_por_hora[hora]
        exceso_termico += (
            max(0.0, BANDA_TERMICA_OPERATIVA_K[0] - temp)
            + max(0.0, temp - BANDA_TERMICA_OPERATIVA_K[1])
        ) * paso
        t += paso
    return dosis, exceso_termico


def aplicar_espera_nocturna(hora_actual: float):
    h = hora_actual % 24
    if VENTANA_SOLAR_LMST[0] <= h < VENTANA_SOLAR_LMST[1]:
        return hora_actual, 0.0
    siguiente_amanecer = (
        math.floor(hora_actual / 24) * 24
        + VENTANA_SOLAR_LMST[0]
        + (24 if h >= VENTANA_SOLAR_LMST[1] else 0)
    )
    return siguiente_amanecer, siguiente_amanecer - hora_actual


def minimizar_costo_ruta(mapa: MapaMision, origen, destino, hora_salida, interes_cientifico, usar_modelo_por_suelo=True):
    """A*: minimiza g = Σ c_ij (función objetivo). Devuelve ruta y nodos expandidos."""
    (fila_o, col_o), (fila_d, col_d) = origen, destino
    metro_celda = mapa.tamano_celda_m
    vecinos = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]

    if usar_modelo_por_suelo:
        r2_max = float(np.nanmax(mapa.r2_modelo))
    else:
        r2_max = mapa.modelos_inclinacion["modelo_global"]["r2_ajustado"]

    costo_minimo_por_metro = (
        (1 + PESO_INCERTIDUMBRE_MODELO * (1 - r2_max)) / VELOCIDAD_MAXIMA_M_H
        + PESO_DOSIS_RADIACION * float(mapa.dosis_rad_por_hora.min()) / VELOCIDAD_MAXIMA_M_H
    )
    heuristica0 = math.hypot(fila_o - fila_d, col_o - col_d) * metro_celda * costo_minimo_por_metro

    # estado: (hora, costo_g, dosis, termico, espera, fila, col, padre)
    nodo_raiz = (hora_salida, 0.0, 0.0, 0.0, 0.0, fila_o, col_o, None)
    contador = 0
    frontera = [(heuristica0, 0.0, contador, nodo_raiz)]
    mejor_costo = {(fila_o, col_o, int(hora_salida % 24 * RESOLUCION_HORARIA_BINS)): 0.0}
    nodos_expandidos = 0

    while frontera:
        _f, costo_g, _, nodo = heapq.heappop(frontera)
        hora, _, dosis0, term0, espera0, fila, col, _padre = nodo
        clave = (fila, col, int(hora % 24 * RESOLUCION_HORARIA_BINS))
        if mejor_costo.get(clave, math.inf) < costo_g - 1e-12:
            continue
        nodos_expandidos += 1

        if math.hypot(fila - fila_d, col - col_d) * metro_celda <= RADIO_LLEGADA_M or (fila, col) == (fila_d, col_d):
            ruta = []
            while nodo is not None:
                ruta.append({
                    "fila": nodo[5], "col": nodo[6], "hora": nodo[0],
                    "costo_objetivo": nodo[1], "dosis_uGy": nodo[2],
                    "estres_termico": nodo[3], "espera_h": nodo[4],
                    # alias internos cortos para reconstrucción
                    "i": nodo[5], "j": nodo[6], "t": nodo[0], "g": nodo[1],
                    "dosis": nodo[2], "term": nodo[3], "espera": nodo[4],
                })
                nodo = nodo[7]
            return ruta[::-1], nodos_expandidos

        for dfila, dcol in vecinos:
            nf, nc = fila + dfila, col + dcol
            if not (0 <= nf < mapa.n_filas and 0 <= nc < mapa.n_columnas) or mapa.celda_bloqueada[nf, nc]:
                continue
            distancia_m = metro_celda * (math.sqrt(2) if dfila and dcol else 1.0)
            hora_salida_celda, horas_espera = aplicar_espera_nocturna(hora)

            if usar_modelo_por_suelo:
                vel = velocidad_efectiva(mapa, nf, nc)
                factor_incertidumbre = 1 + PESO_INCERTIDUMBRE_MODELO * (1 - mapa.r2_modelo[nf, nc])
                penalizacion_suelo = (
                    PENALIZACION_CAMBIO_SUELO
                    if mapa.tipo_suelo[nf, nc] != mapa.tipo_suelo[fila, col]
                    else 0.0
                )
            else:
                vel = VELOCIDAD_MAXIMA_M_H * max(
                    0.1, 1 - mapa.inclinacion_modelo_global[nf, nc] / INCLINACION_LIMITE_VELOCIDAD
                )
                factor_incertidumbre = 1 + PESO_INCERTIDUMBRE_MODELO * (1 - r2_max)
                penalizacion_suelo = 0.0

            delta_t = distancia_m / vel
            dosis, termico = integrar_exposicion(mapa, hora, (hora_salida_celda - hora) + delta_t)

            # ----- FUNCIÓN OBJETIVO (costo del paso) -----
            costo_paso = (
                delta_t * factor_incertidumbre
                + PESO_ESPERA_NOCTURNA * horas_espera
                + penalizacion_suelo
                + PESO_DOSIS_RADIACION * dosis
                + PESO_ESTRES_TERMICO * termico
                + PESO_ATRACCION_CIENTIFICA * (1 - interes_cientifico[nf, nc]) * distancia_m / 1000
            )
            nuevo_g = costo_g + costo_paso
            nueva_hora = hora_salida_celda + delta_t
            nueva_clave = (nf, nc, int(nueva_hora % 24 * RESOLUCION_HORARIA_BINS))
            if nuevo_g < mejor_costo.get(nueva_clave, math.inf):
                mejor_costo[nueva_clave] = nuevo_g
                contador += 1
                heuristica = math.hypot(nf - fila_d, nc - col_d) * metro_celda * costo_minimo_por_metro
                heapq.heappush(
                    frontera,
                    (
                        nuevo_g + heuristica,
                        nuevo_g,
                        contador,
                        (
                            nueva_hora, nuevo_g,
                            dosis0 + dosis, term0 + termico, espera0 + horas_espera,
                            nf, nc, nodo,
                        ),
                    ),
                )
    return None, nodos_expandidos


def formato_hora_lmst(hora_absoluta: float) -> str:
    sol, h = divmod(hora_absoluta, 24)
    return f"S+{int(sol)} {int(h):02d}:{int(round((h % 1) * 60)) % 60:02d}"


def tabla_tramos_ruta(mapa: MapaMision, ruta: list, largo_max_m: float = 600.0) -> pd.DataFrame:
    filas, actual = [], None
    for a, b in zip(ruta[:-1], ruta[1:]):
        dist = mapa.tamano_celda_m * math.hypot(a["i"] - b["i"], a["j"] - b["j"])
        suelo = mapa.tipo_suelo[b["i"], b["j"]]
        if actual is None or suelo != actual["tipo_suelo"] or actual["distancia_m"] >= largo_max_m:
            if actual:
                filas.append(actual)
            lon0, lat0 = mapa.centro_celda(a["i"], a["j"])
            actual = {
                "tipo_suelo": suelo,
                "modelo_usado": mapa.nombre_modelo[b["i"], b["j"]],
                "r2_ajustado": mapa.r2_modelo[b["i"], b["j"]],
                "distancia_m": 0.0,
                "hora_inicio": a["t"],
                "dosis_inicio": a["dosis"],
                "inclinaciones": [],
                "pendientes": [],
                "horas": set(),
                "lon0": lon0, "lat0": lat0,
                "espera_h": 0.0,
            }
        actual["distancia_m"] += dist
        actual["hora_fin"], actual["dosis_fin"] = b["t"], b["dosis"]
        actual["espera_h"] = b["espera"]
        actual["inclinaciones"].append(mapa.inclinacion_predicha[b["i"], b["j"]])
        actual["pendientes"].append(mapa.pendiente_grados[b["i"], b["j"]])
        for t in np.arange(a["t"], b["t"] + 1e-9, 0.25):
            actual["horas"].add(int(t) % 24)
        actual["lon1"], actual["lat1"] = mapa.centro_celda(b["i"], b["j"])
    filas.append(actual)

    out = []
    for k, f in enumerate(filas, 1):
        hs = sorted(f["horas"])
        out.append({
            "tramo": k,
            "hora_lmst_inicio": formato_hora_lmst(f["hora_inicio"]),
            "hora_lmst_fin": formato_hora_lmst(f["hora_fin"]),
            "tipo_suelo": f["tipo_suelo"],
            "modelo_usado": f["modelo_usado"],
            "r2_ajustado": round(f["r2_ajustado"], 3),
            "distancia_m": round(f["distancia_m"]),
            "pendiente_media_grados": round(float(np.mean(f["pendientes"])), 1),
            "inclinacion_media_grados": round(float(np.mean(f["inclinaciones"])), 1),
            "inclinacion_max_grados": round(float(np.max(f["inclinaciones"])), 1),
            "dosis_tramo_uGy": round(f["dosis_fin"] - f["dosis_inicio"], 1),
            "dosis_acumulada_uGy": round(f["dosis_fin"], 1),
            "temp_suelo_K": f"{min(mapa.temp_suelo_min_por_hora[h] for h in hs):.0f}-{max(mapa.temp_suelo_max_por_hora[h] for h in hs):.0f}",
            "lon_inicio": round(f["lon0"], 4),
            "lat_inicio": round(f["lat0"], 4),
            "lon_fin": round(f["lon1"], 4),
            "lat_fin": round(f["lat1"], 4),
            # alias columnas cortas (API / tablas previas)
            "lmst_inicio": formato_hora_lmst(f["hora_inicio"]),
            "lmst_fin": formato_hora_lmst(f["hora_fin"]),
            "suelo": f["tipo_suelo"],
            "modelo": f["modelo_usado"],
            "R2_aj": round(f["r2_ajustado"], 3),
            "largo_m": round(f["distancia_m"]),
            "pendiente_media": round(float(np.mean(f["pendientes"])), 1),
            "tilt_pred_medio": round(float(np.mean(f["inclinaciones"])), 1),
            "tilt_pred_max": round(float(np.max(f["inclinaciones"])), 1),
            "dosis_acum_uGy": round(f["dosis_fin"], 1),
            "T_suelo_K": (
                f"{min(mapa.temp_suelo_min_por_hora[h] for h in hs):.0f}-"
                f"{max(mapa.temp_suelo_max_por_hora[h] for h in hs):.0f}"
            ),
            "lon_ini": round(f["lon0"], 4),
            "lat_ini": round(f["lat0"], 4),
        })
    return pd.DataFrame(out)


def contar_celdas_arena(mapa: MapaMision, ruta: list) -> int:
    return sum(mapa.tipo_suelo[n["i"], n["j"]] == "arena_dunas" for n in ruta)


def celdas_arena_linea_recta(mapa: MapaMision, origen, destino):
    n = int(max(abs(origen[0] - destino[0]), abs(origen[1] - destino[1]))) + 1
    filas = np.round(np.linspace(origen[0], destino[0], n)).astype(int)
    cols = np.round(np.linspace(origen[1], destino[1], n)).astype(int)
    return int(sum(mapa.tipo_suelo[i, j] == "arena_dunas" for i, j in zip(filas, cols))), n


def calcular_ruta_optima(mapa: MapaMision, lon: float, lat: float, material: str, hora_salida: float):
    interes, objetivo = mapa.mapa_interes_cientifico(material)
    origen = mapa.indice_celda(lon, lat)
    destino = mapa.indice_celda(objetivo.lon, objetivo.lat)
    mapa.celda_bloqueada[origen] = mapa.celda_bloqueada[destino] = False

    ruta, nodos = minimizar_costo_ruta(mapa, origen, destino, hora_salida, interes, usar_modelo_por_suelo=True)
    if ruta is None:
        return None
    tramos = tabla_tramos_ruta(mapa, ruta)
    ultimo = ruta[-1]
    distancia_total_m = float(tramos["distancia_m"].sum())

    ruta_global, _ = minimizar_costo_ruta(mapa, origen, destino, hora_salida, interes, usar_modelo_por_suelo=False)
    contrafactual = {
        "celdas_arena": contar_celdas_arena(mapa, ruta_global),
        "celdas_totales": len(ruta_global),
        "distancia_km": round(
            sum(mapa.tamano_celda_m * math.hypot(p["i"] - q["i"], p["j"] - q["j"])
                for p, q in zip(ruta_global[:-1], ruta_global[1:])) / 1000, 2
        ),
        "llegada_lmst": formato_hora_lmst(ruta_global[-1]["t"]),
    }
    t, dos, horas_en_arena = hora_salida, 0.0, 0.0
    for p, q in zip(ruta_global[:-1], ruta_global[1:]):
        dd = mapa.tamano_celda_m * math.hypot(p["i"] - q["i"], p["j"] - q["j"])
        t2, _esp = aplicar_espera_nocturna(t)
        dt = dd / velocidad_efectiva(mapa, q["i"], q["j"])
        if mapa.tipo_suelo[q["i"], q["j"]] == "arena_dunas":
            horas_en_arena += dt
        dos += integrar_exposicion(mapa, t, (t2 - t) + dt)[0]
        t = t2 + dt
    contrafactual["llegada_real_con_arena"] = formato_hora_lmst(t)
    contrafactual["horas_en_arena"] = round(horas_en_arena, 2)
    contrafactual["dosis_real_uGy"] = round(dos, 1)

    from scipy.ndimage import distance_transform_edt
    dist_arena = distance_transform_edt(mapa.tipo_suelo != "arena_dunas") * mapa.tamano_celda_m
    arena_recta, n_recta = celdas_arena_linea_recta(mapa, origen, destino)
    bagnold = {
        "distancia_minima_a_duna_m": round(float(min(dist_arena[n["i"], n["j"]] for n in ruta))),
        "celdas_arena_linea_recta": arena_recta,
        "celdas_linea_recta": n_recta,
        "celdas_arena_ruta_optima": contar_celdas_arena(mapa, ruta),
        "ruta_modelo_global": contrafactual,
        "horas_ahorradas_en_arena": round(horas_en_arena, 2),
    }
    resumen = {
        "celdas": len(ruta),
        "distancia_km": round(distancia_total_m / 1000, 2),
        "largo_km": round(distancia_total_m / 1000, 2),
        "llegada_lmst": formato_hora_lmst(ultimo["t"]),
        "llegada": formato_hora_lmst(ultimo["t"]),
        "dosis_uGy": round(ultimo["dosis"], 1),
        "espera_nocturna_h": round(ultimo["espera"], 2),
        "espera_h": round(ultimo["espera"], 2),
        "costo_objetivo": round(ultimo["g"], 3),
        "costo": round(ultimo["g"], 3),
        "nodos_expandidos": nodos,
        "objetivo_mineral": objetivo.nombre,
        "objetivo": objetivo.nombre,
        "sol_rad": mapa.sol_rad,
        "sol_rems": mapa.sol_rems,
        "material": material,
    }
    # alias Bagnold / contrafactual (API previa)
    bagnold["celdas_duna_ruta_adaptativa"] = bagnold["celdas_arena_ruta_optima"]
    bagnold["contrafactual_modelo_global"] = {
        "celdas_duna": contrafactual["celdas_arena"],
        "celdas": contrafactual["celdas_totales"],
        "largo_km": contrafactual["distancia_km"],
        "llegada": contrafactual["llegada_lmst"],
        "llegada_real_con_arena": contrafactual["llegada_real_con_arena"],
        "horas_en_arena": contrafactual["horas_en_arena"],
        "dosis_real_uGy": contrafactual["dosis_real_uGy"],
    }
    bagnold["distancia_min_ruta_a_duna_m"] = bagnold["distancia_minima_a_duna_m"]
    return {
        "ruta": ruta,
        "ruta_modelo_global": ruta_global,
        "ruta_cf": ruta_global,
        "tramos": tramos,
        "objetivo_mineral": objetivo,
        "objetivo": objetivo,
        "mapa_interes": interes,
        "I": interes,
        "origen": origen,
        "destino": destino,
        "nodos_expandidos": nodos,
        "nexp": nodos,
        "distancia_m": distancia_total_m,
        "largo_m": distancia_total_m,
        "comparativa_dunas": bagnold,
        "bagnold": bagnold,
        "resumen": resumen,
    }


def guardar_ruta_optima(mapa, resultado, material, sol, hora, carpeta_salida):
    tramos = resultado["tramos"]
    ruta, ruta_global = resultado["ruta"], resultado["ruta_modelo_global"]
    objetivo = resultado["objetivo_mineral"]
    ultimo = ruta[-1]
    columnas_claras = [
        "tramo", "hora_lmst_inicio", "hora_lmst_fin", "tipo_suelo", "modelo_usado",
        "r2_ajustado", "distancia_m", "pendiente_media_grados", "inclinacion_media_grados",
        "inclinacion_max_grados", "dosis_tramo_uGy", "dosis_acumulada_uGy", "temp_suelo_K",
        "lon_inicio", "lat_inicio", "lon_fin", "lat_fin",
    ]
    tabla = tramos[[c for c in columnas_claras if c in tramos.columns]].copy()
    xlsx_tramos = os.path.join(carpeta_salida, f"ruta_{material}_tramos.xlsx")
    try:
        from pathlib import Path as _Path
        from exportar_tablas_excel import dataframe_a_xlsx
        dataframe_a_xlsx(tabla, _Path(xlsx_tramos), sheet="Tramos")
    except Exception:
        with pd.ExcelWriter(xlsx_tramos, engine="openpyxl") as w:
            tabla.to_excel(w, sheet_name="Tramos", index=False)
    # CSV opcional (desactivado por defecto: paquete data_usar es Excel-only)
    if os.environ.get("PLANETARY_ESCRIBIR_CSV", "").strip() in {"1", "true", "TRUE", "yes"}:
        tabla.to_csv(os.path.join(carpeta_salida, f"ruta_{material}_tramos.csv"), index=False)

    features = []
    for a, b in zip(ruta[:-1], ruta[1:]):
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [list(mapa.centro_celda(a["i"], a["j"])), list(mapa.centro_celda(b["i"], b["j"]))],
            },
            "properties": {
                "material": material,
                "tipo_suelo": mapa.tipo_suelo[b["i"], b["j"]],
                "modelo_usado": mapa.nombre_modelo[b["i"], b["j"]],
                "capa": "ruta_optima",
            },
        })
    features.append({
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [list(mapa.centro_celda(n["i"], n["j"])) for n in ruta_global],
        },
        "properties": {"nombre": "ruta_modelo_global", "capa": "contrafactual"},
    })
    coords = [list(mapa.centro_celda(n["i"], n["j"])) for n in ruta]
    features.insert(0, {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coords},
        "properties": {
            "material": material,
            "objetivo_mineral": objetivo.nombre,
            "sol_referencia": sol,
            "hora_salida": hora,
            "llegada_lmst": formato_hora_lmst(ultimo["t"]),
            "dosis_uGy": round(ultimo["dosis"], 1),
            "distancia_km": round(resultado["distancia_m"] / 1000, 2),
            "capa": "ruta_optima_completa",
        },
    })
    geojson = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "IAU_2015:49900"}},
        "features": features,
    }
    json.dump(geojson, open(os.path.join(carpeta_salida, f"ruta_{material}.geojson"), "w"), indent=1)
    json.dump(
        {
            "resumen": resultado["resumen"],
            "comparativa_dunas": resultado["comparativa_dunas"],
            "control_calidad": mapa.control_calidad,
        },
        open(os.path.join(carpeta_salida, f"ruta_{material}_resumen.json"), "w"),
        indent=1,
        ensure_ascii=False,
    )


def exportar_bitacora_excel(mapa: MapaMision, resultados: dict, carpeta_salida: str) -> str:
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    try:
        from exportar_tablas_excel import formatear_hoja
    except ImportError:
        formatear_hoja = None

    modelos = mapa.modelos_inclinacion
    filas_auditoria = []
    for nombre, m in list(modelos["modelos"].items()) + [("global", modelos["modelo_global"])]:
        if m.get("estado") != "ajustado":
            filas_auditoria.append({
                "tipo_suelo": nombre, "n_observaciones": m.get("n", 0),
                "metodo": "insuficiente", "r2_ajustado": None, "sigma_residual": None,
            })
            continue
        s = m["supuestos"]
        filas_auditoria.append({
            "tipo_suelo": nombre,
            "n_observaciones": m["n"],
            "metodo": m["metodo"],
            "r2_ajustado": m["r2_ajustado"],
            "sigma_residual": m["sigma_residual"],
            "shapiro_p": s.get("shapiro_p"),
            "breusch_pagan_p": s.get("bp_p"),
            "durbin_watson_p": s.get("dw_p"),
            "vif_maximo": s.get("vif_max"),
            "rho_ar1": m.get("rho_ar1"),
            "tipo_error_estandar": m.get("se_tipo", "OLS"),
            "normalidad_ok": s.get("normalidad_ok"),
            "homocedasticidad_ok": s.get("homocedasticidad_ok"),
            "independencia_ok": s.get("independencia_ok"),
            "se_robustos_aplicados": s.get("se_robustos_aplicados", False),
        })

    filas_coef = []
    for nombre, m in list(modelos["modelos"].items()) + [("global", modelos["modelo_global"])]:
        if m.get("estado") != "ajustado":
            continue
        for coef, val in m["coeficientes"].items():
            filas_coef.append({
                "tipo_suelo": nombre,
                "variable": coef,
                "coeficiente_beta": val,
                "error_estandar": m["error_estandar"].get(coef),
                "error_estandar_HC3": (m.get("error_estandar_robusto_HC3") or {}).get(coef),
                "p_valor": m["p_valores"].get(coef),
                "metodo": m["metodo"],
                "r2_ajustado": m["r2_ajustado"],
                "sigma_residual": m["sigma_residual"],
                "velocidad_mediana_m_sol": m.get("velocidad_mediana_m_sol"),
                "tipo_error_estandar": m.get("se_tipo"),
            })
    for nombre, valor in [
        ("inclinacion_maxima_transitable", INCLINACION_MAXIMA_TRANSITABLE),
        ("z_score_seguridad", Z_SCORE_SEGURIDAD),
        ("pct_celdas_validas_min", PORCENTAJE_CELDAS_VALIDAS_MIN),
        ("velocidad_maxima_m_h", VELOCIDAD_MAXIMA_M_H),
        ("factor_deslizamiento_arena", FACTOR_DESLIZAMIENTO_ARENA),
        ("peso_incertidumbre_modelo", PESO_INCERTIDUMBRE_MODELO),
        ("peso_dosis_radiacion", PESO_DOSIS_RADIACION),
        ("peso_estres_termico", PESO_ESTRES_TERMICO),
        ("peso_espera_nocturna", PESO_ESPERA_NOCTURNA),
        ("peso_atraccion_cientifica", PESO_ATRACCION_CIENTIFICA),
        ("penalizacion_cambio_suelo", PENALIZACION_CAMBIO_SUELO),
    ]:
        filas_coef.append({
            "tipo_suelo": "_parametro_objetivo",
            "variable": nombre,
            "coeficiente_beta": valor,
            "error_estandar": None, "error_estandar_HC3": None, "p_valor": None,
            "metodo": "parametro_funcion_objetivo",
            "r2_ajustado": None, "sigma_residual": None,
            "velocidad_mediana_m_sol": None, "tipo_error_estandar": None,
        })

    filas_rutas = []
    for material, res in resultados.items():
        for _, row in res["tramos"].iterrows():
            filas_rutas.append({
                "material_objetivo": material,
                "nombre_objetivo": res["resumen"]["objetivo_mineral"],
                "tramo": row["tramo"],
                "hora_lmst_inicio": row["hora_lmst_inicio"],
                "hora_lmst_fin": row["hora_lmst_fin"],
                "tipo_suelo": row["tipo_suelo"],
                "modelo_usado": row["modelo_usado"],
                "r2_ajustado": row["r2_ajustado"],
                "distancia_m": row["distancia_m"],
                "inclinacion_media_grados": row["inclinacion_media_grados"],
                "inclinacion_max_grados": row["inclinacion_max_grados"],
                "dosis_tramo_uGy": row["dosis_tramo_uGy"],
                "dosis_acumulada_uGy": row["dosis_acumulada_uGy"],
                "temp_suelo_K": row["temp_suelo_K"],
                "celdas_arena_en_ruta": res["comparativa_dunas"]["celdas_arena_ruta_optima"],
                "distancia_total_km": res["resumen"]["distancia_km"],
                "dosis_total_uGy": res["resumen"]["dosis_uGy"],
                "llegada_lmst": res["resumen"]["llegada_lmst"],
                "espera_nocturna_h": res["resumen"]["espera_nocturna_h"],
                "costo_objetivo": res["resumen"]["costo_objetivo"],
            })

    ruta_xlsx = os.path.join(carpeta_salida, "Bitacora_Calidad_Marte.xlsx")
    hojas = {
        "Auditoria_Modelos": pd.DataFrame(filas_auditoria),
        "Coeficientes_Objetivo": pd.DataFrame(filas_coef),
        "Objetivos_Minerales": mapa.puntos_minerales.copy(),
        "Rutas_Optimas": pd.DataFrame(filas_rutas),
    }
    with pd.ExcelWriter(ruta_xlsx, engine="openpyxl") as writer:
        for nombre, df in hojas.items():
            if df.shape[1] < 2:
                raise ValueError(f"Hoja {nombre} no tiene columnas separadas")
            df.to_excel(writer, sheet_name=nombre, index=False)
            if formatear_hoja:
                formatear_hoja(writer.book[nombre])
            else:
                fill = PatternFill("solid", fgColor="D6EAF8")
                font_b = Font(bold=True, name="Calibri")
                align = Alignment(horizontal="center", vertical="center", wrap_text=True)
                thin = Border(*(Side(style="thin"),) * 4)
                sheet = writer.book[nombre]
                for cell in sheet[1]:
                    cell.fill = fill
                    cell.font = font_b
                    cell.alignment = align
                    cell.border = thin
                for row in sheet.iter_rows(min_row=2):
                    for cell in row:
                        cell.alignment = align
                        cell.font = Font(name="Calibri")
                for col in sheet.columns:
                    sheet.column_dimensions[col[0].column_letter].width = 18
    # verificación post-escritura
    for nombre in hojas:
        chk = pd.read_excel(ruta_xlsx, sheet_name=nombre)
        if chk.shape[1] < 2 or len(chk) == 0:
            raise AssertionError(f"Bitácora inválida en hoja {nombre}: shape={chk.shape}")
    return ruta_xlsx


def dibujar_mapa_rutas(mapa: MapaMision, resultados: dict, carpeta_salida: str) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    fig, ax = plt.subplots(figsize=(10, 12))
    extent = [mapa.limites.left, mapa.limites.right, mapa.limites.bottom, mapa.limites.top]
    im = ax.imshow(mapa.pendiente_grados, extent=extent, origin="upper", cmap="copper", alpha=0.85)
    plt.colorbar(im, ax=ax, fraction=0.03, label="Pendiente (°)")
    duna = (mapa.tipo_suelo == "arena_dunas").astype(float)
    duna[duna == 0] = np.nan
    ax.imshow(duna, extent=extent, origin="upper", cmap=ListedColormap(["#c0392b"]), alpha=0.55)

    colores = {"hematita": "#e74c3c", "esmectitas": "#2980b9", "tridimita": "#27ae60"}
    for material, res in resultados.items():
        coords = np.array([mapa.centro_celda(n["i"], n["j"]) for n in res["ruta"]])
        ax.plot(
            coords[:, 0], coords[:, 1], color=colores.get(material, "white"), lw=2.2,
            label=f"{material} → {res['objetivo_mineral'].nombre} ({res['resumen']['distancia_km']} km)",
        )
        ax.scatter([res["objetivo_mineral"].lon], [res["objetivo_mineral"].lat],
                   c=colores.get(material, "white"), s=60, zorder=5, edgecolors="k", linewidths=0.5)
    ax.scatter([137.4416], [-4.5895], c="yellow", marker="*", s=160, zorder=6, label="Bradbury Landing")
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_xlabel("Longitud E (°)")
    ax.set_ylabel("Latitud (°)")
    ax.set_title("Planetary Explorer — Rutas óptimas (min costo de misión)")
    ax.legend(loc="lower left", fontsize=8)
    ax.set_aspect("equal")
    fig.tight_layout()
    ruta_png = os.path.join(carpeta_salida, "mapa_rutas_gale.png")
    fig.savefig(ruta_png, dpi=150)
    plt.close(fig)
    return ruta_png


def main():
    global VELOCIDAD_MAXIMA_M_H
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datos", default="data", help="Carpeta con processed/ y raw/")
    ap.add_argument("--lon", type=float, default=137.4416)
    ap.add_argument("--lat", type=float, default=-4.5895)
    ap.add_argument("--material", choices=list(COLUMNA_MINERAL), default="hematita")
    ap.add_argument("--sol", type=int, default=1360)
    ap.add_argument("--hora", type=float, default=9.0)
    ap.add_argument("--vmax", type=float, default=VELOCIDAD_MAXIMA_M_H)
    ap.add_argument("--salida", default=None)
    ap.add_argument("--batch", action="store_true", help="3 rutas + Excel + mapa")
    args = ap.parse_args()
    VELOCIDAD_MAXIMA_M_H = args.vmax

    mapa = MapaMision(args.datos, args.sol)
    print("Control de calidad:", json.dumps(mapa.control_calidad, ensure_ascii=False))
    if not mapa.control_calidad["cobertura_ok"]:
        sys.exit(
            f"QC fallido: {mapa.control_calidad['pct_celdas_validas']}% celdas válidas "
            f"(mínimo {100 * PORCENTAJE_CELDAS_VALIDAS_MIN:.0f}%)"
        )

    carpeta_salida = args.salida or os.path.join(args.datos, "processed")
    os.makedirs(carpeta_salida, exist_ok=True)
    materiales = ["hematita", "esmectitas", "tridimita"] if args.batch else [args.material]
    resultados = {}
    for material in materiales:
        print(f"\n========== {material} ==========")
        res = calcular_ruta_optima(mapa, args.lon, args.lat, material, args.hora)
        if res is None:
            print(f"Sin ruta factible para {material}")
            continue
        resultados[material] = res
        r = res["resumen"]
        print(
            f"Origen ({args.lon}, {args.lat}) -> {r['objetivo_mineral']}: "
            f"{r['distancia_km']} km, llegada {r['llegada_lmst']}, "
            f"dosis {r['dosis_uGy']} uGy, costo_objetivo={r['costo_objetivo']}"
        )
        print(res["tramos"].drop(columns=["lon_inicio", "lat_inicio"], errors="ignore").to_string(index=False))
        print("Comparativa dunas:", json.dumps(res["comparativa_dunas"], ensure_ascii=False))
        guardar_ruta_optima(mapa, res, material, args.sol, args.hora, carpeta_salida)

    if resultados:
        np.save(
            os.path.join(carpeta_salida, "_rejilla_suelo_tilt.npy"),
            np.stack([
                (mapa.tipo_suelo == "arena_dunas").astype(float),
                mapa.inclinacion_predicha,
                mapa.celda_bloqueada.astype(float),
                next(iter(resultados.values()))["mapa_interes"],
            ]),
        )
    if args.batch and resultados:
        xlsx = exportar_bitacora_excel(mapa, resultados, carpeta_salida)
        png = dibujar_mapa_rutas(mapa, resultados, carpeta_salida)
        print(f"\nExportado: {xlsx}")
        print(f"Mapa: {png}")


# ---------------------------------------------------------------------------
# Alias de compatibilidad (backend / código previo)
# ---------------------------------------------------------------------------
MATERIALES = COLUMNA_MINERAL
V_MAX_M_H = VELOCIDAD_MAXIMA_M_H
TILT_BLOQUEO = INCLINACION_MAXIMA_TRANSITABLE
PCT_VALIDAS_MIN = PORCENTAJE_CELDAS_VALIDAS_MIN
Z_SEGURIDAD = Z_SCORE_SEGURIDAD
DESLIZAMIENTO_ARENA = FACTOR_DESLIZAMIENTO_ARENA
Entorno = MapaMision
a_estrella = minimizar_costo_ruta
tramos = tabla_tramos_ruta
calcular_ruta = calcular_ruta_optima
clasificar_suelo = clasificar_tipo_suelo
hhmm = formato_hora_lmst
exportar_excel = exportar_bitacora_excel
dibujar_mapa = dibujar_mapa_rutas


if __name__ == "__main__":
    main()
