# Roadmap maestro

Cada tarea tiene un **criterio de aceptación** verificable. El implementador (Antigravity) la
cierra con un PR; el orquestador (Claude Code) la revisa contra ese criterio. Orden de fases =
orden de dependencias. Dentro de una fase, las tareas sin dependencia se pueden hacer en paralelo.

Datos de prueba: los tres cursos previos (PL, SD-II, Simulación). Sus resultados en `legacy/`
son la **prueba de regresión**: el sistema nuevo tiene que reproducirlos o explicar por qué
difiere.

---

## Diagnóstico de la idea original (por qué este orden)

Tu división en tres pasos (ingesta + NLP, estadística, simulacros) está bien orientada y ya
funciona en tus tres materias. Lo que cambia:

1. **Falta un paso 0: validar que las predicciones sirven.** Hoy no se mide si el modelo acierta.
   Con 2 a 4 exámenes por profesor, ninguna prueba de hipótesis va a tener potencia; lo que sí
   se puede hacer es *backtesting*: predecir cada examen pasado usando solo lo anterior y
   puntuarlo (Brier y log score) contra líneas base tontas. Además, un **diario de
   predicciones**: se congela la predicción antes de cada examen real y se puntúa después.
   Eso es la evidencia fuerte, más que cualquier p-valor (fase 5).
2. **El cuello de botella no es la estadística, es la extracción.** TF-IDF falló con fórmulas
   (la pregunta 1 del 19/10 no se detectó como copia de T4-3a) y las fotos se transcribieron a
   mano. Por eso la fase 1 (extracción a LaTeX) y la fase 2 (similitud de fórmulas) van antes.
3. **El etiquetado a mano es el mayor riesgo y el mayor costo.** Rasgos, arquetipos y fuente
   eran tu juicio. Un LLM puede proponerlos, pero solo se confía en él si su acuerdo con tus
   etiquetas en una muestra es aceptable (α de Krippendorff ≥ 0.67). Así lo manual se vuelve
   revisión, no captura (fases 3 y 4).
4. **Los clasificadores Bloom de GitHub no sirven tal cual.** Están entrenados con preguntas
   cortas en inglés de humanidades y programación. Para matemáticas en español conviene un LLM
   con rúbrica y, además de Bloom, Webb DOK y la guía de Stein. Bloom es la etiqueta menos
   informativa para examen de matemáticas (fase 4).
5. **Lo que aprendiste de un profe sirve para el siguiente.** "Qué fracción sale de la tarea",
   "cuánto recicla", "si hay demostración" son parámetros por profesor. Con un modelo jerárquico
   (pooling parcial entre materias) cada profe nuevo arranca con priors informados por los
   anteriores (fase 5).
6. **"Agentes" significa dos cosas, y conviene separarlas:**
   - *Agentes de código* (Antigravity, Claude Code): construyen el repo.
   - *Pasos LLM en tiempo de ejecución* (extraer, etiquetar, generar): se llaman con tu API key.
     Van detrás de una sola capa (`llm.py`, vía LiteLLM) para poder cambiar de proveedor sin tocar
     el resto.
   - El núcleo estadístico es Python determinista y **nunca** depende de un LLM.

---

## Fase 0: Cimientos  *(orquestador: hecho en este commit; implementador: 0.3-0.6)*

- [x] 0.1 Estructura del repo, `pyproject.toml`, extras, scripts de setup (sh/ps1), `.gitignore`
      que protege datos y secretos.
- [x] 0.2 Contratos de datos (`esquemas.py`), CLI `ap` con subcomandos vacíos, `AGENTS.md`.
- [ ] 0.3 **CI en GitHub Actions**: ruff + pytest en Python 3.11 y 3.12 en cada PR.
      *Acepta:* el PR muestra la verificación en verde.
