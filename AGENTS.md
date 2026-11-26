# Reglas para agentes

Este repo tiene **dos** usos y un agente debe saber en cuál está:

- **Analizar material** (alguien te da un zip y quiere simulacros): sigue `PROTOCOLO.md`. No
  modifiques el código; trabaja dentro de `trabajo/<id>/`.
- **Desarrollar el kit** (te piden una tarea del roadmap): sigue el resto de este archivo.

## Roles en el desarrollo

- **Implementador** (Antigravity en la laptop del dueño): toma UNA tarea de `docs/ROADMAP.md`,
  la implementa en su rama, corre las pruebas, hace commit y push, y abre un PR.
- **Orquestador y revisor** (Claude Code): revisa cada PR contra el "Acepta:" de su tarea,
  pide cambios y mantiene el roadmap.
- **Dueño** (humano): elige la tarea, prueba en los chats y hace merge.

## Flujo

1. Rama `fase<N>/<tarea-corta>` desde `main` actualizado.
2. Antes de cada commit: `ruff check src tests ap.py` y `pytest`. Si falla, no hay commit.
3. Commits pequeños en español, en imperativo.
4. Un PR por tarea. La descripción dice qué criterio cumple y cómo se verificó (comando y
   salida).
5. Marca la casilla de la tarea en `docs/ROADMAP.md` en el mismo PR.

## Reglas duras

- **Portabilidad:** en `src/analisis_profesor/` solo se importa a nivel módulo la librería
  estándar, numpy y scipy. Cualquier otra librería (sklearn, sympy, fitz...) se importa dentro
  de una función con `try/except ImportError` y tiene respaldo o un mensaje claro. La CI tiene
  un trabajo sin nada instalado que debe pasar.
- **Sin LLM en el código:** nada de SDKs de OpenAI, Anthropic o Gemini, ni API keys. El juicio lo
  pone la IA que sigue el protocolo.
- **No toques `legacy/`:** es la referencia de las pruebas de regresión.
- **Reproducible:** todo lo aleatorio con semilla. Mismo input + misma semilla = mismo output.
- **Formatos:** si cambias un formato que escribe la IA (Markdown del paso 2, CSV del paso 5,
  `08_banco.md`), actualiza `PROTOCOLO.md`, sube su versión y actualiza los fixtures.
- **Datos:** nunca subas `entrada/`, `trabajo/`, zips ni calificaciones. Los fixtures de la CI
  son inventados (`tests/fixtures/mini`).
- **Incertidumbre:** ningún número estadístico sale de un script sin su intervalo, rango o n.
- Si la tarea es ambigua, pregunta en el PR y detente. No inventes.

## Estilo

Python ≥ 3.10, tipado, funciones puras, nombres en español como en `legacy/`, líneas ≤ 100 y
módulos cortos.
