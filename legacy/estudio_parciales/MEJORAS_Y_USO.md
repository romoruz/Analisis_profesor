# Qué se reutilizó del repo de PL, qué se mejoró y qué salió para SD-II

## 1. ¿Sirvió el código de Programación Lineal?

Sí, la parte estadística se reutilizó casi completa; la parte matemática no.

| Pieza del repo de PL | Uso en SD-II |
|---|---|
| `02_similitud.py` (TF-IDF, línea base p95) | Se reutilizó; ahora es `nucleo/similitud.py` y sirve para cualquier lista de textos |
| `03` y `04` (modelo bayesiano por tipos, rejilla, sorteo con semilla) | Se juntaron en un solo motor configurable, `nucleo/modelo.py` |
| Etiquetado manual por tipo y pesos tarea 2 / clase 1 / teorema 0.5 | Igual, en `config_parcial3.py` |
| Regla de Laplace para rasgos y nivel de cada pregunta | Igual (casi copia / adaptación / nueva) |
| `herramientas/simplex.py`, `sensibilidad.py`, `05`, `06` | No aplican. Se reemplazaron por un banco de ejercicios de SD-II y una verificación con sympy e integración numérica |

El repo de PL quedó intacto en `cursos/programacion_lineal/`: el paso 6 sigue dando 12/12 y los
sorteos salen idénticos con las mismas semillas.

## 2. Mejoras

1. **Núcleo genérico.** Antes cada parcial era un script con los datos adentro. Ahora el motor
   está en `nucleo/` y cada materia solo aporta un archivo de configuración, una tabla de rasgos
   y su banco de ejercicios. `cursos/_plantilla/` arranca una materia nueva.

2. **Score de dificultad tarea vs examen (nuevo).** Cada ejercicio de tarea y cada pregunta de
   examen se describe con 9 rasgos: entregables pedidos, parámetro, dimensión, técnica, si la
   linealización no decide, demostración, carga de cuentas, análisis global y número de casos.
   El score es una suma ponderada reescalada a 0-10. Se compara de dos formas:
   - **global:** media de exámenes contra media de tareas;
   - **por pares:** cada pregunta contra el ejercicio del que salió.

   Como los pesos son opinión, todo se repite 2000 veces con pesos perturbados entre 0.5× y
   1.5×. Además, el score se contrastó con los puntos que Rodrigo perdió por pregunta.

3. **Banda de dificultad para generar ejercicios.** El generador ya no se queda con el primer
   ejercicio "bonito". Para cada tipo de pregunta hay un score objetivo: la media de las preguntas
   de examen de ese tipo o, si nunca salió en examen, la media de la tarea más el delta examen-tarea.
   Solo entran ejercicios a ±1 punto del objetivo. Entre las combinaciones válidas se elige la que
   deja la dificultad total del simulacro más cerca de la de los Parciales 2 viejos.

4. **Sorteo balanceado.** La Metodología de PL ya advertía que cinco sorteos independientes no son
   un promedio. Ahora se sortean 150 exámenes distintos y se eligen los 5 que, juntos, reproducen
   mejor las probabilidades. Con los sorteos independientes del modelo de SD-II, H (demostración
   tipo Poincaré-Bendixson) salía en 5 de 5 simulacros y G (conjuntos límite) en 0 de 5, aunque
   las dos tienen probabilidad cercana a 0.45. Con el balanceado, cada tipo sale 1 a 3 veces, en
   proporción a su probabilidad. Los sorteos independientes se siguen guardando en el JSON para
   comparar.

5. **Reciclaje examen contra examen.** Además de comparar cada pregunta con las tareas, se compara
   con las preguntas de exámenes anteriores. En SD-II esta es la señal más fuerte del análisis.

6. **Verificación por tipo de ejercicio.** Se comprueba con sympy la energía potencial y la
   clasificación de equilibrios, los valores de bifurcación por resultante, las ecuaciones en
   polares, los signos de r' en el anillo atrapante, el criterio de Dulac, la derivada de Lyapunov
   y el intervalo maximal. Con integración numérica se comprueban los ciclos límite y la δ de la
   cuenca. Pasan 44 de 44 ejercicios del banco; las 7 demostraciones se revisaron a mano.

7. **Detalles.**
   - El sorteo ya no puede quedarse en un ciclo infinito cuando hay pocas combinaciones posibles.
   - Los exámenes en foto se transcriben a texto con un formato fijo, `Pregunta N`.
   - `05` y `06` del repo de PL fallaban con `python -I` (modo aislado) porque importan
     `herramientas` desde la carpeta del script. Corridos normal funcionan; no se tocaron.

## 3. Resultados para el Parcial 3 de SD-II

**Supuesto central.** Este semestre hay un parcial más, así que lo que antes era el Parcial 2 es
ahora el Parcial 3. Los Parciales 2 del 29/04/2020 y del 04/05/2026 son el "molde". El Parcial 2
de este semestre (19/10/2026, el del 7) fue del capítulo 3; sirve para saber cómo examina el
profe, no qué va a preguntar.

**El profe recicla mucho, sobre todo de sus propios exámenes.**
- La Tarea 5 es literalmente los ejercicios 3 a 12 de la Tarea 4 (10 de 10).
- Similitud examen contra examen previo:
  - 0.98: la pregunta 2 del 19/10/2026 es la 3 del 04/03/2026;
  - 0.88: el potencial de mayo de 2026 tiene la misma redacción que el de 2020;
  - 0.86: la bifurcación de mayo de 2026 es la de 2020, con la misma ecuación.
- La línea base entre ejercicios distintos es 0.18.
- La pregunta 1 del 19/10/2026 es literal el ejercicio 3a de la Tarea 4.

