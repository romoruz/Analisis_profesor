---
description: Auditoría de rigor matemático y estadístico antes de abrir o fusionar un PR (uso: /auditar)
---
Responde cada punto con evidencia (archivo:línea, comando y salida). Si alguno falla, NO se fusiona.

1. **Regresión:** si la tarea tiene equivalente en `legacy/`, existe un test que reproduce sus números con la tolerancia del roadmap. Si no se reproduce, el PR lo reporta y se detiene: prohibido mover umbrales, tolerancias o datos para que pase.
2. **Fórmulas con fuente:** cada fórmula estadística o matemática nueva cita en su docstring de dónde sale (archivo de `legacy/`, sección de `docs/METODOLOGIA_ESTADISTICA.md` o paper de `docs/INVESTIGACION.md`).
3. **Valores conocidos:** cada función estadística tiene al menos un test contra un valor de referencia independiente:
   - `scipy.stats` cuando exista (p. ej. `scipy.stats.bootstrap(method="BCa")`, `wilcoxon`, `spearmanr`, `beta.ppf`);
   - o un ejemplo calculado a mano en el test;
   - o una simulación de cobertura (p. ej. un IC al 90 % cubre el valor verdadero entre 85 % y 95 % de 2000 réplicas con semilla).
4. **Respaldo en Python puro:** si hay versión sin numpy/scipy, un test demuestra que coincide con la versión completa (tolerancia ≤ 1e-6, o la que el roadmap diga).
5. **Reproducibilidad:** todo lo aleatorio recibe `semilla`; el test corre dos veces y compara byte a byte la salida JSON.
6. **Incertidumbre en la salida:** todo número estadístico del JSON va con su n y su intervalo, rango o p-valor. Si n < 10, la salida marca `"exploratorio": true`.
7. **Sin datos inventados:** los fixtures de `tests/fixtures/mini` son ficticios y lo dicen; no hay texto de exámenes reales en git (`git diff --stat` no toca `entrada/` ni `trabajo/`).
8. **Portabilidad:** `test_ci.py` pasa; `python3 -I ap.py diagnostico` funciona; en `src/` no hay imports fuera de stdlib, numpy y scipy a nivel módulo.
9. **Protocolo:** si cambió un formato que escribe la IA, `PROTOCOLO.md` subió de versión y el fixture se actualizó.

Escribe el resultado de esta auditoría (los 9 puntos con su evidencia) en la descripción del PR.
