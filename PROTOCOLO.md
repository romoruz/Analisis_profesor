# PROTOCOLO: de un .zip de material a simulacros y guía del parcial

> **Si eres una IA (Claude, ChatGPT, Gemini, Antigravity, Claude Code...) y te dieron este
> repositorio, este archivo es tu manual.** Síguelo paso a paso. Tú haces el trabajo de leer,
> transcribir, etiquetar y redactar. Los scripts de `ap.py` hacen las cuentas (similitud,
> estadística, sorteo) para que sean reproducibles y no inventadas.

Versión del protocolo: 5

---

## 0. Antes de empezar

### 0.1 Consigue el kit

- Si tienes el repo clonado o descomprimido, trabaja desde su raíz.
- Si tienes acceso a internet pero no a git, descarga
  `https://github.com/romoruz/Analisis_profesor/archive/refs/heads/main.zip`.
- Si no tienes ninguna de las dos, pídele al usuario que suba ese zip.

### 0.2 Diagnóstico

Ejecuta `python ap.py diagnostico`. El resultado decide el **modo**:

| Modo | Cuándo | Qué cambia |
|---|---|---|
| **Completo** | Puedes ejecutar Python y hay numpy y scipy | Todo el protocolo |
| **Reducido** | Puedes ejecutar Python, pero falta numpy o scipy | `ap.py` usa sus versiones lentas en Python puro; el sorteo tarda más |
| **Sin código** | No puedes ejecutar código | Haz los pasos marcados [script] a mano con las reglas del Anexo C, y dilo en la guía |

### 0.3 Pregunta al usuario solo lo indispensable

Pregunta en un solo mensaje, y solo lo que no puedas deducir del material:

1. Materia y profesor.
2. Qué parcial viene, en qué fecha y qué temas entran (si ya los anunció el profe).
3. Si este semestre hay más o menos parciales que en los exámenes viejos (decide qué exámenes
   viejos sirven de "molde").
4. Opcional: sus calificaciones por pregunta en los exámenes ya presentados.

Si el usuario dice "hazlo todo", no preguntes nada: usa supuestos razonables y anótalos en
`supuestos.md`.

---

## 1. Ingesta [script]

```
python ap.py ingesta <ruta/al/material.zip> --materia <id_corto>
```

Esto crea `trabajo/<id>/` con:

- `00_crudo/`: el zip descomprimido.
- `01_inventario.csv`: una fila por archivo con `tipo` adivinado (examen, tarea, clase, notas,
  temario, pauta), fecha y parcial.
- `02_texto/<doc>.md`: el texto extraído de cada PDF con capa de texto.
- `pendientes_transcripcion.txt`: fotos, escaneos y PDFs sin texto, o con fórmulas rotas.

**Tú:** revisa `01_inventario.csv` y corrige `tipo`, `fecha` y `parcial` donde el adivinado sea
malo. Los exámenes son lo más importante: asegúrate de que estén todos y bien fechados.

## 2. Transcripción (tú)

Para cada archivo de `pendientes_transcripcion.txt`, y para todo examen aunque tenga texto
(pdftotext desarma fórmulas), **mira el documento** y escribe `02_texto/<doc>.md` con este
formato exacto:

```markdown
# <Materia> - <Parcial> - <AAAA-MM-DD>
tipo: examen
duracion_min: 90
calificacion_alumno: 2, 1, 0.5, 0     <- solo si se conoce, en orden de pregunta

## Pregunta 1 (2.5 puntos)
Enunciado con fórmulas en LaTeX: $\dot x = y - x(x^2+y^2)$.

### a)
Inciso a.

## Pregunta 2 (2.5 puntos)
...
```

- Incisos: usa siempre letras minúsculas (`### a)`, `### b)`), aunque el profesor numere con
  `(i)`, `(ii)` o `1)`, `2)`.