**Dificultad (escala 0-10).**
- **Todo el curso:** exámenes 2.62 y tareas 2.57 en promedio, prácticamente iguales.
  - Por pares, la pregunta de examen es 0.27 más fácil que su ejercicio fuente, en 100% de las
    perturbaciones de pesos.
  - En los capítulos 2 y 3 el profe toma un pedazo del ejercicio de tarea.
- **Temas del Parcial 3:** por pares, el examen es 0.40 más difícil que su fuente, en 100% de las
  perturbaciones.
  - Aquí el profe agrega un entregable: ω y α-límites de todo punto, diagrama de bifurcación,
    "demostrar que es el único valor".
  - Esas preguntas caen entre los percentiles 60 y 95 de las tareas.
  - Ojo: el 0.40 lo empujan sobre todo dos preguntas (2020-P3 y mayo 2026-P1).
- **Dificultad total por examen:**

  | Examen | Total |
  |---|---|
  | Parcial 2 de 2020 | 13.4 |
  | Parcial 2 de mayo de 2026 | 12.3 |
  | Parcial 2 de este semestre | 8.0 |
  | Parcial 1 de marzo de 2026 | 8.4 |

  Si el supuesto central es correcto, el Parcial 3 va a ser bastante más pesado que el Parcial 2
  donde Rodrigo sacó 7.
- **Contra calificaciones:** el score se correlaciona con los puntos perdidos por Rodrigo
  (Spearman 0.69, p = 0.06, solo 8 preguntas). Es una validación débil pero va en la dirección
  correcta.

**Probabilidad de que salga cada tipo (base, y mín-máx en 27 combinaciones de hiperparámetros).**

| Tipo | Base | Mín | Máx |
|---|---|---|---|
| A Método del potencial | 0.54 | 0.45 | 0.66 |
| G Demostración de conjuntos límite | 0.46 | 0.30 | 0.58 |
| F Existencia de órbitas periódicas | 0.46 | 0.37 | 0.55 |
| B Bifurcación en EDO de 2o orden | 0.44 | 0.33 | 0.57 |
| H Demostración tipo Poincaré-Bendixson | 0.43 | 0.32 | 0.57 |
| I Intervalo maximal, unicidad, simetría | 0.40 | 0.32 | 0.48 |
| E Polares con parámetro (Hopf y similares) | 0.38 | 0.32 | 0.43 |
| C Bifurcación en sistema plano | 0.33 | 0.23 | 0.40 |
| D Polares sin parámetro, ω/α-límites | 0.32 | 0.19 | 0.44 |
| J Lyapunov | 0.26 | 0.19 | 0.31 |

- D está castigado porque ya salió el 19/10.
- Ordenando por el mínimo, lo más seguro es A, F, B, I, E.
- La probabilidad de que haya al menos una demostración (G o H) es de alrededor de 0.9. Cuatro de
  los cinco simulacros traen una.

**Simulacros.** Hay 5, de 4 preguntas de 2.5 puntos cada uno, en
`cursos/sistemas_dinamicos_ii/docs/Simulacros_Parcial3.pdf`.

| Simulacro | Dificultad total |
|---|---|
| 1 | 13.3 |
| 2 | 15.5 |
| 3 | 13.4 |
| 4 | 14.5 |
| 5 | 13.6 |

La meta era 12.8. Los simulacros 2 y 4 salen más pesados porque traen los tipos C y H, que nunca
han salido en examen y cuya banda viene de la tarea. Las soluciones verificadas están en
`salidas/verificacion.txt`; ábrelo solo después de hacerlos.

**Cómo estudiar con esto.**
- **Material literal primero.** Por el reciclaje, lo más rentable es hacer todos los ejercicios de
  las Tareas 4 y 5 y los dos Parciales 2 viejos tal cual. Sobre todo:
  - x'' = x² − λx + 9, que salió dos veces idéntica;
  - el método del potencial con funciones trigonométricas;
  - las demostraciones de ω(p): compacto, invariante, no vacío, cerrado.
- **Después los simulacros,** con cronómetro y la rúbrica de la Metodología de PL.

## 4. Limitaciones

- Hay solo dos Parciales 2 viejos de este temario. Un examen nuevo mueve más las probabilidades
  que cualquier cambio de hiperparámetros.
- El supuesto "Parcial 3 de hoy = Parcial 2 de antes" no está confirmado. Si el profe anuncia
  temario, agrega `cobertura` en `config_parcial3.py`.
- Los rasgos de dificultad, sus pesos, los minutos por tipo y las etiquetas son juicio mío. La
  robustez solo cubre la incertidumbre de los pesos, no la del etiquetado.
- TF-IDF falla con fórmulas: la pregunta 1 del 19/10 no aparece como copia del ejercicio 3a de la
  Tarea 4 porque pdftotext desarma las ecuaciones. El origen de cada pregunta se decidió leyendo.
- La foto del Parcial 1 de marzo de 2026 está rota y no tiene calificación por pregunta.
- El banco tiene números limpios por diseño. Si el profe pone cuentas feas, el examen se va a
  sentir más pesado que los simulacros.

## 5. Uso en otra materia

1. Copia `cursos/_plantilla` a `cursos/<materia>`.
2. Pasa los PDFs a texto. Si hay fotos de exámenes, transcríbelas.
3. Llena `rasgos_dificultad.csv`: una fila por ejercicio de tarea y por pregunta de examen, con su
   fuente.
4. Llena `config_parcial.py` y corre `python3 src/correr.py 5`.
5. Para el PDF, copia del curso de SD-II el banco, la verificación y los pasos 05 y 07, y cambia
   las familias de ejercicios por las de tu materia.
6. Cuando llegue el examen real, agrégalo a la tabla de rasgos y al `MOLDE`, y vuelve a correr.
