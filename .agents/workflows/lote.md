---
description: Ejecuta un lote de tareas del roadmap en orden, con merge autónomo bajo condiciones estrictas (uso: /lote 1.6 1.7)
---
Estás en modo DESARROLLO POR LOTES. Para cada tarea, en el orden dado:

1. Sigue `.agents/workflows/tarea.md` (rama propia, pruebas primero, implementación mínima, PR).
2. Corre `.agents/workflows/auditar.md` y pega su resultado en el PR.
3. Espera la CI. **Haz merge tú mismo** (`gh pr merge <n> --merge`) solo si se cumplen TODAS:
   - los 4 checks en verde;
   - los 9 puntos de la auditoría en OK;
   - el "Acepta:" de la tarea está verificado por un test, no a mano;
   - no hubo que tocar ningún umbral, tolerancia, fixture real ni archivo de `legacy/` para que pasara.
4. Si cualquier condición falla, o algo del roadmap es ambiguo o contradice los datos: deja el PR abierto, explica el problema en su descripción y **detén el lote entero**. No sigas con la siguiente tarea.
5. Al terminar el lote, entrega un resumen: por tarea, el PR, si se fusionó, y los números clave contra `legacy/`.

El orquestador (Claude Code) revisa después los PRs fusionados del lote; si encuentra un problema, se corrige en un PR nuevo antes del siguiente lote.
