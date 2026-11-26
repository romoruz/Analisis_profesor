# Simulación (EST-24107): qué se reutilizó, qué se mejoró y qué salió para el Segundo Parcial

Alcance: vectores aleatorios (3.4-3.5), integración Monte Carlo y reducción de varianza (tema 5).
MCMC, remuestreo (bootstrap y jackknife) y simulación de procesos estocásticos van hasta el
final: quedan fuera del modelo y de los simulacros (sus ejercicios siguen en el banco para el final).
Profe: Jorge de la Vega. Semestre 2026-II.

## 1. ¿Sirvió el código que ya tenías?

Sí. Casi todo el motor se reutilizó; lo que cambió es lo que depende de la materia y una pieza
nueva para recortar preguntas.

| Pieza | Uso en Simulación |
|---|---|
| `nucleo/similitud.py` (TF-IDF, línea base p95) | Igual. Exámenes contra tareas, contra láminas y examen contra examen |
| `nucleo/dificultad.py` (score por rasgos, pares, robustez) | Igual, pero ahora los rasgos son de cada materia (antes estaban fijos los de SD-II) |
| `nucleo/modelo.py` (modelo bayesiano, rejilla, sorteo balanceado) | Igual, más la opción de material partido en tarea y clase (la idea del Parcial 3 de PL) |
| Regla de Laplace, pesos tarea 2 / clase 1 / teorema 0.5, temario como restricción (kappa) | Igual |
| Metodología de PL, sección 4 (qué hacer sin pauta ni examen previo) | Es justo el caso de este parcial: se siguió paso por paso |
| Banco, verificación y PDF de SD-II | Se rehicieron para Simulación (numpy/scipy en vez de sympy) |

PL y SD-II siguen dando exactamente lo mismo: se volvieron a correr después de los cambios y los
JSON de salida son idénticos byte por byte; el paso 6 de PL sigue en 12/12.

## 2. Mejoras

1. **Rasgos de dificultad por materia.** `nucleo/dificultad.py` tenía los rasgos de SD-II
   escritos adentro. Ahora cada curso pasa los suyos. Para Simulación: entregables, cálculo a
   mano, derivación, demostración, dimensión, técnicas combinadas, cómputo (programar),
   interpretación y casos. La plantilla trae estos como punto de partida.

2. **Preguntas de distinto valor.** El profe pone preguntas de 10 y de 20 puntos. La tabla de
   rasgos tiene `puntos_max`; la dificultad de un examen es el promedio ponderado por puntos
   (la suma simple castigaba al examen con más preguntas cortas) y la comparación contra
   calificaciones usa el valor de cada pregunta.

3. **Material partido en tarea y clase sin examen previo.** No hay ningún Segundo Parcial de
   este profe. El modelo genérico ahora acepta `material = {tarea, clase}` y una probabilidad
   de que cada pregunta salga de la tarea, estimada con los Primeros Parciales (9 de 13
   preguntas salieron de una tarea, Beta(10, 5)).

4. **Recorte por incisos (nuevo, `nucleo/armado.py`).** La calibración mostró que el profe toma
   un pedazo del ejercicio de tarea. Los primeros ejercicios que escribí salían entre 3 y 6 en
   la escala, cuando una pregunta suya de 20 puntos promedia 2.4. Ahora cada ejercicio del banco
   se etiqueta inciso por inciso (qué cálculo, qué derivación, qué técnica, qué incisos necesita
   antes) y el armador elige el recorte que deja la pregunta y el examen en la dificultad del
   profe. Dos candados: todo recorte incluye un inciso "núcleo" (donde de verdad se practica el
   tipo de pregunta) y toda pregunta que no sea de teoría trae números para hacer a mano.

5. **Patrón de puntos.** El número de preguntas fija el patrón, como en sus exámenes: 6 preguntas
   son cuatro de 20 y dos de 10; 7 preguntas son tres de 20 y cuatro de 10. Los 10 puntos van a
   los tipos más cortos.

