# Bitácora de prueba en chat — `<Plataforma>`

Copia esta plantilla en `docs/pruebas_chat/<plataforma>.md` para registrar cada prueba a
ciegas con `kit_analisis_profesor.zip` y `sd2_material.zip` (Fase 2 de `docs/ROADMAP.md`).

---

## 1. Plataforma y modelo

- **Plataforma:** `<Antigravity / Claude.ai / ChatGPT / Gemini>`
- **Modelo / versión:** `<ej. Claude Sonnet ..., GPT-..., Gemini ...>`
- **Fecha:** `<AAAA-MM-DD>`
- **Archivos adjuntos:** `kit_analisis_profesor.zip`, `sd2_material.zip`
- **Prompt usado:** `<del README o personalizado>`

---

## 2. Modo del protocolo alcanzado

- **Modo alcanzado:** `<COMPLETO / REDUCIDO / SIN CÓDIGO>`
- **Salida de `ap.py diagnostico`:**
  - Python: `<versión / no disponible>`
  - Librerías disponibles: `<numpy, scipy, sklearn, sympy, lector_pdf...>`
  - Herramientas del sistema: `<pdftotext, pdflatex>`

---

## 3. Pasos que no pudo ejecutar

| Paso de `PROTOCOLO.md` | ¿Ejecutado? (`Sí` / `No` / `Parcial`) | Motivo (entorno, paquete, red, límite...) | Rodeo aplicado (p. ej. Anexo C) |
|---|---|---|---|
| 1. Ingesta (`ap.py ingesta`) | | | |
| 2. Lectura y transcripción (`02_texto/*.md`) | | | |
| 3. Segmentación (`ap.py items`) | | | |
| 4. Similitud (`ap.py similitud`) | | | |
| 5. Etiquetado (`05_etiquetas.csv`) | | | |
| 6. Dificultad y modelo (`ap.py dificultad`, `modelo`) | | | |
| 7. Banco y verificación (`ap.py verificar`) | | | |
| 8. Armado y PDF (`ap.py armar`) | | | |
| 9–10. Guía y entrega (`GUIA_PARCIAL.md`) | | | |

---

## 4. Datos inventados

Lista cualquier elemento fabricado o asumido sin respaldo en los archivos reales o salidas de
`ap.py` (enunciados, fechas, cifras estadísticas, fuentes inexistentes, calificaciones o
supuestos no declarados en `supuestos.md`):

- `<Ninguno / Detallar caso por caso con evidencia>`

---

## 5. Reciclaje detectado (sí/no por cada uno de los 4 casos conocidos)

| Caso conocido (SD-II) | Detectado (`Sí` / `No`) | Similitud / evidencia reportada por el chat | Notas |
|---|---|---|---|
| **1. Tarea 5 casi copia de Tarea 4** (ejercicios 3–12 de T4, 10 de 10) | | | |
| **2. `P2_2026-10-19:Q2` reciclada de `P1_2026-03-04:Q3`** (mismo parcial/pregunta) | | | |
| **3. Potencial mayo 2026 (`P2_2026-05-04:Q2`) desde abril 2020 (`P2_2020-04-29:Q1`)** | | | |
| **4. Bifurcación mayo 2026 (`P2_2026-05-04:Q3`) desde abril 2020 (`P2_2020-04-29:Q2`)** | | | |

---

## 6. Los 3 temas más probables según el chat

| Puesto | Tema / arquetipo según el chat | Probabilidad / estimación reportada | Intervalo creíble o rango de sensibilidad | ¿Coincide con `legacy` (`A`, `G`/`F`/`H`/`B`)? |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

---

## 7. Número de simulacros con demostración

- **Simulacros con al menos una pregunta de demostración:** `<X / 5>`
- **Probabilidad de demostración reportada en `07_modelo.json` / guía:** `<valor e intervalo>`
- **Verificación del banco de ejercicios:** `<ok automáticos / manuales / sin verificar>`

---

## 8. Tiempo total

- **Tiempo total reloj:** `<ej. 18 min>`
- **Número de mensajes / intervenciones del usuario:** `<N>`
- **¿Llegó a entregables finales (`GUIA_PARCIAL.md`, `SIMULACROS.md`, `SOLUCIONES.md`, PDF)?** `<Sí / Parcial / No>`

---

## 9. Fricciones

- **Dónde se atoró o necesitó ayuda humana:**
  - `<descripción>`
- **Comparación de su `GUIA_PARCIAL.md` contra `legacy/estudio_parciales/MEJORAS_Y_USO.md`:**
  - `<qué acertó, qué omitió y diferencias clave en deltas/temas>`
- **Reglas o mejoras sugeridas para `PROTOCOLO.md` / scripts:**
  - `<cada fricción accionable para el paso 2.3>`
