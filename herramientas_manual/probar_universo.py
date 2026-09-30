import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capturar_tour import AYUDANTES  # noqa: E402
from cdp import Navegador  # noqa: E402


async def main():
    nav = Navegador()
    await nav.conectar()
    await nav.tamano(1440, 5000)
    await nav.ir("http://localhost:8599/")
    await asyncio.sleep(30)
    await nav.js(AYUDANTES)
    # Región: Noreste
    await nav.js("""(() => { const w = __widget('Región'); const i = w.querySelector('input'); i.focus(); i.click();
      i.dispatchEvent(new MouseEvent('mousedown', {bubbles: true})); return true; })()""")
    await asyncio.sleep(1.5)
    print("opción:", await nav.js("""(() => { const o = [...document.querySelectorAll('[role="option"]')].find(o => o.innerText.includes('Noreste')); const t = o && o.innerText; if (o) o.click(); return t; })()"""))
    await asyncio.sleep(12)
    await nav.js(AYUDANTES)
    await nav.js("document.activeElement && document.activeElement.blur()")
    leer = """(() => ({region: [...__widget('Región').querySelectorAll('[data-baseweb="tag"]')].map(t => t.innerText),
      rutas: [...document.querySelectorAll('[data-testid="stMetricValue"]')].map(m => m.innerText)[0]}))()"""
    print("antes:", await nav.js(leer))
    print("clic:", await nav.js("[...document.querySelectorAll('label')].find(l => l.innerText.trim() === 'Todo el universo').click() || true"))
    await asyncio.sleep(14)
    await nav.js(AYUDANTES)
    print("después:", await nav.js(leer))
    nav.cerrar()


asyncio.run(main())