- [ ] 0.4 **Portar `legacy/estudio_parciales/nucleo`** a `src/analisis_profesor/`
      (`similitud.py`, `dificultad.py`, `modelo.py`, `extraer.py`) sin cambiar la lógica, con los
      rasgos como parámetro (como en la versión de Simulación).
      *Acepta:* pruebas de regresión que reproducen `legacy/.../sistemas_dinamicos_ii/salidas/
      modelo_parcial3.json` y `dificultad.json` con las mismas semillas (tolerancia 1e-9).
- [ ] 0.5 **Recuperar el código de Simulación** (`nucleo/armado.py` y `cursos/simulacion/`):
      no venía en el zip. *Acepta:* está en `legacy/` y sus salidas se reproducen.
- [ ] 0.6 `ap nueva <materia>` copia la plantilla. *Acepta:* prueba que crea la carpeta y valida
      `materia.yaml` con un modelo Pydantic `ConfigMateria`.

## Fase 1: Ingesta y extracción

- [ ] 1.1 **Ingesta del .zip** (`ingesta.py`): descomprime a `materias/<m>/datos/crudo`, calcula
      sha256, detecta duplicados y **clasifica cada archivo** (examen, tarea, clase, notas,
      temario, pauta) por nombre y contenido: primero reglas, el LLM solo si las reglas no
      deciden. Escribe `documentos.jsonl` y un `inventario.csv` para que el dueño lo corrija.
      *Acepta:* con los zips de PL y SD-II, el inventario coincide con las carpetas manuales de
      `legacy`.
- [ ] 1.2 **Capa LLM** (`llm.py`): `completar(rol, prompt, esquema_pydantic, imagenes=None)` sobre
      LiteLLM, con modelo por rol desde `.env`, reintentos, caché en disco por hash, registro de
      tokens y costo en `salidas/llm_log.jsonl`, y `AP_LLM_FALSO=1` para las pruebas.
      *Acepta:* pruebas sin red; cambiar de proveedor solo cambia `.env`.
- [ ] 1.3 **Extracción**, con tres caminos según el documento:
      - PDF con texto → PyMuPDF.
      - PDF escaneado, foto o fórmulas densas → VLM (`rol=extraccion`) que devuelve Markdown con
        LaTeX.
      - Opcional: Marker o MinerU locales.

      *Acepta:* en las 4 fotos de SD-II, el texto extraído tiene similitud ≥ 0.9 con las
      transcripciones manuales de `legacy` (corpus/examenes), y las fórmulas compilan en KaTeX.
- [ ] 1.4 **Segmentación en ítems**: preguntas, incisos y puntos; numeración `Pregunta N` / `3a`.
      Reglas por regex más un LLM como respaldo. *Acepta:* número de preguntas e incisos
      correcto en todos los exámenes y tareas de PL y SD-II.
- [ ] 1.5 **Revisión humana**: genera `revision_items.md` con un ítem por bloque para corregir a
      mano y luego reimporta. *Acepta:* el ciclo editar → reimportar marca
      `revisado_por_humano=True`.

## Fase 2: Reciclaje (qué se repite y de dónde)

- [ ] 2.1 **Similitud léxica**: TF-IDF de caracteres y palabras (portado) + MinHash/LSH para
      copias literales.
- [ ] 2.2 **Similitud semántica**: embeddings multilingües (`intfloat/multilingual-e5-base` o
      `BAAI/bge-m3`), extra `nlp`.
- [ ] 2.3 **Similitud de fórmulas**: LaTeX → expresión sympy cuando se pueda, con símbolos
      renombrados a forma canónica (x, y, λ → v1, v2, p1) y constantes abstraídas. Similitud
      por coincidencia de árbol o de subexpresiones, y Jaccard de tokens LaTeX como respaldo.
      *Acepta:* detecta P2_2026-10-19:Q1 ≈ T4:3a (el caso que TF-IDF no vio).
