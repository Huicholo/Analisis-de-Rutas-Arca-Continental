"""Compara el motor de Python contra los valores calculados que trae guardados el Excel.

Uso:
    venv\\Scripts\\python tests\\validar_contra_excel.py [escenario] [caso]

Por defecto usa el escenario y caso con los que está calculado el Excel hoy (Medio, Caso 90).
Sale con código 1 si hay diferencias.
"""
from __future__ import annotations

import math
import numbers
import sys
from pathlib import Path

import openpyxl
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mapa import config as C  # noqa: E402
from mapa import modelo  # noqa: E402

TOL = 1e-6


def valores_excel(ruta) -> pd.DataFrame:
    wb = openpyxl.load_workbook(ruta, data_only=True)
    ws = wb[modelo.HOJA_ANALISIS]
    filas = list(ws.iter_rows(min_row=7, values_only=True))
    enc = [str(h).strip() if h is not None else f"_c{i}" for i, h in enumerate(filas[0])]
    datos = [f for f in filas[1:] if f and f[0] not in (None, "")]
    return pd.DataFrame(datos, columns=enc)


def iguales(a, b) -> bool:
    na = a is None or (isinstance(a, float) and math.isnan(a)) or a == ""
    nb = b is None or (isinstance(b, float) and math.isnan(b)) or b == ""
    if na or nb:
        return na and nb
    if isinstance(a, numbers.Number) and isinstance(b, numbers.Number) and not isinstance(a, bool):
        return abs(float(a) - float(b)) <= TOL * max(1.0, abs(float(b)))
    return str(a).strip() == str(b).strip()


def main():
    escenario = sys.argv[1] if len(sys.argv) > 1 else "Medio"
    caso = sys.argv[2] if len(sys.argv) > 2 else "Caso 90"
    ins = modelo.leer_libro(C.EXCEL_ANALISIS)
    py, res = modelo.calcular(ins, escenario, caso)
    xl = valores_excel(C.EXCEL_ANALISIS)
    print(f"Escenario={escenario} · {caso} · filas Python={len(py)} · filas Excel={len(xl)}")
    print(f"Cortes Python: madurez {res['corte_madurez']} · atractividad {res['corte_atractividad']}")
    if len(py) != len(xl):
        print("❌ Distinto número de filas")
        sys.exit(1)

    total_dif = 0
    for col in py.columns:
        if col not in xl.columns:
            print(f"  (sin columna en Excel) {col}")
            continue
        dif = [i for i in range(len(py)) if not iguales(py[col].iat[i], xl[col].iat[i])]
        if dif:
            total_dif += len(dif)
            i = dif[0]
            print(f"❌ {col}: {len(dif)} diferencias · ej. fila {i + 8} ruta {xl['Ruta'].iat[i]}: "
                  f"Python={py[col].iat[i]!r} Excel={xl[col].iat[i]!r}")
    print("✅ Todo coincide" if total_dif == 0 else f"Total de celdas distintas: {total_dif}")
    sys.exit(0 if total_dif == 0 else 1)


if __name__ == "__main__":
    main()
