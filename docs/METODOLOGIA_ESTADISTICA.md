# Metodología estadística

Punto de partida: por profesor hay **2 a 4 exámenes** y unas decenas de ejercicios de tarea. Con
eso:

- las pruebas de hipótesis tienen muy poca potencia;
- la ji-cuadrada no aplica (frecuencias esperadas < 5);
- lo honesto es **estimar con incertidumbre**, comprobar la **sensibilidad** a los supuestos y
  **validar prediciendo**.

Cada paso de abajo dice qué se usa, por qué, y qué *no* se usa.

## 1. Reciclaje (¿esta pregunta salió de aquella?)

| Qué | Método | Por qué |
|---|---|---|
| Umbral "parecido de verdad" | Distribución nula con pares **no relacionados** (ejercicios distintos de la misma colección); p95 y p-valor empírico | Es lo que ya hacías (línea base 0.18). Se calibra por materia, no con un umbral fijo |
| Muchas comparaciones | Benjamini-Hochberg (FDR 10 %) | Con cientos de pares, el p95 sale ~5 % de falsos positivos por azar |
| Proporción por fuente (p. ej. 9 de 13 de la tarea) | Beta(x + ½, n − x + ½) (Jeffreys) y su intervalo | Con n chico el intervalo de Wald falla; Jeffreys es la base natural del prior Beta del modelo |
| Fórmulas | Similitud estructural (sympy/árbol) fusionada con léxica y semántica | TF-IDF falla con LaTeX desarmado |

## 2. Dificultad: tarea contra examen

**Score.** Suma ponderada de rasgos de la rúbrica, reescalada a 0-10 (como en `legacy`). Bloom,
DOK y Stein se guardan aparte como variables explicativas: no se mezclan en el score.

**Comparación por pares** (pregunta de examen contra su ejercicio fuente). n = número de pares,
típicamente de 4 a 15.

- **Estimador:** media y mediana del delta.
- **Intervalo:** bootstrap BCa (10 000 remuestras). Corrige sesgo y asimetría con n chico.
- **Prueba:** permutación exacta por cambio de signo (2ⁿ configuraciones) y Wilcoxon de rangos
  con signo exacto como chequeo. Con n ≤ 6, el p-valor mínimo alcanzable es 2/2ⁿ (0.03 con
  n = 6): se reporta.
- **Robustez de pesos:** 2000 perturbaciones U(0.5, 1.5) de los pesos (ya existe). Se reporta
  la fracción de perturbaciones con delta > 0.
- **Robustez de etiquetas (nuevo):** se usan las k corridas del LLM como perturbación del
  etiquetado. Antes solo se cubría la incertidumbre de los pesos.

**Comparación global** (todos los exámenes contra todas las tareas): bootstrap de la diferencia
de medias por grupos y Mann-Whitney o Cliff's δ como tamaño de efecto.

**Influencia.** Se repite quitando un par a la vez (*jackknife*). Así se detecta lo de SD-II,
donde dos preguntas empujaban el 0.40.

## 3. Validación de la dificultad contra calificaciones

- Spearman con IC bootstrap y p de permutación. Con n = 7 u 8 se etiqueta como **exploratorio**.
- Comparación "nueva" contra "adaptada" (77 % contra 32 % de puntos perdidos en Simulación):
  diferencia de proporciones ponderada por puntos, con intervalo bootstrap.
- Lo que no se hace: TRI (Rasch o 2PL). Necesita cientos de examinados y aquí hay uno. Si algún
  día tienes calificaciones de un grupo, un Rasch bayesiano jerárquico con priors débiles sí
  sería el modelo correcto para la dificultad empírica.

## 4. Acuerdo de etiquetado (humano contra LLM)

- α de Krippendorff con métrica ordinal para los rasgos, Bloom y DOK; nominal para el arquetipo.
- Umbrales usuales: ≥ 0.80 confiable; 0.67-0.80 solo para conclusiones tentativas; < 0.67 el
  rasgo requiere humano.
