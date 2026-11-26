"""Paso 6. Verifica TODO el banco de ejercicios y escribe salidas/verificacion.txt.
OJO: el archivo de salida contiene soluciones. No lo abras antes de hacer los simulacros."""
import sys
from comun import *
from banco_ejercicios import banco
from verificacion import verifica

solo = set(sys.argv[1:])
lineas, fallas = [], 0
for c in banco():
    if solo and c['id'] not in solo:
        continue
    try:
        ok, res = verifica(c)
    except Exception as e:
        ok, res = False, [f'ERROR {type(e).__name__}: {e}']
    fallas += not ok
    lineas.append(f"{'OK ' if ok else 'XX '} {c['id']:10s} [{c['arq']} {c['nivel']}]")
    lineas += ['     ' + l for l in res]
lineas.append(f'\n{len([l for l in lineas if l[:3] in ("OK ", "XX ")]) - fallas} de {len([l for l in lineas if l[:3] in ("OK ", "XX ")])} ejercicios verificados.')
txt = '\n'.join(lineas)
print(txt)
if not solo:
    open(os.path.join(SALIDAS, 'verificacion.txt'), 'w').write('OJO: CONTIENE SOLUCIONES\n\n' + txt + '\n')
