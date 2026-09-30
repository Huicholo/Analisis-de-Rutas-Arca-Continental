# Manual de uso (static/manual.html)

El manual es un recorrido interactivo con capturas reales de la app. Se sirve desde la misma app en
`/app/static/manual.html` (botón **Abrir el manual de uso** del panel izquierdo).

## Regenerarlo después de cambiar la app

1. Levanta la app en el puerto 8599:
   `venv\Scripts\python -m streamlit run app.py --server.port 8599`
2. Toma las capturas y ubica cada control (usa Google Chrome sin ventana, ~4 min):
   `venv\Scripts\python herramientas_manual\capturar_tour.py`
3. Arma el HTML:
   `venv\Scripts\python herramientas_manual\generar_manual.py`

- Los textos de cada punto del recorrido están en `PUNTOS`, los pasos en `PASOS`, la tabla de controles en
  `CONTROLES` y las preguntas frecuentes en `FAQ` (todo en `generar_manual.py`).
- El glosario sale de `mapa/config.py` (`GLOSARIO_VARIABLES` y `GLOSARIO_CONCEPTOS`), el mismo que usa la app.
- Si un control cambia de nombre en la app, actualiza su etiqueta en `capturar_tour.py`; el script avisa
  con "sin ubicar: [...]" cuando no encuentra algo.
