---
description: Autorrevisión antes de abrir el PR (uso: /revisar)
---
1. `git diff main...HEAD`: ¿solo cambia lo que pide la tarea?
2. ¿Hay secretos, datos de `materias/*/datos` o calificaciones en el diff? Si sí, quítalos.
3. ¿Las pruebas cubren el criterio de aceptación y no llaman APIs reales?
4. ¿Todo lo aleatorio usa semilla? ¿Hay imports fuera de stdlib/numpy/scipy a nivel módulo en `src/`? ¿Algún SDK de LLM o API key?
5. ¿Cada número estadístico nuevo se reporta con su incertidumbre?
6. `.venv/bin/ruff check src tests ap.py && .venv/bin/pytest && python3 -I ap.py diagnostico`.
