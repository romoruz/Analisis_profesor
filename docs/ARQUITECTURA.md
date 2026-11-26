# Arquitectura

## Dos capas

| Capa | Quién la ejecuta | Qué hace |
|---|---|---|
| **Juicio** (`PROTOCOLO.md`) | La IA del chat: Claude, ChatGPT, Gemini, Antigravity, Claude Code | Transcribir fotos y fórmulas, corregir el inventario, decidir la fuente de cada pregunta, definir arquetipos, etiquetar rasgos, Bloom y DOK, escribir el banco y la guía |
| **Cálculo** (`ap.py`) | El sandbox de esa misma IA, o tu terminal | Ingesta, segmentación, similitud, dificultad, modelo bayesiano, verificación y armado de simulacros |

La capa de cálculo **no llama a ningún LLM**: es determinista y reproducible con semilla. Así,
el mismo material da los mismos números en cualquier plataforma, y lo único que varía entre IAs
es el juicio, que queda escrito en archivos revisables.

## Restricciones de portabilidad

- Python ≥ 3.10, sin instalación: `python ap.py ...` agrega `src/` al path.
- Núcleo: librería estándar más numpy y scipy. Si faltan, el modo reducido usa Python puro, más
  lento.
- Opcionales con respaldo: sklearn (TF-IDF), sympy (fórmulas y verificación), fitz, pypdf o
  pdfplumber (PDF), pdflatex (PDF de simulacros).
- Configuración en TOML (`tomllib` es estándar desde 3.11; en 3.10, respaldo a JSON).
- Nada de red: el sandbox de ChatGPT no tiene internet.

## Carpeta de trabajo de un análisis

```
trabajo/<id>/                    (ignorado por git)
  materia.toml                   paso 5.1  (IA)
  supuestos.md                   pasos 0.3 a 9  (IA)
  00_crudo/                      paso 1  [script]
  01_inventario.csv              paso 1  [script] + corrección (IA)
  02_texto/<doc>.md              paso 1  [script] + transcripción (IA), formato fijo
  pendientes_transcripcion.txt   paso 1  [script]
  03_items.jsonl                 paso 3  [script]
  04_similitud.json              paso 4  [script]
  05_etiquetas.csv               paso 5  plantilla [script] + llenado (IA)
  06_dificultad.json             paso 6  [script]
  07_modelo.json                 paso 6  [script]
  08_banco.md                    paso 7  (IA) + verificación [script]
  simulacros.json                paso 8  [script]
  entregables/                   GUIA_PARCIAL.md (IA), SIMULACROS.md, SOLUCIONES.md, .tex, .pdf
```

## Módulos (`src/analisis_profesor/`)

| Módulo | Paso | Notas |
|---|---|---|
| `esquemas.py` | todos | dataclasses + JSONL (hecho) |
| `cli.py` | todos | argparse; `diagnostico` hecho, el resto pendiente |
| `config.py` | 5-8 | lee `materia.toml` y llena valores por defecto del Anexo A |
| `ingesta.py`, `pdf.py` | 1 | zip, inventario, extracción con respaldos |
| `segmentacion.py` | 3 | parser del formato del paso 2 |
| `similitud.py` | 4 | portado de legacy + TF-IDF en Python puro |
| `etiquetas.py` | 5 | CSV ↔ Etiqueta, plantilla, convertidor legacy |
| `estadistica.py` | 6 | BCa, permutación, Jeffreys, Spearman con IC, BH, α de Krippendorff (Python puro con numpy) |
| `dificultad.py` | 6 | portado de legacy, rasgos configurables |
| `modelo.py` | 6 | portado de legacy + material y molde calculados desde etiquetas |
| `banco.py` | 7 | parser de `08_banco.md` y ejecución de verificaciones |
| `armado.py`, `salida.py` | 8 | banda de dificultad, sorteo balanceado, Markdown y LaTeX |

## Contratos

`esquemas.py` define Documento, Item, Etiqueta, Prediccion y Simulacro. Los formatos que escribe
la IA (Markdown del paso 2, CSV del paso 5, `08_banco.md`) están especificados en
`PROTOCOLO.md`. Si cambia uno, cambian los dos, y sube la versión del protocolo.
