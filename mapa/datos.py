"""Carga del Excel de resultados y del GeoJSON de polígonos, cruce y agregación."""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from shapely import make_valid, transform, unary_union
from shapely.geometry import MultiPolygon, Polygon, mapping, shape

from . import config as C


def _normaliza_ruta(valor) -> str:
    """Las rutas llegan como int, float o texto; se homologan a texto sin decimales."""
    if pd.isna(valor):
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).strip()


def _poligonal(geom):
    """Deja sólo la parte poligonal (make_valid puede devolver líneas o colecciones)."""
    geom = make_valid(geom)
    if isinstance(geom, (Polygon, MultiPolygon)):
        return geom
    partes = [g for g in getattr(geom, "geoms", []) if isinstance(g, (Polygon, MultiPolygon))]
    return unary_union(partes) if partes else Polygon()


def formatear(valor, formato: str) -> str:
    if valor is None or pd.isna(valor):
        return "—"
    if formato.startswith("$"):
        return "$" + format(valor, formato[1:])
    return format(valor, formato)


def dias_de_codigo(codigo) -> set[str] | None:
    """'L-J' -> {L, J}; 'M' -> {M}. Códigos que no son días (A, B, C del canal Web) -> None."""
    letras = set(str(codigo or "").upper().replace(" ", "").split("-"))
    return letras if letras and letras <= set(C.DIAS.values()) else None


