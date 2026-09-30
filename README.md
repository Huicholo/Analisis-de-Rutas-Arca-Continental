# Mapa de rutas · Matriz Atractividad × Madurez

App de Streamlit que pinta en el mapa de México los polígonos de las rutas con el resultado
de la matriz (P1 Ampliar cobertura · P2 Mantener · P3 Desarrollar · P4 Evaluar).

> Manual de uso (interactivo, con capturas): `static/manual.html`, se abre desde la app con el botón **Abrir el manual de uso**. Para regenerarlo: `herramientas_manual/LEEME.md`.

## Ejecutar

Doble clic en `iniciar_app.bat` (crea el `venv` la primera vez), o:

```
venv\Scripts\python -m streamlit run app.py
```

## Datos (`Data/`)

- `Analisis de madurez CEDIS y Rutas Arca.xlsx`: libro de análisis. La app lee de él datos y
  parámetros y **calcula todo en Python** (`mapa/modelo.py`, réplica de la hoja
  `Analisis recomendación Rutas v2`).
- `geo_poligonos_rutas_arca.geojson`: polígonos por ruta y día de visita. Todos los polígonos de
  una ruta se unen en una sola huella. Se cruzan con el modelo por `Ruta`.

Para actualizar: editar y guardar el libro en Excel y recargar la página (la app detecta la fecha de
guardado).

## Lógica

- Arriba de la página se eligen el **caso de madurez** (escenario de estándares de
  `Hoja de apoyo v2`: Conservador/Medio/Ambicioso) y el **caso de atractividad** (bloques
  `Atractividad Caso NN` de `Base de datos Rutas`). Los bloques nuevos aparecen solos.
- **Cortes**: `ROUND(MEDIAN(eje),1)` en Madurez y Atractividad, igual que el Excel.
- **CeDi / Territorio / Región**: mediana de ambos ejes de sus rutas, clasificada con los mismos
  cortes; en la matriz todas las rutas del grupo cuentan en el cuadrante del grupo.
- Validación: `venv\Scripts\python tests\validar_contra_excel.py` compara el motor contra los
  valores guardados en el Excel (hoy coinciden las 75 columnas en las 789 filas).

## Otras vistas

- **Variables continuas** (hasta 4): índices, componentes de Madurez y de Atractividad, y las
  columnas numéricas de la hoja de segmentos del libro. Se comparan como **capas** (encender/apagar
  en la leyenda) o **lado a lado** (un mapa por variable). Mediana en niveles agregados; escala p5–p95.
- **Dispersión de la matriz**: seleccionar puntos (caja o lazo, Shift para agregar) filtra el mapa,
  la tabla y la exportación; debajo hay controles para limpiar, quitar un cuadrante o quitar elementos.
- **Encuadre persistente**: el mapa conserva el zoom/paneo del usuario al cambiar filtros o variables
  (`uirevision`); sólo se reencuadra al cambiar *Vista del mapa* o *Ajuste de zoom*.
- **Día de visita**: dibuja sólo los polígonos de los días elegidos (`L-J` cuenta para lunes y jueves).

## Exportar

- Ícono de cámara del mapa → JPG de la vista actual (con tu zoom).
- *Exportar mapa en alta resolución* → JPG con título/subtítulo editables y tamaño de presentación
  (usa `kaleido`, que necesita Chrome o Edge instalado e internet para el mapa base).
- Tabla por nivel → Excel. Pestaña *Modelo completo* → Excel con todas las columnas, parámetros y pesos.
