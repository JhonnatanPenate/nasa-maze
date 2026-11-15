"""exportar_tablas_excel.py

Mantiene / regenera tablas Excel (.xlsx) con UNA columna por campo.
Fuente de lectura preferida para R/Python: .xlsx / .xlsm.
CSV es opcional (solo si aún existe en disco).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


FILL = PatternFill("solid", fgColor="D6EAF8")
FONT_H = Font(bold=True, name="Calibri", size=11)
FONT_B = Font(name="Calibri", size=11)
ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
THIN = Border(*(Side(style="thin"),) * 4)


def formatear_hoja(ws) -> None:
    for cell in ws[1]:
        cell.fill = FILL
        cell.font = FONT_H
        cell.alignment = ALIGN
        cell.border = THIN
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = ALIGN
            cell.font = FONT_B
            cell.border = THIN
    for idx, col in enumerate(ws.columns, start=1):
        letter = get_column_letter(idx)
        maxlen = 12
        for cell in col:
            if cell.value is not None:
                maxlen = max(maxlen, min(36, len(str(cell.value)) + 2))
        ws.column_dimensions[letter].width = maxlen
    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = "A2"


def dataframe_a_xlsx(df: pd.DataFrame, xlsx_path: Path, sheet: str = "Datos") -> Path:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    if df.shape[1] < 2:
        raise ValueError(f"DataFrame no tabular: {df.shape}")
    xlsx_path = Path(xlsx_path)
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet[:31], index=False)
        formatear_hoja(writer.book[sheet[:31]])
    check = pd.read_excel(xlsx_path)
    assert check.shape[1] == df.shape[1] and len(check) == len(df)
    return xlsx_path


def csv_a_xlsx(csv_path: Path, xlsx_path: Path | None = None, sheet: str = "Datos") -> Path:
    csv_path = Path(csv_path)
    if xlsx_path is None:
        xlsx_path = csv_path.with_suffix(".xlsx")
    df = pd.read_csv(csv_path)
    return dataframe_a_xlsx(df, xlsx_path, sheet=sheet)


def reformat_xlsx(xlsx_path: Path, sheet: str | None = None) -> Path:
    """Relee un xlsx/xlsm y lo reescribe formateado (verifica columnas)."""
    xlsx_path = Path(xlsx_path)
    xl = pd.ExcelFile(xlsx_path)
    hoja = sheet or xl.sheet_names[0]
    df = pd.read_excel(xlsx_path, sheet_name=hoja)
    return dataframe_a_xlsx(df, xlsx_path.with_suffix(".xlsx"), sheet=hoja)


def exportar_paquete(raiz: Path) -> list[Path]:
    """Exporta/reformatea tablas conocidas (CSV→xlsx si hay CSV; si no, valida xlsx)."""
    salidas = []
    candidatos = [
        (raiz / "data/processed/gale_matriz_calibracion", "Matriz_Calibracion"),
        (raiz / "data/processed/gale_puntos_quimica", "Objetivos_Minerales"),
        (raiz / "data/raw/ambiental/rad_dosis_observaciones", "RAD"),
        (raiz / "data/raw/ambiental/rems_resumen_horario", "REMS"),
        (raiz / "data/processed/ruta_hematita_tramos", "Tramos"),
        (raiz / "data/processed/ruta_esmectitas_tramos", "Tramos"),
        (raiz / "data/processed/ruta_tridimita_tramos", "Tramos"),
        (raiz / "data_usar/01_datos_entrada/calibracion/gale_matriz_calibracion", "Matriz_Calibracion"),
        (raiz / "data_usar/01_datos_entrada/calibracion/gale_puntos_quimica", "Objetivos_Minerales"),
        (raiz / "data_usar/01_datos_entrada/observaciones/ambiental/rad_dosis_observaciones", "RAD"),
        (raiz / "data_usar/01_datos_entrada/observaciones/ambiental/rems_resumen_horario", "REMS"),
        (raiz / "data_usar/03_salidas/rutas_optimas/hematita/ruta_hematita_tramos", "Tramos"),
        (raiz / "data_usar/03_salidas/rutas_optimas/esmectitas/ruta_esmectitas_tramos", "Tramos"),
        (raiz / "data_usar/03_salidas/rutas_optimas/tridimita_buckskin/ruta_tridimita_tramos", "Tramos"),
    ]
    for stem, sheet in candidatos:
        csv_path = stem.with_suffix(".csv")
        xlsx_path = stem.with_suffix(".xlsx")
        xlsm_path = stem.with_suffix(".xlsm")
        if csv_path.exists():
            out = csv_a_xlsx(csv_path, xlsx_path, sheet=sheet)
            salidas.append(out)
            print(f"OK CSV→XLSX {out}  ({pd.read_csv(csv_path).shape[0]}x{pd.read_csv(csv_path).shape[1]})")
        elif xlsx_path.exists():
            out = reformat_xlsx(xlsx_path, sheet=sheet)
            salidas.append(out)
            df = pd.read_excel(out)
            print(f"OK XLSX {out}  ({df.shape[0]}x{df.shape[1]})")
        elif xlsm_path.exists():
            df = pd.read_excel(xlsm_path, engine="openpyxl")
            out = dataframe_a_xlsx(df, xlsx_path, sheet=sheet)
            salidas.append(out)
            print(f"OK XLSM→XLSX {out}  ({df.shape[0]}x{df.shape[1]})")
    return salidas


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raiz", default=".")
    args = ap.parse_args()
    outs = exportar_paquete(Path(args.raiz))
    print(f"Exportados/validados {len(outs)} Excel")


if __name__ == "__main__":
    main()
