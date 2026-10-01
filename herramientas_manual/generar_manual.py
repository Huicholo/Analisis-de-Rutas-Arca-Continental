"""Genera static/manual.html: tour interactivo con capturas reales de la app y puntos que explican cada parte."""
import base64
import html
import json
import os
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # carpeta del proyecto
sys.path.insert(0, APP)
from mapa import config as C  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
TOUR = os.path.join(AQUI, "tour")
SALIDA = os.path.join(APP, "static", "manual.html")

escenas = {e["clave"]: e for e in json.load(open(os.path.join(TOUR, "escenas.json"), encoding="utf-8"))}

# --------------------------------------------------------------------------- textos de cada punto
# clave -> (título corto, explicación)
PUNTOS = {
    # inicio
    "titulo": ("Nombre de la herramienta", "Abajo del título hay una frase que resume para qué sirve la página."),
    "primera_vez": ("¿Primera vez aquí?", "Haz clic para abrir las instrucciones rápidas en 4 pasos. Léelas antes de empezar."),
    "escenario": ("Escenario de carga de camión OP",
                  "Qué tan exigente es la meta contra la que se mide cada ruta. <b>Conservador</b> = meta más fácil, "
                  "<b>Ambicioso</b> = meta más difícil. Cambia la <b>madurez</b>. Si no sabes cuál usar, deja <b>Medio</b>."),
    "caso": ("Caso de potencial",
             "Qué tan optimista es el cálculo del potencial de la zona. Cambia la <b>atractividad</b>. Si un caso dice "
             "“sin datos”, todavía no está capturado; elige otro."),
    # panel
    "manual": ("Abrir el manual", "Abre esta guía en otra pestaña del navegador."),
    "accesibilidad": ("Accesibilidad", "Haz clic para ver las opciones que hacen la página más fácil de ver."),
    "daltonismo": ("Modo daltonismo",
                   "Cambia los colores por unos que se distinguen aunque no veas bien el rojo y el verde. También "
                   "escribe el cuadrante (P1, P2…) sobre el mapa y usa formas distintas en la gráfica."),
    "texto_grande": ("Texto más grande", "Hace más grandes todas las letras de la página."),
    "libro": ("Libro de análisis (datos)",
              "Dice de qué archivo de Excel salen los datos. Sirve para probar un archivo nuevo sólo en tu sesión: "
              "no cambia lo que ven los demás. Si no te lo pidieron, no lo toques."),
    "colorear_por": ("Paso 1 · Colorear por",
                     "Elige qué ver en el mapa: cada <b>Ruta</b> por separado, o agrupadas por <b>CeDi</b>, "
                     "<b>Territorio</b> o <b>Región</b>. Si agrupas, el color es el cuadrante de la ruta “de en medio” del grupo."),
    "region": ("Filtro · Región", "Deja sólo las rutas de las regiones que elijas. Vacío = todas."),
    "territorio": ("Filtro · Territorio",
                   "Deja sólo las rutas de los territorios que elijas. Sólo aparecen los territorios de las regiones elegidas arriba."),
    "ruta": ("Filtro · Ruta",
             "Escribe el número de la ruta para encontrarla y elígela. Puedes elegir varias. Sólo aparecen las rutas "
             "de la región, territorio y CeDi elegidos arriba."),
    "radio_ws": ("Distancia máxima para buscar zonas sin cobertura",
                 "Para la pregunta del árbol “¿Hay potencial cercano sin cobertura?”: qué tan lejos de la zona de la "
                 "ruta se buscan áreas que ninguna ruta cubre. Empieza en 2 km."),
    "con_p": ("Agregar el mapa de cuadrantes (P)",
              "Sólo en “Mapas lado a lado”. Encendido: el primer mapa muestra los cuadrantes P1–P4 para compararlos "
              "con los indicadores. Apagado: sólo los mapas de los indicadores."),
    "abrir_diagrama": ("Ver el diagrama",
                       "El diagrama del árbol está guardado aquí para no ocupar espacio. Haz clic para abrirlo o "
                       "cerrarlo. La explicación completa del árbol está en el paso “Árbol de decisión completo” de "
                       "este manual."),
    "cedi": ("Filtro · CeDi",
             "Deja sólo las rutas de los CeDis (centros de distribución) que elijas. Sólo aparecen los de la región y territorio elegidos."),
    "dias": ("Filtro · Día de visita",
             "Cada ruta cubre zonas distintas según el día. Quita días para ver sólo la zona de los días que quedan. "
             "No cambia los cuadrantes, sólo lo que se dibuja."),
    "activas": ("Filtro · Solo rutas activas", "Quita las rutas que hoy no están operando."),
    "cuadrantes": ("Cuadrantes visibles en el mapa",
                   "Quita un cuadrante (clic en su “x”) para esconderlo del mapa. Por ejemplo, deja sólo P1 para ver "
                   "dónde hay que crecer. Los números de la matriz no cambian."),
    "colorear_con": ("Paso 3 · Colorear con",
                     "<b>Cuadrante de la matriz</b>: cada zona con el color de su cuadrante (lo normal). "
                     "<b>Variables continuas</b>: cada zona más clara u oscura según un indicador (por ejemplo, clientes por día)."),
    "mapa_base": ("Mapa base", "El fondo del mapa: calles, nombres de ciudades o fondo oscuro. No cambia los datos."),
    "opacidad": ("Opacidad", "Qué tan sólido se ve el color. Más a la izquierda = más transparente (ves las calles de abajo)."),
    "etiquetas": ("Etiquetas con nombre",
                  "Escribe el nombre de cada zona (o el número de ruta) sobre el mapa. Con muchas rutas se puede ver amontonado: acércate."),
    "contorno": ("Contorno oscuro de cada ruta",
                 "Línea oscura alrededor de toda la zona de cada ruta (todos sus días juntos). Aparece al acercarte al "
                 "nivel de ciudad. Sólo en “Ruta”."),
    "perfil": ("Mini gráfica de perfil",
               "Al pasar el cursor sobre el mapa, muestra barras con los indicadores de la zona. Barra más llena = mejor "
               "que las demás rutas."),
    "burbujas": ("Burbujas por grupo",
                 "En CeDi, Territorio o Región dibuja un círculo por grupo. De lejos: con el color de su cuadrante o "
                 "indicador y más grande = más rutas. De cerca (nivel ciudad): círculo blanco con la letra del nivel "
                 "(<b>C</b> = CeDi, <b>T</b> = Territorio, <b>R</b> = Región)."),
    "vista": ("Vista del mapa",
              "A dónde llevar el mapa al pulsar <b>Ir a esta vista</b>: todo el país, el centro de Arca o justo lo que tienes filtrado."),
    "ajuste_zoom": ("Ajuste de zoom", "Acerca (+) o aleja (−) la vista elegida. Se aplica al pulsar <b>Ir a esta vista</b>."),
    "ir_vista": ("Ir a esta vista",
                 "Mueve el mapa a la vista elegida. Importante: si no pulsas este botón, el mapa se queda donde tú lo dejaste."),
    "avanzadas": ("Opciones avanzadas",
                  "Cambian los resultados oficiales. <b>No las toques</b> a menos que te lo pidan. Si las cambiaste por "
                  "error, pulsa <b>Restablecer todo</b>."),
    "canal": ("Canal de polígonos",
              "De qué fuentes se dibujan las zonas. Deja las dos (Convencional y Web): hay rutas que sólo tienen zona "
              "del canal Web y si lo quitas desaparecen del mapa."),
    "umbral_x": ("Corte de atractividad", "La línea vertical de la matriz. El valor oficial es la mediana."),
    "umbral_y": ("Corte de madurez", "La línea horizontal de la matriz. El valor oficial es la mediana."),
    "restablecer": ("Restablecer todo",
                    "Tu botón de emergencia: regresa toda la página a como estaba al abrirla (quita filtros, selecciones y cambios)."),
    # panel variables
    "variables": ("Variables (hasta 2)",
                  "Elige 1 o 2 indicadores para pintar el mapa. Color más oscuro = valor más alto. Qué significa cada uno: "
                  "pestaña <b>Glosario</b>."),
    "como_comparar": ("Cómo verlas",
                      "<b>Un solo mapa</b> (1 indicador) o <b>Bivariado</b> (2 indicadores en un mapa). <b>Mapas lado a "
                      "lado</b>: un mapa por indicador y, si quieres, antes el de cuadrantes; los mapas se mueven juntos."),
    "colores": ("Colores", "<b>Un color por variable</b>: azules y naranjas. <b>Semáforo</b>: de bajo a alto."),
    "percentiles": ("Comparar en percentiles",
                    "Pone los indicadores en la misma escala de 0 a 100 (su posición contra las demás). Úsalo con mapas lado a lado."),
    # matriz
    "matriz": ("La matriz",
               "Arriba = rutas que operan bien. Derecha = zonas con mucho potencial. Cada casilla dice cuántas rutas caen ahí."),
    "p1": ("P1 · Ampliar cobertura", "Opera bien y la zona tiene potencial: <b>hay que crecer</b> (más clientes, más territorio)."),
    "p2": ("P2 · Mantener", "Opera bien pero la zona da poco más: <b>hay que cuidar</b> lo que ya funciona."),
    "p3": ("P3 · Desarrollar", "La zona tiene potencial pero la ruta opera mal: <b>hay que mejorar</b> cómo opera."),
    "p4": ("P4 · Evaluar", "Opera mal y la zona da poco: <b>hay que decidir</b> qué hacer con la ruta."),
    "metricas": ("Totales", "Cuántas rutas hay con tus filtros, cuántas se pueden dibujar y cuántas no tienen datos para ubicarse."),
    "dispersion": ("Gráfica de la matriz",
                   "La misma matriz, con cada ruta en su lugar exacto. La forma del punto dice su cuadrante: "
                   "● P1, ■ P2, ◆ P3, ▲ P4. Selecciona puntos y el mapa mostrará sólo esos."),
    "herramientas": ("Herramientas para seleccionar",
                     "Aparecen al pasar el cursor por la gráfica. Elige el rectángulo o el lazo y arrastra sobre los puntos. "
                     "Para quitar la selección pulsa <b>Limpiar selección</b>."),
    "ayuda": ("Círculo de ayuda (?)", "Todos los títulos tienen uno. Pasa el cursor encima para leer qué es y cómo se usa."),
    # mapa
    "mapa": ("El mapa",
             "Rueda del mouse = acercar o alejar. Arrastrar = moverte. El mapa se queda donde lo dejes aunque cambies filtros."),
    "leyenda": ("Leyenda", "Qué significa cada color. Haz clic en un nombre para esconderlo o mostrarlo en el mapa."),
    "camara": ("Botones del mapa",
               "Aparecen al pasar el cursor. La <b>cámara</b> descarga una imagen de exactamente lo que ves."),
    "detalle": ("Detalle de la zona",
                "Aparece a un lado de la zona al pasar el cursor: su cuadrante, sus datos, sus <b>hogares A/B + C+</b> "
                "(total y potenciales a capturar), las <b>estrategias</b> recomendadas con su porqué y la mini gráfica "
                "de perfil (cada barra dice su estándar o su máximo)."),
    "titulo_mapa": ("Título del mapa", "Dice qué se está pintando y con qué escenarios y filtros."),
    "referencia": ("Barras del detalle: comparar contra",
                   "Sólo cambia qué tan llenas se ven las barras del detalle; <b>no cambia los filtros</b> ni el mapa. "
                   "<b>Lo que tengo filtrado</b>: contra lo filtrado. <b>Todas las rutas</b>: contra todas, sin filtros. "
                   "Junto a cada barra va el <b>estándar</b> (madurez) o el <b>máximo</b> (atractividad)."),
    # exportar
    "titulo_exp": ("Título", "Escribe el título que quieres que salga en la imagen."),
    "subtitulo_exp": ("Subtítulo", "Ya trae los escenarios, filtros y la fecha. Puedes cambiarlo."),
    "tamano": ("Tamaño", "16:9 es el tamaño normal de una lámina de PowerPoint."),
    "resolucion": ("Resolución", "Más alto = imagen más nítida, pero tarda más y pesa más."),
    "generar": ("Generar imagen",
                "Púlsalo y espera unos segundos. La imagen sale con la <b>misma zona y el mismo acercamiento</b> que el "
                "mapa de arriba. Después aparece la vista previa y el botón <b>Descargar imagen</b>."),
    "mostrar_arbol": ("Mostrar la pestaña del árbol de decisión",
                      "El árbol de decisión está oculto. Enciende este interruptor y aparece como la primera pestaña. "
                      "Las estrategias de cada ruta se ven siempre en el detalle del mapa."),
    # árbol
    "pestanas": ("Pestañas", "Cada pestaña muestra otra forma de ver los mismos datos. Haz clic en un nombre para abrirla."),
    "conteo_estrategias": ("Rutas por número de estrategias",
                           "Una ruta puede recibir varias estrategias al mismo tiempo. Aquí ves cuántas reciben 1, 2, 3 o 4."),
    "ver_diagrama": ("Ver en el diagrama", "Muestra el árbol completo o sólo un cuadrante (más fácil de leer y de presentar)."),
    "alto_diagrama": ("Alto del diagrama", "Hazlo más alto si se ve apretado."),
    "diagrama": ("El árbol",
                 "Empieza arriba y sigue las flechas. Cada <b>rombo</b> es una pregunta. Si la respuesta (Sí o No) tiene una "
                 "caja de color, la ruta recibe esa estrategia; después sigue a la siguiente pregunta, así que puede tener "
                 "varias. Rueda del mouse = acercar; arrastrar = moverte; <b>Descargar diagrama</b> = imagen para PowerPoint."),
    # tabla
    "tabla_nivel": ("Tabla", "Una fila por ruta (o por grupo). Clic en el nombre de una columna para ordenar."),
    "descargar_tabla": ("Descargar", "Descarga la misma tabla en Excel."),
    # comparar
    "lado_izq": ("Mapa izquierdo · carga OP", "Escenario de carga del mapa de la izquierda."),
    "caso_izq": ("Mapa izquierdo · potencial", "Caso de potencial del mapa de la izquierda."),
    "lado_der": ("Mapa derecho · carga OP", "Escenario de carga del mapa de la derecha. Elige uno distinto al izquierdo."),
    "caso_der": ("Mapa derecho · potencial", "Caso de potencial del mapa de la derecha."),
    "resaltar": ("Resaltar cambios",
                 "Marca con borde rojo (negro en modo daltonismo) las zonas que están en un cuadrante distinto en cada escenario."),
    "mapas_comp": ("Los dos mapas",
                   "Se mueven juntos: acerca uno y el otro lo sigue. Pasa el cursor sobre una zona para ver si cambia de cuadrante."),
    "conteo_comp": ("Cuántos hay en cada cuadrante",
                    "Izquierdo → derecho. El número pequeño es la diferencia (+ aumentan, − disminuyen)."),
    "transicion": ("De dónde a dónde se mueven",
                   "Cada número dice cuántos pasan del cuadrante de la fila al de la columna. La diagonal verde no cambia."),
    "lista_cambios": ("Lista de lo que cambia", "Cada ruta que cambia de cuadrante, con sus valores en los dos escenarios."),
    "descargar_comp": ("Descargar comparación", "Descarga todo en Excel."),
    # glosario
    "buscar": ("Buscar", "Escribe una palabra (por ejemplo, “ticket”) y la tabla sólo muestra lo que la contiene."),
    "tabla_glosario": ("Indicadores",
                       "Qué mide cada indicador, cómo se calcula y si alto es bueno o malo."),
    "conceptos": ("Conceptos", "Palabras que aparecen en toda la página y qué quieren decir."),
    # bivariado
    "disp_biv": ("Gráfica de 2 indicadores",
                 "Cada punto es una ruta. Las casillas parten cada indicador en 3 grupos (bajo, medio, alto) y dicen cuántas rutas hay en cada una."),
    "rombo": ("Leyenda en rombo",
              "Cómo leer los colores: el 1er indicador crece hacia arriba a la derecha y el 2º hacia arriba a la izquierda. "
              "Casi negro = los dos altos; azul = sólo el 1º alto; naranja = sólo el 2º alto; gris claro = los dos bajos."),
    "mapa_biv": ("Mapa con 2 indicadores", "Cada zona tiene el color de su casilla en el rombo."),
    # daltonismo
    "matriz_dalt": ("Matriz en modo daltonismo", "Azul, azul claro, amarillo y rosa: se distinguen con cualquier tipo de daltonismo."),
    "disp_dalt": ("Formas por cuadrante", "Además del color, cada cuadrante tiene su forma: ● P1, ■ P2, ◆ P3, ▲ P4."),
    "mapa_dalt": ("Mapa en modo daltonismo", "Con las etiquetas encendidas, cada zona dice su cuadrante (por ejemplo, “P3 · 705325”)."),
}

