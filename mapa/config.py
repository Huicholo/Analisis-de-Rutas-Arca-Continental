"""Constantes: rutas de archivos, nombres de columnas, paletas de la matriz y glosario de variables."""
import threading
from collections.abc import Mapping
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data"
# Libro de análisis: la app lee de aquí datos y parámetros y calcula todo en mapa/modelo.py
#
# 2026-10-01 · se apunta a las versiones corregidas, para que esta app y la herramienta
# HTML del Canal Hogar digan EXACTAMENTE lo mismo. Las anteriores se dejan en Data/ para
# poder comparar; para volver a ellas basta cambiar estas dos líneas.
#
# El libro `realHOGAR_j510` trae, respecto al anterior (25-sep):
#   - los bloques `Atractividad Caso 70/85/90 (OSRM)` regenerados con la corrida de ruteo
#     real sobre la base de clientes HOGAR (218,618 clientes actuales, antes 207,612)
#   - la jornada del cálculo de holgura corregida a 510 min (antes 540, que no correspondía
#     a nada: el ruteo mide la carga contra 510 = 600 − 90 de tiempo administrativo)
#   Escenarios resultantes: 70% 75,430 · 85% 81,367 · 90% 83,346
#     (antes 78,635 / 85,258 / 87,466)
#   OJO: es un libro de VALORES, no de fórmulas. El 62.8% de las celdas del original eran
#   fórmulas y openpyxl pierde su valor cacheado al guardar; como esta app lee con
#   `data_only=True`, se guardó el snapshot de valores. No recalcula si se abre en Excel.
#
# El geojson `realHOGAR` trae:
#   - las 13 correcciones de número de ruta (Lincoln 701318→705318, Zapopan 816370→816369,
#     Aguascalientes 901408→901402, Monclova 203300→206300, Ocotlán 8354001→835401,
#     Santa María 80934→809340, Guadiana 9321410→931410)
#   - `cedis` homologado al dueño de la ruta según el Excel oficial, con lo que ningún
#     número de ruta queda repartido entre 2+ CeDis (antes 20 números / 110 polígonos)
#   - `cedis_venta` con la atribución por mayoría de venta, para no perderla
#   - la geometría completa (144,693 vértices; el anterior venía simplificado a 78,458)
EXCEL_ANALISIS = DATA_DIR / "Analisis de madurez CEDIS y Rutas Arca - realHOGAR_j510.xlsx"
GEOJSON_RUTAS = DATA_DIR / "geo_poligonos_rutas_arca_realHOGAR.geojson"

# Columnas del Excel
COL_REGION = "Región"
COL_TERRITORIO = "Territorio EERR"
COL_CEDI = "CeDi"
COL_RUTA = "Ruta"
COL_ESTATUS = "Estatus"
COL_X = "Eje X ruta - Atractividad propia"
COL_Y = "Eje Y ruta - Madurez y saturación"
COL_P = "P homologada de la ruta"
COL_RESULTADO = "Resultado"
COL_EJE_ESTADO = "Eje: estado de la ruta"
COL_EJE_ZONA = "Eje: potencial de la zona"

# Niveles de agregación: etiqueta en la UI -> columna
NIVELES = {
    "Ruta": COL_RUTA,
    "CeDi": COL_CEDI,
    "Territorio": COL_TERRITORIO,
    "Región": COL_REGION,
}

