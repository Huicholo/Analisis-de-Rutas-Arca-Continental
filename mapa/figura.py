"""Construcción del mapa en Plotly (MapLibre), la dispersión de la matriz y exportación a JPG."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from . import config as C
from .datos import a_geojson

ESTILOS_MAPA = {
    "Claro": "carto-positron",
    "Claro sin etiquetas": "carto-positron-nolabels",
    "Calles": "open-street-map",
    "Oscuro": "carto-darkmatter",
}
MODO_CAPAS = "Un solo mapa"
MODO_LADO = "Mapas lado a lado"   # un mapa por variable y, si se pide, antes el mapa de cuadrantes
MODO_BIVARIADO = "Bivariado (paleta 3×3)"
MAX_VARIABLES = 2   # con más de 2 variables el mapa deja de leerse bien

PALETA_DISTINTA = "Un color por variable"
PALETA_SEMAFORO = "Semáforo (de bajo a alto)"
# Escalas secuenciales de un solo tono (claro = bajo, oscuro = alto), una por variable
ESCALAS_VARIABLES = [
    ("Azules", [[0, "#C6DBEF"], [0.35, "#9ECAE1"], [0.7, "#4292C6"], [1, "#08306B"]]),
    ("Naranjas", [[0, "#FDD0A2"], [0.35, "#FDAE6B"], [0.7, "#F16913"], [1, "#7F2704"]]),
    ("Morados", [[0, "#DADAEB"], [0.35, "#BCBDDC"], [0.7, "#807DBA"], [1, "#3F007D"]]),
    ("Verdes", [[0, "#C7E9C0"], [0.35, "#A1D99B"], [0.7, "#41AB5D"], [1, "#00441B"]]),
]

# Paletas bivariadas 3×3. Fila = tercil de la 2ª variable (0 = bajo … 2 = alto);
# columna = tercil de la 1ª variable. La esquina [2][2] = ambas altas; [0][0] = ambas bajas.
def _multiplicar(a: str, b: str, base: float = 0.92) -> str:
    """Mezcla "multiplicar" de dos colores (como superponer dos acetatos)."""
    ra, rb = [int(a[k:k + 2], 16) for k in (1, 3, 5)], [int(b[k:k + 2], 16) for k in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(x * y / 255 * base) for x, y in zip(ra, rb))


# Azul (1ª variable) y naranja (2ª variable) de la paleta del proyecto; la celda es la mezcla de ambos
_AZULES = ["#FFFFFF", "#A9C9EA", "#2F75B5"]
_NARANJAS = ["#FFFFFF", "#F5C6A5", "#E5803D"]
PALETAS_BIVARIADAS = {
    "Azul–naranja": [[_multiplicar(_AZULES[col], _NARANJAS[fila]) for col in range(3)] for fila in range(3)],
}
PALETA_BIV_DEFAULT = "Azul–naranja"
COLORES_BIVARIADOS = PALETAS_BIVARIADAS[PALETA_BIV_DEFAULT]
DESCRIPCION_BIV = {
    "Azul–naranja": "casi negro = ambas altas · azul = sólo la 1ª · naranja = sólo la 2ª · gris = ambas bajas",
}
NIVELES_BIV = ["Bajo", "Medio", "Alto"]


def escala_variable(k: int, paleta: str) -> list:
    return C.escala_continua() if paleta == PALETA_SEMAFORO else ESCALAS_VARIABLES[k % len(ESCALAS_VARIABLES)][1]


def terciles(s: pd.Series) -> pd.Series:
    """0 = tercil bajo, 1 = medio, 2 = alto (sobre los elementos con dato); NaN sin dato."""
    v = pd.to_numeric(s, errors="coerce")
    q1, q2 = v.quantile([1 / 3, 2 / 3])
    return pd.Series(np.where(v.isna(), np.nan, np.where(v <= q1, 0, np.where(v <= q2, 1, 2))), index=s.index)


def cortes_terciles(s: pd.Series) -> tuple[float, float]:
    v = pd.to_numeric(s, errors="coerce")
    q1, q2 = v.quantile([1 / 3, 2 / 3])
    return float(q1), float(q2)


def clasificar_bivariado(a: pd.Series, b: pd.Series, paleta: str = PALETA_BIV_DEFAULT):
    """Terciles de cada variable (sobre los elementos con dato) → clase 'AB' (tercil de a, tercil de b),
    color de la paleta 3×3 y los cortes ((a1, a2), (b1, b2))."""
    colores = PALETAS_BIVARIADAS.get(paleta, COLORES_BIVARIADOS)
    ta, tb = terciles(a), terciles(b)
    clase = pd.Series([None if (np.isnan(x) or np.isnan(y)) else f"{int(x)}{int(y)}" for x, y in zip(ta, tb)],
                      index=a.index)
    color = clase.map(lambda c: colores[int(c[1])][int(c[0])] if isinstance(c, str) else None)
    return clase, color, (cortes_terciles(a), cortes_terciles(b))

# Posición de cada mapa en "lado a lado": (x0, x1, y0, y1) en fracción del área de trazado
_DOMINIOS = {
    1: [(0, 1, 0, 1)],
    2: [(0, 0.495, 0, 1), (0.505, 1, 0, 1)],
    3: [(0, 0.33, 0, 1), (0.335, 0.665, 0, 1), (0.67, 1, 0, 1)],
    4: [(0, 0.495, 0.505, 1), (0.505, 1, 0.505, 1), (0, 0.495, 0, 0.495), (0.505, 1, 0, 0.495)],
}
# Zoom a restar cuando cada mapa ocupa una fracción del ancho/alto
_AJUSTE_ZOOM = {1: 0.0, 2: -1.0, 3: -math.log2(3), 4: -1.0}


def _nombre_subplot(k: int) -> str:
    return "map" if k == 0 else f"map{k + 1}"


def _formato_tick(formato: str) -> dict:
    return {"tickformat": formato.lstrip("$"), "tickprefix": "$" if formato.startswith("$") else ""}


def _capa_cuadrantes(fig, geoms, info, leyenda, opacidad, grosor_borde, subplot="map", mostrar_leyenda=True):
    for p in C.ORDEN_CATEGORIAS:
        sub = info[(info["P"] == p) & info["id"].isin(geoms.keys())]
        if sub.empty:
            continue
        cat = C.CATEGORIAS[p]
        fig.add_trace(go.Choroplethmap(
            geojson=a_geojson({i: geoms[i] for i in sub["id"]}),
            locations=sub["id"], z=[1] * len(sub),
            colorscale=[[0, cat["color"]], [1, cat["color"]]], showscale=False,
            marker=dict(opacity=opacidad, line=dict(color=cat["borde"], width=grosor_borde)),
            name=leyenda.get(p, p), showlegend=mostrar_leyenda, legendgroup=p,
            hovertext=sub["hover"], hovertemplate="%{hovertext}<extra></extra>", subplot=subplot,
        ))


def _capa_base(fig, geoms, info, opacidad, grosor_borde, subplot, mostrar_leyenda):
    """Polígonos en gris debajo de las variables: se ve gris donde la variable no tiene dato."""
    sub = info[info["id"].isin(geoms.keys())]
    if sub.empty:
        return
    cat = C.CATEGORIAS[C.SIN_DATOS]
    fig.add_trace(go.Choroplethmap(
        geojson=a_geojson({i: geoms[i] for i in sub["id"]}),
        locations=sub["id"], z=[1] * len(sub),
        colorscale=[[0, cat["color"]], [1, cat["color"]]], showscale=False,
        marker=dict(opacity=opacidad, line=dict(color=cat["borde"], width=grosor_borde)),
        name="Sin dato", showlegend=mostrar_leyenda, legendrank=1000,
        hovertext=sub["hover"], hovertemplate="%{hovertext}<extra></extra>", subplot=subplot,
    ))


def _capa_variable(fig, geoms, info, var, opacidad, grosor_borde, subplot, visible, colorbar, escala,
                   mostrar_leyenda=True):
    sub = info[info["id"].isin(geoms.keys()) & info[var["col"]].notna()]
    if sub.empty:
        return
    lo, hi = var["rango"]
    fig.add_trace(go.Choroplethmap(
        geojson=a_geojson({i: geoms[i] for i in sub["id"]}),
        locations=sub["id"], z=sub[var["col"]], zmin=lo, zmax=hi,
        colorscale=escala,
        marker=dict(opacity=opacidad, line=dict(color="#555555", width=grosor_borde)),
        colorbar=dict(
            title=dict(text=f"<b>{var['titulo']}</b>", side="top", font=dict(family="Raleway, Arial", size=12)),
            orientation="h", xanchor="left", yanchor="bottom", thickness=12,
            bgcolor="rgba(255,255,255,0.92)", bordercolor="#BBBBBB", borderwidth=1,
            **_formato_tick(var["formato"]), **colorbar,
        ),
        name=var["titulo"], showlegend=mostrar_leyenda, visible=visible,
        hovertext=sub["hover"], hovertemplate="%{hovertext}<extra></extra>", subplot=subplot,
    ))


ZOOM_BURBUJA_LETRA = 8.5   # de aquí hacia adentro las burbujas se ven como círculo blanco con su letra


def _burbujas(fig, burbujas, letra, zoom_ini, subplot, var=None, escala=None, colores=None):
    """Burbujas por grupo. Lejos: color de la variable/cuadrante (tamaño = # rutas). Cerca (zoom ≥
    ZOOM_BURBUJA_LETRA): círculo blanco con la letra del nivel (C, T, R). El cambio al hacer zoom lo hace el
    script del mapa en el navegador; aquí sólo se fija cuál se ve al inicio (y en la imagen exportada)."""
    cerca = zoom_ini >= ZOOM_BURBUJA_LETRA
    tam = 10 + 26 * (burbujas["rutas"] / burbujas["rutas"].max()) ** 0.5
    if colores is not None:
        relleno = dict(color=colores.fillna(C.CATEGORIAS[C.SIN_DATOS]["color"]).tolist())
        borde = "#555555"
    elif var is not None:
        relleno = dict(color=burbujas[var["col"]], colorscale=escala or C.escala_continua(),
                       cmin=var["rango"][0], cmax=var["rango"][1])
        borde = "#555555"
    else:
        relleno = dict(color=[C.CATEGORIAS[p]["color"] for p in burbujas["P"]])
        borde = [C.CATEGORIAS[p]["borde"] for p in burbujas["P"]]
    # Círculo oscuro debajo simula el borde (los marcadores de MapLibre no tienen contorno)
    fig.add_trace(go.Scattermap(lat=burbujas["lat"], lon=burbujas["lon"], mode="markers",
                                marker=dict(size=tam + 3, color=borde), hoverinfo="skip", meta="burbuja",
                                opacity=0 if cerca else 1, showlegend=False, subplot=subplot))
    fig.add_trace(go.Scattermap(lat=burbujas["lat"], lon=burbujas["lon"], mode="markers",
                                marker=dict(size=tam, opacity=1, **relleno), hovertext=burbujas["hover"], meta="burbuja",
                                opacity=0 if cerca else 1,
                                hovertemplate="%{hovertext}<extra></extra>", showlegend=False, subplot=subplot))
    # Vista de cerca: círculo blanco con borde negro y la letra del nivel
    fig.add_trace(go.Scattermap(lat=burbujas["lat"], lon=burbujas["lon"], mode="markers",
                                marker=dict(size=27, color="#000000"), hoverinfo="skip", meta="burbuja_letra",
                                opacity=1 if cerca else 0, showlegend=False, subplot=subplot))
    fig.add_trace(go.Scattermap(lat=burbujas["lat"], lon=burbujas["lon"], mode="markers+text",
                                marker=dict(size=23, color="#FFFFFF"), text=[letra] * len(burbujas),
                                textfont=dict(size=15, color="#000000", weight="bold"), hoverinfo="skip", meta="burbuja_letra",
                                opacity=1 if cerca else 0, showlegend=False, subplot=subplot))


def _capa_bivariada(fig, geoms, info, opacidad, grosor_borde):
    """Un trazo por clase de la paleta 3×3 (columnas 'biv' y 'biv_color' en `info`)."""
    for clase, sub in info[info["id"].isin(geoms.keys()) & info["biv"].notna()].groupby("biv"):
        color = sub["biv_color"].iat[0]
        fig.add_trace(go.Choroplethmap(
            geojson=a_geojson({i: geoms[i] for i in sub["id"]}),
            locations=sub["id"], z=[1] * len(sub),
            colorscale=[[0, color], [1, color]], showscale=False,
            marker=dict(opacity=opacidad, line=dict(color="#555555", width=grosor_borde)),
            showlegend=False, hovertext=sub["hover"], hovertemplate="%{hovertext}<extra></extra>",
        ))


def _fmt(valor: float, formato: str) -> str:
    if valor is None or np.isnan(valor):
        return "—"
    return ("$" + format(valor, formato[1:])) if formato.startswith("$") else format(valor, formato)


def _corto(texto: str, maximo: int = 22) -> str:
    """Nombre corto para escribirlo en diagonal junto al rombo."""
    texto = texto.replace(" (eje Y)", "").replace(" (eje X)", "")
    return texto if len(texto) <= maximo else texto[:maximo - 1] + "…"


def _leyenda_bivariada(fig, cfg: dict, ancho_px: float, alto_px: float):
    """Leyenda en rombo (cuadrícula 3×3 girada 45°) arriba a la izquierda, como el ejemplo europeo:
    la 1ª variable crece hacia arriba-derecha y la 2ª hacia arriba-izquierda. Sobre cada borde inferior,
    paralelos a él, van los valores de corte de los terciles y el nombre de la variable."""
    colores, (var_a, var_b) = cfg["colores"], cfg["titulos"]
    (a1, a2), (b1, b2) = cfg["cortes"]
    fa, fb = cfg["formatos"]
    d, paso = 24.0, 27.0                          # medio rombo y separación entre centros (px)
    caja_x0, caja_ancho, caja_alto = 8.0, 330.0, 290.0
    caja_y1 = alto_px - 8.0
    caja_y0 = caja_y1 - caja_alto
    cx, cy = caja_x0 + caja_ancho / 2, caja_y0 + 128.0  # centro del rombo "ambas bajas"

    def px(x, y):                                 # px desde la esquina inferior izquierda → fracción del área
        return x / ancho_px, y / alto_px

    x0, y0 = px(caja_x0, caja_y0)
    x1, y1 = px(caja_x0 + caja_ancho, caja_y1)
    fig.add_shape(type="rect", xref="paper", yref="paper", x0=x0, y0=y0, x1=x1, y1=y1,
                  fillcolor="rgba(255,255,255,0.95)", line=dict(color="#777777", width=1))
    for fila in range(3):
        for col in range(3):
            ux, uy = cx + (col - fila) * paso, cy + (col + fila) * paso
            puntos = [px(ux, uy - d), px(ux + d, uy), px(ux, uy + d), px(ux - d, uy)]
            ruta = "M " + " L ".join(f"{x:.5f},{y:.5f}" for x, y in puntos) + " Z"
            fig.add_shape(type="path", path=ruta, xref="paper", yref="paper",
                          fillcolor=colores[fila][col], line=dict(color="#333333", width=0.8))
    chica = dict(size=10, family="Raleway, Arial", color="#333")
    fuente = dict(size=11, family="Raleway, Arial", color="#111")
    # Borde inferior derecho: 1ª variable (columnas)
    for k, valor in enumerate((a1, a2)):
        bx, by = cx + (k + 0.5) * paso + d / 2 + 8, cy + (k + 0.5) * paso - d / 2 - 8
        xx, yy = px(bx, by)
        fig.add_annotation(xref="paper", yref="paper", x=xx, y=yy, text=_fmt(valor, fa), textangle=-45,
                           showarrow=False, font=chica)
    # Nombre de la 1ª variable paralelo al borde inferior derecho, con la flecha hacia donde crece
    bx, by = cx + 1.0 * paso + d / 2 + 24, cy + 1.0 * paso - d / 2 - 24
    xx, yy = px(bx, by)
    fig.add_annotation(xref="paper", yref="paper", x=xx, y=yy, text=f"<b>{_corto(var_a)}</b> →", textangle=-45,
                       showarrow=False, font=fuente)
    # Borde inferior izquierdo: 2ª variable (filas)
    for k, valor in enumerate((b1, b2)):
        bx, by = cx - (k + 0.5) * paso - d / 2 - 8, cy + (k + 0.5) * paso - d / 2 - 8
        xx, yy = px(bx, by)
        fig.add_annotation(xref="paper", yref="paper", x=xx, y=yy, text=_fmt(valor, fb), textangle=45,
                           showarrow=False, font=chica)
    # Nombre de la 2ª variable paralelo al borde inferior izquierdo
    bx, by = cx - 1.0 * paso - d / 2 - 24, cy + 1.0 * paso - d / 2 - 24
    xx, yy = px(bx, by)
    fig.add_annotation(xref="paper", yref="paper", x=xx, y=yy, text=f"← <b>{_corto(var_b)}</b>", textangle=45,
                       showarrow=False, font=fuente)
    # Sin dato y lectura rápida
    sx, sy = caja_x0 + caja_ancho - 72, caja_y1 - 22
    a, b = px(sx, sy), px(sx + 14, sy + 14)
    fig.add_shape(type="rect", xref="paper", yref="paper", x0=a[0], y0=a[1], x1=b[0], y1=b[1],
                  fillcolor=C.CATEGORIAS[C.SIN_DATOS]["color"], line=dict(color="#333333", width=0.8))
    xx, yy = px(sx + 20, sy + 7)
    fig.add_annotation(xref="paper", yref="paper", x=xx, y=yy, xanchor="left", text="Sin dato",
                       showarrow=False, font=chica)
    xx, yy = px(caja_x0 + 8, caja_y1 - 6)
    fig.add_annotation(xref="paper", yref="paper", x=xx, y=yy, xanchor="left", yanchor="top", align="left",
                       text="<b>Terciles</b>", showarrow=False, font=chica)


COLOR_CONTORNO = "#1A1A1A"
GROSOR_CONTORNO = 1.8


def _contornos(fig, contornos: dict, subplot: str, mostrar_leyenda: bool,
               color: str = COLOR_CONTORNO, grosor: float = GROSOR_CONTORNO,
               nombre: str = "Contorno de la ruta (todos sus días)"):
    """Borde alrededor de toda la huella de cada elemento (`contornos`: id → anillos). Un solo trazo de
    líneas separadas por None; no captura el cursor para no tapar el detalle de los polígonos."""
    lats, lons = [], []
    for anillos in contornos.values():
        for anillo in anillos:
            xs, ys = anillo.xy
            lons.extend(list(xs) + [None])
            lats.extend(list(ys) + [None])
    if not lats:
        return
    fig.add_trace(go.Scattermap(lat=lats, lon=lons, mode="lines", hoverinfo="skip",
                                line=dict(color=color, width=grosor),
                                name=nombre, legendgroup=nombre,
                                showlegend=mostrar_leyenda, legendrank=2000, subplot=subplot))


ZOOM_MIN_CONTORNO = 8.0   # de nivel ciudad hacia adentro; más lejos las rutas son tan chicas que se verían negras


def capa_contornos(contornos: dict) -> list:
    """Contorno oscuro de cada ruta como capa del mapa base que sólo aparece al acercarse (zoom de ciudad).
    En la vista nacional las rutas son tan pequeñas que el borde las taparía."""
    lineas = [[list(c) for c in anillo.coords] for anillos_ in contornos.values() for anillo in anillos_]
    if not lineas:
        return []
    geojson = {"type": "Feature", "properties": {}, "geometry": {"type": "MultiLineString", "coordinates": lineas}}
    return [dict(sourcetype="geojson", source=geojson, type="line", color=COLOR_CONTORNO,
                 line=dict(width=GROSOR_CONTORNO), minzoom=ZOOM_MIN_CONTORNO)]


def _leyenda_contorno(fig, subplot):
    """Entrada de leyenda para el contorno (la capa del mapa base no aparece sola en la leyenda)."""
    fig.add_trace(go.Scattermap(lat=[None], lon=[None], mode="lines", line=dict(color=COLOR_CONTORNO, width=2),
                                name="Contorno de la ruta (se ve al acercar)", hoverinfo="skip", subplot=subplot,
                                legendrank=2000))


def _mapa_cuadrantes_lado(fig, geoms, info, leyenda, opacidad, grosor_borde, etiquetas, dominio):
    """Primer mapa de "lado a lado": los cuadrantes (P), para comparar con cada variable."""
    x0, x1, _y0, y1 = dominio
    _capa_cuadrantes(fig, geoms, info, leyenda, opacidad, grosor_borde, subplot="map", mostrar_leyenda=True)
    if etiquetas is not None and not etiquetas.empty:
        _etiquetas(fig, etiquetas, "map")
    fig.add_annotation(x=(x0 + x1) / 2, y=y1, xref="paper", yref="paper", yanchor="top",
                       text="<b>Cuadrantes de la matriz (P)</b>", showarrow=False,
                       bgcolor="rgba(255,255,255,0.9)", bordercolor="#BBBBBB", borderwidth=1,
                       font=dict(size=13, family="Raleway, Arial"))


NOMBRE_FONDO = "Rutas sólo web (zona amplia, al fondo)"


def _capa_fondo(fig, geoms, info, subplot, mostrar_leyenda):
    """Rutas con zona muy grande (sólo canal web): gris tenue debajo de todo para no tapar a las demás."""
    sub = info[info["id"].isin(geoms.keys())]
    if sub.empty:
        return
    fig.add_trace(go.Choroplethmap(
        geojson=a_geojson({i: geoms[i] for i in sub["id"]}), locations=sub["id"], z=[1] * len(sub),
        colorscale=[[0, "#BDBDBD"], [1, "#BDBDBD"]], showscale=False,
        marker=dict(opacity=0.22, line=dict(color="#8A8A8A", width=1)),
        name=NOMBRE_FONDO, showlegend=mostrar_leyenda, legendgroup="fondo", legendrank=1500,
        hovertext=sub["hover"], hovertemplate="%{hovertext}<extra></extra>", subplot=subplot))


def _etiquetas(fig, etiquetas, subplot):
    fig.add_trace(go.Scattermap(lat=etiquetas["lat"], lon=etiquetas["lon"], text=etiquetas["texto"],
                                mode="text", textfont=dict(size=12, color="#1F1F1F"),
                                hoverinfo="skip", showlegend=False, subplot=subplot))


def construir_mapa(
    geoms: dict[str, object],
    info: pd.DataFrame,
    leyenda: dict[str, str],
    *,
    titulo: str,
    subtitulo: str = "",
    centro: dict,
    zoom: float,
    opacidad: float = 0.75,
    grosor_borde: float = 0.6,
    estilo: str = "carto-positron",
    etiquetas: pd.DataFrame | None = None,
    burbujas: pd.DataFrame | None = None,
    variables: list[dict] | None = None,
    modo_variables: str = MODO_CAPAS,
    paleta: str = PALETA_DISTINTA,
    bivariado_cfg: dict | None = None,
    contornos: dict | None = None,
    con_cuadrantes: bool = True,
    fondo: set | None = None,
    letra_burbuja: str = "C",
    alto: int = 720,
    ancho: int | None = None,
    uirevision: str | None = None,
) -> go.Figure:
    """Mapa por cuadrante o por variables continuas.

    `info`: id, P, hover y una columna por variable. `variables`: lista de
    {"titulo", "col", "rango": (min, max), "formato"}. En modo capas cada variable es una capa que
    se enciende/apaga en la leyenda (sólo la primera arranca visible); en lado a lado, un mapa por
    variable. `uirevision` conserva el zoom/paneo del usuario mientras no cambie. `contornos`: id → anillos
    exteriores (de `datos.contornos`) que se dibujan como borde oscuro de cada ruta.
    """
    fig = go.Figure()
    variables = variables or []
    lado_a_lado = modo_variables == MODO_LADO and (len(variables) >= 2 or (len(variables) == 1 and con_cuadrantes))
    bivariado = len(variables) == 2 and modo_variables == MODO_BIVARIADO and "biv" in info
    extra_p = 1 if (lado_a_lado and con_cuadrantes) else 0   # 1er mapa = cuadrantes
    n_mapas = len(variables) + extra_p if lado_a_lado else 1
    dominios = _DOMINIOS[n_mapas]
    zoom_ini = zoom + _AJUSTE_ZOOM[n_mapas]
    if fondo:   # rutas de zona muy grande: primero (debajo) y fuera de las demás capas
        de_fondo = info["id"].isin(fondo)
        for k in range(n_mapas):
            _capa_fondo(fig, geoms, info[de_fondo], _nombre_subplot(k), mostrar_leyenda=k == 0)
        info = info[~de_fondo]

    if bivariado:
        _capa_base(fig, geoms, info, opacidad, grosor_borde, "map", mostrar_leyenda=False)
        _capa_bivariada(fig, geoms, info, opacidad, grosor_borde)
        if burbujas is not None and not burbujas.empty and "biv_color" in burbujas:
            _burbujas(fig, burbujas, letra_burbuja, zoom_ini, "map", colores=burbujas["biv_color"])
        if etiquetas is not None and not etiquetas.empty:
            _etiquetas(fig, etiquetas, "map")
        if bivariado_cfg is not None:
            _leyenda_bivariada(fig, bivariado_cfg, float(ancho or 1150), float((alto or 720) - 70))
    elif not variables:
        _capa_cuadrantes(fig, geoms, info, leyenda, opacidad, grosor_borde)
        if burbujas is not None and not burbujas.empty:
            _burbujas(fig, burbujas, letra_burbuja, zoom_ini, "map")
        if etiquetas is not None and not etiquetas.empty:
            _etiquetas(fig, etiquetas, "map")
    elif not lado_a_lado:
        _capa_base(fig, geoms, info, opacidad, grosor_borde, "map", mostrar_leyenda=True)
        for k, var in enumerate(variables):
            # Barras de color apiladas abajo a la izquierda; sólo se ven las de capas encendidas
            _capa_variable(fig, geoms, info, var, opacidad, grosor_borde, "map",
                           visible=True if k == 0 else "legendonly",
                           colorbar=dict(x=0.01, y=0.02 + 0.12 * k, len=0.3), escala=escala_variable(k, paleta))
        if burbujas is not None and not burbujas.empty:
            _burbujas(fig, burbujas, letra_burbuja, zoom_ini, "map", variables[0], escala=escala_variable(0, paleta))
        if etiquetas is not None and not etiquetas.empty:
            _etiquetas(fig, etiquetas, "map")
    else:
        if extra_p:
            _mapa_cuadrantes_lado(fig, geoms, info, leyenda, opacidad, grosor_borde, etiquetas, dominios[0])
        for k0, var in enumerate(variables):
            k = k0 + extra_p
            sp = _nombre_subplot(k)
            x0, x1, y0, y1 = dominios[k]
            _capa_base(fig, geoms, info, opacidad, grosor_borde, sp, mostrar_leyenda=False)
            _capa_variable(fig, geoms, info, var, opacidad, grosor_borde, sp, visible=True,
                           colorbar=dict(x=x0 + 0.01, y=y0 + 0.02, len=(x1 - x0) * 0.6),
                           escala=escala_variable(k0, paleta), mostrar_leyenda=False)
            if burbujas is not None and not burbujas.empty:
                _burbujas(fig, burbujas, letra_burbuja, zoom_ini, sp, var, escala=escala_variable(k0, paleta))
            if etiquetas is not None and not etiquetas.empty:
                _etiquetas(fig, etiquetas, sp)
            fig.add_annotation(x=(x0 + x1) / 2, y=y1, xref="paper", yref="paper", yanchor="top",
                               text=f"<b>{var['titulo']}</b>", showarrow=False,
                               bgcolor="rgba(255,255,255,0.9)", bordercolor="#BBBBBB", borderwidth=1,
                               font=dict(size=13, family="Raleway, Arial"))

    capas = capa_contornos(contornos) if contornos else []
    if capas:
        _leyenda_contorno(fig, "map")

    texto_titulo = f"<b>{titulo}</b>"
    if subtitulo:
        texto_titulo += f"<br><span style='font-size:13px;color:#555'>{subtitulo}</span>"
    rev = uirevision if uirevision is not None else True
    zoom_mapa = zoom + _AJUSTE_ZOOM[n_mapas]
    mapas = {
        _nombre_subplot(k): dict(style=estilo, center=centro, zoom=zoom_mapa, uirevision=rev, layers=capas,
                                 domain=dict(x=[d[0], d[1]], y=[d[2], d[3]]))
        for k, d in enumerate(dominios)
    }
    fig.update_layout(
        title=dict(text=texto_titulo, x=0.01, y=0.98, font=dict(size=20, family="Raleway, Arial")),
        margin=dict(l=0, r=0, t=70, b=0),
        height=alto if n_mapas < 4 else int(alto * 1.25),
        width=ancho,
        showlegend=not bivariado,
        legend=dict(
            x=0.01 if (not variables or lado_a_lado) else 0.99, y=0.02 if (not variables or lado_a_lado) else 0.98,
            xanchor="left" if (not variables or lado_a_lado) else "right",
            yanchor="bottom" if (not variables or lado_a_lado) else "top",
            bgcolor="rgba(255,255,255,0.92)", bordercolor="#BBBBBB", borderwidth=1,
            font=dict(size=12 if lado_a_lado else 13, family="Raleway, Arial"),
            title=dict(text="<b>Matriz Atractividad × Madurez</b>" if (not variables or lado_a_lado)
                       else "<b>Capas</b> <span style='font-size:11px'>(clic para encender/apagar)</span>"),
        ),
        paper_bgcolor="white",
        hoverlabel=dict(align="left", font=dict(family="Raleway, Arial")),
        uirevision=rev,
        **mapas,
    )
    return fig


def n_mapas(variables: list, modo_variables: str, con_cuadrantes: bool) -> int:
    """Cuántos mapas lleva la figura (misma regla que construir_mapa)."""
    lado = modo_variables == MODO_LADO and (len(variables) >= 2 or (len(variables) == 1 and con_cuadrantes))
    return len(variables) + (1 if con_cuadrantes else 0) if lado else 1


def zoom_para_exportar(zoom_pantalla: float, ancho_pantalla: float, alto_pantalla: float,
                       ancho: int, alto: int, mapas: int) -> float:
    """Zoom que hay que pasar a construir_mapa para que la imagen exportada muestre la misma zona que el mapa en
    pantalla (cada mapa de la imagen es más grande que en pantalla, así que se acerca en proporción)."""
    x0, x1, y0, y1 = _DOMINIOS[mapas][0]
    w_img, h_img = ancho * (x1 - x0), (alto - 70) * (y1 - y0)
    factor = min(w_img / max(ancho_pantalla, 1), h_img / max(alto_pantalla, 1))
    return zoom_pantalla + math.log2(max(factor, 1e-3)) - _AJUSTE_ZOOM[mapas]


def anillos(geom) -> list:
    """Bordes exteriores de un polígono o multipolígono."""
    return [g.exterior for g in getattr(geom, "geoms", [geom]) if g.geom_type == "Polygon"]


def construir_comparacion(
    geoms: dict[str, object],
    lados: list[tuple[str, pd.DataFrame]],
    leyenda: dict[str, str],
    *,
    titulo: str,
    centro: dict,
    zoom: float,
    opacidad: float = 0.8,
    grosor_borde: float = 0.6,
    estilo: str = "carto-positron",
    contornos: dict | None = None,
    resaltar: set | None = None,
    fondo: set | None = None,
    alto: int = 640,
    uirevision: str | None = None,
) -> go.Figure:
    """Dos mapas lado a lado coloreados por cuadrante, uno por escenario (`lados`: [(título, info)], info
    con id, P y hover). `resaltar`: ids que cambian de P entre ambos (borde rojo en los dos mapas)."""
    fig = go.Figure()
    dominios = _DOMINIOS[2]
    for k, (subtitulo, info) in enumerate(lados):
        sp = _nombre_subplot(k)
        if fondo:
            _capa_fondo(fig, geoms, info[info["id"].isin(fondo)], sp, mostrar_leyenda=k == 0)
            info = info[~info["id"].isin(fondo)]
        _capa_cuadrantes(fig, geoms, info, leyenda, opacidad, grosor_borde, subplot=sp, mostrar_leyenda=k == 0)
        if resaltar:
            # Rojo normalmente; negro y más grueso en modo daltonismo (el rojo no se distingue del verde)
            _contornos(fig, {i: anillos(geoms[i]) for i in resaltar if i in geoms}, sp, mostrar_leyenda=k == 0,
                       color="#000000" if C.es_daltonismo() else "#F30000",
                       grosor=3.6 if C.es_daltonismo() else 2.6, nombre="Cambia de cuadrante")
        x0, x1, _, y1 = dominios[k]
        # Título de cada mapa pegado a su esquina izquierda, en dos renglones para que no se encimen
        fig.add_annotation(x=x0 + 0.005, y=y1 - 0.01, xref="paper", yref="paper", xanchor="left", yanchor="top",
                           text=f"<b>{'Izquierdo' if k == 0 else 'Derecho'}</b><br>{subtitulo.replace(' · ', '<br>')}",
                           showarrow=False, align="left",
                           bgcolor="rgba(255,255,255,0.94)", bordercolor="#777777", borderwidth=1, borderpad=4,
                           font=dict(size=12, family="Raleway, Arial", color="#1F1F1F"))
    rev = uirevision if uirevision is not None else True
    capas = capa_contornos(contornos) if contornos else []
    if capas:
        _leyenda_contorno(fig, "map")
    mapas = {_nombre_subplot(k): dict(style=estilo, center=centro, zoom=zoom + _AJUSTE_ZOOM[2], uirevision=rev,
                                      layers=capas, domain=dict(x=[d[0], d[1]], y=[d[2], d[3]]))
             for k, d in enumerate(dominios)}
    fig.update_layout(
        title=dict(text=f"<b>{titulo}</b>", x=0.01, y=0.98, font=dict(size=18, family="Raleway, Arial")),
        margin=dict(l=0, r=0, t=60, b=0), height=alto, paper_bgcolor="white", uirevision=rev,
        hoverlabel=dict(align="left", font=dict(family="Raleway, Arial")),
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.01, yanchor="top",
                    font=dict(size=12, family="Raleway, Arial")),
        **mapas,
    )
    return fig


def construir_dispersion(
    puntos: pd.DataFrame, umbral_x: float, umbral_y: float, *, tamano_por_rutas: bool,
    seleccion: set | None = None, alto: int = 420, uirevision: str | None = None,
) -> go.Figure:
    """Matriz como dispersión. `puntos`: id, x, y, P, hover, rutas. customdata = id (para selección).
    `seleccion`: ids resaltados (el resto se atenúa)."""
    fig = go.Figure()
    # Fondo de los cuadrantes con la paleta de la matriz
    cuadrantes = [("P2", 0, umbral_x, umbral_y, 100), ("P1", umbral_x, 100, umbral_y, 100),
                  ("P4", 0, umbral_x, 0, umbral_y), ("P3", umbral_x, 100, 0, umbral_y)]
    for p, x0, x1, y0, y1 in cuadrantes:
        cat = C.CATEGORIAS[p]
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=cat["color"], opacity=0.28,
                      line_width=0, layer="below")
        fig.add_annotation(x=(x0 + x1) / 2, y=y1 - 3, text=f"<b>{cat['nombre']}</b> <i>{p}</i>",
                           showarrow=False, font=dict(size=11, color="#333"), yanchor="top")
    linea_corte = "#111111" if C.es_daltonismo() else "#F30000"
    fig.add_hline(y=umbral_y, line=dict(color=linea_corte, width=1.5, dash="dot"))
    fig.add_vline(x=umbral_x, line=dict(color=linea_corte, width=1.5, dash="dot"))

    maximo = max(puntos["rutas"].max(), 1) if not puntos.empty else 1
    for p in C.ORDEN_CATEGORIAS[:-1]:
        sub = puntos[puntos["P"] == p]
        if sub.empty:
            continue
        cat = C.CATEGORIAS[p]
        tam = (8 + 30 * (sub["rutas"] / maximo) ** 0.5) if tamano_por_rutas else 9
        seleccionados = None
        if seleccion:
            seleccionados = [i for i, x in enumerate(sub["id"]) if x in seleccion]
        fig.add_trace(go.Scatter(
            x=sub["x"], y=sub["y"], mode="markers", name=p,
            # Cada cuadrante con su forma (no sólo su color): círculo, cuadrado, rombo, triángulo
            marker=dict(size=tam, color=cat["color"], symbol=C.SIMBOLOS[p], line=dict(color=cat["borde"], width=1.2)),
            customdata=sub["id"], hovertext=sub["hover"], hovertemplate="%{hovertext}<extra></extra>",
            selectedpoints=seleccionados,
            selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=0.15)),
        ))
    fig.update_layout(
        height=alto, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
        xaxis=dict(title="<b>Atractividad</b>", range=[-2, 102], zeroline=False, showgrid=False),
        yaxis=dict(title="<b>Madurez</b>", range=[-2, 102], zeroline=False, showgrid=False),
        plot_bgcolor="white", dragmode="select",
        font=dict(family="Raleway, Arial"), uirevision=uirevision if uirevision is not None else True,
    )
    return fig


def construir_dispersion_bivariada(
    puntos: pd.DataFrame, cfg: dict, *, tamano_por_rutas: bool, seleccion: set | None = None,
    alto: int = 420, uirevision: str | None = None,
) -> go.Figure:
    """Dispersión de las 2 variables con la cuadrícula 3×3 de terciles pintada con la paleta bivariada y
    el número de elementos de cada celda (como el ejemplo europeo). `puntos`: id, v0, v1, biv, hover, rutas."""
    colores, (var_a, var_b) = cfg["colores"], cfg["titulos"]
    (a1, a2), (b1, b2) = cfg["cortes"]
    fa, fb = cfg["formatos"]
    x, y = puntos["v0"].astype(float), puntos["v1"].astype(float)
    fig = go.Figure()
    if puntos.empty:
        return fig

    def limites(v, c1, c2):
        lo, hi = float(v.min()), float(v.max())
        margen = (hi - lo) * 0.04 or 1.0
        return [lo - margen, c1, c2, hi + margen]
    xs, ys = limites(x, a1, a2), limites(y, b1, b2)
    conteo = puntos["biv"].value_counts()
    for fila in range(3):
        for col in range(3):
            fig.add_shape(type="rect", x0=xs[col], x1=xs[col + 1], y0=ys[fila], y1=ys[fila + 1],
                          fillcolor=colores[fila][col], line_width=0, layer="below")
            n = int(conteo.get(f"{col}{fila}", 0))
            fig.add_annotation(x=(xs[col] + xs[col + 1]) / 2, y=(ys[fila] + ys[fila + 1]) / 2, text=f"<b>{n}</b>",
                               showarrow=False, bgcolor="rgba(255,255,255,0.9)", bordercolor="#333",
                               borderwidth=1, borderpad=2, font=dict(size=11, color="#111"))
    maximo = max(puntos["rutas"].max(), 1)
    tam = (6 + 22 * (puntos["rutas"] / maximo) ** 0.5) if tamano_por_rutas else 5
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="markers", marker=dict(size=tam, color="#111111", line=dict(color="white", width=0.5)),
        customdata=puntos["id"], hovertext=puntos["hover"], hovertemplate="%{hovertext}<extra></extra>",
        selectedpoints=[i for i, v in enumerate(puntos["id"]) if v in seleccion] if seleccion else None,
        selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=0.15)), showlegend=False,
    ))
    fig.update_layout(
        height=alto, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="white", dragmode="select",
        font=dict(family="Raleway, Arial"), uirevision=uirevision if uirevision is not None else True,
        xaxis=dict(title=f"<b>{var_a}</b> →", range=[xs[0], xs[-1]], zeroline=False, showgrid=False,
                   **_formato_tick(fa)),
        yaxis=dict(title=f"<b>{var_b}</b> →", range=[ys[0], ys[-1]], zeroline=False, showgrid=False,
                   **_formato_tick(fb)),
    )
    return fig


def exportar_jpg(fig: go.Figure, ancho: int, alto: int, escala: float = 2.0) -> bytes:
    fig_exp = go.Figure(fig)
    fig_exp.update_layout(width=ancho, height=alto)
    return fig_exp.to_image(format="jpg", width=ancho, height=alto, scale=escala)
