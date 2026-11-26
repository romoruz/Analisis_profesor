# Reglas para agentes de código

Lo leen Antigravity (`AGENTS.md`), Claude Code (vía `CLAUDE.md`) y cualquier otro agente.
El plan está en `docs/ROADMAP.md`; los contratos de datos, en `src/analisis_profesor/esquemas.py`.

## Roles

- **Implementador** (Antigravity u otro agente en la laptop): toma UNA tarea del roadmap a la vez,
  la implementa en su rama, corre las pruebas, hace commit y push, y abre el PR.
- **Orquestador / revisor** (Claude Code): revisa cada PR contra los criterios de aceptación de
  su tarea, pide cambios, actualiza el roadmap. No se hace merge sin su revisión y la del dueño.
- **Dueño** (el humano): aprueba arquetipos y etiquetas, revisa transcripciones y hace merge.

## Flujo de trabajo

1. Rama por tarea: `fase<N>/<tarea-corta>` desde `main` actualizado (p. ej. `fase1/extraccion-pdf`).
2. Antes de cada commit: `ruff check src tests` y `pytest`. Si algo falla, no se hace commit.
3. Commits pequeños en español, en imperativo: `Agrega segmentador de preguntas`.
4. Un PR por tarea. En la descripción va qué criterio de aceptación se cumple y cómo se verificó
   (comando y salida).
5. Al terminar la tarea, marca su casilla en `docs/ROADMAP.md` dentro del mismo PR.

## Reglas duras

- **Nunca** subas `.env`, API keys, ni nada de `materias/*/datos` o `materias/*/salidas`. Las
  calificaciones del alumno son datos personales.
- **Nunca** cambies un campo existente de `esquemas.py` sin actualizar `docs/ARQUITECTURA.md` y
  los tests. Agregar campos opcionales sí se vale.
- **No** toques `legacy/`: es la referencia para las pruebas de regresión.
- Todo lo aleatorio lleva semilla y es reproducible. Mismo input + misma semilla = mismo output.
- Toda llamada a LLM pasa por `analisis_profesor/llm.py` (capa única con caché, registro de
  costo y salida validada con Pydantic). Nada de clientes de proveedor sueltos en otros módulos.
- Los prompts viven en `prompts/*.md` con versión en el encabezado; el código los carga, no los
  escribe en línea.
- Ningún número estadístico se reporta sin su incertidumbre (intervalo, rango de sensibilidad o
  tamaño de muestra). Ver `docs/METODOLOGIA_ESTADISTICA.md`.
- Las pruebas no llaman a APIs reales: usa el modo `AP_LLM_FALSO=1` (respuestas grabadas en
  `tests/fixtures/llm/`).
- Si una tarea es ambigua o choca con estas reglas, detente y deja la pregunta en el PR en vez de
  inventar.

## Estilo

Python ≥ 3.11, tipado, funciones puras donde se pueda, nombres en español como en `legacy/`.
Módulos cortos; la lógica de una materia va en `materias/<m>/` (configuración y verificadores),
nunca en el núcleo.