- [ ] 2.4 **Fusión y línea base nula**: la similitud fusionada se compara con la distribución de
      pares no relacionados (permutación; p95 como en legacy, más un p-valor empírico) y se
      controla FDR (Benjamini-Hochberg) porque son muchas comparaciones. Salida:
      `relaciones.jsonl` con nivel copia, adaptación o nueva.
      *Acepta:* reproduce los hallazgos de SD-II (0.98, 0.88, 0.86; T5 = T4 en 10 de 10) y el
      "no recicla" de Simulación.
- [ ] 2.5 **Matriz de flujo**: de dónde salen las preguntas de examen (tarea, clase, examen
      previo, nueva), con su proporción e intervalo de Jeffreys. Es la entrada `pi` del modelo.

## Fase 3: Temas y arquetipos

- [ ] 3.1 **Propuesta de arquetipos**: BERTopic sobre los ítems (extra `nlp`) **y** una propuesta
      del LLM guiada por el temario. Se combinan en `arquetipos_propuestos.yaml`.
- [ ] 3.2 **Aprobación humana**: el dueño edita el YAML y lo pasa a `materia.yaml`.
- [ ] 3.3 **Asignación ítem → arquetipo** y ítem → fuente con LLM (k corridas). Se guarda la
      etiqueta modal y su consistencia.
      *Acepta:* acuerdo con las etiquetas manuales de SD-II y Simulación ≥ 0.8 (exactitud).

## Fase 4: Dificultad cognitiva

- [ ] 4.1 **Rúbrica por materia** (los rasgos de `materia.yaml`) etiquetada por el LLM con k = 3
      corridas y un prompt que incluye ejemplos ya etiquetados por ti (*few-shot*).
- [ ] 4.2 **Taxonomías**: Bloom revisada, Webb DOK (1-4) y Stein (1-4, solo matemáticas). Los
      tres se guardan; el score principal sigue siendo la rúbrica.
- [ ] 4.3 **Acuerdo**: α de Krippendorff ordinal entre LLM y humano en ≥ 20 ítems por materia,
      y entre corridas del LLM. Si α < 0.67, el rasgo se marca "requiere humano".
      *Acepta:* reporte de acuerdo para SD-II y Simulación contra sus CSV de rasgos.
- [ ] 4.4 **Comparación tarea vs examen** (`dificultad.py` mejorado):
      - Delta por pares (examen contra su fuente), con IC BCa bootstrap, Wilcoxon exacto y
        prueba de permutación por cambio de signo.
      - Delta global con intervalo bootstrap.
      - Robustez de pesos (2000 perturbaciones, como en legacy).
      - Percentil de cada pregunta dentro de la distribución de las tareas.
- [ ] 4.5 **Validación externa** contra la calificación del alumno: Spearman con IC bootstrap y
      p de permutación, y la separación "nueva" contra "adaptada" (lo que encontraste en
      Simulación). Con n < 10 se reporta como exploratorio.

## Fase 5: Modelo predictivo

- [ ] 5.1 **Motor genérico** portado (Dirichlet-multinomial con molde, material, rotación,
      demostración, ventana de minutos y temario) con `materia.yaml` como entrada.
- [ ] 5.2 **Intervalos creíbles** (5-95 %) por arquetipo, además del mín-máx de sensibilidad.
- [ ] 5.3 **Recencia**: peso exponencial por antigüedad del examen (vida media como
      hiperparámetro dentro de la rejilla).
- [ ] 5.4 **Backtesting** dejando fuera un examen a la vez: para cada examen pasado, predecir
      con lo anterior y puntuar con Brier, log score y "temas cubiertos por los 5 simulacros".
      Líneas base: uniforme, solo frecuencia en tareas y solo el examen previo.
      *Acepta:* tabla de puntuaciones para PL, SD-II y Simulación; el modelo le gana a la
      uniforme o se reporta que no.
