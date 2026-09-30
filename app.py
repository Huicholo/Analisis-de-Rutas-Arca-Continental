"""Mapa interactivo de la matriz Atractividad × Madurez por ruta, CeDi, territorio o región.

Ejecutar:  streamlit run app.py
"""
from __future__ import annotations

import hashlib
import io
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from mapa import config as C
from mapa import datos, estrategia, figura, modelo

st.set_page_config(page_title="Mapa de rutas · Atractividad × Madurez", layout="wide")

URL_MANUAL = "app/static/manual.html"


def encabezado(titulo: str, que_es: str, ayuda: str, nivel_titulo: str = "####") -> None:
    """Título de cada visual con su círculo "?" (al pasar el cursor explica todo) y una línea que dice
    qué se está viendo."""
    st.markdown(f"{nivel_titulo} {titulo}", help=ayuda)
    st.markdown(f"<div class='tagline'>{que_es}</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------- datos
# El libro puede venir de Data\ (oficial) o subirse desde la app sólo para esta sesión.
# `clave` identifica la versión: fecha de guardado del oficial o huella del archivo subido.
def fecha_libro() -> float:
    return C.EXCEL_ANALISIS.stat().st_mtime


@st.cache_resource(show_spinner="Leyendo el libro de análisis…", max_entries=4)
def insumos(clave: str, _origen) -> modelo.Insumos:
    return modelo.leer_libro(io.BytesIO(_origen) if isinstance(_origen, bytes) else _origen)


@st.cache_data(show_spinner="Calculando madurez y atractividad…", max_entries=32)
def resultados(clave: str, escenario: str, caso: str, _origen) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    df, resumen = modelo.calcular(insumos(clave, _origen), escenario, caso)
    return df, datos.preparar_resultados(df), resumen


@st.cache_resource(show_spinner="Procesando polígonos de rutas…")
def geometrias(canales: tuple[str, ...], dias: tuple[str, ...] | None) -> dict:
    return datos.cargar_geometrias(canales, dias)


@st.cache_resource(show_spinner="Trazando el contorno de cada ruta…")
def contornos_ruta(canales: tuple[str, ...], dias: tuple[str, ...] | None) -> dict:
    return datos.contornos(geometrias(canales, dias))


@st.cache_resource(show_spinner="Midiendo zonas sin cobertura alrededor de cada ruta…")
def area_sin_cobertura(canales: tuple[str, ...], radio: float) -> dict:
    return datos.area_sin_cobertura(geometrias(canales, None), radio,
                                    cobertura=geometrias(("Convencional",), None))


@st.cache_resource(show_spinner="Uniendo polígonos por nivel…")
def geometrias_grupo(canales: tuple[str, ...], dias: tuple[str, ...] | None,
                     grupos: tuple[tuple[str, tuple[str, ...]], ...]) -> dict:
    return datos.disolver(geometrias(canales, dias), {g: list(r) for g, r in grupos})


def fmt(v, dec=1):
    return "—" if pd.isna(v) else f"{v:,.{dec}f}"


# --------------------------------------------------------------------------- libro de análisis
st.title("Mapa de rutas · Matriz Atractividad × Madurez")
st.markdown("<div class='tagline'>Esta página acomoda cada ruta en una matriz de 4 cuadrantes según <b>qué tan bien "
            "opera</b> (madurez) y <b>qué tanto potencial tiene su zona</b> (atractividad), y te dice qué hacer con "
            "cada una. Pasa el cursor sobre cualquier círculo <b>?</b> para ver una explicación.</div>",
            unsafe_allow_html=True)
with st.expander("¿Primera vez aquí? Cómo usar esta página en 4 pasos", expanded=False):
    st.markdown(
        "1. **Elige los escenarios** con los dos selectores de abajo (si no sabes cuál, deja *Medio* y *Conservador*).\n"
        "2. **Elige qué ver** en el panel de la izquierda: por ruta, CeDi, territorio o región, y filtra si quieres.\n"
        "3. **Lee la matriz y el mapa**: el color de cada zona dice su cuadrante. Pasa el cursor sobre el mapa para "
        "ver el detalle y la estrategia recomendada.\n"
        "4. **Descarga** lo que necesites (imagen del mapa o tablas en Excel) con los botones *Descargar*.\n\n"
        "Si algo se ve raro, usa **Restablecer todo** al final del panel izquierdo para volver a como estaba al abrir. "
        "El manual completo está en el botón **Abrir el manual de uso**.")

# --- Arriba del panel: manual y accesibilidad (antes que nada, porque cambian cómo se ve todo)
st.sidebar.link_button("Abrir el manual de uso", URL_MANUAL, width="stretch", type="primary",
                       help="Guía paso a paso con imágenes de cada parte de la herramienta. Se abre en otra pestaña.")
with st.sidebar.expander("Accesibilidad", expanded=False):
    modo_daltonismo = st.toggle(
        "Modo daltonismo", key="modo_daltonismo",
        help="Cambia los colores por unos que se distinguen aunque la persona no vea bien el rojo y el verde "
             "(u otros colores). Además escribe el cuadrante (P1, P2…) sobre el mapa y usa formas distintas "
             "para cada cuadrante en la gráfica.")
    texto_grande = st.toggle("Texto más grande", key="texto_grande",
                             help="Aumenta el tamaño de todas las letras de la página.")
C.usar_paleta("Daltonismo" if modo_daltonismo else "Normal")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Raleway:ital,wght@0,400;0,600;0,700;1,400&display=swap');
.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
.stApp button, .stApp input, .stApp textarea, .stApp [data-baseweb="select"] div,
.stApp [data-testid="stMetricValue"], .stApp [data-testid="stMetricLabel"] {{
    font-family: Raleway, Arial, sans-serif;
}}
.stApp h1 {{ color: #000000; }}
.stApp h4 {{ color: #000000; margin-bottom: 0; }}
.tagline {{ color: #5E5E5E; font-size: 0.95rem; margin: 0 0 0.6rem 0; }}
.paso {{ background: #F30000; color: white; border-radius: 50%; display: inline-block; width: 1.6em;
         height: 1.6em; text-align: center; line-height: 1.6em; font-weight: 700; margin-right: 6px; }}
{"html { font-size: 19px; } .stApp p, .stApp li, .stApp label { font-size: 1.08rem !important; }"
 if texto_grande else ""}
</style>""", unsafe_allow_html=True)

exp_libro = st.sidebar.expander("Libro de análisis (datos)", expanded=False)
with exp_libro:
    subido = st.file_uploader(
        "Probar con otro libro (.xlsx)", type=["xlsx"],
        help="Se usa sólo en esta sesión del navegador; no reemplaza el archivo de la carpeta Data. "
             "Debe tener la misma estructura que el libro oficial.")
    if subido is not None:
        contenido = subido.getvalue()
        clave, origen = f"subido:{hashlib.sha1(contenido).hexdigest()}", contenido
        nombre_libro, fecha_txt = subido.name, "subido en esta sesión"
    else:
        try:
            clave, origen = f"oficial:{fecha_libro()}", C.EXCEL_ANALISIS
        except FileNotFoundError:
            st.error(f"No existe `{C.EXCEL_ANALISIS}`")
            st.stop()
        nombre_libro = C.EXCEL_ANALISIS.name
        fecha_txt = pd.Timestamp(fecha_libro(), unit="s", tz="UTC").tz_convert("America/Mexico_City") \
            .strftime("guardado %d/%m/%Y %H:%M")
    st.caption(f"En uso: **{nombre_libro}** ({fecha_txt}).")

try:
    ins = insumos(clave, origen)
except Exception as e:  # libro ausente, bloqueado o con otra estructura
    st.error(f"No se pudo leer el libro de análisis `{nombre_libro}`: {e}")
    st.stop()
if subido is not None:
    st.info(f"Usando el libro subido **{subido.name}** (sólo en esta sesión). "
            "Quítalo en *Libro de análisis (datos)* para volver al oficial.")

# --------------------------------------------------------------------------- casos del modelo

escenarios = list(ins.escenarios)
casos = list(ins.casos_atractividad)
caso_con_datos = {c: ins.caso_disponible(c) for c in casos}
col_esc, col_caso = st.columns(2)
def nombre_caso(c: str) -> str:
    """Casos de potencial con su nombre de negocio (Conservador / Medio / Ambicioso)."""
    return C.NOMBRES_POTENCIAL.get(c, c)


escenario = col_esc.radio(
    "Escenarios de carga de camión OP", escenarios, horizontal=True,
    index=escenarios.index(C.ESCENARIO_DEFAULT) if C.ESCENARIO_DEFAULT in escenarios else 0,
    help="Qué tan exigente es la meta contra la que se mide cada ruta. Conservador = meta más fácil, "
         "Ambicioso = meta más difícil. Cambia la MADUREZ (qué tan bien opera la ruta). Si no sabes cuál, "
         "deja Medio.")
caso = col_caso.radio(
    "Casos de potencial", casos, horizontal=True,
    index=next((i for i, c in enumerate(casos) if caso_con_datos[c]), 0),
    format_func=lambda c: nombre_caso(c) if caso_con_datos[c] else f"{nombre_caso(c)} (sin datos)",
    help="Qué tan optimista es el cálculo del potencial de la zona de cada ruta. Conservador = potencial "
         "más bajo, Ambicioso = más alto. Cambia la ATRACTIVIDAD (qué tanto se puede crecer ahí). "
         "Si un caso dice 'sin datos', todavía no está capturado en el Excel.")
if not caso_con_datos[caso]:
    st.warning(f"El caso de potencial **{nombre_caso(caso)}** ({caso}) todavía no tiene datos en "
               "'Base de datos Rutas': ninguna ruta tiene "
               "atractividad y todas quedan como *Sin datos*. Captura el bloque en el Excel y guarda; "
               "la app lo tomará al recargar.")

df_modelo, df_base, resumen_modelo = resultados(clave, escenario, caso, origen)
# Catálogo de variables continuas: etiqueta -> (columna, formato, grupo)
catalogo = dict(C.VARIABLES_CONTINUAS)


def formato_auto(serie: pd.Series) -> str:
    """Formato para variables de segmento según su escala (fracciones → %, montos grandes sin decimales)."""
    v = pd.to_numeric(serie, errors="coerce").dropna()
    if v.empty:
        return ",.2f"
    if v.abs().max() <= 1.5:
        return ".1%"
    mediana = v.abs().median()
    return ",.0f" if mediana >= 1000 else (",.1f" if mediana >= 10 else ",.2f")


# Variables de la hoja de segmentos: se cruzan por Ruta o por CeDi y se agregan al catálogo
seg = ins.segmentos
if seg is not None and seg.variables:
    renombre = {v: f"Seg · {v}" for v in seg.variables}
    df_base = df_base.merge(seg.datos.rename(columns=renombre), on=seg.llave, how="left")
    for v, col in renombre.items():
        catalogo[v if v not in catalogo else f"{v} (segmento)"] = (col, formato_auto(df_base[col]), "Segmento")
    con_dato = int(df_base[list(renombre.values())].notna().any(axis=1).sum())
    exp_libro.caption(f"Hoja de segmentos **{seg.hoja}**: {len(seg.variables)} variables, cruce por "
                      f"{seg.llave} ({con_dato:,} de {len(df_base):,} rutas con dato).")
elif seg is not None:
    exp_libro.warning(f"La hoja **{seg.hoja}** no tiene columnas numéricas para usar como variables.")
umbral_y_default = resumen_modelo["corte_madurez"]
umbral_x_default = resumen_modelo["corte_atractividad"]
if pd.isna(umbral_x_default):
    umbral_x_default = C.UMBRAL_X_DEFAULT
if pd.isna(umbral_y_default):
    umbral_y_default = 50.0

# --------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("<span class='paso'>1</span> **¿Qué quieres ver en el mapa?**", unsafe_allow_html=True)
    nivel = st.radio("Colorear por", list(C.NIVELES), horizontal=True,
                     help="Ruta = cada ruta por separado (lo más detallado). CeDi, Territorio y Región = agrupa "
                          "las rutas; el color es el cuadrante de la ruta 'de en medio' (mediana) del grupo.")
    col_nivel = C.NIVELES[nivel]

    st.markdown("<span class='paso'>2</span> **Filtra (opcional)**", unsafe_allow_html=True)
    st.caption("Vacío = se ven todas. Cada filtro sólo ofrece opciones que existen dentro del anterior.")
    regiones = st.multiselect("Región", sorted(df_base[C.COL_REGION].dropna().unique()),
                              placeholder="Todas las regiones",
                              help="Deja sólo las rutas de las regiones que elijas. Puedes elegir varias.")
    df_f = df_base[df_base[C.COL_REGION].isin(regiones)] if regiones else df_base
    territorios = st.multiselect("Territorio", sorted(df_f[C.COL_TERRITORIO].dropna().unique()),
                                 placeholder="Todos los territorios",
                                 help="Deja sólo las rutas de los territorios que elijas. Sólo aparecen los "
                                      "territorios de las regiones elegidas arriba.")
    df_f = df_f[df_f[C.COL_TERRITORIO].isin(territorios)] if territorios else df_f
    cedis = st.multiselect("CeDi", sorted(df_f[C.COL_CEDI].dropna().unique()), placeholder="Todos los CeDis",
                           help="Deja sólo las rutas de los CeDis (centros de distribución) que elijas. Sólo "
                                "aparecen los CeDis de la región y territorio elegidos arriba.")
    df_f = df_f[df_f[C.COL_CEDI].isin(cedis)] if cedis else df_f
    rutas_sel = st.multiselect(
        "Ruta", sorted(df_f[C.COL_RUTA].dropna().unique(), key=lambda r: (len(r), r)),
        placeholder="Todas las rutas (escribe para buscar)",
        help="Escribe el número de la ruta para encontrarla y elígela. Puedes elegir varias. Sólo aparecen las rutas "
             "de la región, territorio y CeDi elegidos arriba.")
    df_f = df_f[df_f[C.COL_RUTA].isin(rutas_sel)] if rutas_sel else df_f
    dias_sel = st.multiselect("Día de visita", list(C.DIAS), default=list(C.DIAS),
                              help="Cada ruta visita zonas distintas según el día. Quita días para ver sólo el "
                                   "área que la ruta cubre esos días. No cambia los cuadrantes, sólo lo que se "
                                   "dibuja. Si lo dejas vacío se ven todos los días.")
    dias = None if len(dias_sel) in (0, len(C.DIAS)) else tuple(C.DIAS[d] for d in dias_sel)
    solo_activas = st.checkbox("Solo rutas activas", value=False,
                               help="Quita las rutas que hoy no están operando (inactivas).")
    if solo_activas:
        df_f = df_f[df_f[C.COL_ESTATUS] == "Activa"]

    cuadrantes_visibles = st.multiselect(
        "Cuadrantes visibles en el mapa", C.ORDEN_CATEGORIAS, default=C.ORDEN_CATEGORIAS,
        format_func=lambda p: p if p == C.SIN_DATOS else f"{p} · {C.CATEGORIAS[p]['nombre']}",
        help="Quita un cuadrante para esconderlo del mapa (por ejemplo, para ver sólo las rutas P1). "
             "Los conteos de la matriz no cambian.",
    )

    st.markdown("<span class='paso'>3</span> **¿Con qué coloreo el mapa?**", unsafe_allow_html=True)
    modo_color = st.radio("Colorear con", ["Cuadrante de la matriz", "Variables continuas"],
                          label_visibility="collapsed",
                          help="Cuadrante: cada zona con el color de su cuadrante (P1 a P4). Variables continuas: "
                               "cada zona con un color más claro u oscuro según el valor de un indicador "
                               "(por ejemplo, clientes por día). Qué significa cada indicador: pestaña "
                               "'Glosario' abajo.")
    variables_sel: list[str] = []
    modo_variables = figura.MODO_CAPAS
    if modo_color == "Variables continuas":
        variables_sel = st.multiselect(
            "Variables (hasta 2)", list(catalogo), default=[next(iter(catalogo))],
            max_selections=figura.MAX_VARIABLES,
            format_func=lambda v: f"{catalogo[v][2]} · {v}",
            help="Elige 1 o 2 indicadores. Color más oscuro = valor más alto. Qué significa cada uno: pestaña "
                 "'Glosario' (abajo de la página). En CeDi/Territorio/Región se usa el valor de la ruta de en medio "
                 "(mediana).")
        if not variables_sel:
            st.warning("Elige al menos un indicador en la lista de arriba para colorear el mapa.")
        modos = ([figura.MODO_BIVARIADO, figura.MODO_LADO] if len(variables_sel) == 2
                 else [figura.MODO_CAPAS, figura.MODO_LADO])
        modo_variables = st.radio(
            "Cómo verlas", modos, disabled=not variables_sel,
            help="Un solo mapa: el indicador en un mapa. Bivariado (con 2 indicadores): los dos en un solo mapa; casi "
                 "negro = los dos altos, azul = sólo el 1º alto, naranja = sólo el 2º alto, gris claro = los dos bajos. "
                 "Mapas lado a lado: un mapa por indicador (y, si quieres, el de cuadrantes); se mueven juntos.")
        con_cuadrantes = st.toggle(
            "Agregar el mapa de cuadrantes (P)", value=True, disabled=modo_variables != figura.MODO_LADO,
            help="Sólo en 'Mapas lado a lado': pone primero un mapa con los cuadrantes P1–P4 para compararlos con los "
                 "indicadores. Apágalo para ver sólo los indicadores.")
        es_bivariado = modo_variables == figura.MODO_BIVARIADO and len(variables_sel) == 2
        paleta_biv = figura.PALETA_BIV_DEFAULT
        paleta = st.radio(
            "Colores", [figura.PALETA_DISTINTA, figura.PALETA_SEMAFORO], disabled=es_bivariado,
            help="Un color por variable: cada indicador con su propio color (azules y naranjas). Semáforo: de "
                 "rojo (bajo) a verde (alto); en modo daltonismo, de azul oscuro (bajo) a amarillo (alto).")
        en_percentiles = st.checkbox(
            "Comparar en percentiles (0–100)", value=False, disabled=es_bivariado,
            help="Pone los indicadores en la misma escala de 0 a 100 (su posición contra las demás rutas). Úsalo "
                 "para comparar dos mapas lado a lado. Al pasar el cursor sigues viendo el valor real.")
    else:
        paleta, en_percentiles, es_bivariado = figura.PALETA_DISTINTA, False, False
        paleta_biv = figura.PALETA_BIV_DEFAULT
        con_cuadrantes = True

    st.markdown("<span class='paso'>4</span> **Cómo se ve el mapa**", unsafe_allow_html=True)
    estilo = st.selectbox("Mapa base", list(figura.ESTILOS_MAPA),
                          help="El fondo del mapa (calles, nombres de ciudades). No cambia los datos.")
    opacidad = st.slider("Opacidad de polígonos", 0.2, 1.0, 0.8, 0.05,
                         help="Qué tan sólido se ve el color de cada zona. Más bajo = se transparenta y ves las "
                              "calles de abajo.")
    etiquetas_on = st.checkbox("Etiquetas con nombre", value=nivel != "Ruta" or modo_daltonismo,
                               help="Escribe sobre el mapa el nombre de cada zona (o el número de ruta). En modo "
                                    "daltonismo también escribe su cuadrante (P1, P2…).")
    contorno_on = st.checkbox("Contorno oscuro de cada ruta", value=True, disabled=nivel != "Ruta",
                              help="Borde oscuro alrededor de toda la huella de la ruta (la suma de sus "
                                   "polígonos por día). Sólo al colorear por Ruta.")
    perfil_on = st.checkbox("Mini gráfica de perfil en el detalle", value=True,
                            help="Al pasar el cursor sobre el mapa, barras con el percentil de los 7 componentes "
                                 "de madurez y los 4 de atractividad frente al resto de lo filtrado.")
    burbujas_on = st.checkbox("Burbujas por grupo (tamaño = # rutas)", value=nivel in ("Territorio", "Región"),
                              disabled=nivel == "Ruta",
                              help="Útil en vista nacional, donde los polígonos se ven pequeños.")
    st.session_state.setdefault("encuadre_ver", 0)
    vista = st.radio("Vista del mapa", ["Vista general", "Centro Arca", "Ajustar a los filtros"],
                     help="Vista general: norte y centro de México con todas las rutas. "
                          "Centro Arca: centroide del territorio (25.804, -103.448) con zoom 12 de folium. "
                          "Ajustar a los filtros: encuadra lo que esté filtrado. El mapa conserva tu zoom y "
                          "posición ante cualquier cambio; usa el botón para ir a esta vista.")
    ajuste_zoom = st.slider("Ajuste de zoom", -6.0, 4.0, 0.0, 0.25,
                            help="Acerca (+) o aleja (−) la vista elegida al pulsar el botón.")
    if st.button("Ir a esta vista", width="stretch",
                 help="Mueve el mapa a la vista y zoom elegidos. Fuera de este botón, el mapa se queda "
                      "donde lo dejes."):
        st.session_state["encuadre_ver"] += 1

    with st.expander("Opciones avanzadas (sólo si sabes lo que haces)"):
        st.caption("Cambiar esto modifica los resultados oficiales. Si tienes dudas, no lo toques.")
        canales = tuple(st.multiselect("Canal de polígonos", ["Convencional", "Web"],
                                       default=["Convencional", "Web"],
                                       help="De qué fuentes se dibujan las zonas de las rutas. Deja las dos: hay rutas "
                                            "que sólo tienen zona del canal Web y si lo quitas desaparecen del mapa.")
                        or ["Convencional", "Web"])
        radio_ws = st.slider("Distancia máxima para buscar zonas sin cobertura (km)", 0.5, 5.0,
                             float(estrategia.RADIO_SIN_COBERTURA_KM), 0.5,
                             help="Para la pregunta del árbol '¿Hay potencial cercano sin cobertura?': qué tan lejos de la "
                                  "zona de la ruta se buscan áreas que ninguna ruta cubre.")
        umbral_x = st.number_input("Umbral Atractividad (eje X)", 0.0, 100.0, float(umbral_x_default), 1.0,
                                   format="%.1f",
                                   help=f"Por defecto la mediana de Atractividad redondeada a 1 decimal "
                                        f"({umbral_x_default:g}), igual que en el Excel.")
        umbral_y = st.number_input("Umbral Madurez (eje Y)", 0.0, 100.0, float(umbral_y_default), 0.5, format="%.1f",
                                   help=f"Por defecto la mediana de Madurez redondeada a 1 decimal "
                                        f"({umbral_y_default:g}), igual que en el Excel. Si cambias algún "
                                        "umbral, el cuadrante de cada ruta se recalcula con él.")

    st.divider()
    if st.button("Restablecer todo", width="stretch",
                 help="Regresa todos los controles a como estaban al abrir la página (quita filtros, "
                      "selecciones y cambios)."):
        st.session_state.clear()
        st.rerun()

# --------------------------------------------------------------------------- cálculo
if df_f.empty:
    st.warning("No hay ninguna ruta con los filtros que elegiste. Quita alguno de los filtros del panel izquierdo "
               "(Región, Territorio, CeDi o 'Solo rutas activas') o pulsa **Restablecer todo**.")
    st.stop()
if not cuadrantes_visibles:
    st.warning("Quitaste todos los cuadrantes de 'Cuadrantes visibles en el mapa': el mapa quedaría vacío. "
               "Vuelve a elegir al menos uno en el panel izquierdo.")
umbrales_default = umbral_x == umbral_x_default and umbral_y == umbral_y_default
if not umbrales_default:
    st.warning(f"Estás usando cortes distintos a los oficiales (Atractividad {umbral_x:g}, Madurez {umbral_y:g}). "
               "Los cuadrantes ya no coinciden con el Excel. Para volver: *Opciones avanzadas* o **Restablecer todo**.")
df_f = datos.aplicar_clasificacion(df_f, umbral_x, umbral_y, usar_p_excel=umbrales_default)
geoms_ruta = geometrias(canales, dias)
# Rutas que sólo tienen zona del canal Web: sus zonas son muy grandes y se dibujan al fondo
rutas_solo_web = (set(geoms_ruta) - set(geometrias(("Convencional",), dias))
                  if "Web" in canales and "Convencional" in canales else set())
df_f["Con polígono"] = df_f[C.COL_RUTA].isin(geoms_ruta.keys())

cols_variables = {v: catalogo[v][0] for v in variables_sel}
nombre_grupo_ = {"Ruta": "rutas", "CeDi": "CeDis", "Territorio": "territorios", "Región": "regiones"}[nivel]
# Componentes para la mini gráfica del detalle
componentes = {v: catalogo[v][0] for v in catalogo if catalogo[v][2] in ("Madurez", "Atractividad")}
REFERENCIAS_PERFIL = {"filtro": "Lo que tengo filtrado", "universo": "Todas las rutas (sin filtros)"}
# Estándar de cada componente de madurez (columna del modelo, según el escenario de carga)
ESTANDAR_DE = dict(zip(modelo.KPIS, modelo.KPIS_EST))
# El control está abajo del título del mapa, pero su valor se necesita antes para armar el detalle
referencia_perfil = st.session_state.get("referencia_perfil", "filtro")


def _posicion(valores: pd.Series, referencia: pd.Series) -> pd.Series:
    """Percentil (0–1) de cada valor dentro de la distribución de `referencia`."""
    ref = np.sort(pd.to_numeric(referencia, errors="coerce").dropna().to_numpy())
    if not len(ref):
        return pd.Series(np.nan, index=valores.index)
    v = pd.to_numeric(valores, errors="coerce")
    pos = np.searchsorted(ref, v.to_numpy(), side="right") / len(ref)
    return pd.Series(np.where(v.isna(), np.nan, pos), index=valores.index)


def texto_perfil(valores: dict[str, pd.Series], referencias: dict[str, pd.Series] | None = None,
                 estandares: dict[str, pd.Series] | None = None) -> pd.Series:
    """Mini gráfica de barras en texto: muestra el valor de cada componente; la barra se llena según su
    percentil frente a lo filtrado (`referencias` = None) o frente a todo el universo. Junto a la barra va el
    estándar del componente (madurez) o el máximo de la referencia (atractividad)."""
    estandares = estandares or {}
    maximos = {v: pd.to_numeric((referencias or valores)[v], errors="coerce").max() for v in valores}
    if referencias is None:
        pcts = {v: s.rank(pct=True) for v, s in valores.items()}
        vs_txt = "lo filtrado"
    else:
        pcts = {v: _posicion(s, referencias[v]) for v, s in valores.items()}
        vs_txt = "todo el universo" if nivel == "Ruta" else f"todos los {nombre_grupo_}"
    indice = next(iter(valores.values())).index
    vacio = C.COLOR_BARRA["vacío"]

    def filas(i):
        partes = ["<br><br><b>Perfil</b> <span style='font-size:10px;color:#777'>(barra = posición vs. "
                  f"{vs_txt})</span>"]
        for grupo in ("Madurez", "Atractividad"):
            color = C.COLOR_BARRA[grupo]
            partes.append(f"<br><span style='font-size:11px;color:{color}'><b>{grupo}</b></span>")
            for v in (x for x in componentes if catalogo[x][2] == grupo):
                p, x = pcts[v].at[i], valores[v].at[i]
                fmt_v = catalogo[v][1]
                est = estandares.get(v)
                est = est.at[i] if est is not None else np.nan
                ref = (f"estándar {datos.formatear(est, fmt_v)}" if pd.notna(est)
                       else f"máx. {datos.formatear(maximos[v], fmt_v)}")
                mono = "font-family:Consolas,monospace"
                if pd.isna(p):
                    partes.append(f"<br><span style='{mono};color:{vacio}'>{'░' * 10}</span>  s/d · {v}")
                    continue
                n = int(round(p * 10))
                partes.append(f"<br><span style='{mono};color:{color}'>{'█' * n}</span>"
                              f"<span style='{mono};color:{vacio}'>{'█' * (10 - n)}</span>  "
                              f"<b>{datos.formatear(x, fmt_v)}</b> · {v} "
                              f"<span style='font-size:10px;color:#5E5E5E'>({ref})</span>")
        return "".join(partes)
    return pd.Series([filas(i) for i in indice], index=indice)


def lineas_variables(valores: list) -> str:
    """Renglones del hover con todas las variables elegidas (para comparar al pasar el cursor)."""
    return "".join(f"<br><b>{v}:</b> {datos.formatear(x, catalogo[v][1])}" for v, x in zip(variables_sel, valores))


def linea_hogares(total, potencial) -> str:
    """Hogares A/B + C+ del caso de potencial: total y los que faltan por capturar."""
    if pd.isna(total) and pd.isna(potencial):
        return "<br><b>Hogares A/B + C+:</b> s/d"
    pct = f" ({potencial / total:.0%})" if pd.notna(total) and pd.notna(potencial) and total else ""
    return (f"<br><b>Hogares A/B + C+:</b> {fmt(total, 0)} en total · "
            f"<b>{fmt(potencial, 0)}</b> potenciales a capturar{pct}")


if nivel == "Ruta":
    df_grupos = None
    info = pd.DataFrame({
        "id": df_f[C.COL_RUTA],
        "P": df_f["P"],
        "hover": [
            f"<b>Ruta {r[C.COL_RUTA]}</b> · {r[C.COL_CEDI]}<br>"
            f"{r[C.COL_TERRITORIO]} · {r[C.COL_REGION]}<br>"
            f"<b>{r['P']}{'' if r['P'] == C.SIN_DATOS else ' · ' + C.CATEGORIAS[r['P']]['nombre']}</b><br>"
            f"Atractividad: {fmt(r[C.COL_X])} · Madurez: {fmt(r[C.COL_Y])}<br>"
            f"{r[C.COL_EJE_ESTADO]} · {r[C.COL_EJE_ZONA]} · {r[C.COL_ESTATUS]}"
            + linea_hogares(r[modelo.COL_HOG_ABC_TOTAL], r[modelo.COL_HOG_ABC_POT])
            + lineas_variables([r[c] for c in cols_variables.values()])
            for _, r in df_f.iterrows()
        ],
        "x": df_f[C.COL_X], "y": df_f[C.COL_Y], "rutas": 1,
        **{f"v{k}": pd.to_numeric(df_f[c], errors="coerce") for k, c in enumerate(cols_variables.values())},
    })
    geoms_mapa = {r: geoms_ruta[r] for r in info["id"] if r in geoms_ruta}
else:
    # Las rutas sólo web (zona muy grande) no se suman a la zona de su grupo, salvo que el grupo no tenga otras
    def _sin_web(rutas):
        normales = tuple(r for r in rutas if r not in rutas_solo_web)
        return normales or tuple(rutas)
    df_grupos = datos.agregar(df_f, col_nivel, umbral_x, umbral_y,
                              variables={**cols_variables, **(componentes if perfil_on else {})})
    rutas_por_grupo = tuple(
        (g, _sin_web(sorted(sub[C.COL_RUTA]))) for g, sub in df_f.groupby(col_nivel, sort=True)
    )
    geoms_mapa = geometrias_grupo(canales, dias, rutas_por_grupo)
    hogares_grupo = df_f.groupby(col_nivel)[[modelo.COL_HOG_ABC_TOTAL, modelo.COL_HOG_ABC_POT]].sum(min_count=1)
    df_grupos = df_grupos.join(hogares_grupo, on=col_nivel)
    info = pd.DataFrame({
        "id": df_grupos[col_nivel],
        "P": df_grupos["P"],
        "hover": [
            f"<b>{nivel}: {r[col_nivel]}</b><br>"
            f"<b>{r['P']}{'' if r['P'] == C.SIN_DATOS else ' · ' + C.CATEGORIAS[r['P']]['nombre']}</b><br>"
            f"Mediana atractividad: {fmt(r['Mediana atractividad'])}<br>"
            f"Mediana madurez: {fmt(r['Mediana madurez'])}<br>"
            f"Rutas: {r['Rutas']} ({r['Rutas con dato']} con dato)<br>"
            f"Mezcla de rutas: P1 {r['Rutas P1']} · P2 {r['Rutas P2']} · "
            f"P3 {r['Rutas P3']} · P4 {r['Rutas P4']} · s/d {r['Rutas Sin datos']}"
            + linea_hogares(r[modelo.COL_HOG_ABC_TOTAL], r[modelo.COL_HOG_ABC_POT]).replace(
                "A/B + C+:</b>", "A/B + C+ (suma de sus rutas):</b>")
            + lineas_variables([r[f"Mediana {v}"] for v in variables_sel])
            for _, r in df_grupos.iterrows()
        ],
        "x": df_grupos["Mediana atractividad"], "y": df_grupos["Mediana madurez"], "rutas": df_grupos["Rutas"],
        **{f"v{k}": df_grupos[f"Mediana {v}"] for k, v in enumerate(variables_sel)},
    })

# Árbol de decisión: cortes sobre la base completa (grupo de referencia escalonado para métricas de ruta),
# reglas sobre la P vigente de cada ruta. Las condiciones no son excluyentes: una ruta puede tener varias.
# Área sin cobertura alrededor de cada ruta (para "¿Hay potencial cercano sin cobertura?")
areas_libres = area_sin_cobertura(canales, radio_ws)
df_base = df_base.assign(**{estrategia.COL_SINCOB: df_base[C.COL_RUTA].map(areas_libres)})
df_f = df_f.assign(**{estrategia.COL_SINCOB: df_f[C.COL_RUTA].map(areas_libres)})
cortes_arbol = estrategia.cortes(df_base, umbral_y)
evaluacion = estrategia.evaluar(df_f, cortes_arbol)
df_f = df_f.assign(**{
    "Estrategias": evaluacion["Estrategias"],
    "Nº de estrategias": evaluacion["Nº de estrategias"],
    "Respuestas del árbol": evaluacion["Claves"].map(lambda cs: " | ".join(
        estrategia.REGLAS_POR_CLAVE[c].condicion for c in cs)),
    "Porque": evaluacion["Porques"].map(" | ".join),
})
if nivel == "Ruta":
    texto_estrategia = pd.Series([
        estrategia.texto_hover_ruta(p, c, pq) for p, c, pq in
        zip(df_f["P"], evaluacion["Claves"], evaluacion["Porques"])], index=info.index)
else:
    por_grupo = {g: estrategia.texto_hover_grupo(evaluacion.loc[sub.index, "Claves"])
                 for g, sub in df_f.groupby(col_nivel)}
    texto_estrategia = info["id"].map(por_grupo).fillna("")

perfil = None
if perfil_on and not info.empty:
    universo = referencia_perfil == "universo"
    if nivel == "Ruta":
        perfil = texto_perfil(
            {v: pd.to_numeric(df_f[c], errors="coerce") for v, c in componentes.items()},
            {v: df_base[c] for v, c in componentes.items()} if universo else None,
            {v: pd.to_numeric(df_f[ESTANDAR_DE[v]], errors="coerce") for v in componentes if v in ESTANDAR_DE})
    else:
        refs = None
        if universo:   # medianas de TODOS los grupos del nivel (sin filtros)
            todos = datos.agregar(datos.aplicar_clasificacion(df_base, umbral_x, umbral_y, usar_p_excel=umbrales_default),
                                  col_nivel, umbral_x, umbral_y, variables=componentes)
            refs = {v: todos[f"Mediana {v}"] for v in componentes}
        # estándar del grupo = mediana de los estándares de sus rutas
        est_grupo = df_f.groupby(col_nivel)[[ESTANDAR_DE[v] for v in componentes if v in ESTANDAR_DE]].median()
        perfil = texto_perfil({v: df_grupos[f"Mediana {v}"] for v in componentes}, refs,
                              {v: df_grupos[col_nivel].map(est_grupo[ESTANDAR_DE[v]])
                               for v in componentes if v in ESTANDAR_DE})

resumen = datos.resumen_matriz(df_f, df_grupos)
nombre_grupo = {"Ruta": "rutas", "CeDi": "CeDis", "Territorio": "territorios", "Región": "regiones"}[nivel]


def etiqueta_leyenda(p: str) -> str:
    r = resumen[p]
    base = p if p == C.SIN_DATOS else f"{p} · {C.CATEGORIAS[p]['nombre']}"
    conteo = f"{r['rutas']} rutas" if r["grupos"] is None else f"{r['grupos']} {nombre_grupo} · {r['rutas']} rutas"
    return f"{base}  —  {conteo} ({r['pct']:.1%})"


leyenda = {p: etiqueta_leyenda(p) for p in C.ORDEN_CATEGORIAS}
info_visible = info[info["P"].isin(cuadrantes_visibles)]

# Bivariado: terciles sobre todo lo visible (antes de la selección, para que los colores y la
# cuadrícula de la dispersión no cambien al seleccionar)
bivariado_cfg = None
if es_bivariado:
    clase, color_biv, cortes_biv = figura.clasificar_bivariado(info_visible["v0"], info_visible["v1"], paleta_biv)
    texto_biv = clase.map(lambda c: "" if not isinstance(c, str) else
                          f"<br><b>Bivariado:</b> {variables_sel[0]} {figura.NIVELES_BIV[int(c[0])].lower()} · "
                          f"{variables_sel[1]} {figura.NIVELES_BIV[int(c[1])].lower()}")
    info_visible = info_visible.assign(biv=clase, biv_color=color_biv, hover=info_visible["hover"] + texto_biv)
    bivariado_cfg = {"colores": figura.PALETAS_BIVARIADAS[paleta_biv], "titulos": tuple(variables_sel),
                     "cortes": cortes_biv, "formatos": (catalogo[variables_sel[0]][1], catalogo[variables_sel[1]][1])}

# --- Selección desde la dispersión.
# La lista `sel_{nivel}` es la fuente de verdad: se llena al seleccionar en la gráfica y se edita con
# los controles de abajo (quitar elementos, quitar un cuadrante, limpiar). Para borrar el recuadro de
# selección de la gráfica se cambia su clave (`sel_ver_{nivel}`), lo que la vuelve a dibujar limpia.
k_sel, k_ver, k_firma = f"sel_{nivel}", f"sel_ver_{nivel}", f"sel_firma_{nivel}"
st.session_state.setdefault(k_sel, [])
st.session_state.setdefault(k_ver, 0)
st.session_state.setdefault(k_firma, ())
clave_disp = f"dispersion_{nivel}_{st.session_state[k_ver]}"
if es_bivariado:     # la dispersión muestra las 2 variables: entra todo lo que tenga ambas
    puntos_disp = info_visible[info_visible["v0"].notna() & info_visible["v1"].notna()]
else:
    puntos_disp = info_visible[info_visible["P"] != C.SIN_DATOS]
p_por_id = dict(zip(puntos_disp["id"], puntos_disp["P"]))

evento = st.session_state.get(clave_disp)
ids_evento = []
if evento and evento.get("selection"):
    for pt in evento["selection"].get("points", []):
        cd = pt.get("customdata")
        ids_evento.append(cd[0] if isinstance(cd, (list, tuple)) else cd)
if tuple(ids_evento) != st.session_state[k_firma]:        # selección nueva en la gráfica
    st.session_state[k_firma] = tuple(ids_evento)
    st.session_state[k_sel] = list(dict.fromkeys(ids_evento))
# Sólo elementos que siguen visibles con los filtros actuales
st.session_state[k_sel] = [i for i in st.session_state[k_sel] if i in p_por_id]
seleccion = list(st.session_state[k_sel])
if seleccion:
    info_visible = info_visible[info_visible["id"].isin(seleccion)]


def _reiniciar_grafica():
    st.session_state[k_ver] += 1
    st.session_state[k_firma] = ()


def limpiar_seleccion():
    st.session_state[k_sel] = []
    _reiniciar_grafica()


def quitar_cuadrante(p: str):
    st.session_state[k_sel] = [i for i in st.session_state[k_sel] if p_por_id.get(i) != p]
    _reiniciar_grafica()


def _rango(serie: pd.Series) -> tuple[float, float]:
    vals = serie.dropna()
    rango = (float(vals.quantile(0.05)), float(vals.quantile(0.95))) if len(vals) > 1 else (0.0, 1.0)
    return (rango[0] - 1, rango[1] + 1) if rango[0] == rango[1] else rango


if en_percentiles and variables_sel:
    # Percentil de cada elemento entre los visibles: misma escala 0–100 para todas las variables
    info_visible = info_visible.assign(**{f"v{k}": info_visible[f"v{k}"].rank(pct=True) * 100
                                          for k in range(len(variables_sel))})
variables_mapa = [
    {"titulo": f"{v} · percentil" if en_percentiles else v, "col": f"v{k}",
     "rango": (0.0, 100.0) if en_percentiles else _rango(info_visible[f"v{k}"]),
     "formato": ".0f" if en_percentiles else catalogo[v][1]}
    for k, v in enumerate(variables_sel)]
# Estrategia y mini gráfica sólo en el mapa (no en la dispersión) para no hacer pesada la página
info_visible = info_visible.assign(hover=info_visible["hover"] + texto_estrategia.loc[info_visible.index])
if perfil is not None:
    info_visible = info_visible.assign(hover=info_visible["hover"] + perfil.loc[info_visible.index])
geoms_visibles = [geoms_mapa[i] for i in info_visible["id"] if i in geoms_mapa]
contornos_mapa = None
if nivel == "Ruta" and contorno_on:
    todos_contornos = contornos_ruta(canales, dias)
    contornos_mapa = {i: todos_contornos[i] for i in info_visible["id"]
                      if i in todos_contornos and i not in rutas_solo_web}

puntos = pd.DataFrame(
    [(i, g.representative_point()) for i, g in ((i, geoms_mapa.get(i)) for i in info_visible["id"]) if g is not None],
    columns=["id", "pt"],
)
puntos["lat"] = [p.y for p in puntos["pt"]]
puntos["lon"] = [p.x for p in puntos["pt"]]
etiquetas = None
if etiquetas_on and not puntos.empty:
    # En modo daltonismo la etiqueta también dice el cuadrante, para no depender sólo del color
    p_de = dict(zip(info_visible["id"], info_visible["P"]))
    etiquetas = puntos.assign(texto=[
        f"{p_de.get(i, '')} · {i}" if modo_daltonismo and p_de.get(i) in C.CATEGORIAS and p_de.get(i) != C.SIN_DATOS
        else i for i in puntos["id"]])
burbujas = None
if burbujas_on and df_grupos is not None and not puntos.empty:
    burbujas = puntos.merge(info_visible, on="id")

filtros_txt = " · ".join(filter(None, [
    f"Carga OP: {escenario} · Potencial: {nombre_caso(caso)}",
    ", ".join(regiones), ", ".join(territorios), ", ".join(cedis), (f"Rutas: {', '.join(rutas_sel)}" if rutas_sel else ""),
    "Solo activas" if solo_activas else "",
    f"Días: {', '.join(dias_sel)}" if dias else "",
    f"{len(seleccion)} {nombre_grupo} seleccionados" if seleccion else "",
])) or "Todas las regiones"

# --------------------------------------------------------------------------- UI principal


def celda(p: str) -> str:
    cat, r = C.CATEGORIAS[p], resumen[p]
    linea = f"{r['rutas']} rutas" if r["grupos"] is None else f"{r['grupos']} {nombre_grupo} – {r['rutas']} rutas"
    return (f"<div class='mz-cell' style='background:{cat['color']}'>"
            f"<div class='mz-t'>{cat['nombre']}</div><div class='mz-p'>{C.SIMBOLOS_TEXTO[p]} {p}</div>"
            f"<div class='mz-n'>{linea}</div><div class='mz-n'>{r['pct']:.1%}</div></div>")


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Raleway:ital,wght@0,400;0,700;1,400&display=swap');
.mz-wrap{display:flex;gap:10px;align-items:stretch;font-family:Raleway,Arial,sans-serif;max-width:620px}
.mz-y{writing-mode:vertical-rl;transform:rotate(180deg);font-weight:700;text-align:center;
      border-left:3px solid #F30000;padding-left:4px}
.mz-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;flex:1}
.mz-cell{padding:14px 10px;text-align:center;color:#111;border-radius:2px}
.mz-t{font-weight:700;font-size:1.25rem}.mz-p{font-style:italic;font-size:.8rem}
.mz-n{font-style:italic;font-size:1rem;margin-top:4px}
.mz-x{max-width:620px;text-align:center;font-weight:700;font-family:Raleway,Arial,sans-serif;
      border-top:3px solid #F30000;margin:4px 0 0 28px;padding-top:2px}
</style>""", unsafe_allow_html=True)

col_mz, col_disp = st.columns([1, 1])
with col_mz:
    encabezado(
        "Matriz de cuadrantes",
        f"Cuántas {'rutas' if nivel == 'Ruta' else nombre_grupo} caen en cada uno de los 4 cuadrantes, con lo "
        "que tienes filtrado.",
        "Arriba = rutas que operan bien (madurez alta); derecha = zonas con mucho potencial (atractividad alta). "
        "P1 Ampliar cobertura: opera bien y la zona tiene potencial, hay que crecer. P2 Mantener: opera bien pero "
        "la zona da poco más, hay que cuidarla. P3 Desarrollar: la zona tiene potencial pero la ruta opera mal, hay "
        "que mejorarla. P4 Evaluar: opera mal y la zona da poco, hay que decidir qué hacer. Las líneas que dividen "
        "la matriz son la mediana: la mitad de las rutas queda de cada lado.")
    st.markdown(
        f"<div class='mz-wrap'><div class='mz-y'>Madurez</div><div class='mz-grid'>"
        f"{celda('P2')}{celda('P1')}{celda('P4')}{celda('P3')}</div></div>"
        f"<div class='mz-x'>Atractividad</div>",
        unsafe_allow_html=True,
    )
    sd = resumen[C.SIN_DATOS]
    k1, k2, k3 = st.columns(3)
    k1.metric("Rutas en el análisis", f"{len(df_f):,}", help="Rutas que cumplen los filtros del panel izquierdo.")
    k2.metric("Rutas con polígono", f"{int(df_f['Con polígono'].sum()):,}",
              help="Rutas que se pueden dibujar en el mapa. Las demás cuentan en la matriz pero no tienen zona "
                   "dibujada (lista en la pestaña 'Rutas sin polígono').")
    k3.metric("Rutas sin datos", f"{sd['rutas']:,}",
              help="Rutas que no se pueden ubicar en la matriz porque les falta información (por ejemplo, están "
                   "inactivas o no tienen datos de capacidad o de zona)."
                   + ("" if sd["grupos"] is None else f" {sd['grupos']} {nombre_grupo} no tienen ninguna ruta con datos."))
    st.caption(("Rutas: cuadrante calculado por el modelo. " if umbrales_default else
                "Rutas: recalculadas con los cortes de Opciones avanzadas. ")
               + f"Cortes: Atractividad ≥ {umbral_x:g} · Madurez ≥ {umbral_y:g}"
               + (" (medianas redondeadas). " if umbrales_default else ". ")
               + ("" if nivel == "Ruta" else f"Cada {nivel.lower()} se clasifica por la mediana de sus rutas "
                                             "y todas sus rutas cuentan en ese cuadrante."))
with col_disp:
    if es_bivariado:
        encabezado(
            "Gráfica de los 2 indicadores",
            f"Cada punto es una {'ruta' if nivel == 'Ruta' else nivel.lower()}: a la derecha = {variables_sel[0]} "
            f"más alto; arriba = {variables_sel[1]} más alto. Puedes seleccionar puntos para verlos en el mapa.",
            "Las líneas parten cada indicador en 3 grupos iguales (bajo, medio, alto). Cada casilla tiene el color "
            "que se usa en el mapa y el número de elementos que caen en ella. Para seleccionar: haz clic en un "
            "punto, o arrastra un rectángulo o un lazo (iconos arriba de la gráfica). Con Shift agregas más.")
    else:
        encabezado(
            "Gráfica de la matriz",
            f"Cada punto es una {'ruta' if nivel == 'Ruta' else nivel.lower()}: a la derecha = zona con más "
            "potencial; arriba = opera mejor. Puedes seleccionar puntos para verlos en el mapa.",
            "Es la misma matriz de la izquierda, pero con cada elemento en su lugar exacto. La forma del punto dice "
            "su cuadrante: círculo P1, cuadrado P2, rombo P3, triángulo P4. Las líneas punteadas son los cortes "
            "(mediana). Para seleccionar: clic en un punto, o arrastra un rectángulo o un lazo (iconos arriba de la "
            "gráfica). Con Shift agregas más. En CeDi/Territorio/Región, los puntos más grandes tienen más rutas.")
    if es_bivariado:
        fig_disp = figura.construir_dispersion_bivariada(
            puntos_disp, bivariado_cfg, tamano_por_rutas=nivel != "Ruta", seleccion=set(seleccion),
            uirevision=f"biv|{variables_sel}")
    else:
        fig_disp = figura.construir_dispersion(puntos_disp, umbral_x, umbral_y, tamano_por_rutas=nivel != "Ruta",
                                               seleccion=set(seleccion), uirevision="matriz")
    st.plotly_chart(fig_disp, width="stretch", key=clave_disp, on_select="rerun",
                    selection_mode=("points", "box", "lasso"),
                    config={"displaylogo": False, "modeBarButtonsToRemove": ["toImage"]})
    if es_bivariado:
        st.caption(f"Dispersión bivariada: celdas = terciles, número = {nombre_grupo} en cada celda "
                   f"({figura.DESCRIPCION_BIV[paleta_biv]}).")
    if not seleccion:
        st.caption("Selecciona puntos (clic, rectángulo o lazo; con **Shift** agregas más) para mostrar sólo "
                   "esos en el mapa.")
    else:
        conteo_p = pd.Series([p_por_id[i] for i in seleccion]).value_counts()
        b0, *bs = st.columns(1 + len(conteo_p))
        b0.button("Limpiar selección", on_click=limpiar_seleccion, width="stretch", type="primary",
                  help="Quita la selección y vuelve a mostrar todo en el mapa.")
        for b, p in zip(bs, [p for p in C.ORDEN_CATEGORIAS if p in conteo_p]):
            b.button(f"Quitar {p} ({conteo_p[p]})", on_click=quitar_cuadrante, args=(p,), width="stretch",
                     help=f"Quita de la selección los elementos {p} · {C.CATEGORIAS[p]['nombre']}")
        with st.expander(f"Seleccionados: {len(seleccion)} {nombre_grupo} (quita uno con ✕)", expanded=False):
            st.multiselect("Elementos seleccionados", options=list(p_por_id), key=k_sel,
                           format_func=lambda i: f"{i} · {p_por_id.get(i, '')}",
                           on_change=_reiniciar_grafica, label_visibility="collapsed")

if seleccion:
    st.info(f"El mapa sólo muestra los {len(seleccion)} {nombre_grupo} que seleccionaste en la gráfica. "
            "Para ver todo otra vez, pulsa **Limpiar selección**.")

# Streamlit vuelve a crear el mapa en cada cambio, así que `uirevision` no basta para conservar la vista.
# Este script (en el navegador) guarda centro/zoom cada vez que el usuario mueve el mapa y los vuelve a
# aplicar al mapa nuevo, mientras la revisión (que sólo cambia con "Ir a esta vista") sea la misma.
_JS_VISTA = """
<script>
(function () {
  const P = window.parent;
  // Mapa principal ("mapa|…", en lado a lado sus mapas se mueven juntos) y comparación ("comp|…")
  const TIPOS = {"mapa|": {clave: "vista_mapa_rutas", sincronizar: true},
                 "comp|": {clave: "vista_mapa_comparacion", sincronizar: true}};
  const leer = k => { try { return JSON.parse(P.sessionStorage.getItem(k)) || null; } catch (e) { return null; } };
  const guardar = (k, v) => { try { P.sessionStorage.setItem(k, JSON.stringify(v)); } catch (e) {} };
  const vistaDe = m => { const c = m.getCenter();
    return {lon: c.lng, lat: c.lat, zoom: m.getZoom(), bearing: m.getBearing(), pitch: m.getPitch()}; };
  const aplicar = (m, x, original) => m.jumpTo({center: [x.lon, x.lat], zoom: x.zoom, bearing: x.bearing || 0,
                                               pitch: x.pitch || 0}, original ? {originalEvent: true} : {});
  // El cuadro de detalle se coloca a un lado del polígono (derecha, o izquierda si no cabe) para no taparlo
  function cajaPoligono(gd, pt) {
    if (!pt || !pt.data || pt.data.type !== "choroplethmap") return null;
    const sp = gd._fullLayout[pt.data.subplot || "map"]; const m = sp && sp._subplot && sp._subplot.map;
    const feats = (pt.data.geojson && pt.data.geojson.features) || [];
    const f = feats.find(x => String(x.id) === String(pt.location));
    if (!m || !f) return null;
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    const recorrer = c => { if (typeof c[0] === "number") { const q = m.project(c);
      x0 = Math.min(x0, q.x); x1 = Math.max(x1, q.x); y0 = Math.min(y0, q.y); y1 = Math.max(y1, q.y); }
      else c.forEach(recorrer); };
    recorrer(f.geometry.coordinates);
    const cv = m.getCanvas().getBoundingClientRect();
    return {l: cv.left + x0, r: cv.left + x1, t: cv.top + y0, b: cv.top + y1, lienzo: cv};
  }
  function acomodarDetalle(gd) {
    const hl = gd.querySelector(".hoverlayer .hovertext"); const caja = gd.__cajaHover;
    if (!hl || !caja) return;
    const r = hl.getBoundingClientRect(), g = caja.lienzo;   // límites: el mapa donde está el polígono
    let izq = caja.r + 14;
    if (izq + r.width > g.right - 4) izq = caja.l - 14 - r.width;               // no cabe a la derecha
    if (izq < g.left + 4) izq = Math.min(Math.max(g.left + 4, caja.r + 14), g.right - r.width - 4);
    const arriba = Math.min(Math.max(caja.t, g.top + 4), g.bottom - r.height - 4);
    const t = /translate\\(([-\\d.e]+)[ ,]+([-\\d.e]+)\\)/.exec(hl.getAttribute("transform") || "");
    if (!t) return;
    hl.setAttribute("transform", `translate(${+t[1] + izq - r.left},${+t[2] + arriba - r.top})`);
  }
  function hoverAlLado(gd) {
    gd.on("plotly_hover", ev => { gd.__cajaHover = cajaPoligono(gd, ev.points && ev.points[0]);
      requestAnimationFrame(() => acomodarDetalle(gd)); });
    gd.on("plotly_unhover", () => { gd.__cajaHover = null; });
    // Plotly vuelve a dibujar el cuadro al mover el mouse dentro del mismo polígono: se vuelve a acomodar
    const capa = gd.querySelector(".hoverlayer");
    if (capa) new MutationObserver(() => acomodarDetalle(gd)).observe(capa, {childList: true});
  }
  function revisar() {
    for (const gd of P.document.querySelectorAll(".js-plotly-plot")) {
      const fl = gd._fullLayout; if (!fl) continue;
      const rev = String((gd.layout || {}).uirevision || "");
      const pref = Object.keys(TIPOS).find(t => rev.startsWith(t)); if (!pref) continue;
      const tipo = TIPOS[pref];
      if (!gd.__hoverLado && gd.on) { gd.__hoverLado = true; hoverAlLado(gd); }
      const mapas = Object.keys(fl).filter(k => /^map\\d*$/.test(k))
        .map(n => [n, fl[n]._subplot && fl[n]._subplot.map]).filter(([, m]) => m);
      for (const [nombre, m] of mapas) {
        if (m.__vistaLista) continue;
        m.__vistaLista = true;
        const v = leer(tipo.clave);
        const guardada = v && v.rev === rev && v.vistas &&
          (v.vistas[nombre] || (tipo.sincronizar ? Object.values(v.vistas)[0] : null));
        if (guardada) {
          gd.__sincronizando = true;
          // originalEvent hace que Plotly registre la vista en su layout (como si la moviera el usuario)
          aplicar(m, guardada, true);
          gd.__sincronizando = false;
        }
        if (tipo.sincronizar) {
          m.on("move", e => {
            if (!e.originalEvent || gd.__sincronizando) return;
            gd.__sincronizando = true;
            const x = vistaDe(m);
            for (const [n2, m2] of mapas) if (m2 !== m) aplicar(m2, x, false);
            gd.__sincronizando = false;
          });
        }
        m.on("moveend", e => {
          if (!e.originalEvent || gd.__sincronizando) return;
          const act = leer(tipo.clave);
          const vistas = act && act.rev === rev ? act.vistas : {};
          const x = vistaDe(m);
          if (tipo.sincronizar) { for (const [n2] of mapas) vistas[n2] = x; } else { vistas[nombre] = x; }
          guardar(tipo.clave, {rev: rev, vistas: vistas});
        });
      }
    }
  }
  setInterval(revisar, 150);
})();
</script>
"""


def recordar_vista_mapa() -> None:
    st.iframe(_JS_VISTA, height=1)


# Diagrama de flujo con zoom (rueda del mouse / botones) y paneo (arrastrar). El SVG lo arma
# estrategia.diagrama_svg; el zoom se hace moviendo el viewBox del SVG, así el texto sigue nítido.
_HTML_ARBOL = """
<link href="https://fonts.googleapis.com/css2?family=Raleway:wght@400;700&display=swap" rel="stylesheet">
<div id="barra" style="font:13px Raleway,Arial,sans-serif;display:flex;gap:6px;align-items:center;margin-bottom:6px">
  <button data-z="1.25">+ Acercar</button><button data-z="0.8">− Alejar</button>
  <button id="ajustar">Ver completo</button><button id="svg">Descargar diagrama (SVG)</button>
  <span style="color:#777">Rueda del mouse = zoom · arrastrar = mover</span>
</div>
<div id="lienzo" style="width:100%;height:__ALTO__px;border:1px solid #ddd;border-radius:6px;overflow:hidden;
     cursor:grab;background:#fff"></div>
<style>button{border:1px solid #ccc;background:#f7f7f7;border-radius:6px;padding:3px 10px;cursor:pointer;font-family:Raleway,Arial,sans-serif}
button:hover{background:#fff;border-color:#F30000;color:#F30000}</style>

<script>
const SVG = __SVG__;
const lienzo = document.getElementById("lienzo");
(() => {
  lienzo.innerHTML = SVG;
  const svg = lienzo.querySelector("svg");
  const vb0 = svg.viewBox.baseVal; const base = {x: vb0.x, y: vb0.y, w: vb0.width, h: vb0.height};
  svg.removeAttribute("width"); svg.removeAttribute("height");
  svg.style.width = "100%"; svg.style.height = "100%";
  svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
  lienzo.appendChild(svg);
  let vb = {...base};
  const poner = () => svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
  const zoom = (f, cx, cy) => {           // cx, cy en fracción del lienzo
    const w = vb.w / f, h = vb.h / f;
    if (w > base.w * 4 || w < base.w / 40) return;
    vb = {x: vb.x + (vb.w - w) * cx, y: vb.y + (vb.h - h) * cy, w, h}; poner();
  };
  lienzo.addEventListener("wheel", e => {
    e.preventDefault(); const r = lienzo.getBoundingClientRect();
    zoom(e.deltaY < 0 ? 1.15 : 1 / 1.15, (e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height);
  }, {passive: false});
  let arr = null;
  lienzo.addEventListener("mousedown", e => { arr = {x: e.clientX, y: e.clientY, vb: {...vb}}; lienzo.style.cursor = "grabbing"; });
  window.addEventListener("mouseup", () => { arr = null; lienzo.style.cursor = "grab"; });
  window.addEventListener("mousemove", e => {
    if (!arr) return; const r = lienzo.getBoundingClientRect();
    const esc = Math.max(vb.w / r.width, vb.h / r.height);
    vb = {...arr.vb, x: arr.vb.x - (e.clientX - arr.x) * esc, y: arr.vb.y - (e.clientY - arr.y) * esc}; poner();
  });
  document.querySelectorAll("[data-z]").forEach(b => b.onclick = () => zoom(+b.dataset.z, 0.5, 0.5));
  document.getElementById("ajustar").onclick = () => { vb = {...base}; poner(); };
  document.getElementById("svg").onclick = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(svg)], {type: "image/svg+xml"}));
    a.download = "arbol_de_decision.svg"; a.click();
  };
})();
</script>
"""


def diagrama_con_zoom(svg: str, alto: int) -> None:
    import json
    html = _HTML_ARBOL.replace("__ALTO__", str(alto)).replace("__SVG__", json.dumps(svg))
    st.iframe(html, height=alto + 50)


def encuadre_mapa(ancho_px: int = 1100, alto_px: int = 750) -> tuple[dict, float]:
    if vista == "Vista general":
        return C.CENTRO_GENERAL, C.ZOOM_GENERAL
    if vista == "Centro Arca":
        return C.CENTRO_ARCA, C.ZOOM_ARCA
    return datos.encuadre(geoms_visibles, ancho_px, alto_px)


centro, zoom = encuadre_mapa()
if variables_sel:
    que_es_mapa = (f"Cada zona pintada según {' y '.join(variables_sel)}"
                   + (" (ver la leyenda en rombo arriba a la izquierda)." if es_bivariado else
                      ": más oscuro = valor más alto."))
else:
    que_es_mapa = ("Cada zona pintada con el color de su cuadrante (ver la leyenda abajo a la izquierda). "
                   "Pasa el cursor sobre una zona para ver su detalle y qué hacer con ella.")
encabezado(
    "Mapa", que_es_mapa,
    "Cómo moverte: rueda del mouse = acercar/alejar; arrastrar = moverte. El mapa se queda donde lo dejes aunque "
    "cambies filtros; para ir a otro lugar usa 'Ir a esta vista' en el panel izquierdo. Pasa el cursor sobre una zona "
    "para ver: su cuadrante, sus datos, sus hogares A/B + C+ y las estrategias recomendadas. Haz clic en un nombre "
    "de la leyenda para esconderlo o mostrarlo. La línea oscura rodea toda la zona de cada ruta (todos sus días). "
    "El ícono de cámara (arriba a la derecha del mapa) descarga la imagen de lo que estás viendo.")
st.radio(
    "Barras del detalle: comparar contra", list(REFERENCIAS_PERFIL), format_func=REFERENCIAS_PERFIL.get,
    horizontal=True, key="referencia_perfil", disabled=not perfil_on,
    help="Sólo cambia qué tan llenas se ven las barras del detalle al pasar el cursor sobre el mapa. NO cambia los "
         "filtros, el mapa ni los números. Lo que tengo filtrado: la barra compara contra lo filtrado en el panel "
         "izquierdo. Todas las rutas: compara contra todas las rutas (o todos los grupos), sin importar los filtros.")
titulo_mapa = (f"Atractividad × Madurez por {nivel}" if not variables_sel
               else f"{' · '.join(variables_sel)} por {nivel}")
# El mapa conserva el zoom/paneo del usuario ante cualquier cambio; sólo el botón "Ir a esta vista"
# cambia la revisión y aplica la vista elegida.
revision_mapa = f"mapa|{st.session_state['encuadre_ver']}"
fig = figura.construir_mapa(
    geoms_mapa, info_visible, leyenda,
    titulo=titulo_mapa, subtitulo=filtros_txt,
    centro=centro, zoom=zoom + ajuste_zoom, opacidad=opacidad,
    grosor_borde=0.4 if nivel == "Ruta" else 1.2,
    estilo=figura.ESTILOS_MAPA[estilo], etiquetas=etiquetas, burbujas=burbujas,
    variables=variables_mapa, modo_variables=modo_variables, paleta=paleta, con_cuadrantes=con_cuadrantes,
    bivariado_cfg=bivariado_cfg, contornos=contornos_mapa, alto=760, uirevision=revision_mapa,
    fondo=rutas_solo_web if nivel == "Ruta" else None,
)
st.plotly_chart(fig, width="stretch", key="mapa_principal", config={
    "scrollZoom": True, "displaylogo": False,
    "toImageButtonOptions": {"format": "jpeg", "filename": "mapa_rutas_vista", "scale": 2},
})
recordar_vista_mapa()
st.caption("Para guardar una imagen: el ícono de cámara del mapa descarga **exactamente lo que ves**. Abajo "
           "puedes hacer una versión grande con título, para presentaciones.")

# --------------------------------------------------------------------------- exportación
with st.expander("Descargar el mapa como imagen para presentación (JPG)", expanded=False):
    st.caption("1) Escribe el título, 2) elige el tamaño, 3) pulsa **Generar imagen**, 4) pulsa **Descargar**. "
               "La imagen muestra todo lo filtrado, con la vista elegida en el panel izquierdo.")
    c1, c2, c3 = st.columns([3, 2, 1])
    titulo_exp = c1.text_input("Título", titulo_mapa)
    subtitulo_exp = c1.text_input("Subtítulo", f"{filtros_txt} · {date.today():%d/%m/%Y}")
    tamanos = {"Presentación 16:9 (1920×1080)": (1920, 1080), "Presentación 4:3 (1600×1200)": (1600, 1200),
               "Cuadrado (1400×1400)": (1400, 1400), "Vertical (1200×1600)": (1200, 1600)}
    tam = c2.selectbox("Tamaño", list(tamanos), help="16:9 es el tamaño normal de una lámina de PowerPoint.")
    escala = c2.select_slider("Resolución", [1.0, 1.5, 2.0, 3.0], value=2.0, format_func=lambda s: f"×{s:g}",
                              help="Más alto = imagen más nítida pero más pesada y tarda más.")
    ancho, alto = tamanos[tam]
    firma = (titulo_exp, subtitulo_exp, tam, escala, estilo, opacidad, vista, ajuste_zoom, nivel,
             tuple(info_visible["id"]), tuple(info_visible["P"]), etiquetas_on, burbujas_on, contorno_on, canales,
             dias, tuple(variables_sel), modo_variables, paleta, paleta_biv, en_percentiles, escenario, caso)

    if c3.button("Generar imagen", type="primary"):
        centro_e, zoom_e = encuadre_mapa(ancho, alto - 90)
        fig_e = figura.construir_mapa(
            geoms_mapa, info_visible, leyenda,
            titulo=titulo_exp, subtitulo=subtitulo_exp,
            centro=centro_e, zoom=zoom_e + ajuste_zoom, opacidad=opacidad,
            grosor_borde=0.5 if nivel == "Ruta" else 1.4,
            estilo=figura.ESTILOS_MAPA[estilo], etiquetas=etiquetas, burbujas=burbujas,
            variables=variables_mapa, modo_variables=modo_variables, paleta=paleta, con_cuadrantes=con_cuadrantes,
            bivariado_cfg=bivariado_cfg, contornos=contornos_mapa, alto=alto, ancho=ancho,
            fondo=rutas_solo_web if nivel == "Ruta" else None,
        )
        with st.spinner("Renderizando imagen (tarda ~20 s)…"):
            try:
                st.session_state["jpg"] = (firma, figura.exportar_jpg(fig_e, ancho, alto, escala))
            except Exception as e:  # kaleido necesita Chrome/Edge y acceso a los tiles del mapa base
                st.session_state.pop("jpg", None)
                st.error(f"No se pudo generar la imagen: {e}. Usa el ícono de cámara del mapa como alternativa.")

    if st.session_state.get("jpg") and st.session_state["jpg"][0] == firma:
        jpg = st.session_state["jpg"][1]
        st.image(jpg, caption="Vista previa")
        st.download_button("Descargar imagen", jpg, file_name=f"mapa_{nivel.lower()}_{date.today():%Y%m%d}.jpg",
                           mime="image/jpeg")
    elif st.session_state.get("jpg"):
        st.info("Cambiaste algo en la página: pulsa **Generar imagen** otra vez para que la imagen quede igual.")

# --------------------------------------------------------------------------- tablas
st.markdown("#### Más detalle", help="Cada pestaña muestra otra forma de ver los mismos datos. Haz clic en el "
            "nombre de una pestaña para abrirla.")
tab_arbol, tab_nivel, tab_comp, tab_glosario, tab_modelo, tab_sin_geo = st.tabs(
    ["Árbol de decisión", f"Tabla por {nivel}", "Comparar escenarios", "Glosario: qué significa cada cosa",
     "Modelo completo", "Rutas sin polígono"])

with tab_arbol:
    conteo_arbol = {r.clave: int(evaluacion[r.clave].sum()) for r in estrategia.REGLAS}
    rutas_p = df_f["P"].value_counts().to_dict()
    encabezado(
        "Árbol de decisión: qué hacer con cada ruta",
        "Diagrama de preguntas que decide la estrategia de cada ruta según su cuadrante. Los números son rutas del "
        "filtro actual.",
        "Cómo leerlo: empieza arriba en 'Rutas Arca' y sigue las flechas. Cada rombo es una pregunta. Si su respuesta "
        "(Sí o No) tiene una caja de color, la ruta recibe esa estrategia; después sigue a la siguiente pregunta, así "
        "que puede recibir varias. Las rutas sin cuadrante (a la derecha) reciben una sola acción. El diagrama está "
        "en el desplegable 'Ver el diagrama'; usa la rueda del mouse para acercar y arrastra para moverte.")
    n_est = evaluacion.loc[df_f["P"].isin(estrategia.CUADRANTES), "Nº de estrategias"].value_counts().sort_index()
    cols_n = st.columns(max(len(n_est), 1))
    for col_m, (n, rutas) in zip(cols_n, n_est.items()):
        col_m.metric(f"Rutas con {n} estrategia{'s' if n > 1 else ''}", f"{rutas:,}",
                     help="Cuántas rutas (con cuadrante) reciben este número de estrategias al mismo tiempo.")
    exp_diagrama = st.expander("Ver el diagrama del árbol de decisión", expanded=False)
    ver = exp_diagrama.radio("Ver en el diagrama", ["Todo", "P1", "P2", "P3", "P4", "Sin cuadrante"], horizontal=True,
                   format_func=lambda x: x if x in ("Todo", "Sin cuadrante") else f"{x} · {C.CATEGORIAS[x]['nombre']}",
                   help="Muestra el árbol completo o sólo la parte de un cuadrante (más fácil de leer y presentar).")
    alto_arbol = exp_diagrama.select_slider("Alto del diagrama", [500, 650, 800, 1000, 1300], value=800,
                                  format_func=lambda h: f"{h} px", help="Hazlo más alto si se ve muy apretado.")
    with exp_diagrama:
        diagrama_con_zoom(estrategia.diagrama_svg(conteo_arbol, ver, rutas_p), alto_arbol)
        st.caption("Rombo = pregunta. Caja de color = estrategia (con cuántas rutas la reciben). Con Sí o con No la "
                   "ruta sigue a la siguiente pregunta, así que puede recibir varias estrategias.")

    # --- Tabla del árbol: cómo se contesta cada pregunta
    encabezado(
        "Tabla del árbol: cómo se contesta cada pregunta",
        "Cada estrategia del diagrama, con la pregunta que la dispara y los datos con los que se contesta.",
        "Paso: número de la pregunta en su cuadrante. Respuesta: con qué respuesta se recibe la estrategia. Cómo se "
        "contesta: qué datos de la ruta se comparan y contra qué (p75 = el valor que deja al 75% de las rutas abajo; "
        "p25 = deja al 25% abajo; mediana = el de en medio).")
    tabla_reglas = estrategia.tabla_reglas(cortes_arbol, conteo_arbol)
    st.dataframe(tabla_reglas, width="stretch", hide_index=True,
                 column_config={"Cómo se contesta": st.column_config.TextColumn(width="large"),
                                "Estrategia": st.column_config.TextColumn(width="large")})
    st.caption("Valores de corte con lo que hay hoy: " + estrategia.resumen_cortes(cortes_arbol)
               + f" · zonas sin cobertura buscadas a {radio_ws:g} km de la ruta (Opciones avanzadas).")

    cols_arbol = [C.COL_REGION, C.COL_TERRITORIO, C.COL_CEDI, C.COL_RUTA, "P", "Nº de estrategias", "Estrategias",
                  "Respuestas del árbol", "Porque"]
    tabla_arbol = df_f[cols_arbol].rename(columns={"P": "Cuadrante"})
    with st.expander(f"Ver la lista de rutas y sus estrategias ({len(tabla_arbol)} rutas)"):
        st.caption("Una fila por ruta. Si tiene varias estrategias, van separadas con “|”, en el mismo orden que su "
                   "porqué.")
        st.dataframe(tabla_arbol, width="stretch", hide_index=True)
    buf_a = io.BytesIO()
    with pd.ExcelWriter(buf_a, engine="openpyxl") as xw:
        tabla_arbol.to_excel(xw, sheet_name="Rutas", index=False)
        tabla_reglas.to_excel(xw, sheet_name="Árbol", index=False)
    st.download_button("Descargar árbol y estrategias (Excel)", buf_a.getvalue(),
                       file_name=f"arbol_decision_{escenario}_{nombre_caso(caso)}.xlsx".lower())
with tab_nivel:
    encabezado(
        f"Tabla por {nivel}",
        f"Una fila por {'ruta' if nivel == 'Ruta' else nivel.lower()} con su cuadrante y sus datos, con lo que tienes "
        "filtrado y seleccionado.",
        "Haz clic en el nombre de una columna para ordenar. Pasa el cursor sobre la tabla para ver el ícono de "
        "buscar y de pantalla completa. El botón de abajo descarga la misma tabla en Excel.")
    if df_grupos is None:
        cols = [C.COL_REGION, C.COL_TERRITORIO, C.COL_CEDI, C.COL_RUTA, C.COL_ESTATUS, "P",
                C.COL_X, C.COL_Y, "Nº de estrategias", "Estrategias", "Porque",
                C.COL_EJE_ESTADO, C.COL_EJE_ZONA, "Con polígono"]
        tabla = df_f[cols].rename(columns={"P": "Cuadrante"})
    else:
        tabla = df_grupos.rename(columns={"P": "Cuadrante"})
    tabla = tabla[tabla["Cuadrante"].isin(cuadrantes_visibles)]
    if seleccion:
        tabla = tabla[tabla[col_nivel].isin(seleccion)]
    st.dataframe(tabla, width="stretch", hide_index=True)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        tabla.to_excel(xw, sheet_name=nivel, index=False)
        if df_grupos is not None:
            df_f[[C.COL_REGION, C.COL_TERRITORIO, C.COL_CEDI, C.COL_RUTA, "P", C.COL_X, C.COL_Y]] \
                .to_excel(xw, sheet_name="Rutas", index=False)
    st.download_button("Descargar esta tabla (Excel)", buf.getvalue(), file_name=f"clasificacion_{nivel.lower()}.xlsx")

with tab_comp:
    encabezado(
        "Comparar dos escenarios",
        f"Dos mapas lado a lado: a la izquierda un escenario y a la derecha otro, por {nivel}. En rojo lo que cambia "
        "de cuadrante.",
        "Elige arriba de cada mapa qué escenario quieres ver. Los dos mapas se mueven juntos: acerca uno y el otro lo "
        "sigue. Pasa el cursor sobre una zona para ver su cuadrante en ese escenario y si cambia en el otro. Abajo "
        "están los conteos y la lista de lo que cambia, y un botón para descargarla.")

    def etiqueta_caso(c: str) -> str:
        return nombre_caso(c) if caso_con_datos[c] else f"{nombre_caso(c)} (sin datos)"

    ca, cb = st.columns(2)
    ca.markdown("**Mapa izquierdo**")
    esc_a = ca.selectbox("Carga de camión OP · izquierdo", escenarios, index=escenarios.index(escenario))
    caso_a = ca.selectbox("Caso de potencial · izquierdo", casos, index=casos.index(caso), format_func=etiqueta_caso)
    otros_esc = [e for e in escenarios if e != escenario] or escenarios
    cb.markdown("**Mapa derecho**")
    esc_b = cb.selectbox("Carga de camión OP · derecho", escenarios, index=escenarios.index(otros_esc[0]))
    caso_b = cb.selectbox("Caso de potencial · derecho", casos, index=casos.index(caso), format_func=etiqueta_caso)
    nombre_a = f"Carga OP {esc_a} · Potencial {nombre_caso(caso_a)}"
    nombre_b = f"Carga OP {esc_b} · Potencial {nombre_caso(caso_b)}"

    rutas_filtro = set(df_f[C.COL_RUTA])

    def escenario_filtrado(esc: str, cs: str) -> tuple[pd.DataFrame, dict]:
        """Rutas del filtro actual con la P del modelo de ese escenario."""
        _, base_x, res_x = resultados(clave, esc, cs, origen)
        base_x = base_x[base_x[C.COL_RUTA].isin(rutas_filtro)]
        cx = res_x["corte_atractividad"] if pd.notna(res_x["corte_atractividad"]) else C.UMBRAL_X_DEFAULT
        cy = res_x["corte_madurez"] if pd.notna(res_x["corte_madurez"]) else 50.0
        return datos.aplicar_clasificacion(base_x, cx, cy, usar_p_excel=True), {**res_x, "cx": cx, "cy": cy}

    df_a, res_a = escenario_filtrado(esc_a, caso_a)
    df_b, res_b = escenario_filtrado(esc_b, caso_b)

    def p_por_elemento(dfx: pd.DataFrame, res_x: dict) -> pd.DataFrame:
        if nivel == "Ruta":
            return pd.DataFrame({"id": dfx[C.COL_RUTA], "P": dfx["P"], "x": dfx[C.COL_X], "y": dfx[C.COL_Y],
                                 "rutas": 1, "cedi": dfx[C.COL_CEDI]})
        g = datos.agregar(dfx, col_nivel, res_x["cx"], res_x["cy"])
        return pd.DataFrame({"id": g[col_nivel], "P": g["P"], "x": g["Mediana atractividad"],
                             "y": g["Mediana madurez"], "rutas": g["Rutas"], "cedi": ""})

    el_a, el_b = p_por_elemento(df_a, res_a), p_por_elemento(df_b, res_b)
    pares = el_a.merge(el_b[["id", "P", "x", "y"]], on="id", how="outer", suffixes=("_a", "_b"))
    pares[["P_a", "P_b"]] = pares[["P_a", "P_b"]].fillna(C.SIN_DATOS)
    cambian = set(pares.loc[pares["P_a"] != pares["P_b"], "id"])

    def nombre_p(p_: str) -> str:
        return p_ if p_ == C.SIN_DATOS else f"{p_} · {C.CATEGORIAS[p_]['nombre']}"

    def info_lado(propio: str, otro: str, nombre_otro: str) -> pd.DataFrame:
        encabezado = "Ruta " if nivel == "Ruta" else f"{nivel}: "
        hover = [
            f"<b>{encabezado}{r['id']}</b>{(' · ' + r['cedi']) if isinstance(r['cedi'], str) and r['cedi'] else ''}<br>"
            f"<b>{nombre_p(r['P_' + propio])}</b><br>"
            f"Atractividad: {fmt(r['x_' + propio])} · Madurez: {fmt(r['y_' + propio])}<br>"
            + (f"<span style='color:{'#000000' if modo_daltonismo else '#F30000'}'><b>Cambia de cuadrante:</b> "
               f"en {nombre_otro} es {nombre_p(r['P_' + otro])}</span>"
               if r["P_a"] != r["P_b"] else f"<span style='color:#777'>Igual en {nombre_otro}</span>")
            for _, r in pares.iterrows()]
        return pd.DataFrame({"id": pares["id"], "P": pares["P_" + propio], "hover": hover})

    if (esc_a, caso_a) == (esc_b, caso_b):
        st.info("Los dos mapas tienen el mismo escenario: no va a haber cambios. Elige otro escenario en uno de los "
                "dos lados.")
    resaltar_on = st.checkbox(
        "Resaltar lo que cambia de cuadrante" + (" (borde negro grueso)" if modo_daltonismo else " (borde rojo)"),
        value=True, help="Marca con un borde las zonas que están en un cuadrante distinto en cada escenario.")
    leyenda_comp = {p_: nombre_p(p_) for p_ in C.ORDEN_CATEGORIAS}
    contornos_comp = None
    if nivel == "Ruta" and contorno_on:
        todos_c = contornos_ruta(canales, dias)
        contornos_comp = {i_: todos_c[i_] for i_ in pares["id"] if i_ in todos_c and i_ not in rutas_solo_web}
    fig_comp = figura.construir_comparacion(
        geoms_mapa, [(nombre_a, info_lado("a", "b", nombre_b)), (nombre_b, info_lado("b", "a", nombre_a))],
        leyenda_comp, titulo=f"Comparación de escenarios por {nivel}", centro=centro, zoom=zoom + ajuste_zoom,
        opacidad=opacidad, grosor_borde=0.4 if nivel == "Ruta" else 1.2, estilo=figura.ESTILOS_MAPA[estilo],
        contornos=contornos_comp, resaltar=cambian if resaltar_on else None, alto=680,
        fondo=rutas_solo_web if nivel == "Ruta" else None,
        uirevision=f"comp|{st.session_state['encuadre_ver']}")
    st.plotly_chart(fig_comp, width="stretch", key="mapa_comparacion",
                    config={"scrollZoom": True, "displaylogo": False,
                            "toImageButtonOptions": {"format": "jpeg", "filename": "comparacion_escenarios", "scale": 2}})

    # Conteo por cuadrante de cada lado
    conteo_a = el_a["P"].value_counts().reindex(C.ORDEN_CATEGORIAS, fill_value=0)
    conteo_b = el_b["P"].value_counts().reindex(C.ORDEN_CATEGORIAS, fill_value=0)
    encabezado("Cuántos hay en cada cuadrante",
               "Izquierdo → derecho: cuántos había en cada cuadrante y cuántos hay en el otro escenario.",
               "El número pequeño de abajo es la diferencia (+ = aumentan en el mapa derecho, − = disminuyen).")
    m1, m2 = st.columns(2)
    m1.metric(f"{nombre_grupo[:1].upper() + nombre_grupo[1:]} en la comparación", f"{len(pares):,}",
              help="Todos los elementos que cumplen los filtros del panel izquierdo.")
    m2.metric("Cambian de cuadrante", f"{len(cambian):,}", f"{len(cambian) / len(pares):.1%}" if len(pares) else None,
              delta_color="off", help="Cuántos están en un cuadrante distinto en cada escenario, y qué porcentaje son.")
    cols_p = st.columns(len(C.ORDEN_CATEGORIAS))
    for col_p, p_ in zip(cols_p, C.ORDEN_CATEGORIAS):
        col_p.metric(nombre_p(p_), f"{conteo_a[p_]:,} → {conteo_b[p_]:,}",
                     f"{conteo_b[p_] - conteo_a[p_]:+,}" if conteo_b[p_] != conteo_a[p_] else None,
                     delta_color="off", help=f"Izquierdo → derecho ({nombre_grupo})")

    cruce = pd.crosstab(pares["P_a"], pares["P_b"]).reindex(
        index=C.ORDEN_CATEGORIAS, columns=C.ORDEN_CATEGORIAS, fill_value=0)
    cruce.index.name = f"Izquierdo ({nombre_a})"
    cruce.columns.name = f"Derecho ({nombre_b})"
    encabezado(
        "De dónde a dónde se mueven",
        "Filas = cuadrante en el mapa izquierdo; columnas = cuadrante en el derecho.",
        "Cada número dice cuántos pasan del cuadrante de la fila al de la columna. La diagonal (en verde) son los que "
        "no cambian. Fuera de la diagonal, más naranja = más elementos que cambian así.")
    maximo = max(int(cruce.to_numpy().max()), 1)

    def estilo_cruce(t: pd.DataFrame) -> pd.DataFrame:
        # Diagonal (sin cambio) en verde; fuera de ella, naranja más intenso a más elementos
        out = pd.DataFrame("", index=t.index, columns=t.columns)
        for i_, _ in enumerate(t.index):
            for j_, _ in enumerate(t.columns):
                v = t.iat[i_, j_]
                if i_ == j_:
                    out.iat[i_, j_] = "background-color:#DDF1E3;font-weight:700"
                elif v:
                    out.iat[i_, j_] = f"background-color:rgba(255,153,102,{0.15 + 0.75 * v / maximo:.2f})"
        return out

    st.dataframe(cruce.style.apply(estilo_cruce, axis=None), width="stretch")

    tabla_pares = pares.rename(columns={
        "id": nivel, "P_a": f"Cuadrante · {nombre_a}", "P_b": f"Cuadrante · {nombre_b}",
        "x_a": f"Atractividad · {nombre_a}", "x_b": f"Atractividad · {nombre_b}",
        "y_a": f"Madurez · {nombre_a}", "y_b": f"Madurez · {nombre_b}"}).drop(columns=["cedi"])
    tabla_pares.insert(1, "Cambia", pares["P_a"] != pares["P_b"])
    cambios = tabla_pares[tabla_pares["Cambia"]].drop(columns="Cambia")
    encabezado(f"{nombre_grupo[:1].upper() + nombre_grupo[1:]} que cambian de cuadrante ({len(cambios)})",
               "Lista de lo que está en un cuadrante distinto en cada escenario, con sus valores en los dos.",
               "Haz clic en el nombre de una columna para ordenar. El botón de abajo descarga esta lista y la tabla "
               "completa en Excel.")
    st.dataframe(cambios, width="stretch", hide_index=True)
    buf_c = io.BytesIO()
    with pd.ExcelWriter(buf_c, engine="openpyxl") as xw:
        cruce.to_excel(xw, sheet_name="Transición")
        cambios.to_excel(xw, sheet_name="Cambian de cuadrante", index=False)
        tabla_pares.to_excel(xw, sheet_name="Todos", index=False)
    st.download_button("Descargar comparación (Excel)", buf_c.getvalue(),
                       file_name=f"comparacion_{esc_a}_{nombre_caso(caso_a)}_vs_{esc_b}_{nombre_caso(caso_b)}"
                                 f"_{nivel}.xlsx".replace(" ", "_").lower())

with tab_glosario:
    encabezado(
        "Glosario: qué significa cada indicador",
        "Todos los indicadores que puedes elegir para colorear el mapa, explicados en palabras sencillas.",
        "Qué mide = qué te dice el indicador. Cómo se calcula = de dónde sale el número. Cómo leerlo = si alto es "
        "bueno o malo. Escribe en el buscador para encontrar uno.")
    buscar = st.text_input("Buscar un indicador o concepto", placeholder="Por ejemplo: ticket, hogares, madurez…",
                           help="Escribe una palabra y la tabla sólo muestra lo que la contiene.")
    filas_glosario = []
    for v, (col_v, formato_v, grupo_v) in catalogo.items():
        que, como, leer = C.GLOSARIO_VARIABLES.get(v, (
            f"Indicador de la hoja de segmentos del libro ({seg.hoja if seg is not None else 'segmentos'}).",
            "Viene tal cual del Excel; en CeDi/Territorio/Región se usa la mediana de sus rutas.",
            "Depende del indicador."))
        filas_glosario.append({"Indicador": v, "Grupo": grupo_v, "Qué mide": que, "Cómo se calcula": como,
                               "Cómo leerlo": leer})
    glosario = pd.DataFrame(filas_glosario)
    conceptos = pd.DataFrame([{"Concepto": k, "Qué significa": v} for k, v in C.GLOSARIO_CONCEPTOS.items()])
    if buscar:
        patron = buscar.strip().lower()
        glosario = glosario[glosario.apply(lambda f: patron in " ".join(map(str, f)).lower(), axis=1)]
        conceptos = conceptos[conceptos.apply(lambda f: patron in " ".join(map(str, f)).lower(), axis=1)]
        if glosario.empty and conceptos.empty:
            st.info(f"No encontré nada con “{buscar}”. Prueba con otra palabra o borra el buscador.")
    st.dataframe(glosario, width="stretch", hide_index=True,
                 column_config={c: st.column_config.TextColumn(c, width="large")
                                for c in ["Qué mide", "Cómo se calcula", "Cómo leerlo"]})
    encabezado("Conceptos de la herramienta", "Palabras que aparecen en toda la página y qué quieren decir.",
               "Si una palabra de la página no se entiende, búscala aquí.")
    st.dataframe(conceptos, width="stretch", hide_index=True,
                 column_config={"Qué significa": st.column_config.TextColumn("Qué significa", width="large")})

with tab_modelo:
    encabezado("Modelo completo", "Todas las columnas del cálculo, ruta por ruta (para revisar o auditar).",
               "Es la misma información que la hoja de análisis del Excel, calculada por la herramienta con los "
               "escenarios elegidos arriba. Úsala sólo si necesitas revisar de dónde sale un número.")
    st.caption(f"Todas las columnas del modelo para **{escenario} · {caso}** (misma estructura que la hoja "
               f"'{modelo.HOJA_ANALISIS}'). Cortes: Madurez ≥ {resumen_modelo['corte_madurez']:g} · "
               f"Atractividad ≥ {resumen_modelo['corte_atractividad']:g}.")
    st.dataframe(df_modelo, width="stretch", hide_index=True)
    pesos = pd.DataFrame({"KPI": list(resumen_modelo["pesos_ejecucion"]),
                          "Peso en Índice de Ejecución": list(resumen_modelo["pesos_ejecucion"].values())})
    with st.expander("Pesos del Índice de Ejecución (calculados como en 'Análisis de KPIs')"):
        st.dataframe(pesos, hide_index=True)
    buf_m = io.BytesIO()
    with pd.ExcelWriter(buf_m, engine="openpyxl") as xw:
        df_modelo.to_excel(xw, sheet_name="Modelo", index=False)
        pd.DataFrame({
            "Parámetro": ["Escenario de carga de camión OP", "Caso de potencial", "Corte Madurez", "Corte Atractividad",
                          "Libro", "Versión del libro"],
            "Valor": [escenario, f"{nombre_caso(caso)} ({caso})", resumen_modelo["corte_madurez"],
                      resumen_modelo["corte_atractividad"],
                      nombre_libro, fecha_txt],
        }).to_excel(xw, sheet_name="Parámetros", index=False)
        pesos.to_excel(xw, sheet_name="Pesos", index=False)
    st.download_button("Descargar modelo completo (Excel)", buf_m.getvalue(),
                       file_name=f"modelo_{escenario}_{caso}.xlsx".replace(" ", "_").lower())

with tab_sin_geo:
    encabezado("Rutas sin polígono", "Rutas que cuentan en la matriz pero que no se pueden dibujar en el mapa.",
               "Pasa cuando la ruta no tiene su zona dibujada en el archivo de polígonos, o cuando quitaste los días "
               "en que visita. No es un error de la página: hay que completar el archivo de polígonos.")
    sin_geo = df_f[~df_f["Con polígono"]][[C.COL_REGION, C.COL_TERRITORIO, C.COL_CEDI, C.COL_RUTA, C.COL_ESTATUS, "P"]]
    st.caption(f"{len(sin_geo)} rutas del Excel no tienen polígono en el GeoJSON (canal: {', '.join(canales)}"
               + (f"; días: {', '.join(dias_sel)}" if dias else "") + "); "
               "cuentan en la matriz pero no se dibujan.")
    st.dataframe(sin_geo, width="stretch", hide_index=True)
    excel_rutas = set(df_base[C.COL_RUTA])
    geo_sin_excel = sorted(r for r in geoms_ruta if r not in excel_rutas)
    if geo_sin_excel:
        st.caption(f"{len(geo_sin_excel)} polígonos del GeoJSON no tienen resultado en el Excel: "
                   + ", ".join(geo_sin_excel))
