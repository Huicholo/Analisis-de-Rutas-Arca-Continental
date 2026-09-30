"""Mini cliente de Chrome DevTools Protocol para tomar capturas de la app (sin Playwright)."""
import asyncio
import base64
import json
import subprocess
import tempfile
import time
import urllib.request

import websockets

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PUERTO = 9333


class Navegador:
    def __init__(self, ancho=1440, alto=900):
        self.ancho, self.alto = ancho, alto
        self.proc = subprocess.Popen([
            CHROME, "--headless=new", f"--remote-debugging-port={PUERTO}", f"--window-size={ancho},{alto}",
            f"--user-data-dir={tempfile.mkdtemp()}", "--hide-scrollbars", "--enable-unsafe-swiftshader",
            "--ignore-gpu-blocklist", "--no-first-run", "--no-default-browser-check", "--lang=es-MX",
            "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                paginas = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/json"))
                self.ws_url = next(p["webSocketDebuggerUrl"] for p in paginas if p["type"] == "page")
                break
            except Exception:
                time.sleep(0.2)
        self.id = 0

    async def conectar(self):
        self.ws = await websockets.connect(self.ws_url, max_size=2 ** 30)
        await self.cmd("Page.enable")
        await self.cmd("Runtime.enable")

    async def cmd(self, metodo, **params):
        self.id += 1
        mi = self.id
        await self.ws.send(json.dumps({"id": mi, "method": metodo, "params": params}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == mi:
                if "error" in msg:
                    raise RuntimeError(f"{metodo}: {msg['error']}")
                return msg.get("result", {})

    async def js(self, codigo, esperar=True):
        r = await self.cmd("Runtime.evaluate", expression=codigo, awaitPromise=esperar, returnByValue=True)
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"].get("exception", {}).get("description", r["exceptionDetails"]))
        return r.get("result", {}).get("value")

    async def tamano(self, ancho, alto):
        await self.cmd("Emulation.setDeviceMetricsOverride", width=ancho, height=alto, deviceScaleFactor=1,
                       mobile=False)

    async def ir(self, url):
        await self.cmd("Page.navigate", url=url)

    async def captura(self, ruta, x, y, w, h, calidad=82, completa=True):
        r = await self.cmd("Page.captureScreenshot", format="jpeg", quality=calidad,
                           clip={"x": x, "y": y, "width": w, "height": h, "scale": 1}, captureBeyondViewport=completa)
        with open(ruta, "wb") as f:
            f.write(base64.b64decode(r["data"]))

    def cerrar(self):
        self.proc.kill()


def correr(corutina):
    return asyncio.run(corutina)