- [ ] 5.5 **Modelo jerárquico entre profesores** (extra `bayes`): `pi_tarea`, `pi_molde`, tasa de
      demostración y fracción "nueva" con priors Beta jerárquicos; el profe nuevo hereda la
      posterior poblacional.
- [ ] 5.6 **Diario de predicciones**: `ap modelo` guarda `predicciones/<fecha>.json` con la fecha
      de emisión; `ap evaluar <materia> <examen>` puntúa cuando llega el examen real.
- [ ] 5.7 **Chequeos predictivos posteriores** en lugar de ji-cuadrada (con n chico no aplica):
      ¿los exámenes simulados se parecen en número de preguntas, minutos y mezcla de fuentes a
      los reales?

## Fase 6: Banco de ejercicios y simulacros

- [ ] 6.1 **Generador de variantes** (LLM, `rol=generacion`): a partir de un ítem fuente y su
      arquetipo, genera k variantes con nuevos números o funciones, con la solución y la
      etiqueta de rasgos.
- [ ] 6.2 **Verificadores enchufables** por materia (`materias/<m>/verificadores.py`): sympy,
      integración numérica o simulación. Lo que no se pueda verificar se marca "revisión
      humana". *Acepta:* reproduce 44/44 en SD-II y 67/67 en Simulación con los bancos de
      `legacy`.
- [ ] 6.3 **Recorte por incisos** (portado de `armado.py` de Simulación) y banda de dificultad
      ±1 alrededor del objetivo por arquetipo.
- [ ] 6.4 **Sorteo balanceado** (portado) y armado por búsqueda local con semilla.
- [ ] 6.5 **Salida**: LaTeX/PDF de enunciados y PDF de soluciones aparte, más `simulacros.json`.
      Plantillas Jinja.

## Fase 7: Orquestación del flujo

- [ ] 7.1 `ap todo <materia> <parcial>` encadena las fases y se salta lo que ya está hecho
      (caché por hash de entradas).
- [ ] 7.2 **Puntos de control humanos** explícitos: el flujo se detiene después de 1.5, 3.2 y
      4.3 si hay pendientes de revisión.
- [ ] 7.3 **Reporte** HTML/PDF por materia con reciclaje, dificultad, probabilidades con
      intervalos, backtesting y limitaciones (como tus `MEJORAS_Y_USO.md`, pero generado).
- [ ] 7.4 (Opcional) **Servidor MCP** que expone `ap` como herramientas, para que cualquier agente
      (Claude, Gemini, etc.) lo use desde un chat.
- [ ] 7.5 (Opcional) Interfaz Streamlit para subir el zip y revisar etiquetas.

## Fase 8: Migración y cierre

- [ ] 8.1 Migrar PL, SD-II y Simulación a `materias/` con `materia.yaml` y reproducir sus
      resultados.
- [ ] 8.2 Comparar lo viejo contra lo nuevo (extracción automática contra manual, etiquetas del
      LLM contra las tuyas) y documentar las diferencias.
- [ ] 8.3 Guía "nueva materia en 30 minutos".

---

## Cómo trabajan Antigravity y Claude Code juntos

```
 Dueño ──(elige tarea)──> Antigravity (laptop)
                           ├─ git checkout -b fase1/ingesta-zip
                           ├─ implementa + pruebas + ruff
                           ├─ git push  → abre PR
 Claude Code (nube) <──────┘
   ├─ revisa PR contra el criterio de aceptación (código, pruebas, reglas de AGENTS.md)
   ├─ comenta / pide cambios
   └─ actualiza ROADMAP si cambia el plan
 Dueño ── merge ──> main
```

- Prompt para Antigravity por tarea: *"Implementa la tarea X.Y de docs/ROADMAP.md siguiendo
  AGENTS.md. Abre un PR cuando pasen ruff y pytest."* (también está en
  `.agents/workflows/tarea.md`).
- Para pedir revisión a Claude Code: *"Revisa el PR #N contra la tarea X.Y del roadmap."*