# Los cortes de la matriz son las medianas redondeadas a 1 decimal que calcula el modelo.
UMBRAL_X_DEFAULT = 50.0  # respaldo si el caso de atractividad no tiene datos
ESCENARIO_DEFAULT = "Medio"  # escenario de carga de camión OP con el que abre la app
# Nombre con el que se muestran los casos de potencial (bloques "Atractividad Caso NN" del libro)
#
# 2026-10-01 · el libro trae ahora SEIS bloques: los 3 originales (haversine) y los 3
# nuevos con ruteo OSRM real. Los VIGENTES son los OSRM, así que se quedan con el nombre
# de negocio a secas y los anteriores se marcan, para que nadie los confunda en el
# selector. Los `Caso 85`/`Caso 70` antiguos están vacíos en el libro nuevo y la propia
# app les añade "(sin datos)".
_SUF_OSRM = " (OSRM, atención 5 min) · NUEVO 2026-09-25"
NOMBRES_POTENCIAL = {
    "Caso 90" + _SUF_OSRM: "Conservador",
    "Caso 85" + _SUF_OSRM: "Medio",
    "Caso 70" + _SUF_OSRM: "Ambicioso",
    "Caso 90": "Conservador (anterior)",
    "Caso 85": "Medio (anterior)",
    "Caso 70": "Ambicioso (anterior)",
}
# Colores de la mini gráfica del detalle (paleta de temas del proyecto)
COLOR_BARRA = {"Madurez": "#68C9CD", "Atractividad": "#E5803D", "vacío": "#D5D5D5"}

# Vista por defecto: norte y centro de México con todo el territorio de rutas a la vista.
CENTRO_GENERAL = {"lat": 25.97, "lon": -104.1}
ZOOM_GENERAL = 4.9

# Vista alternativa: centroide del territorio Arca.
# Equivale a folium.Map(location=[25.8041258, -103.4481389], zoom_start=12): Leaflet usa tiles de
# 256 px y MapLibre (Plotly) de 512 px, así que el mismo encuadre es un nivel de zoom menos.
CENTRO_ARCA = {"lat": 25.8041258, "lon": -103.4481389}
ZOOM_FOLIUM_ARCA = 12
ZOOM_ARCA = ZOOM_FOLIUM_ARCA - 1

# Paletas de la matriz. "Normal" = la matriz de referencia; "Daltonismo" = colores de Okabe–Ito, que se
# distinguen con los tipos más comunes de daltonismo (rojo–verde y azul–amarillo).
SIN_DATOS = "Sin datos"
PALETAS_MATRIZ = {
    "Normal": {
        "P1": {"nombre": "Ampliar cobertura", "color": "#A5E2B2", "borde": "#3E9A55"},
        "P2": {"nombre": "Mantener", "color": "#FED697", "borde": "#C99526"},
        "P3": {"nombre": "Desarrollar", "color": "#FF9966", "borde": "#C8551E"},
        "P4": {"nombre": "Evaluar", "color": "#FF9494", "borde": "#C43C3C"},
        SIN_DATOS: {"nombre": "Sin datos", "color": "#D0D0D0", "borde": "#8A8A8A"},
    },
    "Daltonismo": {
        "P1": {"nombre": "Ampliar cobertura", "color": "#7FB8E0", "borde": "#0072B2"},
        "P2": {"nombre": "Mantener", "color": "#C9E6F7", "borde": "#3A8FC4"},
        "P3": {"nombre": "Desarrollar", "color": "#F5CB6B", "borde": "#B07A00"},
        "P4": {"nombre": "Evaluar", "color": "#E7A3C9", "borde": "#A0457A"},
        SIN_DATOS: {"nombre": "Sin datos", "color": "#D0D0D0", "borde": "#6E6E6E"},
    },
}
ORDEN_CATEGORIAS = ["P1", "P2", "P3", "P4", SIN_DATOS]
# Forma de cada cuadrante en las gráficas (para no depender sólo del color)
SIMBOLOS = {"P1": "circle", "P2": "square", "P3": "diamond", "P4": "triangle-up", SIN_DATOS: "x"}
SIMBOLOS_TEXTO = {"P1": "●", "P2": "■", "P3": "◆", "P4": "▲", SIN_DATOS: "✕"}

# La app corre en línea con varias personas a la vez: la paleta elegida vale sólo para la sesión (hilo)
# que la eligió. `usar_paleta()` se llama al inicio de cada ejecución de la app.
_sesion = threading.local()


def usar_paleta(nombre: str) -> None:
    _sesion.paleta = nombre if nombre in PALETAS_MATRIZ else "Normal"