- Tareas: igual, pero con `## Ejercicio N`; usa `### a)`, `### b)` solo cuando los incisos
  sean ejercicios independientes (otros datos u otro objeto). Por ejemplo, si un ejercicio pide
  lo mismo para varios sistemas o ecuaciones distintos, cada uno va en su propio `### a)`.
- Láminas y notas: no se segmentan por pregunta. Basta un resumen de temas y los resultados
  importantes (teoremas, definiciones, ejemplos resueltos) con `## Tema` por sección.
- Transcribe fielmente: no corrijas ni completes lo que no se lee; marca `[ilegible]`.

## 3. Segmentación [script]

```
python ap.py items <id>
```

Lee `02_texto/*.md` y escribe `03_items.jsonl` (una pregunta, ejercicio o inciso por línea).
En exámenes el ítem etiquetable es la pregunta (`Q3`) y sus incisos son ítems hijos con
`padre_id`. En tareas, si los incisos son ejercicios independientes (otros datos u otro
objeto, marcados con `### a)`), cada inciso es el ítem etiquetable (`T1:2a`); si no, lo es el
ejercicio.
También imprime un conteo por documento. **Tú:** compara el conteo con lo que viste; si no
coincide, arregla los encabezados del `.md` y vuelve a correr.

## 4. Reciclaje [script + tú]

```
python ap.py similitud <id>
```

Escribe `04_similitud.json` con:

- la línea base (p95 entre ejercicios distintos);
- para cada pregunta de examen, sus 3 candidatos más parecidos entre tareas, clase y exámenes
  previos;
- una clasificación sugerida (casi copia, adaptación o nueva).

**Tú:** la similitud de texto falla con fórmulas. Para cada pregunta de examen decide, leyendo,
de dónde sale. Anótalo en `fuente` y `nivel` del paso 5. Busca sobre todo:

- **examen ← examen anterior**: la señal más fuerte de reciclaje;
- **tarea nueva ← tarea vieja**;
- **preguntas "nuevas"**: salen de la clase o de ningún lado.
- **Convención para tareas:** se asume que las tareas se repiten entre semestres, por lo que un
  examen viejo puede citar un ejercicio de una tarea actual como su `fuente`.

## 5. Arquetipos y etiquetas (tú)

### 5.1 Arquetipos