# --------------------------------------------------------------------------- pasos del tour
PASOS = [
    ("inicio", "La parte de arriba", "Lo primero que ves al abrir la página: el título, las instrucciones rápidas y los 2 escenarios del cálculo."),
    ("panel", "El panel de la izquierda", "Aquí eliges qué ver, filtras y cambias cómo se ve el mapa. Está ordenado en pasos numerados."),
    ("matriz", "La matriz y su gráfica", "El resumen de todo: cuántas rutas hay en cada cuadrante y dónde cae cada una."),
    ("mapa", "El mapa", "Dónde está cada ruta y en qué cuadrante cae. Pasa el cursor sobre una zona para ver todo su detalle."),
    ("panel_variables", "Colorear con indicadores", "Si en el paso 3 eliges “Variables continuas”, aparecen estas opciones."),
    ("bivariado", "Ver 2 indicadores a la vez", "Con 2 indicadores en modo bivariado, el mapa y la gráfica usan una paleta de 9 colores."),
    ("exportar", "Descargar el mapa como imagen", "Para poner el mapa en una presentación, con título y buena calidad."),
    ("tabla", "Tabla por nivel", "Todos los datos en una tabla que puedes ordenar y descargar."),
    ("comparar", "Comparar escenarios", "Dos mapas lado a lado para ver qué rutas cambian de cuadrante entre dos escenarios."),
    ("glosario", "Glosario", "Qué significa cada indicador y cada palabra de la página."),
    ("daltonismo", "Modo daltonismo", "Así se ve la página con el modo daltonismo encendido (panel izquierdo → Accesibilidad)."),
]

