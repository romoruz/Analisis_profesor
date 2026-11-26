# Plantilla para una materia nueva

1. Copia esta carpeta a `cursos/<materia>/`.
2. PDFs en `datos/tareas`, `datos/clases`, `datos/examenes`; pásalos a texto con `nucleo/extraer.py`.
   Si los exámenes son fotos, transcríbelos a `corpus/examenes/<nombre>.txt` con una línea
   `Pregunta N` por pregunta.
3. Define los tipos de pregunta y llena `rasgos_dificultad.csv` (una fila por ejercicio de tarea y
   por pregunta de examen; en `fuente` pon el ejercicio del que salió la pregunta, si lo hay).
4. Llena `src/config_parcial.py` y corre `python3 src/correr.py 5`.
5. Para generar ejercicios y el PDF, copia `banco_ejercicios.py`, `verificacion.py`,
   `05_armar_simulacros.py` y `07_pdf_simulacros.py` de `cursos/sistemas_dinamicos_ii/src` y cambia
   las familias de ejercicios y los checks por los de tu materia.
