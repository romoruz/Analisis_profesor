# Sistemas Dinámicos II: simulacros del Parcial 3 (temas 4.3 a 4.6)

    datos/        PDFs de las tareas 1-5 y fotos de los exámenes
    corpus/       tareas en texto (paso 1) y exámenes transcritos a mano
    rasgos_dificultad.csv   rasgos de dificultad de cada ejercicio de tarea y pregunta de examen
    src/          pasos numerados (usan ../../nucleo)
    salidas/      JSON y TXT de cada paso
    docs/         Simulacros_Parcial3.tex y .pdf (solo enunciados)

Orden: `sh correr_todo.sh`, o paso por paso desde `src/`:

    python3 01_extraer_textos.py      # tareas PDF -> texto
    python3 02_similitud.py           # examen vs tareas y vs exámenes previos
    python3 03_dificultad.py          # score de dificultad y banda objetivo por tipo
    python3 04_modelo_parcial3.py 5   # probabilidades por tipo y sorteo balanceado de 5 exámenes
    python3 06_verificar.py           # verifica el banco (OJO: imprime soluciones)
    python3 05_armar_simulacros.py    # llena cada hueco del sorteo con un ejercicio del banco
    python3 07_pdf_simulacros.py      # PDF

Para agregar tus ejercicios al banco: nueva entrada en `src/banco_ejercicios.py` con sus rasgos y
un `check`; corre `06_verificar.py <id>` para probarla.