def paleta_activa() -> str:
    return getattr(_sesion, "paleta", "Normal")


def es_daltonismo() -> bool:
    return paleta_activa() == "Daltonismo"


class _Categorias(Mapping):
    """CATEGORIAS["P1"] devuelve los colores de la paleta activa de la sesión."""

    def __getitem__(self, clave):
        return PALETAS_MATRIZ[paleta_activa()][clave]

    def __iter__(self):
        return iter(PALETAS_MATRIZ["Normal"])

    def __len__(self):
        return len(PALETAS_MATRIZ["Normal"])


CATEGORIAS = _Categorias()

# Variables para colorear en escala continua: etiqueta -> (columna del modelo, formato, grupo)
# Formato: especificación de Python; prefijo "$" para moneda. Las variables de la hoja de segmentos
# del libro se agregan solas al catálogo con el grupo "Segmento".
VARIABLES_CONTINUAS = {
    "Índice de madurez (eje Y)": (COL_Y, ".1f", "Índices"),
    "Índice de atractividad (eje X)": (COL_X, ".1f", "Índices"),
    "% Utilización de capacidad": ("% Utilización de capacidad", ".0%", "Índices"),
    "Clientes/día": ("Clientes/día", ",.1f", "Madurez"),
    "Efectividad de compra": ("Efectividad de compra", ".0%", "Madurez"),
    "Ingreso OP/día": ("Ingreso OP/día", "$,.0f", "Madurez"),
    "Ingreso GFN/día": ("Ingreso GFN/día", "$,.0f", "Madurez"),
    "#CU GFN/día": ("#CU GFN/día", ",.1f", "Madurez"),
    "#CU OP/día": ("#CU OP/día", ",.1f", "Madurez"),
    "Ticket x cliente": ("Ticket x cliente", "$,.0f", "Madurez"),
    "% Hogares totales ABC+": ("% Hogares totales ABC+", ".1%", "Atractividad"),
    "Hogares actual + potencial (%)": ("Hogares actual + potencial (%)", ".1%", "Atractividad"),
    "Potencial Ingreso / hogar": ("Potencial Ingreso / hogar", "$,.1f", "Atractividad"),
    "Potencial CU / hogar": ("Potencial CU / hogar", ",.2f", "Atractividad"),
    "Hogares A/B + C+ actuales": ("Hogares A/B + C+ actuales", ",.0f", "Hogares"),
    "Hogares A/B + C+ potenciales a capturar": ("Hogares A/B + C+ potenciales a capturar", ",.0f", "Hogares"),
    "% Venta web": ("% Venta Web", ".1%", "Canal"),
}
# Escala continua con la paleta de la matriz: bajo (Evaluar) -> alto (Ampliar cobertura)
_ESCALA_SEMAFORO = [
    [0.0, "#D9534F"], [0.25, "#FF9494"], [0.45, "#FF9966"],
    [0.6, "#FED697"], [0.8, "#A5E2B2"], [1.0, "#3E9A55"],
]
# En modo daltonismo: "cividis" (azul oscuro → amarillo), legible con cualquier tipo de daltonismo
_ESCALA_CIVIDIS = [
    [0.0, "#00204D"], [0.25, "#414D6B"], [0.5, "#7C7B78"], [0.75, "#BCAF6F"], [1.0, "#FFEA46"],
]


def escala_continua() -> list:
    return _ESCALA_CIVIDIS if es_daltonismo() else _ESCALA_SEMAFORO


