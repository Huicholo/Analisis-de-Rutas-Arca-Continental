"""Recorre la app en Chrome sin ventana, toma las capturas del manual y ubica cada control (puntos del tour).
Salida: tour/escenas.json + tour/*.jpg"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import Navegador  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tour")
URL = "http://localhost:8599/"
ANCHO, ALTO = 1440, 7000

AYUDANTES = r"""
window.__el = (sel, texto, exacto) => {
  const els = [...document.querySelectorAll(sel)];
  const t = (e) => (e.innerText || e.textContent || e.getAttribute('aria-label') || '').trim();
  return els.find(e => exacto ? t(e) === texto : t(e).includes(texto)) || null;
};
window.__rect = (e) => { if (!e) return null; const r = e.getBoundingClientRect();
  return r.width ? {x: r.x, y: r.y, w: r.width, h: r.height} : null; };
window.__widget = (etiqueta) => {   // contenedor del control cuya etiqueta empieza con `etiqueta`
  const lab = [...document.querySelectorAll('[data-testid="stWidgetLabel"]')]
    .find(l => l.innerText.trim().startsWith(etiqueta));
  if (!lab) return null;
  return lab.closest('[data-testid="stElementContainer"], .stElementContainer, .element-container') || lab.parentElement;
};
window.__click = (sel, texto, exacto) => { const e = __el(sel, texto, exacto); if (e) e.click(); return !!e; };
true;
"""


class Tour:
    def __init__(self, nav):
        self.nav = nav
        self.escenas = []

    async def esperar(self, s=10):
        # espera a que Streamlit termine de correr (sin el indicador de "Running")
        await asyncio.sleep(2)
        for _ in range(int(s * 2)):
            corriendo = await self.nav.js(
                "!!document.querySelector('[data-testid=\"stStatusWidget\"]') && "
                "document.querySelector('[data-testid=\"stStatusWidget\"]').innerText.includes('Running')")
            if not corriendo:
                break
            await asyncio.sleep(0.5)
        await asyncio.sleep(s / 2)
        await self.nav.js(AYUDANTES)

    async def rects(self, puntos: dict) -> dict:
        """puntos: clave -> expresión JS que devuelve un elemento."""
        cuerpo = ",".join(f"{json.dumps(k)}: __rect({v})" for k, v in puntos.items())
        return await self.nav.js(f"({{{cuerpo}}})")

    async def escena(self, clave, titulo, recorte, puntos: dict):
        """recorte: (x, y, w, h) o expresión JS que devuelve {x,y,w,h}."""
        if isinstance(recorte, str):
            r = await self.nav.js(recorte)
            recorte = (r["x"], r["y"], r["w"], r["h"])
        x, y, w, h = [round(v) for v in recorte]
        ubicados = await self.rects(puntos)
        faltan = [k for k, v in ubicados.items() if not v]
        if faltan:
            print(f"  [{clave}] sin ubicar: {faltan}")
        hot = {k: {"x": (v["x"] - x) / w, "y": (v["y"] - y) / h, "w": v["w"] / w, "h": v["h"] / h}
               for k, v in ubicados.items() if v}
        ruta = os.path.join(OUT, f"{clave}.jpg")
        await self.nav.captura(ruta, x, y, w, h, 80)
        self.escenas.append({"clave": clave, "titulo": titulo, "imagen": f"{clave}.jpg", "ancho": w, "alto": h,
                             "puntos": hot})
        print(f"  escena {clave}: {w}x{h}, {len(hot)} puntos")


def W(etiqueta):
    return f"__widget({json.dumps(etiqueta)})"


def E(sel, texto, exacto=False):
    return f"__el({json.dumps(sel)}, {json.dumps(texto)}, {str(exacto).lower()})"


def H4(texto):
    return E("h4", texto)


RECT_MAIN = "(() => { const b = document.querySelector('[data-testid=\"stMainBlockContainer\"]').getBoundingClientRect(); return b; })()"


def entre(desde, hasta, margen=12):
    """Recorte del área principal desde el título `desde` hasta el título `hasta` (h4)."""
    return f"""(() => {{
      const m = document.querySelector('[data-testid="stMainBlockContainer"]').getBoundingClientRect();
      const a = {desde}.getBoundingClientRect(); const b = {hasta}.getBoundingClientRect();
      return {{x: m.x, y: a.y - {margen}, w: m.width, h: b.y - a.y}};
    }})()"""


async def main():
    os.makedirs(OUT, exist_ok=True)
    nav = Navegador()
    await nav.conectar()
    await nav.tamano(ANCHO, ALTO)
    await nav.ir(URL)
    # espera a que aparezca la página completa (la primera carga calcula el modelo y las zonas)
    for _ in range(120):
        await asyncio.sleep(1)
        if await nav.js("!!document.querySelector('h4') && document.querySelectorAll('.js-plotly-plot').length > 1"):
            break
    await asyncio.sleep(8)
    t = Tour(nav)
    await t.esperar(6)

    # ---------------------------------------------------------------- 1. inicio
    await t.escena("inicio", "La parte de arriba", entre(E("h1", "Mapa de rutas"), H4("Matriz de cuadrantes"), 20), {
        "titulo": E("h1", "Mapa de rutas"),
        "primera_vez": E("[data-testid='stExpander'] summary", "¿Primera vez aquí?"),
        "escenario": W("Escenarios de carga de camión OP"),
        "caso": W("Casos de potencial"),
    })

    # ---------------------------------------------------------------- 2. panel izquierdo (todo abierto)
    await nav.js("__click('[data-testid=\"stSidebar\"] summary', 'Accesibilidad')")
    await nav.js("__click('[data-testid=\"stSidebar\"] summary', 'Libro de análisis')")
    await t.esperar(3)
    panel = """(() => { const s = document.querySelector('[data-testid="stSidebarUserContent"]');
      const b = [...s.querySelectorAll('button')].find(x => x.innerText.trim() === 'Restablecer todo').getBoundingClientRect();
      return {x: 0, y: 0, w: 300, h: b.bottom + 24}; })()"""
    await t.escena("panel", "El panel de la izquierda", panel, {
        "manual": E("[data-testid='stSidebar'] a, [data-testid='stSidebar'] button", "Abrir el manual"),
        "accesibilidad": E("[data-testid='stSidebar'] summary", "Accesibilidad"),
        "daltonismo": W("Modo daltonismo"),
        "texto_grande": W("Texto más grande"),
        "libro": E("[data-testid='stSidebar'] summary", "Libro de análisis"),
        "colorear_por": W("Colorear por"),
        "region": W("Región"), "territorio": W("Territorio"), "cedi": W("CeDi"), "ruta": W("Ruta"),
        "dias": W("Día de visita"), "activas": W("Solo rutas activas"),
        "cuadrantes": W("Cuadrantes visibles"),
        "colorear_con": E("[data-testid='stSidebar'] [data-testid='stRadio']", "Cuadrante de la matriz"),
        "mapa_base": W("Mapa base"), "opacidad": W("Opacidad"), "etiquetas": W("Etiquetas con nombre"),
        "contorno": W("Contorno oscuro"), "perfil": W("Mini gráfica"), "burbujas": W("Burbujas por grupo"),
        "vista": W("Vista del mapa"), "ajuste_zoom": W("Ajuste de zoom"),
        "ir_vista": E("[data-testid='stSidebar'] button", "Ir a esta vista", True),
        "restablecer": E("[data-testid='stSidebar'] button", "Restablecer todo", True),
    })
    await nav.js("__click('[data-testid=\"stSidebar\"] summary', 'Libro de análisis')")

    # ---------------------------------------------------------------- 3. matriz y gráfica
    await t.escena("matriz", "La matriz y su gráfica", entre(H4("Matriz de cuadrantes"), H4("Mapa")), {
        "matriz": "document.querySelector('.mz-wrap')",
        "p1": E(".mz-cell", "Ampliar cobertura"), "p2": E(".mz-cell", "Mantener"),
        "p3": E(".mz-cell", "Desarrollar"), "p4": E(".mz-cell", "Evaluar"),
        "metricas": "document.querySelector('[data-testid=\"stMetric\"]').closest('[data-testid=\"stHorizontalBlock\"]')",
        "dispersion": "document.querySelectorAll('.js-plotly-plot')[0]",
        "herramientas": "document.querySelectorAll('.js-plotly-plot')[0].querySelector('.modebar')",
        "ayuda": "document.querySelector('h4 [data-testid=\"stTooltipIcon\"], h4 svg')",
    })

    # ---------------------------------------------------------------- 4. mapa con detalle abierto
    await nav.js("""(() => { const g = [...document.querySelectorAll('.js-plotly-plot')].find(g => String(g.layout?.uirevision).startsWith('mapa|'));
      const m = g._fullLayout.map._subplot.map; m.jumpTo({center: [-100.36, 25.70], zoom: 10.6}, {originalEvent: true}); return true; })()""")
    await asyncio.sleep(6)
    await nav.js("""(() => { const g = [...document.querySelectorAll('.js-plotly-plot')].find(g => String(g.layout?.uirevision).startsWith('mapa|'));
      const m = g._fullLayout.map._subplot.map; const c = m.getCanvas(); const r = c.getBoundingClientRect();
      const p = m.project([-100.37, 25.69]);
      const ev = new MouseEvent('mousemove', {clientX: r.left + p.x, clientY: r.top + p.y, bubbles: true});
      c.dispatchEvent(ev); return true; })()""")
    await asyncio.sleep(2)
    mapa_expr = "[...document.querySelectorAll('.js-plotly-plot')].find(g => String(g.layout?.uirevision).startsWith('mapa|'))"
    await t.escena("mapa", "El mapa", entre(H4("Mapa"), E("[data-testid='stExpander'] summary", "Descargar el mapa como imagen"), 12), {
        "mapa": mapa_expr,
        "leyenda": f"{mapa_expr}.querySelector('.legend')",
        "camara": f"{mapa_expr}.querySelector('.modebar')",
        "detalle": f"{mapa_expr}.querySelector('.hoverlayer .hovertext')",
        "titulo_mapa": f"{mapa_expr}.querySelector('.gtitle')",
        "referencia": W("Barras del detalle"),
    })

    # ---------------------------------------------------------------- 5. descargar imagen y pestañas
    await nav.js("__click('[data-testid=\"stExpander\"] summary', 'Descargar el mapa como imagen')")
    await t.esperar(3)
    await t.escena("exportar", "Descargar el mapa como imagen",
                   entre(E("[data-testid='stExpander'] summary", "Descargar el mapa como imagen"), H4("Más detalle"), 8), {
        "titulo_exp": W("Título"), "subtitulo_exp": W("Subtítulo"), "tamano": W("Tamaño"), "resolucion": W("Resolución"),
        "generar": E("button", "Generar imagen", True),
    })
    await nav.js("__click('[data-testid=\"stExpander\"] summary', 'Descargar el mapa como imagen')")

    # ---------------------------------------------------------------- 6. árbol
    fin_pagina = "document.querySelector('[data-testid=\"stMainBlockContainer\"]').lastElementChild"
    recorte_tab = f"""(() => {{
      const m = document.querySelector('[data-testid="stMainBlockContainer"]').getBoundingClientRect();
      const a = {H4('Más detalle')}.getBoundingClientRect();
      const panel = [...document.querySelectorAll('[role="tabpanel"]')].find(p => !p.hidden && p.offsetHeight);
      const b = panel.getBoundingClientRect();
      return {{x: m.x, y: a.y - 12, w: m.width, h: Math.min(b.bottom - a.y + 30, __LIM__)}};
    }})()"""

    # ---------------------------------------------------------------- 7. comparar
    await nav.js("__click('[role=\"tab\"]', 'Comparar escenarios')")
    await t.esperar(8)
    comp_expr = "[...document.querySelectorAll('.js-plotly-plot')].find(g => String(g.layout?.uirevision).startsWith('comp|'))"
    await nav.js(f"""(() => {{ const g = {comp_expr}; const m = g._fullLayout.map._subplot.map;
      m.jumpTo({{center: [-100.33, 25.70], zoom: 10.3}}, {{originalEvent: true}});
      for (const k of Object.keys(g._fullLayout).filter(k => /^map\\d+$/.test(k)))
        g._fullLayout[k]._subplot.map.jumpTo({{center: [-100.33, 25.70], zoom: 10.3}});
      return true; }})()""")
    await asyncio.sleep(6)
    await t.escena("comparar", "Comparar escenarios", recorte_tab.replace("__LIM__", "2600"), {
        "lado_izq": W("Carga de camión OP · izquierdo"), "caso_izq": W("Caso de potencial · izquierdo"),
        "lado_der": W("Carga de camión OP · derecho"), "caso_der": W("Caso de potencial · derecho"),
        "resaltar": W("Resaltar lo que cambia"),
        "mapas_comp": comp_expr,
        "conteo_comp": H4("Cuántos hay en cada cuadrante"),
        "transicion": H4("De dónde a dónde"),
        "lista_cambios": E("h4", "Rutas que cambian"),
        "descargar_comp": E("button", "Descargar comparación"),
    })

    # ---------------------------------------------------------------- 8. glosario
    await nav.js("__click('[role=\"tab\"]', 'Glosario')")
    await t.esperar(5)
    await t.escena("glosario", "Glosario", recorte_tab.replace("__LIM__", "1500"), {
        "buscar": W("Buscar un indicador"),
        "tabla_glosario": "[...document.querySelectorAll('[role=\"tabpanel\"]')].find(p => !p.hidden && p.offsetHeight).querySelector('[data-testid=\"stDataFrame\"]')",
        "conceptos": H4("Conceptos de la herramienta"),
    })

    # ---------------------------------------------------------------- 9. tabla por nivel
    await nav.js("__click('[role=\"tab\"]', 'Tabla por')")
    await t.esperar(5)
    await t.escena("tabla", "Tabla por nivel", recorte_tab.replace("__LIM__", "900"), {
        "pestanas": "document.querySelector('[role=\"tablist\"]')",
        "tabla_nivel": "[...document.querySelectorAll('[role=\"tabpanel\"]')].find(p => !p.hidden && p.offsetHeight).querySelector('[data-testid=\"stDataFrame\"]')",
        "descargar_tabla": E("button", "Descargar esta tabla"),
    })

    # ---------------------------------------------------------------- 10. variables continuas (bivariado)
    await nav.js("__click('[data-testid=\"stSidebar\"] label', 'Variables continuas')")
    await t.esperar(10)
    # agrega la 2ª variable: abre la lista y elige "Índice de atractividad"
    await nav.js("""(() => { const w = __widget('Variables (hasta 2)'); const i = w.querySelector('input'); i.focus(); i.click();
      i.dispatchEvent(new MouseEvent('mousedown', {bubbles: true})); return true; })()""")
    await asyncio.sleep(1.5)
    await nav.js("""(() => { const o = [...document.querySelectorAll('[role="option"]')].find(o => o.innerText.includes('Índice de atractividad'));
      if (o) o.click(); return !!o; })()""")
    await t.esperar(12)
    await nav.js("document.activeElement && document.activeElement.blur()")
    await nav.js(f"""(() => {{ const g = {mapa_expr}; const m = g._fullLayout.map._subplot.map;
      m.jumpTo({{center: [-100.33, 25.70], zoom: 10.3}}, {{originalEvent: true}}); return true; }})()""")
    await asyncio.sleep(6)
    recorte_biv = f"""(() => {{
      const m = document.querySelector('[data-testid="stMainBlockContainer"]').getBoundingClientRect();
      const a = {H4('Matriz de cuadrantes')}.getBoundingClientRect(); const g = ({mapa_expr}).getBoundingClientRect();
      return {{x: m.x, y: a.y - 12, w: m.width, h: g.bottom - a.y + 24}}; }})()"""
    await t.escena("bivariado", "Colorear con 2 indicadores", recorte_biv, {
        "disp_biv": "document.querySelectorAll('.js-plotly-plot')[0]",
        "rombo": f"{mapa_expr}.querySelector('.layer-above .shapelayer') || {mapa_expr}.querySelector('.shapelayer')",
        "mapa_biv": mapa_expr,
    })
    panel_var = """(() => { const a = __widget('Variables (hasta 2)').getBoundingClientRect();
      const b = __widget('Comparar en percentiles').getBoundingClientRect();
      return {x: 0, y: a.y - 60, w: 300, h: b.bottom - a.y + 80}; })()"""
    await t.escena("panel_variables", "Opciones de los indicadores", panel_var, {
        "variables": W("Variables (hasta 2)"), "como_comparar": W("Cómo verlas"),
        "con_p": W("Agregar el mapa de cuadrantes"),
        "colores": W("Colores"), "percentiles": W("Comparar en percentiles"),
    })

    # ---------------------------------------------------------------- 11. modo daltonismo
    await nav.js("__click('[data-testid=\"stSidebar\"] label', 'Cuadrante de la matriz')")
    await t.esperar(8)
    await nav.js("[...document.querySelectorAll('[data-testid=\"stSidebar\"] label')].find(l => l.innerText.includes('Modo daltonismo')).querySelector('input').click()")
    await t.esperar(12)
    await nav.js(f"""(() => {{ const g = {mapa_expr}; const m = g._fullLayout.map._subplot.map;
      m.jumpTo({{center: [-100.33, 25.70], zoom: 11}}, {{originalEvent: true}}); return true; }})()""")
    await asyncio.sleep(6)
    await t.escena("daltonismo", "Modo daltonismo", recorte_biv, {
        "matriz_dalt": "document.querySelector('.mz-wrap')",
        "disp_dalt": "document.querySelectorAll('.js-plotly-plot')[0]",
        "mapa_dalt": mapa_expr,
    })

    with open(os.path.join(OUT, "escenas.json"), "w", encoding="utf-8") as f:
        json.dump(t.escenas, f, ensure_ascii=False, indent=1)
    nav.cerrar()


if __name__ == "__main__":
    asyncio.run(main())
