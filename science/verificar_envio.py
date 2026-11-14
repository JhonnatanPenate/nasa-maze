"""Verificación pre-envío del repo planetary-explorer-fase2-3."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from optimizador_rutas import MapaMision, calcular_ruta_optima

errs: list[str] = []
oks: list[str] = []


def ok(m: str) -> None:
    oks.append(m)


def err(m: str) -> None:
    errs.append(m)


# Limpieza
if list(ROOT.glob("_*.py")):
    err(f"Basura en root: {list(ROOT.glob('_*.py'))}")
else:
    ok("Sin scripts temporales _* en root")
if (ROOT / "salida_R.txt").exists():
    err("salida_R.txt presente")
else:
    ok("Sin salida_R.txt")
# Ignorar __pycache__ bajo scripts/ (se crea al importar durante esta verificación)
pycaches = [p for p in ROOT.rglob("__pycache__") if "scripts" not in p.parts]
if pycaches:
    err(f"Quedan __pycache__: {pycaches}")
else:
    ok("Sin __pycache__ fuera de scripts/")
if (ROOT / "frontend/node_modules").exists():
    err("node_modules presente (no enviar; npm install)")
else:
    ok("Sin node_modules (correcto para envío)")
if list((ROOT / "data").rglob("*.csv")) or list((ROOT / "data_usar").rglob("*.csv")):
    err("Quedan CSV")
else:
    ok("0 CSV en data/ y data_usar/")

# Estructura mínima
for p in [
    "README.md",
    ".gitignore",
    "requirements.txt",
    "start.bat",
    "start.sh",
    "backend/main.py",
    "backend/requirements.txt",
    "frontend/package.json",
    "frontend/src/App.tsx",
    "scripts/optimizador_rutas.py",
    "scripts/modelos_inclinacion_por_suelo.R",
    "scripts/exportar_tablas_excel.py",
    "data/processed/rejilla_ruta_90m.tif",
    "data/processed/modelos_por_suelo.json",
    "data/processed/gale_matriz_calibracion.xlsx",
    "data/processed/gale_puntos_quimica.xlsx",
    "data/raw/ambiental/rad_dosis_observaciones.xlsx",
    "data/raw/ambiental/rems_resumen_horario.xlsx",
    "data_usar/04_documentacion/HANDOFF_SOFTWARE.md",
]:
    if (ROOT / p).exists():
        ok(f"hay {p}")
    else:
        err(f"falta {p}")

# Excel columnar
for base in (ROOT / "data", ROOT / "data_usar"):
    for p in base.rglob("*.xlsx"):
        for sh in pd.ExcelFile(p).sheet_names:
            df = pd.read_excel(p, sheet_name=sh)
            if df.shape[1] < 2:
                err(f"Excel pegado {p.name}!{sh}")
            else:
                ok(f"xlsx {p.relative_to(ROOT).as_posix()}!{sh} {df.shape[0]}x{df.shape[1]}")

# KPIs
for mat, km in [("hematita", 7.73), ("esmectitas", 10.3), ("tridimita", 6.71)]:
    p = ROOT / "data/processed" / f"ruta_{mat}_resumen.json"
    body = json.loads(p.read_text(encoding="utf-8")).get("resumen", {})
    if abs(float(body["distancia_km"]) - km) > 0.15:
        err(f"KPI {mat} {body.get('distancia_km')}")
    else:
        ok(f"KPI {mat} {body['distancia_km']} km / {body['dosis_uGy']} uGy")

# Pipeline
mapa = MapaMision(str(ROOT / "data"), 1360)
res = calcular_ruta_optima(mapa, 137.4416, -4.5895, "hematita", 9.0)
if abs(float(res["resumen"]["distancia_km"]) - 7.73) > 0.05:
    err("pipeline falló")
else:
    ok(f"pipeline OK {res['resumen']['distancia_km']} km")

# Scripts Excel-aware
src = (ROOT / "scripts/optimizador_rutas.py").read_text(encoding="utf-8")
rsrc = (ROOT / "scripts/modelos_inclinacion_por_suelo.R").read_text(encoding="utf-8")
if "xlsm" in src and "readxl" in rsrc:
    ok("Python+R Excel-aware")
else:
    err("Código no Excel-aware")

print(f"OK={len(oks)} ERR={len(errs)}")
for e in errs:
    print(" -", e)
print("VERDICT", "PASS" if not errs else "FAIL")
raise SystemExit(0 if not errs else 1)
