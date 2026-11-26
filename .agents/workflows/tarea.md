---
description: Implementa una tarea del roadmap (uso: /tarea 1.2)
---
1. Lee `AGENTS.md`, `docs/ARQUITECTURA.md` y la tarea indicada en `docs/ROADMAP.md`, incluido su criterio de aceptación.
2. `git checkout main && git pull`, luego `git checkout -b fase<N>/<nombre-corto>`.
3. Escribe primero las pruebas que demuestran el criterio de aceptación (en `tests/`, sin llamar APIs reales).
4. Implementa lo mínimo para que pasen. Respeta `esquemas.py`; si necesitas un campo nuevo, que sea opcional.
5. Corre `ruff check src tests` y `pytest`. Si algo falla, corrige antes de seguir.
6. Marca la casilla de la tarea en `docs/ROADMAP.md`.
7. Haz commits pequeños en español, `git push -u origin <rama>` y abre un PR con: la tarea, el criterio de aceptación y el comando y la salida que lo demuestran.
8. Si algo es ambiguo, no inventes: escribe la pregunta en el PR y detente.
