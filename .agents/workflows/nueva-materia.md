---
description: Da de alta una materia nueva a partir de un .zip (uso: /nueva-materia <id> <ruta.zip>)
---
1. `ap nueva <id>` y edita `materias/<id>/materia.yaml` (nombre, profesor, semestre, parcial objetivo, temario si se conoce).
2. `ap ingesta <id> --zip <ruta.zip>` y pide al dueño que revise `materias/<id>/salidas/inventario.csv` y `revision_items.md`.
3. `ap reciclaje <id>` y `ap etiquetar <id>`. Pide al dueño que apruebe `arquetipos_propuestos.yaml` y una muestra de etiquetas.
4. `ap dificultad <id>`, `ap modelo <id> <parcial>`, `ap simulacros <id> <parcial> --n 5`.
5. Nunca hagas commit de `materias/<id>/datos` ni de `materias/<id>/salidas`; sí de `materia.yaml`, `verificadores.py`, `banco/` y `predicciones/`.
