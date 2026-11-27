# Bitácora: Claude.ai (Opus 5.5, razonamiento medio), 2026-11-27

**Veredicto: funciona, pero la prueba NO fue a ciegas.** Recibió `estudio_parciales.zip`
completo (con `salidas/` y `MEJORAS_Y_USO.md` de SD-II) y dice textualmente "Reviso el análisis
previo que viene en estudio_parciales.zip como referencia". Hay que repetirla con
`sd2_material.zip` solamente.

## Modo y pasos
- Modo COMPLETO; instaló sympy por su cuenta.
- Ejecutó los pasos 1 a 10 con los scripts. Hizo a mano el paso `acuerdo` (no implementado):
  3 de 128 rasgos difirieron entre pasadas.
- Banco: 30 ejercicios (3 por arquetipo), 25 verificados con código y 5 demostraciones revisadas
  leyéndolas. PDF generado.

## Reciclaje (4 casos conocidos)
| Caso | Detectado | Evidencia |
|---|---|---|
| T5 = T4 (10 de 10) | Sí | "T4:3-11 son los mismos que T5:1-10" |
| P2 oct Q2 ← P1 mar Q3 | Sí | similitud 1.000 |
| Potencial may-2026 ← 2020 | Sí | 0.847, y ecuación literal de T4:12c |
| Bifurcación may-2026 ← 2020 | Sí | 0.915, misma EDO con λ |

## Temas (por p) y comparación con legacy
- Claude: A 0.61, G 0.58, B 0.54, D 0.44, E 0.40, F 0.31.
- Legacy: A 0.54, G 0.46, F 0.46, B 0.44, H 0.43, D 0.32.
- Diferencias: D sube (en legacy se castigaba por haber salido el 19/10) y F baja. Sin el zip de
  `trabajo/` no se sabe si fue el etiquetado o la rotación. Ver "Pendientes".

## Matemáticas (revisión del orquestador, 20 de 20 preguntas)
- Sin errores en las 20 soluciones. Se recalcularon a mano:
  - potenciales y valores de U (S1-P1, S2-P1, S3-P3);
  - ecuaciones en polares (S1-P2, S2-P2, S4-P3, S5-P3);
  - el jacobiano y el umbral foco/nodo λ < 4/5 (S4-P2);
  - la explosión en tiempo finito (S5-P3);
  - la divergencia de Bendixson (S5-P2).
- Las demostraciones (ω(p) cerrado, no vacío y conexo; anillo; fuente hiperbólica) son las
  estándar y están completas.
- Demostración presente en 5 de 5 simulacros (p = 0.88 → esperado 4.4).

## Honestidad
- Reporta "no hay diferencia clara" en dificultad, con intervalo y p. Avisa que los intervalos son
  anchos, que no hubo backtesting y que en 7 huecos el armado relajó el nivel.
- Cifras trazables a los JSON. Observación: reporta "IC 95 %" en las proporciones; el protocolo v6
  pide el nivel que trae el JSON.

## Pendientes
1. Repetir a ciegas con `sd2_material.zip`.
2. Pedirle el zip de `trabajo/sd2/` para auditar etiquetas y rotación.