6. **Búsqueda local en vez de producto cartesiano.** Con recortes hay cientos de opciones por
   hueco; el armador de SD-II probaba todas las combinaciones. Ahora es búsqueda local con
   semilla fija (reproducible).

7. **Detalles.** `nucleo/extraer.py` acepta `excluir=` (apuntes escaneados) y ya no llena la
   pantalla de avisos de pdftotext. El paso 6 dice al final qué ejercicio del banco es cada
   pregunta de cada simulacro, para encontrar su respuesta.

## 3. Resultados

**Datos.** Tareas 1 a 4, láminas de la Semana 7 (métodos particulares y vectores aleatorios) y
de la Semana 11 (integración Monte Carlo y reducción de varianza), los apuntes a mano y dos
Primeros Parciales: la reposición de 2024 y el del 5/10/2026 de Rodrigo (53 puntos).

**Reciclaje.** Este profe no recicla como el de SD-II.
- El Parcial 1 de 2026 no se parece a la reposición de 2024 (máximo 0.17, contra una línea base
  de 0.15 entre ejercicios distintos): no repite exámenes.
- TF-IDF ve poco reciclaje literal: el examen redacta corto y con otros números. Leyendo, 9 de
  13 preguntas nacen de una tarea y 4 de la clase (RANDU, la prueba de póker, la distribución
  empírica, dos maneras de construir una ji-cuadrada).
- La tarea sí copia la clase en Wishart (0.58 contra la lámina de Bartlett); la Tarea 4 adapta
  las láminas de multinomial y normal multivariada.

**Dificultad (escala 0-10).**
- Tareas 2.89 contra exámenes 2.21. Por pares, la pregunta de examen es 1.69 más fácil que su
  ejercicio fuente, en 100% de las 2000 perturbaciones de pesos. Sin contar el rasgo de cómputo
  (en la tarea se programa), la diferencia por pares sigue en 1.41.
- Pregunta de 20 puntos: 2.43 en promedio. De 10 puntos: 1.95.
- Parcial 1 de 2026: 2.60. Reposición 2024: 1.97. Los simulacros apuntan a 2.60 (el examen más
  reciente; las reposiciones suelen salir más fáciles).
- **Lo que le costó a Rodrigo no es lo largo, es lo nuevo.** El score se correlaciona al revés
  con los puntos que perdió (Spearman -0.62, p = 0.14, 7 preguntas). En las preguntas nuevas
  (las que salen de la clase) perdió 77% de los puntos; en las adaptadas de la tarea, 32%.

**Probabilidad de que salga cada tipo** (base, y mínimo-máximo en 27 combinaciones de
hiperparámetros), ordenado por el mínimo:

| Tipo | Base | Mín | Máx |
|---|---|---|---|
| N Teoría corta (justificar, demostrar, comparar métodos) | 0.86 | 0.83 | 0.88 |
| C Dirichlet, Wishart (Bartlett), esfera | 0.79 | 0.69 | 0.87 |
| E Integración Monte Carlo | 0.77 | 0.69 | 0.83 |
| B Multinomial, método condicional, mezclas | 0.75 | 0.65 | 0.85 |
| A Normal multivariada (Cholesky, espectral) | 0.68 | 0.59 | 0.78 |
| D Correlacionadas y cópulas (NORTA) | 0.53 | 0.51 | 0.60 |
| G Variables de control | 0.44 | 0.37 | 0.51 |
| J Estratificado y números comunes | 0.40 | 0.32 | 0.47 |
| F Antitéticas | 0.35 | 0.27 | 0.43 |
| H Condicionamiento | 0.35 | 0.26 | 0.43 |
| I Muestreo de importancia | 0.34 | 0.26 | 0.41 |

- Alguna pregunta de vectores aleatorios: 0.999. Alguna de reducción de varianza (F a J): 0.96.
  Cada técnica por separado anda entre 0.34 y 0.44, pero casi seguro sale una de ellas.