# Glosario: qué significa cada variable del catálogo, en lenguaje sencillo.
# (qué mide, cómo se calcula, cómo leerla)
GLOSARIO_VARIABLES = {
    "Índice de madurez (eje Y)": (
        "Qué tan bien opera la ruta hoy. Es el eje vertical de la matriz.",
        "75% viene del Índice de Ejecución (cuánto cumple la ruta de sus 7 indicadores contra el estándar de su "
        "Región en el escenario de carga elegido) y 25% de si la ruta ya está saturada (llena). Va de 0 a 100.",
        "Más alto = ruta más madura. La mitad de las rutas queda arriba del corte (la mediana)."),
    "Índice de atractividad (eje X)": (
        "Qué tanto potencial tiene la zona que cubre la ruta. Es el eje horizontal de la matriz.",
        "Promedio de 4 puntajes de la zona (hogares A/B + C+, hogares actuales + potenciales, ingreso potencial "
        "por hogar y cajas potenciales por hogar), comparando cada ruta con las de su CeDi. Va de 0 a 100. "
        "Depende del caso de potencial elegido.",
        "Más alto = zona más atractiva. La mitad de las rutas queda a la derecha del corte (la mediana)."),
    "% Utilización de capacidad": (
        "Qué tan llena está la ruta.",
        "Capacidad utilizada ÷ capacidad instalada de la ruta.",
        "100% = la ruta ya no tiene espacio para más clientes. Más bajo = hay espacio para crecer."),
    "Clientes/día": (
        "Cuántos clientes atiende la ruta en un día.",
        "Clientes atendidos por día (dato real de la base de rutas).",
        "Más alto = mejor. Es uno de los 7 indicadores de madurez."),
    "Efectividad de compra": (
        "De cada 100 clientes visitados, cuántos compran.",
        "Clientes que compran ÷ clientes visitados (dato real).",
        "Más alto = mejor. Es uno de los 7 indicadores de madurez."),
    "Ingreso OP/día": (
        "Cuánto vende la ruta al día en otros productos (OP, todo lo que no es garrafón).",
        "Venta OP del periodo ÷ días trabajados.",
        "Más alto = mejor. Es uno de los 7 indicadores de madurez."),
    "Ingreso GFN/día": (
        "Cuánto vende la ruta al día en garrafón (GFN).",
        "Venta de garrafón del periodo ÷ días trabajados.",
        "Más alto = mejor. Es uno de los 7 indicadores de madurez."),
    "#CU GFN/día": (
        "Cuántas cajas unidad de garrafón mueve la ruta al día.",
        "Cajas unidad de garrafón del periodo ÷ días trabajados.",
        "Más alto = mejor. Es uno de los 7 indicadores de madurez."),
    "#CU OP/día": (
        "Cuántas cajas unidad de otros productos mueve la ruta al día.",
        "Cajas unidad de otros productos del periodo ÷ días trabajados.",
        "Más alto = mejor. Es uno de los 7 indicadores de madurez."),
    "Ticket x cliente": (
        "Cuánto compra en promedio cada cliente por visita.",
        "Venta ÷ clientes que compran (dato real).",
        "Más alto = mejor. Es uno de los 7 indicadores de madurez."),
    "% Hogares totales ABC+": (
        "Qué parte de los hogares de la zona son de nivel A/B o C+ (sin contar los potenciales por capturar).",
        "(Hogares A/B + C+ − hogares potenciales a capturar) ÷ hogares de la zona. Depende del caso de "
        "potencial elegido.",
        "Más alto = zona con más hogares de interés. Es uno de los 4 componentes de atractividad."),
    "Hogares actual + potencial (%)": (
        "Qué parte de los hogares de la zona son A/B o C+, contando los actuales y los potenciales.",
        "Hogares A/B + C+ ÷ hogares de la zona. Depende del caso de potencial elegido.",
        "Más alto = más mercado. Es uno de los 4 componentes de atractividad."),
    "Potencial Ingreso / hogar": (
        "Cuánto dinero adicional puede dejar cada hogar de la zona.",
        "Potencial de ingreso ÷ (hogares potenciales + hogares de la zona). Depende del caso de potencial.",
        "Más alto = más dinero por capturar. Es uno de los 4 componentes de atractividad."),
    "Potencial CU / hogar": (
        "Cuántas cajas unidad adicionales puede comprar cada hogar de la zona.",
        "Potencial de cajas unidad ÷ (hogares potenciales + hogares de la zona). Depende del caso de potencial.",
        "Más alto = más volumen por capturar. Es uno de los 4 componentes de atractividad."),
}

