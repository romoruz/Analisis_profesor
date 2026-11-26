"""Paso 1. Extrae el texto de todos los PDF de datos/ a corpus/ (requiere pdftotext, de poppler-utils).

Uso:  python src/01_extraer_textos.py  [carpeta_datos]  [carpeta_corpus]
"""
import os, subprocess, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, 'datos')
CORPUS = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RAIZ, 'corpus')

def main():
    n = 0
    for sub in ('examenes', 'tareas', 'clases'):
        src = os.path.join(DATOS, sub); dst = os.path.join(CORPUS, sub)
        os.makedirs(dst, exist_ok=True)
        for f in sorted(os.listdir(src)):
            if not f.lower().endswith('.pdf'):
                continue
            out = os.path.join(dst, f[:-4] + '.txt')
            subprocess.run(['pdftotext', '-layout', os.path.join(src, f), out], check=True)
            n += 1
    print(f'{n} PDF convertidos a texto en {CORPUS}')

if __name__ == '__main__':
    main()