- Muestra: ≥ 20 ítems por materia, estratificados por tipo de documento.
- Además: acuerdo entre corridas del LLM (consistencia propia). Si el LLM no es consistente
  consigo mismo, no puede coincidir contigo.

## 5. Modelo predictivo (qué tipos salen)

**Estructura** (de `legacy`): mezcla de dos Dirichlet-multinomial, "material" (tareas y clase)
y "molde" (exámenes previos del mismo parcial). La probabilidad de mezcla `pi` es Beta, con
rotación de lo ya preguntado, reserva para demostración y restricciones de formato.

**Mejoras:**

1. **Intervalos creíbles** de 5 y 95 % por arquetipo, a partir de la distribución de θ
   simulada. El mín-máx sobre la rejilla es *sensibilidad*, no incertidumbre: se reportan los
   dos.
2. **Recencia:** peso `0.5^(antigüedad / vida_media)` en los conteos del molde.
3. **Jerarquía entre profesores:** `pi_tarea_j ~ Beta(μ·κ, (1 − μ)·κ)` para cada profesor j,
   con μ y κ compartidos. Pooling parcial: un profe con 2 exámenes toma fuerza de los otros.
   Con 3 a 5 profesores es casi empírico; aun así es mejor que fijar Beta(4, 6) a mano.
4. **Prior simétrico de suavizado:** el valor de 0.3 se justifica con resultados de priors
   objetivos para multinomiales con muchas celdas (a ≈ 0.8/m, Berger, Bernardo y Sun) y se
   incluye en la rejilla.

**Validación** (la parte más importante):

- **Backtesting** dejando fuera un examen a la vez, en orden temporal (solo con datos
  anteriores a cada examen).
- **Puntuaciones propias:** Brier multiclase y log score sobre "qué arquetipos aparecieron".
  Además, *cobertura*: fracción de preguntas reales cuyo arquetipo apareció en al menos uno de
  los 5 simulacros.
- **Líneas base:** uniforme, frecuencia solo en tareas y "repetir el último examen". Si el
  modelo no le gana a la uniforme, se dice.
- **Diario de predicciones:** predicción congelada con fecha antes del examen real. Es la única
  validación sin fuga de información.
- **Chequeos predictivos posteriores** en vez de bondad de ajuste clásica: se compara la
  distribución simulada de número de preguntas, minutos, fracción de reciclaje y presencia de
  demostración contra lo observado (p-valor posterior predictivo). Si hace falta una prueba de
  bondad de ajuste, se usa la multinomial exacta o por Monte Carlo, nunca la ji-cuadrada
  asintótica.

## 6. ¿Y el muestreo de importancia?

En la simulación de exámenes **no hace falta**: generar exámenes es barato y el muestreo directo
con rechazo funciona. Tiene dos usos legítimos y opcionales:

1. **Reponderar en vez de re-simular** al recorrer la rejilla de hiperparámetros: se simula
   una vez con (β₀, π₀) y se repondera a (β, π) con pesos normalizados. Hay que vigilar el
   tamaño efectivo de muestra; si baja de ~10 %, se re-simula. Acelera la rejilla.
2. **Comparar modelos** ("el profe recicla" contra "no recicla") con verosimilitud marginal
   estimada por muestreo de importancia o *bridge sampling*. Con 2 a 4 exámenes el factor de
   Bayes va a ser débil; el backtesting es más útil.

## 7. Selección de simulacros

Sorteo balanceado (de `legacy`): entre 150 exámenes candidatos, se eligen los 5 cuyas
frecuencias conjuntas se acercan más a n·p. Se agrega la meta de **cobertura**: cada arquetipo
con p ≥ 0.3 aparece al menos una vez. Se reporta la discrepancia entre frecuencia en los
simulacros y probabilidad.

## 8. Reglas de reporte

- Todo número va con incertidumbre (IC, intervalo creíble o rango de sensibilidad) y con n.
- Se separa **confirmatorio** (backtesting, diario de predicciones) de **exploratorio** (todo lo
  demás).
- Lista de limitaciones en cada reporte: n de exámenes, supuestos de temario, quién etiquetó,
  números limpios del banco.