GLOSARIO_VARIABLES.update({
    "Hogares A/B + C+ actuales": (
        "Cuántos hogares de nivel A/B o C+ de la zona de la ruta ya son clientes.",
        "Hogares A/B + C+ totales − hogares potenciales a capturar, del caso de potencial elegido. En CeDi/Territorio/"
        "Región se usa la ruta de en medio (mediana).",
        "Más alto = la ruta ya atiende a muchos hogares de interés."),
    "Hogares A/B + C+ potenciales a capturar": (
        "Cuántos hogares de nivel A/B o C+ de la zona todavía se pueden ganar como clientes.",
        "Dato del caso de potencial elegido (columna 'Hogares potenciales a capturar'). En CeDi/Territorio/Región "
        "se usa la ruta de en medio (mediana).",
        "Más alto = más clientes por ganar. El árbol de decisión lo usa en '¿Tiene muchos hogares por capturar?'."),
    "% Venta web": (
        "Qué parte de la venta de la ruta llega por el canal web.",
        "Venta web ÷ venta total de la ruta (dato de la base de rutas).",
        "Más alto = sus clientes ya usan la web. El árbol lo usa en '¿Hay potencial para venta web?'."),
})

# Conceptos generales de la herramienta (para el glosario y las ayudas)
GLOSARIO_CONCEPTOS = {
    "Matriz Atractividad × Madurez": "Tabla de 2 × 2 que acomoda cada ruta según qué tan bien opera (madurez, "
                                     "arriba/abajo) y qué tanto potencial tiene su zona (atractividad, "
                                     "derecha/izquierda).",
    "Cuadrante": "Cada una de las 4 casillas de la matriz: P1 Ampliar cobertura, P2 Mantener, P3 Desarrollar y "
                 "P4 Evaluar. Dice qué hacer con la ruta.",
    "P1 · Ampliar cobertura": "Ruta madura en zona atractiva: crecer (más clientes, más territorio).",
    "P2 · Mantener": "Ruta madura en zona poco atractiva: cuidar lo que ya funciona.",
    "P3 · Desarrollar": "Ruta poco madura en zona atractiva: mejorar cómo opera para aprovechar la zona.",
    "P4 · Evaluar": "Ruta poco madura en zona poco atractiva: revisar si conviene seguir igual.",
    "Sin datos": "La ruta no tiene la información necesaria para ubicarla en la matriz (por ejemplo, está "
                 "inactiva o le faltan datos de capacidad o de zona).",
    "Corte (mediana)": "La línea que divide la matriz. Es el valor de en medio: la mitad de las rutas queda de "
                       "cada lado.",
    "Ruta / CeDi / Territorio / Región": "Niveles de la organización, de lo más chico a lo más grande. Un CeDi "
                                         "(centro de distribución) tiene varias rutas; un Territorio, varios "
                                         "CeDis; una Región, varios Territorios.",
    "Escenario de carga de camión OP": "Qué tan exigente es el estándar contra el que se mide cada ruta "
                                       "(Conservador, Medio o Ambicioso). Cambia la madurez.",
    "Caso de potencial": "Qué tan optimista es el cálculo del potencial de la zona (Conservador, Medio o "
                         "Ambicioso). Cambia la atractividad.",
    "Percentil": "Posición de un valor contra los demás, de 0 a 100. Percentil 75 = está arriba del 75% de las "
                 "rutas.",
    "Terciles": "Dividir las rutas en 3 grupos del mismo tamaño: bajo, medio y alto.",
    "Polígono / huella de la ruta": "El área del mapa que cubre la ruta. Cada ruta tiene un polígono por día "
                                    "de visita; juntos forman su huella.",
}

# Días de visita: etiqueta -> letra usada en el código del GeoJSON (L-J, M-V, X-S, L, M, ...)
DIAS = {"Lunes": "L", "Martes": "M", "Miércoles": "X", "Jueves": "J", "Viernes": "V", "Sábado": "S"}