# --------------------------------------------------------------------------- referencia de controles y FAQ
CONTROLES = [
    ("Arriba de la página", "Escenarios de carga de camión OP", "Conservador · Medio · Ambicioso", "Medio",
     "Qué tan exigente es la meta de cada ruta. Cambia la madurez."),
    ("Arriba de la página", "Casos de potencial", "Conservador · Medio · Ambicioso", "Conservador",
     "Qué tan optimista es el potencial de la zona. Cambia la atractividad."),
    ("Panel · Accesibilidad", "Modo daltonismo", "Encendido / apagado", "Apagado", "Colores para daltonismo, formas y etiquetas con el cuadrante."),
    ("Panel · Accesibilidad", "Texto más grande", "Encendido / apagado", "Apagado", "Letras más grandes."),
    ("Panel · Paso 1", "Colorear por", "Ruta · CeDi · Territorio · Región", "Ruta", "Qué se pinta en el mapa: cada ruta o grupos de rutas."),
    ("Panel · Paso 2", "Región", "Una o varias", "Todas", "Deja sólo esas regiones."),
    ("Panel · Paso 2", "Territorio", "Uno o varios (de las regiones elegidas)", "Todos", "Deja sólo esos territorios."),
    ("Panel · Paso 2", "CeDi", "Uno o varios (de los territorios elegidos)", "Todos", "Deja sólo esos CeDis."),
    ("Panel · Paso 2", "Ruta", "Una o varias (escribe para buscar)", "Todas", "Deja sólo esas rutas."),
    ("Panel · Paso 2", "Día de visita", "Lunes a sábado", "Todos", "Dibuja sólo la zona de esos días. No cambia los cuadrantes."),
    ("Panel · Paso 2", "Solo rutas activas", "Sí / no", "No", "Quita las rutas que no operan."),
    ("Panel · Paso 2", "Cuadrantes visibles en el mapa", "P1 · P2 · P3 · P4 · Sin datos", "Todos", "Esconde cuadrantes del mapa."),
    ("Panel · Paso 3", "Colorear con", "Cuadrante · Variables continuas", "Cuadrante", "Pintar por cuadrante o por un indicador."),
    ("Panel · Paso 3", "Variables (hasta 2)", "Indicadores del glosario", "El primero", "Qué indicador(es) pintar."),
    ("Panel · Paso 3", "Cómo verlas", "Un solo mapa o Bivariado · Mapas lado a lado", "Un solo mapa / Bivariado",
     "Un mapa, o un mapa por indicador."),
    ("Panel · Paso 3", "Agregar el mapa de cuadrantes (P)", "Encendido / apagado", "Encendido",
     "En lado a lado, pone primero el mapa de cuadrantes para compararlo con los indicadores."),
    ("Panel · Paso 3", "Colores", "Un color por variable · Semáforo", "Un color por variable", "Paleta de los indicadores."),
    ("Panel · Paso 3", "Comparar en percentiles", "Sí / no", "No", "Misma escala 0–100 para todos los indicadores."),
    ("Abajo del título del mapa", "Barras del detalle: comparar contra", "Lo que tengo filtrado · Todas las rutas",
     "Lo que tengo filtrado", "Contra qué se llenan las barras del detalle. No cambia los filtros."),
    ("Panel · Paso 4", "Mapa base", "Claro · Claro sin etiquetas · Calles · Oscuro", "Claro", "Fondo del mapa."),
    ("Panel · Paso 4", "Opacidad de polígonos", "0.2 a 1", "0.8", "Qué tan sólido se ve el color."),
    ("Panel · Paso 4", "Etiquetas con nombre", "Sí / no", "No en Ruta, sí en grupos", "Nombres sobre el mapa."),
    ("Panel · Paso 4", "Contorno oscuro de cada ruta", "Sí / no", "Sí", "Borde de toda la zona de la ruta (al acercarte)."),
    ("Panel · Paso 4", "Mini gráfica de perfil en el detalle", "Sí / no", "Sí", "Barras con los indicadores al pasar el cursor."),
    ("Panel · Paso 4", "Burbujas por grupo", "Sí / no", "Sí en Territorio y Región", "Círculo por grupo, más grande = más rutas."),
    ("Panel · Paso 4", "Vista del mapa", "Vista general · Centro Arca · Ajustar a los filtros", "Vista general", "A dónde lleva el botón Ir a esta vista."),
    ("Panel · Paso 4", "Ajuste de zoom", "−6 a +4", "0", "Acerca o aleja la vista elegida."),
    ("Panel · Paso 4", "Ir a esta vista", "Botón", "—", "Mueve el mapa a la vista elegida."),
    ("Panel · al final", "Restablecer todo", "Botón", "—", "Regresa todo a como estaba al abrir."),
]

