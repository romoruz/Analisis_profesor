"""Paso 7. Escribe docs/Simulacros_Parcial3.tex con el formato de los exámenes del profe y lo
compila a PDF. Solo enunciados: no lleva soluciones."""
import json, subprocess
from comun import *

sim = json.load(open(os.path.join(SALIDAS, 'simulacros.json')))
CAB = r"""\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{amsmath,amssymb}
\usepackage[letterpaper,margin=2.3cm]{geometry}
\setlength{\parindent}{0pt}
\pagestyle{plain}
\begin{document}
"""
EXAMEN = r"""\textbf{Sistemas Dinámicos II}\\
\textbf{Tercer examen parcial -- Simulacro %(n)d}

\vspace{0.6cm}
Nombre: \underline{\hspace{9cm}} \quad Clave: \underline{\hspace{3cm}}

\vspace{0.5cm}
\begin{center}
JUSTIFICA CON DETALLE TUS RESPUESTAS\\
NO se permiten libros, apuntes, calculadoras, celulares o tabletas\\
Tiempo: 90 minutos
\end{center}
\vspace{-0.2cm}
\rule{\textwidth}{0.4pt}
\vspace{0.2cm}

\begin{enumerate}
%(preguntas)s
\end{enumerate}

\vspace{0.5cm}
\begin{center}
\Large Buena suerte!!
\end{center}
"""
partes = []
for e in sim['examenes']:
    qs = '\n'.join('\\item (2.5 puntos) ' + q['tex'] + '\n\\vspace{0.15cm}\n' for q in e['preguntas'])
    partes.append(EXAMEN % {'n': e['numero'], 'preguntas': qs})
tex = CAB + '\n\\newpage\n'.join(partes) + '\n\\end{document}\n'
os.makedirs(DOCS, exist_ok=True)
ruta = os.path.join(DOCS, 'Simulacros_Parcial3.tex')
open(ruta, 'w').write(tex)
for _ in range(2):
    r = subprocess.run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error', 'Simulacros_Parcial3.tex'],
                       cwd=DOCS, capture_output=True, text=True)
if r.returncode:
    print(r.stdout[-3000:]); raise SystemExit('LaTeX falló')
for ext in ('aux', 'log'):
    try: os.remove(os.path.join(DOCS, f'Simulacros_Parcial3.{ext}'))
    except FileNotFoundError: pass
print('PDF:', ruta.replace('.tex', '.pdf'))
