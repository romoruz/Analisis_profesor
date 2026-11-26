"""PDF -> texto con pdftotext -layout (poppler-utils). Sirve para cualquier materia.

Las fotos de exámenes (jpg/png) no se pueden pasar a texto con calidad suficiente para
fórmulas: se transcriben a mano en corpus/examenes/<nombre>.txt con una línea
'Pregunta N ...' por pregunta (ver cursos/sistemas_dinamicos_ii/corpus/examenes).
"""
import os, subprocess

def pdfs_a_texto(datos, corpus, subcarpetas=('examenes', 'tareas', 'clases')):
    n = 0
    for sub in subcarpetas:
        src = os.path.join(datos, sub)
        if not os.path.isdir(src):
            continue
        dst = os.path.join(corpus, sub)
        os.makedirs(dst, exist_ok=True)
        for f in sorted(os.listdir(src)):
            if f.lower().endswith('.pdf'):
                subprocess.run(['pdftotext', '-layout', os.path.join(src, f),
                                os.path.join(dst, f[:-4] + '.txt')], check=True)
                n += 1
    return n
