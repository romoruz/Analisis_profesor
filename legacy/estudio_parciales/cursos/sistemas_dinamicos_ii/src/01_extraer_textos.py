"""Paso 1. Tareas PDF -> corpus/tareas. Los exámenes son fotos: ya están transcritos a mano
en corpus/examenes/*.txt (una línea 'Pregunta N' por pregunta)."""
from comun import CURSO, CORPUS, os
from nucleo.extraer import pdfs_a_texto
print(pdfs_a_texto(os.path.join(CURSO, 'datos'), CORPUS, ('tareas',)), 'PDF convertidos')