FAQ = [
    ("El mapa está vacío o dice que no hay rutas",
     "Tienes demasiados filtros. Quita alguno (Región, Territorio, CeDi o “Solo rutas activas”) o pulsa <b>Restablecer todo</b>."),
    ("No encuentro mi ruta en el mapa",
     "Escribe su número en el filtro <b>Ruta</b> del panel izquierdo y pulsa <b>Ir a esta vista</b> con “Ajustar a los "
     "filtros”. Si aún no aparece, búscala en la pestaña <b>Rutas sin polígono</b>: ahí están las rutas sin zona dibujada."),
    ("El mapa se movió a otro lugar y no sé regresar",
     "En el panel izquierdo elige <b>Vista general</b> y pulsa <b>Ir a esta vista</b>."),
    ("Moví algo y ya no sé qué cambié", "Pulsa <b>Restablecer todo</b> al final del panel izquierdo."),
    ("La imagen descargada no muestra la zona que quería",
     "Mueve y acerca el mapa de arriba a la zona que quieres y vuelve a pulsar <b>Generar imagen</b>: sale con la "
     "misma zona y el mismo acercamiento."),
    ("No distingo bien los colores", "Abre <b>Accesibilidad</b> en el panel izquierdo y enciende <b>Modo daltonismo</b>."),
    ("No entiendo qué significa un indicador", "Abre la pestaña <b>Glosario</b> y escribe su nombre en el buscador."),
    ("Quiero una imagen para una presentación",
     "Abre <b>Descargar el mapa como imagen</b> abajo del mapa, escribe el título, pulsa <b>Generar imagen</b> y luego <b>Descargar imagen</b>."),
    ("Quiero los datos en Excel", "Cada tabla tiene un botón <b>Descargar … (Excel)</b> abajo."),
    ("¿Por qué una ruta tiene varias estrategias?",
     "Porque pasa por todas las preguntas de su cuadrante y recibe la estrategia de cada respuesta que tenga una. "
     "Aparecen en el mismo orden que las preguntas del árbol."),
    ("¿Cómo se decide la estrategia de cada ruta?",
     "Con el árbol de decisión explicado en el paso <b>Cómo se deciden las estrategias</b> de este manual. En la "
     "herramienta, al pasar el cursor sobre una ruta en el mapa, cada estrategia dice su <b>porqué</b> con el valor de "
     "la ruta; también están en la pestaña <b>Tabla por Ruta</b>."),
    ("Las zonas se ven todas negras", "Estás muy lejos con el contorno encendido: acércate con la rueda del mouse o apaga <b>Contorno oscuro de cada ruta</b>."),
]


