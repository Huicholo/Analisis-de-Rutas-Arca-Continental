"""Árbol de decisión: qué estrategias aplicar a cada ruta según su cuadrante (P1–P4).

Cada cuadrante es un flujo de preguntas. Las preguntas NO son excluyentes: la ruta pasa por todas y acumula
la estrategia de cada respuesta que tenga una (Sí o No), así que puede tener varias. Ninguna estrategia aplica
"a todas" las rutas: todas dependen de una respuesta. Las rutas sin cuadrante reciben una sola acción (fuera de
evaluación, revisar estatus o completar datos).

Cómo se contesta cada pregunta (condiciones definidas por el negocio):
- ¿Tiene muchos hogares por capturar?  % A/B + C+ < 40% de los hogares  y  % ABC+ capturable > 50%
  (capturable = hogares A/B + C+ por capturar ÷ hogares A/B + C+ totales).
- ¿Hay potencial cercano sin cobertura?  Hay zonas sin cobertura (whitespace) alrededor del polígono, dentro de la
  distancia máxima: área que ninguna ruta cubre ≥ `AREA_MIN_WHITESPACE` km².
- ¿Hay potencial para venta web?  % OP (volumen) > p75 de su Región  y  hogares por manzana > mediana.
- ¿Ya opera en niveles óptimos?  Índice de madurez > p75 de su Región.
- ¿Es top player?  Índice de madurez > p75 general  y  índice de atractividad < p25 general.
- ¿Está muy cerca de la frontera con P1/P2?  Índice de madurez > corte de la matriz (mediana) − 5 puntos.
- ¿Está cerca de P1/P2?  Índice de madurez > corte de la matriz (mediana) − 10 puntos.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config as C

# Umbrales (fáciles de ajustar)
ABC_MAX = 0.40              # % A/B + C+ de los hogares menor a esto…
CAPTURABLE_MIN = 0.50       # …y % ABC+ capturable mayor a esto = "muchos hogares por capturar"
AREA_MIN_WHITESPACE = 0.5   # km² sin cobertura para contar como "zona sin cobertura"
RADIO_SIN_COBERTURA_KM = 2.0   # distancia máxima por defecto (se puede cambiar en la app)
PUNTOS_MUY_CERCA = 5.0      # puntos de madurez por debajo del corte
PUNTOS_CERCA = 10.0

# Columnas que usa el árbol
COL_ABC = "% A/B + C+"
COL_CAPTURABLE = "% ABC+ capturable"
COL_SINCOB = "Área sin cobertura cercana (km²)"
COL_OPVOL = "% OP (volumen)"
COL_HMAN = "Hogares por manzana"
COL_MAD = C.COL_Y
COL_ATR = C.COL_X
COL_IE = "Índice de Ejecución (0-100)"


@dataclass(frozen=True)
class Pregunta:
    clave: str
    cuadrante: str
    texto: str          # para el rombo del diagrama
    como: str           # cómo se contesta (variables y corte), en lenguaje sencillo


@dataclass(frozen=True)
class Regla:
    """Una estrategia (hoja del árbol)."""
    clave: str
    cuadrante: str
    estrategia: str
    pregunta: str = ""       # clave de la Pregunta que la dispara
    respuesta: str = "Sí"    # "Sí" o "No"
    explicacion: str = ""

    @property
    def condicion(self) -> str:
        if not self.pregunta:
            return self.explicacion
        return f"{PREGUNTAS[self.pregunta].texto.replace(chr(10), ' ')} → {self.respuesta}"


COMO = {
    "hogares": f"% A/B + C+ < {ABC_MAX:.0%} de los hogares y % ABC+ capturable > {CAPTURABLE_MIN:.0%} "
               "(hogares A/B + C+ por capturar ÷ hogares A/B + C+ totales)",
    "cercano": f"Hay zonas sin cobertura (whitespace) alrededor del polígono dentro de la distancia máxima: "
               f"área que ninguna ruta cubre ≥ {AREA_MIN_WHITESPACE:g} km²",
    "web": "% OP (volumen) > p75 de su Región y hogares por manzana > mediana de todas las rutas",
    "optimo": "Índice de madurez > p75 de su Región",
    "top": "Índice de madurez > p75 general e índice de atractividad < p25 general",
    "muy_cerca": f"Índice de madurez > corte de la matriz (mediana) − {PUNTOS_MUY_CERCA:g} puntos",
    "cerca": f"Índice de madurez > corte de la matriz (mediana) − {PUNTOS_CERCA:g} puntos",
}
TEXTO = {
    "hogares": "¿Tiene muchos hogares\npor capturar?",
    "cercano": "¿Hay potencial cercano\nsin cobertura?",
    "web": "¿Hay potencial para\nventa web?",
    "optimo": "¿Ya opera en niveles\nóptimos de ejecución?",
    "top": "¿Es top player?",
}


def _preg(cuadrante: str, tipo: str, texto: str | None = None) -> Pregunta:
    return Pregunta(f"{cuadrante.lower()}_{tipo}", cuadrante, texto or TEXTO[tipo], COMO[tipo])


_P = [
    _preg("P1", "hogares"), _preg("P1", "cercano"), _preg("P1", "web"),
    _preg("P2", "optimo"), _preg("P2", "hogares"), _preg("P2", "top"), _preg("P2", "cercano"),
    _preg("P3", "muy_cerca", "¿Está muy cerca de\nla frontera con P1?"), _preg("P3", "cerca", "¿Está cerca de P1?"),
    _preg("P3", "hogares"), _preg("P3", "cercano"),
    _preg("P4", "muy_cerca", "¿Está muy cerca de\nla frontera con P2?"), _preg("P4", "cerca", "¿Está cerca de P2?"),
    _preg("P4", "cercano"),
]
PREGUNTAS = {p.clave: p for p in _P}

# --------------------------------------------------------------------------- estrategias (lenguaje estandarizado)
DENSIFICAR = "Densificar la ruta con el modelo convencional"
ZONA_CERCANA = "Evaluar cubrir la zona cercana sin cobertura desde la ruta actual (revisar distancias)"
FUSIONAR = "Evaluar fusionar con rutas existentes"
REGLAS = [
    # P1 · Ampliar cobertura
    Regla("p1_densificar", "P1", DENSIFICAR, "p1_hogares", "Sí", "Hay muchos hogares A/B + C+ por capturar en su zona"),
    Regla("p1_zona_cercana", "P1", ZONA_CERCANA, "p1_cercano", "Sí", "Junto a la ruta hay zonas sin cobertura"),
    Regla("p1_web", "P1", "Impulsar el canal web", "p1_web", "Sí", "Buen volumen de otros productos en zona densa"),
    Regla("p1_fusionar", "P1", "Evaluar fusionar con una ruta contigua", "p1_web", "No",
          "Sin potencial web: revisar si conviene unirla con la ruta de al lado"),
    # P2 · Mantener
    Regla("p2_disciplina", "P2", "Mejorar la disciplina operativa y el apego a procesos", "p2_optimo", "No",
          "Opera bien, pero todavía no en el nivel óptimo de su Región"),
    Regla("p2_densificar", "P2", DENSIFICAR, "p2_hogares", "Sí", "Hay muchos hogares A/B + C+ por capturar en su zona"),
    Regla("p2_top", "P2", "Reconocer como top player y usarla de referencia", "p2_top", "Sí",
          "Opera de lo mejor aunque su zona tiene poco potencial"),
    Regla("p2_zona_cercana", "P2", ZONA_CERCANA, "p2_cercano", "Sí", "Junto a la ruta hay zonas sin cobertura"),
    Regla("p2_mantener", "P2", "Mantener los indicadores y darles seguimiento", "p2_cercano", "No",
          "Sin zonas cercanas por cubrir: cuidar lo que ya logró"),
    # P3 · Desarrollar
    Regla("p3_mejorar", "P3", "Mejorar la operación para pasar a P1", "p3_muy_cerca", "Sí",
          "Le falta muy poco de madurez para ser P1"),
    Regla("p3_fusionar", "P3", FUSIONAR, "p3_cerca", "Sí", "Está cerca de P1: juntarla con otra ruta puede subir su madurez"),
    Regla("p3_densificar", "P3", DENSIFICAR, "p3_hogares", "Sí", "Hay muchos hogares A/B + C+ por capturar en su zona"),
    Regla("p3_zona_cercana", "P3", ZONA_CERCANA, "p3_cercano", "Sí", "Junto a la ruta hay zonas sin cobertura"),
    Regla("p3_web", "P3", "Impulsar el canal web", "p3_cercano", "No", "Sin zonas cercanas por cubrir: crecer por web"),
    # P4 · Evaluar
    Regla("p4_mejorar", "P4", "Mejorar la operación para pasar a P2", "p4_muy_cerca", "Sí",
          "Le falta muy poco de madurez para ser P2"),
    Regla("p4_fusionar", "P4", FUSIONAR, "p4_cerca", "Sí", "Está cerca de P2: juntarla con otra ruta puede subir su madurez"),
    Regla("p4_incluir_zonas", "P4", "Incluir zonas con potencial sin cobertura", "p4_cercano", "Sí",
          "Junto a la ruta hay zonas sin cobertura"),
    Regla("p4_web_desestimar", "P4", "Impulsar el canal web y después evaluar desestimar la ruta", "p4_cercano", "No",
          "Zona con poco potencial y sin zonas cercanas por cubrir"),
    # Sin cuadrante (una sola acción, la primera causa)
    Regla("s_inactiva", "S", "Ruta inactiva: fuera de evaluación", explicacion="La ruta no está operando"),
    Regla("s_no_elegible", "S", "No elegible: revisar código o estatus",
          explicacion="Sin código válido o marcada como no elegible"),
    Regla("s_indicadores", "S", "Completar datos de indicadores para clasificar",
          explicacion="No alcanza la cobertura mínima de indicadores para calcular el Índice de Ejecución"),
    Regla("s_capacidad", "S", "Completar datos de capacidad/saturación para clasificar",
          explicacion="Sin capacidad instalada o clientes actuales no se calcula la saturación ni la madurez"),
    Regla("s_zona", "S", "Completar datos de zona (potencial) para clasificar",
          explicacion="Sin datos de zona no se calcula la atractividad"),
    # Ruta con cuadrante a la que le faltan datos para contestar las preguntas
    Regla("x_datos", "*", "Completar datos para definir la estrategia",
          explicacion="Faltan datos para contestar las preguntas de su cuadrante"),
]
REGLAS_POR_CLAVE = {r.clave: r for r in REGLAS}
CUADRANTES = ["P1", "P2", "P3", "P4"]
SIN_CUADRANTE = "S"
PREGUNTAS_SIN_CUADRANTE = ["¿Ruta activa?", "¿Elegible para\nel estándar?", "¿Tiene Índice\nde Ejecución?",
                           "¿Tiene datos de\ncapacidad/saturación?"]

# Orden de las preguntas de cada cuadrante
FLUJO = {
    "P1": [("q", "p1_hogares"), ("q", "p1_cercano"), ("q", "p1_web")],
    "P2": [("q", "p2_optimo"), ("q", "p2_hogares"), ("q", "p2_top"), ("q", "p2_cercano")],
    "P3": [("q", "p3_muy_cerca"), ("q", "p3_cerca"), ("q", "p3_hogares"), ("q", "p3_cercano")],
    "P4": [("q", "p4_muy_cerca"), ("q", "p4_cerca"), ("q", "p4_cercano")],
}


def reglas_de(cuadrante: str) -> list[Regla]:
    return [r for r in REGLAS if r.cuadrante == cuadrante]


def reglas_de_pregunta(pregunta: str, respuesta: str) -> list[Regla]:
    return [r for r in REGLAS if r.pregunta == pregunta and r.respuesta == respuesta]


def paso_de(regla: Regla) -> int:
    for k, (tipo, clave) in enumerate(FLUJO.get(regla.cuadrante, []), start=1):
        if (tipo == "q" and clave == regla.pregunta) or (tipo == "a" and clave == regla.clave):
            return k
    return 0


# --------------------------------------------------------------------------- cortes
def _num(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce") if col in df else pd.Series(np.nan, index=df.index)


def cortes(base: pd.DataFrame, corte_madurez: float | None = None) -> dict:
    """Valores de corte. Por ruta (Series alineadas a `base`) los que dependen de su Región; números sueltos los
    generales."""
    mad = _num(base, COL_MAD)
    return {
        "mad_p75_region": base[C.COL_REGION].map(mad.groupby(base[C.COL_REGION]).quantile(0.75)),
        "opvol_p75_region": base[C.COL_REGION].map(_num(base, COL_OPVOL).groupby(base[C.COL_REGION]).quantile(0.75)),
        "mad_p75": float(mad.quantile(0.75)),
        "atr_p25": float(_num(base, COL_ATR).quantile(0.25)),
        "hman_mediana": float(_num(base, COL_HMAN).median()),
        "frontera": float(corte_madurez) if corte_madurez is not None else float(mad.median()),
    }


def resumen_cortes(ct: dict) -> str:
    """Texto con los valores de corte vigentes (para la tabla del árbol)."""
    mr, orr = ct["mad_p75_region"].dropna(), ct["opvol_p75_region"].dropna()
    return (f"% A/B + C+ < {ABC_MAX:.0%} y % ABC+ capturable > {CAPTURABLE_MIN:.0%} · zona sin cobertura ≥ "
            f"{AREA_MIN_WHITESPACE:g} km² · % OP (volumen) p75 por Región entre {orr.min():.0%} y {orr.max():.0%} · "
            f"hogares por manzana mediana = {ct['hman_mediana']:.1f} · madurez p75 por Región entre {mr.min():.1f} y "
            f"{mr.max():.1f} · madurez p75 general = {ct['mad_p75']:.1f} · atractividad p25 general = {ct['atr_p25']:.1f}"
            f" · corte de madurez de la matriz = {ct['frontera']:g} (muy cerca > {ct['frontera'] - PUNTOS_MUY_CERCA:g}; "
            f"cerca > {ct['frontera'] - PUNTOS_CERCA:g})")


# --------------------------------------------------------------------------- evaluación
def _y(a: pd.Series, b: pd.Series) -> pd.Series:
    """Y lógico con datos faltantes: False si alguna es False; NaN si falta dato y ninguna es False."""
    out = []
    for x, y in zip(a, b):
        if (x is False) or (y is False) or (isinstance(x, (bool, np.bool_)) and not x) or \
                (isinstance(y, (bool, np.bool_)) and not y):
            out.append(False)
        elif pd.isna(x) or pd.isna(y):
            out.append(np.nan)
        else:
            out.append(True)
    return pd.Series(out, index=a.index, dtype=object)


def _comp(v: pd.Series, c, mayor: bool) -> pd.Series:
    c = c if isinstance(c, pd.Series) else pd.Series(c, index=v.index)
    r = (v > c) if mayor else (v < c)
    return r.astype(object).where(v.notna() & c.notna(), np.nan)


def evaluar(df: pd.DataFrame, ct: dict, col_p: str = "P") -> pd.DataFrame:
    """Estrategias de cada ruta de `df` (debe compartir índice con la base de `cortes()`).

    Columnas: una booleana por estrategia (True = la ruta la recibe), 'Claves' (lista en el orden del árbol),
    'Estrategias' (texto), 'Nº de estrategias' y 'Porques' (lista: la respuesta con el valor de la ruta)."""
    idx = df.index
    abc, cap = _num(df, COL_ABC), _num(df, COL_CAPTURABLE)
    area, opvol, hman = _num(df, COL_SINCOB), _num(df, COL_OPVOL), _num(df, COL_HMAN)
    mad, atr = _num(df, COL_MAD), _num(df, COL_ATR)
    mad_reg, op_reg = ct["mad_p75_region"].reindex(idx), ct["opvol_p75_region"].reindex(idx)
    frontera = ct["frontera"]

    c_abc, c_cap = _comp(abc, ABC_MAX, False), _comp(cap, CAPTURABLE_MIN, True)
    c_op, c_hman = _comp(opvol, op_reg, True), _comp(hman, ct["hman_mediana"], True)
    c_mad_p75, c_atr_p25 = _comp(mad, ct["mad_p75"], True), _comp(atr, ct["atr_p25"], False)
    resp = {
        "hogares": _y(c_abc, c_cap),
        "cercano": (area >= AREA_MIN_WHITESPACE).astype(object).where(area.notna(), np.nan),
        "web": _y(c_op, c_hman),
        "optimo": _comp(mad, mad_reg, True),
        "top": _y(c_mad_p75, c_atr_p25),
        "muy_cerca": _comp(mad, frontera - PUNTOS_MUY_CERCA, True),
        "cerca": _comp(mad, frontera - PUNTOS_CERCA, True),
    }

    def f(x, fmt):
        return format(x, fmt) if pd.notna(x) else "s/d"

    def porque(tipo, i):
        if tipo == "hogares":
            return (f"% A/B + C+ {f(abc.at[i], '.0%')} (corte < {ABC_MAX:.0%}) y % ABC+ capturable "
                    f"{f(cap.at[i], '.0%')} (corte > {CAPTURABLE_MIN:.0%})")
        if tipo == "cercano":
            return f"área sin cobertura cercana {f(area.at[i], ',.1f')} km² (corte ≥ {AREA_MIN_WHITESPACE:g} km²)"
        if tipo == "web":
            return (f"% OP (volumen) {f(opvol.at[i], '.0%')} (p75 de su Región {f(op_reg.at[i], '.0%')}) y hogares "
                    f"por manzana {f(hman.at[i], ',.1f')} (mediana {ct['hman_mediana']:.1f})")
        if tipo == "optimo":
            return f"índice de madurez {f(mad.at[i], '.1f')} (p75 de su Región {f(mad_reg.at[i], '.1f')})"
        if tipo == "top":
            return (f"índice de madurez {f(mad.at[i], '.1f')} (p75 general {ct['mad_p75']:.1f}) e índice de "
                    f"atractividad {f(atr.at[i], '.1f')} (p25 general {ct['atr_p25']:.1f})")
        pts = PUNTOS_MUY_CERCA if tipo == "muy_cerca" else PUNTOS_CERCA
        return (f"índice de madurez {f(mad.at[i], '.1f')} (corte de la matriz {frontera:g} − {pts:g} puntos = "
                f"{frontera - pts:g})")

    p = df[col_p]
    salida = pd.DataFrame(False, index=idx, columns=[r.clave for r in REGLAS])
    claves, porques = [], []
    for i in idx:
        pp = p.at[i]
        if pp in CUADRANTES:
            cs, pqs = [], []
            for _tipo, clave in FLUJO[pp]:
                tipo = clave.split("_", 1)[1]
                r = resp[tipo].at[i]
                if pd.isna(r):
                    continue
                for regla in reglas_de_pregunta(clave, "Sí" if r else "No"):
                    cs.append(regla.clave)
                    pqs.append(porque(tipo, i))
            if not cs:
                cs, pqs = ["x_datos"], [REGLAS_POR_CLAVE["x_datos"].explicacion]
        else:
            fila = df.loc[i]
            if fila.get("Estatus") != "Activa":
                clave = "s_inactiva"
            elif fila.get("Elegible p/ estándar") != "Sí":
                clave = "s_no_elegible"
            elif pd.isna(pd.to_numeric(fila.get(COL_IE), errors="coerce")):
                clave = "s_indicadores"
            elif fila.get("Índice de Saturación") == "N/D":
                clave = "s_capacidad"
            else:
                clave = "s_zona"
            cs, pqs = [clave], [REGLAS_POR_CLAVE[clave].explicacion]
        for c in cs:
            salida.at[i, c] = True
        claves.append(cs)
        porques.append(pqs)
    salida["Claves"] = claves
    salida["Estrategias"] = [" | ".join(REGLAS_POR_CLAVE[c].estrategia for c in cs) for cs in claves]
    salida["Nº de estrategias"] = [len(cs) for cs in claves]
    salida["Porques"] = porques
    return salida


def tabla_reglas(ct: dict, conteo: dict[str, int]) -> pd.DataFrame:
    """Una fila por estrategia: dónde está en el árbol, cómo se contesta la pregunta y cuántas rutas la reciben."""
    filas = []
    for r in REGLAS:
        if r.cuadrante == "*":
            continue
        preg = PREGUNTAS.get(r.pregunta)
        filas.append({
            "Cuadrante": "Sin cuadrante" if r.cuadrante == "S" else r.cuadrante,
            "Paso": paso_de(r) if r.cuadrante in CUADRANTES else reglas_de("S").index(r) + 1,
            "Pregunta": preg.texto.replace("\n", " ") if preg else r.explicacion,
            "Respuesta": r.respuesta if r.cuadrante != "S" else "—",
            "Cómo se contesta": preg.como if preg else "—",
            "Estrategia": r.estrategia,
            "Rutas con esta estrategia": int(conteo.get(r.clave, 0)),
        })
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------- textos del detalle
def texto_hover_ruta(p: str, claves: list[str], porques: list[str]) -> str:
    color = C.CATEGORIAS[p]["borde"] if p in CUADRANTES else "#555555"
    cab = p if p in CUADRANTES else "sin cuadrante"
    titulo = "Estrategia" if len(claves) == 1 else f"Estrategias ({len(claves)})"
    partes = [f"<br><br><b>{titulo} · {cab}:</b>"]
    for k, (c, pq) in enumerate(zip(claves, porques), start=1):
        num = f"{k}. " if len(claves) > 1 else ""
        partes.append(f"<br><span style='color:{color}'><b>{num}{REGLAS_POR_CLAVE[c].estrategia}</b></span>"
                      f"<br><span style='font-size:11px;color:#777'>Porque {pq}</span>")
    return "".join(partes)


def texto_hover_grupo(claves: pd.Series, maximo: int = 4) -> str:
    """`claves`: lista de claves por ruta. Cuenta cuántas rutas reciben cada estrategia."""
    conteo = claves.explode().dropna().map(lambda c: REGLAS_POR_CLAVE[c].estrategia).value_counts()
    if conteo.empty:
        return ""
    filas = [f"<br>▸ {e} <span style='color:#777'>({n} rutas)</span>" for e, n in conteo.head(maximo).items()]
    if len(conteo) > maximo:
        filas.append(f"<br><span style='color:#777'>… y {len(conteo) - maximo} estrategias más</span>")
    return ("<br><br><b>Estrategias de sus rutas</b> <span style='font-size:10px;color:#777'>"
            "(una ruta puede tener varias)</span>" + "".join(filas))


# --------------------------------------------------------------------------- diagrama de flujo (SVG en cuadrícula)
# Todo se dibuja sobre una cuadrícula fija: cajas y rombos del mismo tamaño, líneas sólo verticales y horizontales.
# Cada cuadrante es una columna: preguntas (rombos) al centro de su carril izquierdo y estrategias (cajas) a la
# derecha, a la misma altura de su pregunta.
ROMBO_W, ROMBO_H = 230, 120
CAJA_W, CAJA_H = 230, 86   # todas las cajas miden lo mismo (ancho = rombo)
SEP_X = 60          # entre el vértice derecho del rombo y su caja
COL_GAP = 70        # entre columnas de cuadrantes
FILA = 150          # distancia vertical entre preguntas consecutivas
MARGEN = 30
LINEA = "#5E5E5E"
ROJO = "#F30000"
FUENTE = "Raleway, Arial, sans-serif"
EJES_P = {"P1": "Madurez alta · Atractividad alta", "P2": "Madurez alta · Atractividad baja",
          "P3": "Madurez baja · Atractividad alta", "P4": "Madurez baja · Atractividad baja"}


def _xml(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _partir(texto: str, max_car: int) -> list[str]:
    palabras, lineas, actual = texto.replace("\n", " ").split(), [], ""
    for w in palabras:
        if actual and len(actual) + 1 + len(w) > max_car:
            lineas.append(actual)
            actual = w
        else:
            actual = f"{actual} {w}".strip()
    if actual:
        lineas.append(actual)
    return lineas


class _Lienzo:
    def __init__(self):
        self.partes: list[str] = []
        self.alto = 0.0
        self.ancho = 0.0

    def _crece(self, x, y):
        self.ancho, self.alto = max(self.ancho, x), max(self.alto, y)

    def texto(self, x, y, lineas, tam=12, color="#000", negritas=(), interlinea=14.5):
        y0 = y - (len(lineas) - 1) * interlinea / 2
        for k, l in enumerate(lineas):
            peso = "700" if k in negritas else "400"
            self.partes.append(f'<text x="{x:.1f}" y="{y0 + k * interlinea:.1f}" font-size="{tam}" font-weight="{peso}" '
                               f'fill="{color}" text-anchor="middle" dominant-baseline="middle">{_xml(l)}</text>')

    def caja(self, x, y, lineas, relleno, borde, color="#fff", negritas=(), grosor=1.5, w=CAJA_W, h=CAJA_H):
        self.partes.append(f'<rect x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" width="{w}" height="{h}" rx="10" '
                           f'fill="{relleno}" stroke="{borde}" stroke-width="{grosor}"/>')
        self.texto(x, y, lineas, color=color, negritas=negritas)
        self._crece(x + w / 2, y + h / 2)

    def rombo(self, x, y, lineas, borde, relleno="#fff"):
        w, h = ROMBO_W / 2, ROMBO_H / 2
        self.partes.append(f'<polygon points="{x},{y - h} {x + w},{y} {x},{y + h} {x - w},{y}" fill="{relleno}" '
                           f'stroke="{borde}" stroke-width="2"/>')
        self.texto(x, y, lineas, tam=11.5, color="#000", negritas=(0,) if lineas and lineas[0][:2].strip(". ").isdigit()
                   else ())
        self._crece(x + w, y + h)

    def linea(self, puntos, etiqueta="", pos_etq=None, flecha=True):
        d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in puntos)
        self.partes.append(f'<path d="{d}" fill="none" stroke="{LINEA}" stroke-width="1.6"'
                           + (' marker-end="url(#flecha)"' if flecha else "") + "/>")
        if etiqueta:
            (x, y), anc = pos_etq
            self.partes.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="11" font-weight="700" fill="{ROJO}" '
                               f'text-anchor="{anc}" dominant-baseline="middle">{_xml(etiqueta)}</text>')

    def svg(self) -> str:
        w, h = self.ancho + MARGEN, self.alto + MARGEN
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" '
                f'height="{h:.0f}" font-family="{FUENTE}">'
                '<defs><marker id="flecha" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{LINEA}"/></marker></defs>'
                f'<rect width="100%" height="100%" fill="#fff"/>' + "".join(self.partes) + "</svg>")


def _lineas_caja(texto: str, n: int | None) -> tuple[list[str], tuple]:
    lineas = _partir(texto, 30)
    if n is not None:
        lineas.append(f"{n:,} rutas")
    return lineas, ((len(lineas) - 1,) if n is not None else ())


def _columna(lz: _Lienzo, x0: float, y_cab: float, clave_col: str, conteo: dict, rutas_p: dict) -> tuple[float, float]:
    """Dibuja un cuadrante (o 'S') a partir de la esquina x0. Devuelve (x del carril de preguntas, y de la cabecera)."""
    xq = x0 + ROMBO_W / 2
    xa = x0 + ROMBO_W + SEP_X + CAJA_W / 2
    if clave_col == SIN_CUADRANTE:
        cat = {"color": "#D5D5D5", "borde": "#5E5E5E", "nombre": "Sin cuadrante"}
        cab = ["Sin cuadrante", "Faltan datos o no se evalúa", f"{rutas_p.get(C.SIN_DATOS, 0):,} rutas"]
    else:
        cat = C.CATEGORIAS[clave_col]
        cab = [f"{clave_col} · {cat['nombre']}", EJES_P[clave_col], f"{rutas_p.get(clave_col, 0):,} rutas"]
    lz.caja(xq, y_cab, cab, cat["color"], cat["borde"], color="#000", negritas=(0, 2), grosor=2.5, w=ROMBO_W)
    anterior = (xq, y_cab + CAJA_H / 2)     # punto de salida hacia abajo
    etq = ""
    y = y_cab + CAJA_H / 2 + 40 + ROMBO_H / 2

    def baja(hacia_y, etiqueta):
        lz.linea([anterior, (xq, hacia_y)], etiqueta, ((xq + 8, (anterior[1] + hacia_y) / 2), "start"))

    def hoja(x, yy, regla):
        lineas, neg = _lineas_caja(regla.estrategia, conteo.get(regla.clave, 0))
        lz.caja(x, yy, lineas, cat["borde"], cat["borde"], negritas=neg)

    if clave_col == SIN_CUADRANTE:
        reglas = reglas_de(SIN_CUADRANTE)
        for k, preg in enumerate(PREGUNTAS_SIN_CUADRANTE):
            baja(y - ROMBO_H / 2, etq)
            lz.rombo(xq, y, _partir(preg, 18), cat["borde"])
            lz.linea([(xq + ROMBO_W / 2, y), (xa - CAJA_W / 2, y)], "No", ((xq + ROMBO_W / 2 + 8, y - 10), "start"))
            hoja(xa, y, reglas[k])
            anterior, etq = (xq, y + ROMBO_H / 2), "Sí"
            y += FILA
        yy = y - FILA + ROMBO_H / 2 + 40 + CAJA_H / 2
        baja(yy - CAJA_H / 2, etq)
        hoja(xq, yy, reglas[-1])
        return xq, y_cab

    pasos = FLUJO[clave_col]
    for k, (tipo, clave) in enumerate(pasos, start=1):
        if tipo == "a":                    # estrategia que aplica siempre: caja en el carril central
            yy = y - ROMBO_H / 2 + CAJA_H / 2
            baja(yy - CAJA_H / 2, etq)
            regla = REGLAS_POR_CLAVE[clave]
            lineas, neg = _lineas_caja(regla.estrategia, conteo.get(regla.clave, 0))
            lz.caja(xq, yy, lineas, cat["borde"], cat["borde"], negritas=neg, w=ROMBO_W)
            anterior, etq = (xq, yy + CAJA_H / 2), ""
            y = yy + CAJA_H / 2 + 40 + ROMBO_H / 2
            continue
        preg = PREGUNTAS[clave]
        baja(y - ROMBO_H / 2, etq)
        lz.rombo(xq, y, [f"{k}."] + _partir(preg.texto, 18), cat["borde"])
        si, no = reglas_de_pregunta(clave, "Sí"), reglas_de_pregunta(clave, "No")
        lado, resp = (si, "Sí") if si else (no, "No")
        # estrategias de la respuesta a la derecha, apiladas si son varias
        yl = y
        lz.linea([(xq + ROMBO_W / 2, y), (xa - CAJA_W / 2, y)], resp, ((xq + ROMBO_W / 2 + 8, y - 10), "start"))
        for j, regla in enumerate(lado):
            if j:
                lz.linea([(xa, yl + CAJA_H / 2), (xa, yl + CAJA_H / 2 + 24)])
                yl += CAJA_H + 24
            hoja(xa, yl, regla)
        anterior, etq = (xq, y + ROMBO_H / 2), "Sí o No"
        y_sig = max(y + FILA, yl + CAJA_H / 2 + 40 + ROMBO_H / 2)
        if si and no:                      # la otra respuesta termina abajo del rombo
            yy = y + ROMBO_H / 2 + 40 + CAJA_H / 2
            baja(yy - CAJA_H / 2, "No")
            hoja(xq, yy, no[0])
            break
        y = y_sig
    return xq, y_cab


def diagrama_svg(conteo: dict[str, int], mostrar: str = "Todo", rutas_p: dict[str, int] | None = None) -> str:
    """Diagrama de flujo del árbol como SVG. `conteo`: clave → rutas con esa estrategia; `rutas_p`: rutas por
    cuadrante (y C.SIN_DATOS). `mostrar`: "Todo", "P1"…"P4" o "Sin cuadrante"."""
    rutas_p = rutas_p or {}
    columnas = (CUADRANTES + [SIN_CUADRANTE] if mostrar == "Todo" else
                [SIN_CUADRANTE] if mostrar == "Sin cuadrante" else [mostrar])
    lz = _Lienzo()
    ancho_col = ROMBO_W + SEP_X + CAJA_W
    con_inicio = len(columnas) > 1
    y_cab = MARGEN + CAJA_H / 2 + (330 if con_inicio else 0)
    xs = {}
    for k, col in enumerate(columnas):
        xs[col], _ = _columna(lz, MARGEN + k * (ancho_col + COL_GAP), y_cab, col, conteo, rutas_p)
    if con_inicio:
        cuad = [xs[c] for c in CUADRANTES]
        xc = (min(cuad) + max(cuad)) / 2
        y_ini = MARGEN + 30
        lz.caja(xc, y_ini, ["Rutas Arca", f"{sum(rutas_p.values()):,} rutas"], "#000", "#000", negritas=(0,),
                w=ROMBO_W, h=60)
        y_q = y_ini + 30 + 40 + ROMBO_H / 2
        lz.linea([(xc, y_ini + 30), (xc, y_q - ROMBO_H / 2)])
        lz.rombo(xc, y_q, ["¿Tiene madurez y", "atractividad?"], LINEA, relleno="#F2F2F2")
        # Sí: bus horizontal que reparte a los 4 cuadrantes
        y_bus = y_q + ROMBO_H / 2 + 45
        lz.linea([(xc, y_q + ROMBO_H / 2), (xc, y_bus)], "Sí", ((xc + 8, y_q + ROMBO_H / 2 + 20), "start"), flecha=False)
        lz.linea([(min(cuad), y_bus), (max(cuad), y_bus)], flecha=False)
        for x in cuad:
            lz.linea([(x, y_bus), (x, y_cab - CAJA_H / 2)])
        # No: a la columna de sin cuadrante
        xs_s = xs[SIN_CUADRANTE]
        lz.linea([(xc + ROMBO_W / 2, y_q), (xs_s, y_q), (xs_s, y_cab - CAJA_H / 2)], "No",
                 ((xc + ROMBO_W / 2 + 8, y_q - 10), "start"))
    return lz.svg()