- Número de preguntas: 6 o 7 con 0.39 cada uno; 5 con 0.19.

**Simulacros.** 5 exámenes de 100 puntos, todos en `docs/Simulacros_Parcial2.tex` (y su PDF),
solo enunciados. Entre los cinco aparecen los 11 tipos del alcance, en proporción a su probabilidad.
La guía de estudio está en `docs/Guia_Parcial2_Simulacion.tex` (y su PDF).

| Simulacro | Preguntas | Dificultad ponderada |
|---|---|---|
| 1 | 6 | 2.44 |
| 2 | 6 | 2.55 |
| 3 | 7 | 2.33 |
| 4 | 5 | 2.55 |
| 5 | 7 | 2.44 |

Meta 2.60. Las respuestas están en `salidas/verificacion.txt` (67 de 67 ejercicios del banco
verificados); ábrelo solo después de hacerlos. Al final de ese archivo dice qué ejercicio es cada
pregunta.

## 4. Cómo estudiar con esto

- **Teoría de la clase primero.** Es lo que más puntos le quitó a Rodrigo y lo que más
  probablemente sale (N, 0.86). Los resultados de las láminas: corolario de antitéticas,
  Var(E(X|Z)) ≤ Var(X), densidad óptima de muestreo de importancia, Dirichlet con Gammas,
  Bartlett, por qué NORTA no conserva Pearson, Cholesky contra espectral.
- **Después la Tarea 4 y los ejercicios 7 a 10 de la Tarea 3, pero a mano.** En el examen te dan
  las uniformes o las normales y piden 2 o 3 observaciones, no 10,000.
- **Luego los simulacros**, con cronómetro de 90 minutos y la rúbrica de la Metodología de PL.

## 5. Limitaciones

- No hay ningún Segundo Parcial de este profe. Todo descansa en el material y en dos Primeros
  Parciales de otro temario.
- Números aleatorios comunes está en el temario pero no en el material que recibí. Tiene el peso
  mínimo de "anunciado en temario" (el +1 de `CLASE['J']` en `config_parcial2.py`).
- Para el final: agrega K, L y M (están en `TEMAS_DEL_FINAL`) a `ARQUETIPOS` en una configuración
  nueva y quita `FUERA_DE_ALCANCE`; los ejercicios ya están escritos y verificados.
- No hay tarea de integración Monte Carlo ni de reducción de varianza (¿Tarea 5?). Si llega,
  agrégala a `rasgos_dificultad.csv` y a `TAREA` y vuelve a correr: cambiaría bastante el peso de
  esos temas.
- Los apuntes a mano tienen huecos: faltan algunas clases y la de integración Monte Carlo no
  está.
- Los rasgos, sus pesos, los minutos y las etiquetas son juicio mío. La robustez cubre los pesos,
  no el etiquetado. Y el score mide trabajo, no novedad: por eso no predice lo que le cuesta al
  alumno.
- El banco tiene números limpios. Si el profe pone cuentas feas, el examen se sentirá más pesado.

## 6. Uso en otra materia

1. Copia `cursos/_plantilla` a `cursos/<materia>`.
2. Pasa los PDFs a texto y transcribe los exámenes en foto con una línea `Pregunta N` por
   pregunta.
3. Ajusta `RASGOS` y llena `rasgos_dificultad.csv` (con `fuente`, `puntos_max` y, si los sabes,
   tus `puntos`).
4. Llena la configuración (con molde si hay exámenes previos del mismo parcial; con material
   partido en tarea y clase si no) y corre `python3 src/correr.py 5`.
5. Para el banco, la verificación y el LaTeX, copia de `cursos/simulacion/src` los pasos 05 a 07,
   `banco_ejercicios.py` y `verificacion.py`, y cambia los ejercicios.
6. Cuando llegue el examen real, agrégalo a la tabla y vuelve a correr.