# --------------------------------------------------------------------------- armado
def img64(nombre):
    with open(os.path.join(TOUR, nombre), "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()


def paso_html(n, clave, titulo, intro):
    e = escenas[clave]
    puntos = [(k, v) for k, v in e["puntos"].items() if k in PUNTOS]
    # ordenar de arriba hacia abajo y de izquierda a derecha para numerar en orden de lectura
    puntos.sort(key=lambda kv: (round(kv[1]["y"] * 40), kv[1]["x"]))
    marcas, items = [], []
    for i, (k, r) in enumerate(puntos, start=1):
        t, texto = PUNTOS[k]
        grande = r["w"] * r["h"] > 0.15      # elementos grandes (mapas, gráficas): el número va en su centro
        cx = min(max((r["x"] + (r["w"] / 2 if grande else 0)) * 100, 0.8), 97)
        cy = min(max((r["y"] + (r["h"] * 0.55 if grande else 0)) * 100, 0.4), 98)
        marcas.append(
            f"<div class='zona' data-p='{n}-{i}' style='left:{r['x']*100:.2f}%;top:{r['y']*100:.2f}%;"
            f"width:{r['w']*100:.2f}%;height:{r['h']*100:.2f}%'></div>"
            f"<button class='punto' data-p='{n}-{i}' style='left:{cx:.2f}%;top:{cy:.2f}%' aria-label='{html.escape(t)}'>"
            f"{i}<span class='burbuja'><b>{html.escape(t)}</b><br>{texto}</span></button>")
        items.append(f"<li data-p='{n}-{i}'><span class='num'>{i}</span><div><b>{html.escape(t)}</b><br>{texto}</div></li>")
    angosta = e["ancho"] < 500
    return f"""
<section class="paso" id="paso-{n}" data-n="{n}">
  <div class="paso-cab"><span class="paso-num">{n}</span><div><h2>{html.escape(titulo)}</h2><p class="intro">{intro}</p></div></div>
  <p class="instr">Pasa el cursor sobre los <span class="mini">1</span> círculos numerados de la imagen (o sobre la lista) para ver qué es cada parte.</p>
  <div class="cuerpo {'angosta' if angosta else ''}">
    <div class="captura"><div class="lienzo"><img src="{img64(e['imagen'])}" alt="{html.escape(titulo)}">{''.join(marcas)}</div></div>
    <ol class="lista">{''.join(items)}</ol>
  </div>
</section>"""


cuadrantes_html = "".join(
    f"<div class='cuad' style='background:{C.PALETAS_MATRIZ['Normal'][p]['color']};border-color:{C.PALETAS_MATRIZ['Normal'][p]['borde']}'>"
    f"<div class='cuad-p'>{C.SIMBOLOS_TEXTO[p]} {p}</div><div class='cuad-n'>{C.PALETAS_MATRIZ['Normal'][p]['nombre']}</div>"
    f"<div class='cuad-t'>{t}</div></div>"
    for p, t in [("P2", "Opera bien · zona con poco potencial<br><b>Cuidar lo que funciona</b>"),
                 ("P1", "Opera bien · zona con potencial<br><b>Crecer</b>"),
                 ("P4", "Opera mal · zona con poco potencial<br><b>Decidir qué hacer</b>"),
                 ("P3", "Opera mal · zona con potencial<br><b>Mejorar cómo opera</b>")])

bienvenida = f"""
<section class="paso" id="paso-0" data-n="0">
  <div class="paso-cab"><span class="paso-num">0</span><div><h2>Antes de empezar: ¿para qué sirve?</h2>
  <p class="intro">Esta herramienta acomoda cada ruta en una <b>matriz de 4 cuadrantes</b> y te dice <b>qué hacer con ella</b>.</p></div></div>
  <div class="dos">
    <div>
      <h3>Se mide cada ruta con 2 preguntas</h3>
      <div class="eje"><span class="chip" style="background:#68C9CD;color:#000">Madurez</span> ¿Qué tan bien <b>opera</b> la ruta hoy? (arriba = mejor)</div>
      <div class="eje"><span class="chip" style="background:#E5803D;color:#000">Atractividad</span> ¿Qué tanto <b>potencial</b> tiene su zona? (derecha = más)</div>
      <p>La línea que divide la matriz es el valor “de en medio” (la mediana): la mitad de las rutas queda de cada lado.</p>
      <h3>Lo que vas a poder hacer</h3>
      <ul class="check">
        <li>Ver en un mapa dónde está cada ruta y en qué cuadrante cae.</li>
        <li>Saber qué estrategia seguir con cada ruta.</li>
        <li>Comparar dos escenarios lado a lado.</li>
        <li>Descargar imágenes y tablas en Excel.</li>
      </ul>
    </div>
    <div>
      <div class="matriz-demo"><div class="eje-y">Madurez ↑</div><div class="rejilla">{cuadrantes_html}</div></div>
      <div class="eje-x">Atractividad →</div>
    </div>
  </div>
  <div class="consejo"><b>Regla de oro:</b> en la página, todo lo que tenga un círculo <span class="q">?</span> se explica solo:
  pasa el cursor encima. Y si algo sale mal, el botón <b>Restablecer todo</b> (abajo del panel izquierdo) regresa todo a como estaba.</div>
</section>"""

controles_html = "".join(
    f"<tr><td>{html.escape(a)}</td><td><b>{html.escape(b)}</b></td><td>{html.escape(c)}</td><td>{html.escape(d)}</td><td>{html.escape(e)}</td></tr>"
    for a, b, c, d, e in CONTROLES)
faq_html = "".join(f"<details><summary>{html.escape(q)}</summary><p>{a}</p></details>" for q, a in FAQ)
def arbol_completo_html(n: int) -> str:
    """Sección del manual con el árbol completo: diagrama (con los conteos del escenario base) y, por cuadrante,
    cada pregunta con los datos con que se contesta y la estrategia de cada respuesta."""
    import pandas as pd
    from mapa import datos, estrategia as E, modelo
    ins = modelo.leer_libro(C.EXCEL_ANALISIS)
    esc, caso = C.ESCENARIO_DEFAULT, next(c for c in ins.casos_atractividad if ins.caso_disponible(c))
    df, res = modelo.calcular(ins, esc, caso)
    b = datos.aplicar_clasificacion(datos.preparar_resultados(df), res["corte_atractividad"], res["corte_madurez"],
                                    usar_p_excel=True)
    b[E.COL_SINCOB] = b[C.COL_RUTA].map(datos.area_sin_cobertura(
        datos.cargar_geometrias(("Convencional", "Web")), E.RADIO_SIN_COBERTURA_KM,
        cobertura=datos.cargar_geometrias(("Convencional",))))
    ct = E.cortes(b, res["corte_madurez"])
    ev = E.evaluar(b, ct)
    conteo = {r.clave: int(ev[r.clave].sum()) for r in E.REGLAS}
    rutas_p = b["P"].value_counts().to_dict()
    nombre = f"Carga OP {esc} · Potencial {C.NOMBRES_POTENCIAL.get(caso, caso)}"

    bloques = []
    for p in E.CUADRANTES + ["S"]:
        if p == "S":
            filas = "".join(
                f"<tr><td>{k}</td><td>{html.escape(preg.replace(chr(10), ' '))}</td><td>—</td>"
                f"<td>{'—'}</td><td><b>No →</b> {html.escape(r.estrategia)}<br><small>{html.escape(r.explicacion)}</small>"
                f"<br><span class='cnt'>{conteo.get(r.clave, 0):,} rutas</span></td></tr>"
                for k, (preg, r) in enumerate(zip(E.PREGUNTAS_SIN_CUADRANTE, E.reglas_de("S")), start=1))
            ultima = E.reglas_de("S")[-1]
            filas += (f"<tr><td>{len(E.PREGUNTAS_SIN_CUADRANTE) + 1}</td><td>Si respondió Sí a todo lo anterior</td>"
                      f"<td>—</td><td>—</td><td>{html.escape(ultima.estrategia)}<br><small>{html.escape(ultima.explicacion)}"
                      f"</small><br><span class='cnt'>{conteo.get(ultima.clave, 0):,} rutas</span></td></tr>")
            titulo, desc = "Rutas sin cuadrante", ("Rutas que no se pueden ubicar en la matriz. Reciben una sola acción: "
                                                   "la de la primera pregunta que contestan con No.")
        else:
            cat = C.PALETAS_MATRIZ["Normal"][p]
            filas = ""
            for k, (_t, clave) in enumerate(E.FLUJO[p], start=1):
                q = E.PREGUNTAS[clave]

                def celda(resp):
                    rs = E.reglas_de_pregunta(clave, resp)
                    if not rs:
                        return "<span class='nada'>Sin estrategia: sigue a la siguiente pregunta</span>"
                    return "<br>".join(f"<b>{html.escape(r.estrategia)}</b><br><small>{html.escape(r.explicacion)}</small>"
                                       f"<br><span class='cnt'>{conteo.get(r.clave, 0):,} rutas</span>" for r in rs)
                filas += (f"<tr><td>{k}</td><td><b>{html.escape(q.texto.replace(chr(10), ' '))}</b></td>"
                          f"<td>{html.escape(q.como)}</td><td>{celda('Sí')}</td><td>{celda('No')}</td></tr>")
            titulo = f"{p} · {cat['nombre']}"
            desc = (f"{E.EJES_P[p]}. {rutas_p.get(p, 0):,} rutas. Cada ruta contesta todas las preguntas, en orden; "
                    "por cada respuesta que tenga estrategia, la recibe (puede recibir varias).")
        svg = E.diagrama_svg(conteo, "Sin cuadrante" if p == "S" else p, rutas_p)
        bloques.append(f"""
  <div class="cuad-arbol">
    <h3>{html.escape(titulo)}</h3><p>{desc}</p>
    <div class="arbol-dos"><div class="svg-caja">{svg}</div>
    <div class="tabla-wrap"><table><thead><tr><th>#</th><th>Pregunta</th><th>Cómo se contesta (datos)</th>
    <th>Si la respuesta es Sí</th><th>Si la respuesta es No</th></tr></thead><tbody>{filas}</tbody></table></div></div>
  </div>""")

    completo = E.diagrama_svg(conteo, "Todo", rutas_p)
    return f"""
<section class="paso" id="paso-{n}" data-n="{n}">
  <div class="paso-cab"><span class="paso-num">{n}</span><div><h2>Cómo se deciden las estrategias</h2>
  <p class="intro">Las estrategias que ves en el detalle del mapa (y en la pestaña <b>Tabla por Ruta</b>) salen de este
  árbol de decisión: todas las preguntas, cómo se contesta cada una con los datos de la ruta y qué estrategia recibe la
  ruta con cada respuesta. Los números de rutas son del escenario base ({html.escape(nombre)}); en la herramienta
  cambian con los escenarios y filtros que elijas.</p></div></div>
  <h3>Cómo se lee</h3>
  <ul class="check">
    <li>Primero se revisa si la ruta tiene <b>madurez y atractividad</b>. Si sí, cae en su cuadrante (P1 a P4); si no, va a <b>Sin cuadrante</b>.</li>
    <li>Dentro de su cuadrante la ruta contesta <b>todas</b> las preguntas, de arriba hacia abajo.</li>
    <li>Si la respuesta (Sí o No) tiene una <b>caja de color</b> al lado o abajo, la ruta recibe esa estrategia.</li>
    <li>Después sigue a la siguiente pregunta, conteste Sí o No (flecha “Sí o No”). Por eso una ruta puede tener <b>varias estrategias</b>.</li>
    <li>Ninguna estrategia se da “a todas”: todas dependen de una respuesta.</li>
    <li>Si a una ruta le falta un dato para contestar una pregunta, esa pregunta se salta.</li>
  </ul>
  <h3>El árbol completo</h3>
  <p class="nota">Desliza hacia los lados para ver todo el diagrama.</p>
  <div class="svg-grande">{completo}</div>
  <h3>Valores de corte (escenario base)</h3>
  <p class="nota">{html.escape(E.resumen_cortes(ct))}. Zonas sin cobertura buscadas a {E.RADIO_SIN_COBERTURA_KM:g} km de la
  ruta.</p>
  <h3>Cuadrante por cuadrante</h3>
  {''.join(bloques)}
</section>"""


glosario_html = "".join(
    f"<tr><td><b>{html.escape(v)}</b></td><td>{html.escape(q)}</td><td>{html.escape(l)}</td></tr>"
    for v, (q, _c, l) in C.GLOSARIO_VARIABLES.items())
conceptos_html = "".join(f"<tr><td><b>{html.escape(k)}</b></td><td>{html.escape(v)}</td></tr>"
                         for k, v in C.GLOSARIO_CONCEPTOS.items())

n_ref = len(PASOS) + 2      # + la sección completa del árbol
n_arbol = len(PASOS) + 1
referencia = arbol_completo_html(n_arbol) + f"""
<section class="paso" id="paso-{n_ref}" data-n="{n_ref}">
  <div class="paso-cab"><span class="paso-num">{n_ref}</span><div><h2>Todos los controles y filtros</h2>
  <p class="intro">La lista completa de lo que puedes mover, qué opciones tiene, con qué empieza y qué hace.</p></div></div>
  <div class="tabla-wrap"><table><thead><tr><th>Dónde está</th><th>Control</th><th>Opciones</th><th>Al abrir</th><th>Qué hace</th></tr></thead>
  <tbody>{controles_html}</tbody></table></div>
</section>
<section class="paso" id="paso-{n_ref + 1}" data-n="{n_ref + 1}">
  <div class="paso-cab"><span class="paso-num">{n_ref + 1}</span><div><h2>¿Qué hago si…?</h2>
  <p class="intro">Haz clic en una pregunta para ver la respuesta.</p></div></div>
  <div class="faq">{faq_html}</div>
</section>
<section class="paso" id="paso-{n_ref + 2}" data-n="{n_ref + 2}">
  <div class="paso-cab"><span class="paso-num">{n_ref + 2}</span><div><h2>Glosario</h2>
  <p class="intro">Qué significa cada indicador y cada palabra. (También está dentro de la herramienta, en la pestaña <b>Glosario</b>.)</p></div></div>
  <div class="tabla-wrap"><table><thead><tr><th>Indicador</th><th>Qué mide</th><th>Cómo leerlo</th></tr></thead><tbody>{glosario_html}</tbody></table></div>
  <div class="tabla-wrap" style="margin-top:18px"><table><thead><tr><th>Concepto</th><th>Qué significa</th></tr></thead><tbody>{conceptos_html}</tbody></table></div>
</section>"""

indice = [(0, "Antes de empezar")] + [(i, t) for i, (_, t, _) in enumerate(PASOS, start=1)] + [
    (n_arbol, "Cómo se deciden las estrategias"), (n_ref, "Todos los controles"), (n_ref + 1, "¿Qué hago si…?"), (n_ref + 2, "Glosario")]
nav_html = "".join(f"<li><a href='#paso-{n}' data-n='{n}'><span>{n}</span>{html.escape(t)}</a></li>" for n, t in indice)
pasos_html = bienvenida + "".join(paso_html(i, c, t, intro) for i, (c, t, intro) in enumerate(PASOS, start=1)) + referencia
total = n_ref + 2

PLANTILLA = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manual de uso · Mapa de rutas</title>
<link href="https://fonts.googleapis.com/css2?family=Raleway:ital,wght@0,400;0,600;0,700;0,800;1,400&display=swap" rel="stylesheet">
<style>
:root{--negro:#000000;--rojo:#F30000;--gris-os:#5E5E5E;--gris-cl:#D5D5D5;--naranja:#E5803D;--ambar:#F79802;--oro:#D7B75A;--verde:#69CE7E;--turquesa:#68C9CD;--rojo-suave:#FFECEC;--gris:#F4F4F4;--texto:#000;--suave:#5E5E5E;
  --p1:#A5E2B2;--p2:#FED697;--p3:#FF9966;--p4:#FF9494;}
*{box-sizing:border-box}
body{margin:0;font-family:Raleway,Arial,sans-serif;color:var(--texto);background:var(--gris);font-size:17px;line-height:1.5}
header{background:var(--negro);color:#fff;padding:18px 28px;display:flex;align-items:center;gap:18px;position:sticky;top:0;z-index:50;
  box-shadow:0 2px 8px rgba(0,0,0,.2)}
header h1{margin:0;font-size:1.45rem;font-weight:800}
header .sub{opacity:.85;font-size:.95rem}
.barra-prog{position:absolute;left:0;bottom:0;height:5px;background:var(--rojo);transition:width .3s}
.marca{display:flex;gap:4px}.marca i{width:12px;height:12px;display:block}
.cont{display:flex;max-width:1500px;margin:0 auto}
nav{width:270px;flex-shrink:0;padding:20px 12px;position:sticky;top:78px;height:calc(100vh - 78px);overflow:auto}
nav h3{font-size:.8rem;text-transform:uppercase;letter-spacing:.08em;color:var(--suave);margin:4px 10px 10px}
nav ol{list-style:none;margin:0;padding:0}
nav a{display:flex;gap:10px;align-items:center;padding:8px 10px;border-radius:8px;color:var(--texto);text-decoration:none;font-weight:600}
nav a span{background:#fff;border:2px solid var(--rojo);color:var(--rojo);width:28px;height:28px;border-radius:50%;
  display:inline-flex;align-items:center;justify-content:center;font-size:.85rem;flex-shrink:0}
nav a:hover{background:var(--rojo-suave)}
nav a.activo{background:var(--rojo);color:#fff}nav a.activo span{background:#fff;color:var(--rojo);border-color:#fff}
main{flex:1;padding:20px 28px 60px;min-width:0}
.paso{background:#fff;border-radius:14px;padding:26px 28px;margin-bottom:26px;box-shadow:0 1px 4px rgba(0,0,0,.08);scroll-margin-top:95px}
.paso-cab{display:flex;gap:16px;align-items:flex-start}
.paso-num{background:var(--rojo);color:#fff;width:46px;height:46px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-weight:800;font-size:1.3rem;flex-shrink:0}
h2{margin:2px 0 4px;color:var(--negro);font-size:1.6rem}
h3{color:var(--negro);margin:18px 0 8px}
.intro{margin:0;color:var(--suave);font-size:1.05rem}
.instr{background:var(--rojo-suave);border-left:5px solid var(--rojo);padding:10px 14px;border-radius:6px;margin:16px 0}
.mini,.q{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;background:var(--rojo);
  color:#fff;font-weight:800;font-size:.8rem;vertical-align:middle}
.q{background:#fff;color:var(--suave);border:1.5px solid var(--suave)}
.cuerpo{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:22px;align-items:start}
.cuerpo.angosta{grid-template-columns:340px minmax(0,1fr)}
.captura{border:1px solid #DDD;border-radius:10px;overflow:auto;max-height:78vh;background:#fff}
.lienzo{position:relative}
.lienzo img{display:block;width:100%;height:auto}
.zona{position:absolute;border:3px dashed var(--rojo);border-radius:6px;background:rgba(243,0,0,.08);opacity:0;pointer-events:none;
  transition:opacity .15s}
.zona.on{opacity:1}
.punto{position:absolute;transform:translate(-40%,-40%);width:30px;height:30px;border-radius:50%;border:3px solid #fff;background:var(--rojo);
  color:#fff;font:800 14px Raleway,Arial;cursor:help;box-shadow:0 2px 6px rgba(0,0,0,.35);z-index:5;padding:0;
  animation:latido 2.4s infinite}
.punto:hover,.punto.on{background:var(--negro);z-index:20;animation:none}
@keyframes latido{0%,100%{box-shadow:0 0 0 0 rgba(243,0,0,.55),0 2px 6px rgba(0,0,0,.35)}50%{box-shadow:0 0 0 9px rgba(243,0,0,0),0 2px 6px rgba(0,0,0,.35)}}
.burbuja{display:none;position:absolute;left:34px;top:-6px;width:290px;background:var(--negro);color:#fff;border-left:5px solid var(--rojo);text-align:left;font:400 14.5px/1.45 Raleway,Arial;
  padding:12px 14px;border-radius:10px;box-shadow:0 6px 18px rgba(0,0,0,.3)}
.burbuja b{font-weight:800;color:#fff}
.punto:hover .burbuja,.punto.on .burbuja{display:block}
.punto.izq .burbuja{left:auto;right:34px}
.lista{list-style:none;margin:0;padding:0;max-height:78vh;overflow:auto}
.lista li{display:flex;gap:10px;padding:10px 12px;border-radius:10px;border:1px solid transparent;cursor:default}
.lista li:hover,.lista li.on{background:var(--rojo-suave);border-color:#F7A1A1}
.lista .num{background:var(--rojo);color:#fff;border-radius:50%;width:28px;height:28px;display:inline-flex;align-items:center;justify-content:center;
  font-weight:800;flex-shrink:0}
.dos{display:grid;grid-template-columns:1fr 1fr;gap:30px;margin-top:10px}
.eje{margin:8px 0}.chip{color:#fff;border-radius:20px;padding:3px 12px;font-weight:700;margin-right:6px}
.check{padding-left:0;list-style:none}.check li{padding-left:28px;position:relative;margin:6px 0}
.check li:before{content:"✓";position:absolute;left:4px;color:var(--rojo);font-weight:800}
.matriz-demo{display:flex;gap:8px}.eje-y{writing-mode:vertical-rl;transform:rotate(180deg);font-weight:800;color:var(--turquesa);text-align:center}
.rejilla{display:grid;grid-template-columns:1fr 1fr;gap:8px;flex:1}
.cuad{border:3px solid;border-radius:8px;padding:14px;text-align:center}
.cuad-p{font-weight:800;font-size:1.2rem}.cuad-n{font-weight:700}.cuad-t{font-size:.92rem;margin-top:4px}
.eje-x{text-align:center;font-weight:800;color:var(--naranja);margin:6px 0 0 30px}
.consejo{margin-top:22px;background:var(--gris);border-left:5px solid var(--rojo);padding:12px 16px;border-radius:6px}
.tabla-wrap{overflow:auto;margin-top:14px}
table{border-collapse:collapse;width:100%;font-size:.95rem}
th{background:var(--negro);color:#fff;text-align:left;padding:10px;position:sticky;top:0}
td{padding:9px 10px;border-bottom:1px solid #E5E5E5;vertical-align:top}
tr:nth-child(even) td{background:#FAFAFA}
.svg-grande{overflow:auto;border:1px solid #DDD;border-radius:10px;background:#fff;max-height:80vh}
.svg-grande svg{display:block}
.cuad-arbol{border-top:3px solid var(--gris-cl);padding-top:10px;margin-top:22px}
.arbol-dos{display:grid;grid-template-columns:minmax(0,560px) minmax(0,1fr);gap:18px;align-items:start}
.svg-caja{border:1px solid #DDD;border-radius:10px;overflow:auto;max-height:80vh;background:#fff}
.svg-caja svg{width:100%;height:auto;display:block}
.cnt{display:inline-block;margin-top:3px;background:var(--rojo-suave);color:var(--rojo);border-radius:10px;padding:1px 8px;
  font-weight:700;font-size:.85rem}
.nada{color:var(--suave);font-style:italic}
.nota{color:var(--suave)}
@media (max-width:1300px){.arbol-dos{grid-template-columns:1fr}}
.faq details{border:1px solid #DDD;border-radius:10px;margin:10px 0;padding:0 16px;background:#fff}
.faq summary{cursor:pointer;padding:14px 0;font-weight:700;color:var(--negro);font-size:1.05rem}
.faq details[open]{border-color:var(--rojo);box-shadow:0 1px 6px rgba(243,0,0,.18)}
.nav-pasos{display:flex;justify-content:space-between;margin-top:18px}
.btn{background:var(--rojo);color:#fff;border:0;border-radius:8px;padding:10px 18px;font:700 15px Raleway,Arial;cursor:pointer;text-decoration:none}
.btn.sec{background:#fff;color:var(--rojo);border:2px solid var(--rojo)}
.acc{margin-left:auto;display:flex;gap:8px}
.acc button{background:transparent;color:#fff;border:2px solid rgba(255,255,255,.6);border-radius:8px;padding:6px 10px;font:700 13px Raleway,Arial;cursor:pointer}
body.grande{font-size:20px}
@media (max-width:1100px){.cuerpo,.cuerpo.angosta,.dos{grid-template-columns:1fr}nav{display:none}}
@media print{header,nav,.instr,.punto{display:none}.paso{break-inside:avoid;box-shadow:none}}
</style></head>
<body>
<header>
  <div class="marca"><i style="background:#F30000"></i><i style="background:#E5803D"></i><i style="background:#F79802"></i><i style="background:#D7B75A"></i><i style="background:#69CE7E"></i><i style="background:#68C9CD"></i></div>
  <div><h1>Manual de uso · Mapa de rutas</h1><div class="sub">Matriz Atractividad × Madurez · guía paso a paso</div></div>
  <div class="acc"><button id="bt-grande" title="Hacer las letras más grandes">A+ Texto grande</button>
  <button onclick="window.print()" title="Imprimir o guardar como PDF">Imprimir</button></div>
  <div class="barra-prog" id="prog"></div>
</header>
<div class="cont">
  <nav><h3>Recorrido (__TOTAL__ pasos)</h3><ol>__NAV__</ol></nav>
  <main>__PASOS__
    <div class="nav-pasos"><a class="btn sec" href="#paso-0">Volver al inicio</a></div>
  </main>
</div>
<script>
// Enlazar punto ↔ zona ↔ elemento de la lista
document.querySelectorAll('[data-p]').forEach(el => {
  const id = el.dataset.p;
  const todos = () => document.querySelectorAll(`[data-p="${id}"]`);
  el.addEventListener('mouseenter', () => todos().forEach(x => x.classList.add('on')));
  el.addEventListener('mouseleave', () => todos().forEach(x => x.classList.remove('on')));
  if (el.tagName === 'LI') el.addEventListener('mouseenter', () => {
    const p = document.querySelector(`.punto[data-p="${id}"]`); const cap = p && p.closest('.captura');
    if (cap) { const r = p.getBoundingClientRect(), c = cap.getBoundingClientRect();
      if (r.top < c.top || r.bottom > c.bottom) cap.scrollTo({top: p.offsetTop - cap.clientHeight / 2, behavior: 'smooth'}); }
  });
});
// Burbujas cerca del borde derecho se abren hacia la izquierda
function acomodar(){ document.querySelectorAll('.punto').forEach(p => p.classList.toggle('izq', parseFloat(p.style.left) > 55)); }
acomodar();
// Paso actual en el índice y barra de avance
const secciones = [...document.querySelectorAll('section.paso')];
const enlaces = [...document.querySelectorAll('nav a')];
const obs = new IntersectionObserver(ents => ents.forEach(e => { if (e.isIntersecting) {
  const n = e.target.dataset.n; enlaces.forEach(a => a.classList.toggle('activo', a.dataset.n === n));
  document.getElementById('prog').style.width = (100 * (+n + 1) / secciones.length) + '%'; } }), {rootMargin: '-40% 0px -55% 0px'});
secciones.forEach(s => obs.observe(s));
// Flechas del teclado: paso anterior / siguiente
document.addEventListener('keydown', e => {
  if (!['ArrowRight', 'ArrowLeft'].includes(e.key)) return;
  const act = enlaces.findIndex(a => a.classList.contains('activo'));
  const sig = Math.min(Math.max(act + (e.key === 'ArrowRight' ? 1 : -1), 0), enlaces.length - 1);
  secciones[sig].scrollIntoView({behavior: 'smooth'});
});
document.getElementById('bt-grande').onclick = () => document.body.classList.toggle('grande');
</script>
</body></html>"""

salida = (PLANTILLA.replace("__NAV__", nav_html).replace("__PASOS__", pasos_html).replace("__TOTAL__", str(total + 1)))
os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
with open(SALIDA, "w", encoding="utf-8") as f:
    f.write(salida)
sin_texto = sorted({k for e in escenas.values() for k in e["puntos"] if k not in PUNTOS})
print("manual:", SALIDA, f"{os.path.getsize(SALIDA) / 1e6:.1f} MB", "· puntos sin texto:", sin_texto)
