# Arquitectura

## Principios

1. **Núcleo determinista, LLM en los bordes.** Estadística, similitud, armado y verificación son
   Python puro, reproducible con semilla. El LLM solo extrae, propone etiquetas y genera
   variantes, y todo lo que produce pasa por validación con Pydantic y, cuando aplica, por
   revisión humana o un verificador simbólico.
2. **Agnóstico de proveedor.** Una sola capa `llm.py` sobre LiteLLM. El modelo por rol se elige en
   `.env`. Funciona con Anthropic, Gemini, OpenAI o modelos locales.
3. **Agnóstico de materia.** El núcleo no sabe de simplex ni de Poincaré-Bendixson. Lo específico
   vive en `materias/<m>/`: `materia.yaml`, `verificadores.py` y el banco.
4. **Archivos planos versionables.** JSONL, CSV y YAML entre fases. Nada de base de datos hasta
   que haga falta.
5. **Humano en el ciclo** en tres puntos: inventario y transcripción, arquetipos y muestra de
   etiquetas.

## Módulos (`src/analisis_profesor/`)

| Módulo | Fase | Entrada → salida |
|---|---|---|
| `esquemas.py` | 0 | Contratos Pydantic (Documento, Item, Relacion, Etiqueta, Prediccion, Simulacro) |
| `config.py` | 0 | `materia.yaml` → `ConfigMateria` |
| `llm.py` | 1 | `completar(rol, prompt, esquema, imagenes)` con caché, costo y modo falso |
| `ingesta.py` | 1 | zip → `datos/crudo`, `documentos.jsonl`, `inventario.csv` |
| `extraccion.py` | 1 | Documento → Markdown + LaTeX (PyMuPDF, VLM, Marker) |
| `segmentacion.py` | 1 | texto → `items.jsonl` |
| `similitud/` (`lexica`, `semantica`, `formulas`, `fusion`) | 2 | items → `relaciones.jsonl` |
| `temas.py` | 3 | items → `arquetipos_propuestos.yaml` |
| `etiquetado.py` | 3-4 | items → `etiquetas.jsonl` (k corridas por ítem) |
| `acuerdo.py` | 4 | etiquetas humano/LLM → α de Krippendorff |
| `dificultad.py` | 4 | etiquetas → scores, pares, pruebas, robustez |
| `estadistica.py` | 2-5 | BCa, permutación, Jeffreys, BH, Spearman con IC |
| `modelo.py` | 5 | config + etiquetas → `prediccion.json`, simulaciones |
| `backtest.py` | 5 | historial → puntuaciones Brier y log |
| `banco.py`, `armado.py`, `sorteo.py` | 6 | → `simulacros.json` |
| `salida/` (plantillas Jinja LaTeX/HTML) | 6-7 | → PDF y reporte |
| `cli.py` | todas | `ap ...` |

## Carpeta de una materia

```
materias/<m>/
  materia.yaml          configuración (arquetipos, rasgos, formato, objetivo)
  verificadores.py      cómo comprobar soluciones del banco (sympy, numérico...)
  banco/                ejercicios generados y aprobados (yaml)
  datos/                (no se versiona) crudo/, extraido/
  salidas/              (no se versiona) *.jsonl, prediccion, simulacros, reporte
  predicciones/         diario de predicciones congeladas (sí se versiona)
```

## Capa LLM

- Roles: `extraccion` (visión), `clasificacion`, `etiquetado`, `generacion`, `barato`.
- Cada llamada recibe un prompt de `prompts/<nombre>.md` (versión en el encabezado) y un
  `response_format` Pydantic. Si la validación falla, se reintenta con el error y luego se marca
  para revisión humana.
- Caché: clave = hash(modelo, versión del prompt, entrada). Volver a correr no cuesta.
- `salidas/llm_log.jsonl`: rol, modelo, tokens, costo estimado y duración.
- Pruebas: `AP_LLM_FALSO=1` lee respuestas de `tests/fixtures/llm/<hash>.json`.

## Agentes de código

- Antigravity lee `AGENTS.md` y `.agents/workflows/*.md` (comandos con `/`).
- Claude Code lee `CLAUDE.md`, que importa `AGENTS.md`.
- Opcional en la fase 7: servidor MCP que expone `ap` para que cualquier agente lo use como
  herramienta.
