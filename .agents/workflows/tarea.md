---
description: Implementa una tarea del roadmap (uso: /tarea 1.3)
---
Estás en modo DESARROLLO.

1. Lee `AGENTS.md`, `docs/ARQUITECTURA.md`, `PROTOCOLO.md` y la tarea indicada en `docs/ROADMAP.md`, incluido su "Acepta:".
2. `git switch main && git pull`, luego `git switch -c fase<N>/<nombre-corto>`.
3. Escribe primero las pruebas que demuestran el "Acepta:", con `tests/fixtures/mini` o con `@pytest.mark.real` si necesitan datos de `entrada/`.
4. Implementa lo mínimo para que pasen. En `src/` solo se importan a nivel módulo la librería estándar, numpy y scipy; todo lo demás va dentro de una función con try/except y respaldo.
5. `.venv/bin/ruff check src tests ap.py && .venv/bin/pytest` y `python3 -I ap.py diagnostico` (sin venv) deben pasar.
6. Marca la casilla de la tarea en `docs/ROADMAP.md`.
7. Commits pequeños en español, `git push -u origin <rama>` y abre un PR con: tarea, criterio de aceptación, y comando y salida que lo demuestran.
8. Si algo es ambiguo, no inventes: escribe la pregunta en el PR y detente.