Define de 6 a 12 **tipos de pregunta** para el parcial objetivo, con una letra cada uno, a
partir del temario y de los ejercicios. Un arquetipo es "lo que se practica" (p. ej. "Método del
potencial: U, equilibrios, estabilidad, retrato fase"), no un tema amplio. Escríbelos en
`trabajo/<id>/materia.toml` (plantilla en `materias/_plantilla/materia.toml`) con sus minutos
estimados.

### 5.2 Etiquetas

```
python ap.py plantilla-etiquetas <id>
```

Esto crea `05_etiquetas.csv` con una fila por ítem. Llena para **cada pregunta de examen y cada
ejercicio de tarea del alcance**:

| Columna | Valor |
|---|---|
| `arquetipo` | Letra, o `-` si no es del alcance |
| `fuente` | id del ítem del que sale (solo en exámenes) |
| `nivel` | `casi copia` \| `adaptación` \| `nueva` |
| rasgos de la rúbrica | Enteros según el Anexo A y `materia.toml` |
| `bloom` | recordar, comprender, aplicar, analizar, evaluar o crear (Anexo B) |
| `dok` | 1-4 (Anexo B) |
| `minutos` | Estimado para un alumno preparado |
| `puntos` | Puntos que obtuvo el alumno, si los dio |

**Consistencia:** etiqueta los rasgos de los exámenes **dos veces**, la segunda sin mirar la
primera, y corre `python ap.py acuerdo <id>`. Revisa a conciencia los rasgos con desacuerdo y
deja una sola versión.

**Punto de control:** muestra al usuario la tabla de arquetipos y las fuentes de cada pregunta
de examen (no todos los rasgos). Si dijo "hazlo todo", sigue.

## 6. Dificultad y modelo [script]

```
python ap.py dificultad <id>
python ap.py modelo <id>
```

- `06_dificultad.json`:
  - score de 0 a 10 por ítem;
  - examen contra tarea, global y por pares, con IC bootstrap y prueba de permutación;
  - robustez de pesos;
  - correlación con las calificaciones, si las hay.
- `07_modelo.json`:
  - probabilidad de que salga cada arquetipo, con intervalo creíble y rango de sensibilidad;
  - probabilidad de que haya demostración;
  - combinaciones más probables;
  - backtesting, si hay 2 o más exámenes del mismo parcial.

Los pesos del material, el molde, la rotación y el formato salen **automáticamente** de
`05_etiquetas.csv` y `materia.toml`. No los inventes a mano.

## 7. Banco de ejercicios (tú) + verificación [script]

Para cada arquetipo con probabilidad ≥ 0.2, escribe **al menos 3 ejercicios nuevos** en
`08_banco.md` con este formato:

```markdown
## B-A-1
arquetipo: A
nivel: adaptación
familia: A-potencial
basado_en: T4:12
rasgos: entregables=4, parametro=0, tecnica=1, demostracion=0, algebra=1, casos=1
enunciado: |
  Usando el método del potencial ... $\ddot x = \sin x \cos x$ ...
solucion: |
  U(x) = ...
verificacion: |
  # Python (sympy/numpy) que hace assert de la solución.
```

- `nivel:` indica la distancia al material original (`casi copia`, `adaptación` o `nueva`);
  es opcional y ayuda a balancear el armado.
- `familia:` identifica variantes estructuralmente análogas para penalizar que aparezcan en
  simulacros distintos (opcional; por defecto toma el valor de `basado_en` o el id).
- En ejercicios puramente demostrativos, escribe `verificacion: manual` en una línea.
- Varía números y funciones, pero conserva lo que se practica y la redacción del profe.
- Las variantes deben quedar a ±1 punto de dificultad del objetivo que reporta `07_modelo.json`
  para su arquetipo. Calcula sus rasgos con la misma rúbrica; no "declares" la dificultad.
- Números limpios, pero no triviales.

Luego corre `python ap.py verificar <id>`. Ejecuta cada bloque `verificacion` en un
subproceso con límite de tiempo y marca el ejercicio como verificado o no (`08_verificacion.json`).
Corrige los que fallen. Las demostraciones se revisan leyéndolas y quedan marcadas con
`verificacion: manual`.

## 8. Armado de simulacros [script]

```
python ap.py armar <id> --n 5 --semilla 2026
```

Elige 5 exámenes que juntos reproducen las probabilidades del modelo (sorteo balanceado),
respetan el formato (número de preguntas, puntos, minutos) y quedan en la dificultad total de los
exámenes "molde". Escribe:

- `entregables/SIMULACROS.md`: solo enunciados, con encabezado de examen;
- `entregables/SOLUCIONES.md`: aparte;
- `entregables/simulacros.tex`, y el `.pdf` si hay `pdflatex`.

## 9. Guía del parcial (tú)

Escribe `entregables/GUIA_PARCIAL.md` con `plantillas/GUIA_PARCIAL.md`. Toda cifra sale de los
JSON de `trabajo/<id>/`; no inventes números. Secciones:

1. **Qué entra y qué supuse.**
2. **Cómo examina este profe:**
   - recicla o no, y de dónde (con los pares de similitud más fuertes);
   - examen más fácil o más difícil que la tarea (delta con su intervalo);
   - cuántas preguntas, cuántos minutos, si pone demostración.
3. **Temas por probabilidad**, en tabla con intervalo. Ordénalos por el mínimo de sensibilidad
   ("lo más seguro").
4. **Lista de estudio literal:** ejercicios de tarea y de exámenes viejos que hay que saber hacer
   tal cual, por la evidencia de reciclaje.
5. **Plan de estudio** por días hasta la fecha del examen: material literal primero, después
   simulacros con cronómetro.
6. **Limitaciones:** n de exámenes, supuestos, que las etiquetas las puso una IA y que el modelo
   predice tipos, no preguntas exactas.

## 10. Entrega

Dale al usuario los archivos de `entregables/`:

- `GUIA_PARCIAL.md`
- `SIMULACROS.md` (o el PDF)
- `SOLUCIONES.md`

Dile que abra las soluciones solo después de hacer cada simulacro. Si el entorno lo permite,
ofrece un zip de `trabajo/<id>/` para que pueda retomar el análisis en otro chat.

---

## Reglas

- **No inventes material:** ni preguntas de examen, ni fechas, ni calificaciones. Si algo no está
  en el zip, es un supuesto y va en `supuestos.md`.
- **Las cifras las dan los scripts.** En modo sin código, di explícitamente que son
  aproximaciones manuales (Anexo C).
- **Privacidad:** las calificaciones del alumno no salen de `trabajo/`.
- **Pocos datos = intervalos anchos.** Dilo; no conviertas una probabilidad de 0.45 en "va a
  salir".
- **Si el usuario sube un examen nuevo después** (por ejemplo, el parcial real), agrégalo, corre
  los pasos 3 a 6 de nuevo y compara contra `07_modelo.json` anterior (diario de predicciones).

---

## Anexo A: rúbrica de rasgos de dificultad (por defecto)

`materia.toml` puede redefinirla. Cada rasgo va de su base (no suma) a su máximo:

| Rasgo | Peso | Base-máx | Ancla |
|---|---|---|---|
| `entregables` | 0.6 | 1-5 | Número de cosas distintas que pide (calcular, clasificar, dibujar, justificar...) |
| `parametro` | 1.2 | 0-2 | 0 sin parámetro; 1 un valor crítico; 2 varios regímenes |
| `dimension` | 0.5 | 1-4 | 1 escalar; 2 plano o 2 variables; 3 R³; 4 Rⁿ o abstracto |
| `tecnica` | 1.2 | 0-3 | 0 receta directa; 1 truco o cambio de variable; 2 construcción; 3 argumento global |
| `demostracion` | 1.0 | 0-2 | 1 aplicar un teorema a un caso; 2 demostración abstracta |
| `algebra` | 0.6 | 0-2 | Carga de cuentas: 0 poca; 2 mucha o fea |
| `computo` | 0.5 | 0-2 | 1 programar algo corto; 2 simulación o programa completo |
| `casos` | 0.4 | 1-4 | Casos o regímenes a analizar |

Score = 10 · Σ peso·(x − base) / Σ peso·(máx − base).

## Anexo B: Bloom revisado y Webb DOK (resumen operativo)

- **Bloom:**
  - *recordar*: definir o enunciar;
  - *comprender*: explicar o interpretar;
  - *aplicar*: ejecutar un procedimiento conocido;
  - *analizar*: descomponer, comparar casos, encontrar la estructura;
  - *evaluar*: justificar, decidir, demostrar que algo vale;
  - *crear*: construir un objeto o argumento nuevo (contraejemplo, función de Lyapunov,
    demostración original).
- **DOK:**
  1. recordar o reproducir un procedimiento de un paso;
  2. procedimiento de varios pasos con decisiones;
  3. razonamiento estratégico, justificar o planear, con más de una vía;
  4. razonamiento extendido entre conceptos (raro en un parcial).

El verbo no decide el nivel: decide lo que hay que pensar.

## Anexo C: modo sin código

- **Similitud:** decide leyendo; no reportes números de similitud.
- **Probabilidad por arquetipo:** regla de Laplace sobre conteos ponderados,
  `p_k ≈ (molde_k + 0.5·material_k + 1) / (total + K)`, escalada al número de preguntas, y di
  que es una aproximación.
- **Simulacros:** arma 5 a mano de modo que cada arquetipo aparezca un número de veces cercano a
  5·p_k.
- **Dificultad:** reporta el score por rúbrica, pero sin intervalos.
