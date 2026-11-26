# Estudio de parciales: análisis del profe y simulacros

Repositorio maestro. Lo que no depende de la materia vive en `nucleo/`; cada materia tiene su
carpeta en `cursos/`.

    nucleo/
      extraer.py      PDF -> texto (pdftotext)
      similitud.py    TF-IDF + coseno con línea base p95: copia / adaptación / nueva
      dificultad.py   score de dificultad por rasgos, calibración tarea vs examen, robustez
      modelo.py       modelo bayesiano de tipos de pregunta, rejilla de hiperparámetros,
                      sorteo de simulacros (independiente o balanceado)
    cursos/
      programacion_lineal/      repo original de PL (MAT-24410), sin cambios: sigue
                                reproduciendo los mismos resultados y sorteos
      sistemas_dinamicos_ii/    Parcial 3 de SD-II: corpus, dificultad, modelo, banco de
                                ejercicios verificados y PDF de 5 simulacros
      _plantilla/               punto de partida para otra materia
    MEJORAS_Y_USO.md            qué se reutilizó del repo de PL, qué se mejoró y resultados de SD-II

Requisitos: `pip install -r requirements.txt`, más poppler-utils (pdftotext) y pdflatex.

Para SD-II: `sh cursos/sistemas_dinamicos_ii/correr_todo.sh`.
Para PL: los mismos comandos de siempre desde `cursos/programacion_lineal/`.
Para otra materia: `cursos/_plantilla/README.md`.
