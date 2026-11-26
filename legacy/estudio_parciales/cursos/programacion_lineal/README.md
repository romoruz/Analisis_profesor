# Análisis del profesor y generación de parciales — Programación Lineal (MAT-24410)

Código para (1) medir cuánto recicla el profe de tareas y clases, (2) estimar con un modelo
bayesiano qué tipos de pregunta van a salir, (3) sortear simulacros con semilla fija y
(4) diseñar y verificar los ejercicios con aritmética exacta. La metodología completa, sus
limitaciones y qué hacer cuando no hay pauta están en `docs/Metodologia.pdf`.

## Estructura

    datos/        PDFs originales (pautas de las pruebas, tareas 1-4, clases 7-16)
    corpus/       texto extraído de los PDFs (lo genera el paso 1)
    src/          scripts numerados, se corren en orden
    src/herramientas/  simplex exacto (fracciones) y análisis de sensibilidad
    salidas/      resultados de cada paso (JSON y TXT)
    docs/         Metodologia.tex y su PDF

## Cómo correrlo

    pip install -r requirements.txt          # y poppler-utils para pdftotext
    python src/01_extraer_textos.py          # PDF -> corpus/
    python src/02_similitud.py examenes      # preguntas de examen vs tareas y clases
    python src/02_similitud.py tarea4        # Tarea 4 vs Clases 12-16
    python src/03_modelo_parcial2.py [salida.json] [n_sorteos]   # default 3 sorteos, semilla 31102026
    python src/04_modelo_parcial3.py [salida.json] [n_sorteos]   # default 5 sorteos, semilla 9112026
    python src/05_generar_problemas.py RECETA [semilla] [cuantos]
    python src/06_verificar_respuestas.py    # OJO: contiene soluciones

Recetas del generador: `infactible`, `no_acotado`, `multiples`, `degenerado`,
`sensibilidad`, `dual_simplex`.

Los pasos 3 y 4 son deterministas: con las mismas semillas salen exactamente los mismos
sorteos que se usaron para los simulacros. Si quieres sorteos nuevos, pide más con el segundo
argumento (los primeros se conservan) o cambia la semilla dentro del script.

## Para otro parcial u otro curso

1. Pon los PDFs nuevos en `datos/` y corre el paso 1.
2. Ajusta en el paso 2 las listas de tareas/clases que se comparan.
3. Copia `04_modelo_parcial3.py`, cambia el diccionario `ARQ` (tipos de pregunta y minutos),
   los pesos `tarea` y `clase` (cuántas veces aparece cada tipo en el material) y los bloques
   del temario anunciado (`SENS`, `DUAL`).
4. Genera los ejercicios con el paso 5 y verifícalos agregando casos al paso 6.