def preparar_resultados(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza la tabla del modelo para la app: rutas como texto, sin 'Sin código' ni duplicados."""
    df = df.copy()
    for col, *_ in C.VARIABLES_CONTINUAS.values():
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df[C.COL_RUTA] = df[C.COL_RUTA].map(_normaliza_ruta)
    # Filas "Sin código" no tienen ruta real que mapear
    df = df[(df[C.COL_RUTA] != "") & (df[C.COL_RUTA] != "Sin código")].copy()
    df = df.drop_duplicates(subset=C.COL_RUTA, keep="first")
    return df.reset_index(drop=True)


def clasificar(x: float, y: float, umbral_x: float, umbral_y: float) -> str:
    if x is None or y is None or pd.isna(x) or pd.isna(y):
        return C.SIN_DATOS
    atractiva = x >= umbral_x
    madura = y >= umbral_y
    if atractiva and madura:
        return "P1"
    if madura:
        return "P2"
    if atractiva:
        return "P3"
    return "P4"


def aplicar_clasificacion(df: pd.DataFrame, umbral_x: float, umbral_y: float,
                          usar_p_excel: bool = True) -> pd.DataFrame:
    """Cuadrante de cada ruta.

    Con usar_p_excel (umbrales por defecto) se respeta la "P homologada" del Excel tal cual;
    si se mueven los umbrales, se recalcula con ellos.
    """
    df = df.copy()
    if usar_p_excel:
        p = df[C.COL_P].astype(str).str.strip().str.upper()
        df["P"] = p.where(p.isin(["P1", "P2", "P3", "P4"]), C.SIN_DATOS)
    else:
        df["P"] = [clasificar(x, y, umbral_x, umbral_y) for x, y in zip(df[C.COL_X], df[C.COL_Y])]
    return df


def cargar_geometrias(canales: tuple[str, ...], dias: tuple[str, ...] | None = None) -> dict[str, object]:
    """Une los polígonos de cada ruta en una sola huella (del canal Convencional; Web sólo si no tiene convencional).

    `dias`: letras de día (L, M, X, J, V, S) a incluir; None = todos. Los polígonos cuyo
    código no es un día (A/B/C del canal Web) se incluyen siempre.
    """
    with open(C.GEOJSON_RUTAS, encoding="utf-8") as f:
        gj = json.load(f)

    # Por ruta y canal. Cada ruta usa su polígono del primer canal elegido que tenga (Convencional primero):
    # así las rutas que sólo existen en el canal Web también aparecen, sin encimar su zona web sobre la convencional.
    por_canal: dict[str, dict[str, list]] = {}
    for feat in gj["features"]:
        props = feat.get("properties") or {}
        if props.get("canal") not in canales or not feat.get("geometry"):
            continue
        if dias is not None:
            dias_feat = dias_de_codigo(props.get("dia"))
            if dias_feat is not None and not dias_feat & set(dias):
                continue
        geom = _poligonal(shape(feat["geometry"]))
        por_canal.setdefault(_normaliza_ruta(props.get("ruta")), {}).setdefault(props.get("canal"), []).append(geom)
    orden = [c for c in ("Convencional", "Web") if c in canales] + [c for c in canales if c not in ("Convencional", "Web")]
    por_ruta = {ruta: next(partes[c] for c in orden if c in partes) for ruta, partes in por_canal.items()}

    geoms = {}
    for ruta, partes in por_ruta.items():
        geoms[ruta] = _poligonal(unary_union(partes).simplify(0.0001, preserve_topology=True))
    return geoms


def contornos(geoms: dict[str, object], cierre: float = 0.0006) -> dict[str, object]:
    """Contorno exterior de cada ruta: la huella de todos sus polígonos/día como una sola figura.
    Los polígonos de distintos días dejan rendijas y huecos entre ellos; un cierre morfológico
    (buffer +`cierre` y luego −`cierre`, ~60 m) los une antes de tomar el borde exterior."""
    salida = {}
    for ruta, g in geoms.items():
        cerrado = g.buffer(cierre, quad_segs=2).buffer(-cierre, quad_segs=2)
        partes = getattr(cerrado, "geoms", [cerrado])
        salida[ruta] = [p.exterior for p in partes if p.geom_type == "Polygon" and not p.is_empty]
    return salida


def area_sin_cobertura(geoms: dict[str, object], radio_km: float = 2.0,
                       cobertura: dict[str, object] | None = None) -> dict[str, float]:
    """Por ruta: km² que ninguna ruta cubre en un anillo de `radio_km` alrededor de su huella.
    Aproximación del "potencial cercano sin cobertura" mientras no haya un análisis de distancias."""
    import math
    from shapely.ops import unary_union as union
    if not geoms:
        return {}
    # Lo "cubierto" son las zonas de reparto convencional (las zonas web son muy amplias y no son reparto)
    cubierto = union(list((cobertura or geoms).values()))
    salida = {}
    for ruta, g in geoms.items():
        lat = g.centroid.y
        km_lat, km_lon = 110.57, 111.32 * math.cos(math.radians(lat))   # km por grado
        anillo = g.buffer(radio_km / km_lat, quad_segs=4).difference(g)
        libre = anillo.difference(cubierto)
        salida[ruta] = libre.area * km_lat * km_lon
    return salida


def disolver(geoms: dict[str, object], rutas_por_grupo: dict[str, list[str]]) -> dict[str, object]:
    salida = {}
    for grupo, rutas in rutas_por_grupo.items():
        partes = [geoms[r] for r in rutas if r in geoms]
        if partes:
            salida[grupo] = _poligonal(unary_union(partes).simplify(0.0003, preserve_topology=True))
    return salida


def agregar(df: pd.DataFrame, col_nivel: str, umbral_x: float, umbral_y: float,
            variables: dict[str, str] | None = None) -> pd.DataFrame:
    """Mediana de los ejes por grupo y su cuadrante; incluye la mezcla de P de sus rutas y la
    mediana de cada variable pedida (`variables`: etiqueta -> columna) como "Mediana {etiqueta}"."""
    filas = []
    for grupo, sub in df.groupby(col_nivel, sort=True):
        med_x = sub[C.COL_X].median()
        med_y = sub[C.COL_Y].median()
        mezcla = sub["P"].value_counts()
        filas.append({
            col_nivel: grupo,
            "Región": sub[C.COL_REGION].iloc[0] if col_nivel != C.COL_REGION else grupo,
            "Rutas": len(sub),
            "Rutas con dato": int(sub[C.COL_X].notna().mul(sub[C.COL_Y].notna()).sum()),
            "Mediana atractividad": med_x,
            "Mediana madurez": med_y,
            "P": clasificar(med_x, med_y, umbral_x, umbral_y),
            **{f"Rutas {p}": int(mezcla.get(p, 0)) for p in C.ORDEN_CATEGORIAS},
            **{f"Mediana {nombre}": pd.to_numeric(sub[col], errors="coerce").median()
               for nombre, col in (variables or {}).items()},
        })
    return pd.DataFrame(filas)


def resumen_matriz(df_rutas: pd.DataFrame, df_grupos: pd.DataFrame | None) -> dict[str, dict]:
    """Conteos por cuadrante como en la matriz de referencia.

    - Nivel Ruta: cada ruta cuenta en su propio cuadrante.
    - Niveles agregados: el grupo se clasifica por mediana y todas sus rutas cuentan
      en el cuadrante del grupo ("11 CeDis – 113 rutas").
    """
    total = len(df_rutas)
    res = {}
    for p in C.ORDEN_CATEGORIAS:
        if df_grupos is None:
            n_rutas = int((df_rutas["P"] == p).sum())
            n_grupos = None
        else:
            sel = df_grupos[df_grupos["P"] == p]
            n_rutas = int(sel["Rutas"].sum())
            n_grupos = len(sel)
        res[p] = {"grupos": n_grupos, "rutas": n_rutas, "pct": n_rutas / total if total else 0.0}
    return res


def a_geojson(geoms: dict[str, object]) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "id": k, "properties": {}, "geometry": mapping(transform(g, lambda c: np.round(c, 5)))}
            for k, g in geoms.items() if not g.is_empty
        ],
    }


def encuadre(geoms: list, ancho_px: int = 1100, alto_px: int = 750) -> tuple[dict, float]:
    """Centro y zoom (escala web-mercator) que encuadran las geometrías dadas."""
    if not geoms:
        return {"lat": 23.6, "lon": -102.5}, 4.2
    minx, miny, maxx, maxy = unary_union(geoms).bounds
    centro = {"lat": (miny + maxy) / 2, "lon": (minx + maxx) / 2}

    def merc_y(lat):
        lat = math.radians(max(min(lat, 85), -85))
        return math.log(math.tan(math.pi / 4 + lat / 2))

    dx = max(maxx - minx, 1e-4) / 360
    dy = max(merc_y(maxy) - merc_y(miny), 1e-5) / (2 * math.pi)
    zoom = min(math.log2(ancho_px / 512 / dx), math.log2(alto_px / 512 / dy)) - 0.35
    return centro, max(min(zoom, 15), 3)
