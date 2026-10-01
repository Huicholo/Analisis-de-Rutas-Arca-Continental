"""Prueba en Chrome: imagen con la vista de pantalla, Restablecer todo y burbujas con letra al acercarse."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capturar_tour import AYUDANTES  # noqa: E402
from cdp import Navegador  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "prueba_final")
MAPA = "[...document.querySelectorAll('.js-plotly-plot')].find(g => String(g.layout?.uirevision).startsWith('mapa|'))"


async def esperar_carga(nav):
    for _ in range(120):
        await asyncio.sleep(1)
        if await nav.js("!!document.querySelector('h4') && document.querySelectorAll('.js-plotly-plot').length > 1"):
            break
    await asyncio.sleep(6)
    await nav.js(AYUDANTES)


async def main():
    os.makedirs(OUT, exist_ok=True)
    nav = Navegador()
    await nav.conectar()
    await nav.tamano(1440, 5200)
    await nav.ir("http://localhost:8599/")
    await esperar_carga(nav)

    # 1) mover el mapa y generar la imagen
    await nav.js(f"(() => {{ const m = {MAPA}._fullLayout.map._subplot.map; "
                 "m.jumpTo({center: [-100.31, 25.68], zoom: 11.5}, {originalEvent: true}); return true; })()")
    await asyncio.sleep(2)
    print("URL tras mover:", await nav.js("location.search"))
    await nav.js("__click('[data-testid=\"stExpander\"] summary', 'Descargar el mapa como imagen')")
    await asyncio.sleep(3)
    await nav.js("__click('button', 'Generar imagen', true)")
    for _ in range(90):
        await asyncio.sleep(2)
        if await nav.js("!!document.querySelector('[data-testid=\"stImage\"] img')"):
            break
    print("URL tras generar:", await nav.js("location.search"))
    src = await nav.js("(document.querySelector('[data-testid=\"stImage\"] img') || {}).src || ''")
    print("vista previa:", bool(src))
    if src:   # foto de la vista previa de la imagen exportada
        r = await nav.js("(() => { const e = document.querySelector('[data-testid=\"stImage\"] img').getBoundingClientRect(); "
                         "return {x: e.x, y: e.y, w: e.width, h: e.height}; })()")
        await nav.captura(os.path.join(OUT, "export.jpg"), r["x"], r["y"], r["w"], r["h"], 80)
    await nav.captura(os.path.join(OUT, "pantalla_mapa.jpg"), 300, 900, 1140, 1100, 70)

    # 2) burbujas por CeDi: lejos y cerca
    await nav.js("__click('[data-testid=\"stSidebar\"] label', 'CeDi')")
    await asyncio.sleep(12)
    await nav.js(AYUDANTES)
    await nav.js("[...document.querySelectorAll('[data-testid=\"stSidebar\"] label')].find(l => l.innerText.includes('Burbujas por grupo')).querySelector('input').click()")
    await asyncio.sleep(12)
    estado = (f"(() => {{ const g = {MAPA}; const m = g._fullLayout.map._subplot.map; const out = {{zoom: m.getZoom()}};"
              "for (const t of g._fullData) if (t.meta) { const id = 'plotly-trace-layer-' + t.uid + '-circle';"
              "out[t.meta] = m.getLayer(id) ? m.getPaintProperty(id, 'circle-opacity') : 'sin capa'; } return out; })()")
    await nav.js(f"(() => {{ const m = {MAPA}._fullLayout.map._subplot.map; "
                 "m.jumpTo({center: [-102.5, 24.5], zoom: 5}, {originalEvent: true}); return true; })()")
    await asyncio.sleep(2)
    print("lejos:", await nav.js(estado))
    await nav.js(f"(() => {{ const m = {MAPA}._fullLayout.map._subplot.map; "
                 "m.jumpTo({center: [-100.31, 25.68], zoom: 10}, {originalEvent: true}); return true; })()")
    await asyncio.sleep(3)
    print("cerca:", await nav.js(estado))
    await nav.captura(os.path.join(OUT, "burbujas_cerca.jpg"), 300, 900, 1140, 1100, 70)

    # 3) restablecer todo
    print("antes de restablecer:", await nav.js("[...document.querySelectorAll('[data-testid=\"stSidebar\"] input[type=radio]:checked')].map(i => i.closest('label').innerText.trim())"))
    await nav.js("__click('[data-testid=\"stSidebar\"] button', 'Restablecer todo', true)")
    await asyncio.sleep(5)
    await esperar_carga(nav)
    print("después de restablecer:", await nav.js("[...document.querySelectorAll('[data-testid=\"stSidebar\"] input[type=radio]:checked')].map(i => i.closest('label').innerText.trim())"),
          "· URL:", await nav.js("location.search"))
    nav.cerrar()


asyncio.run(main())
