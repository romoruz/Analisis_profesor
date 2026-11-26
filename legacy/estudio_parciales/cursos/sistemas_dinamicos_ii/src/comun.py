"""Rutas del curso y acceso al núcleo genérico (estudio_parciales/nucleo)."""
import os, re, sys
CURSO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.dirname(os.path.dirname(CURSO))
sys.path.insert(0, RAIZ)
CORPUS = os.path.join(CURSO, 'corpus')
SALIDAS = os.path.join(CURSO, 'salidas')
DOCS = os.path.join(CURSO, 'docs')
os.makedirs(SALIDAS, exist_ok=True)

# examen -> prefijo de ids, en orden cronológico
EXAMENES = [('P2_2020-04-29', 'E20'), ('P1_2026-03-04', 'E26m'), ('P2_2026-05-04', 'E26a'), ('P2_2026-10-19', 'E26b')]

# la Tarea 4 trae la numeración rota ('4.' dos veces y el 13/14 partido): se numera por orden
# de aparición y se junta el último encabezado con el anterior.
def ejercicios_tarea(n):
    t = open(os.path.join(CORPUS, 'tareas', f'Tarea_{n}.txt'), encoding='utf-8').read().splitlines()
    idx = [k for k, l in enumerate(t) if re.match(r'^\s{0,4}\d{1,2}\.\s', l)]
    bloques = ['\n'.join(t[a:b]) for a, b in zip(idx, idx[1:] + [len(t)])]
    if n == 4:
        bloques = bloques[:-2] + [bloques[-2] + '\n' + bloques[-1]]
    return [(f'T{n}-{k + 1}', b) for k, b in enumerate(bloques)]

def preguntas_examen(nombre, prefijo):
    t = open(os.path.join(CORPUS, 'examenes', nombre + '.txt'), encoding='utf-8').read()
    partes = re.split(r'^Pregunta\s+(\d)', t, flags=re.M)
    return [(f'{prefijo}-{partes[i]}', partes[i + 1]) for i in range(1, len(partes), 2)]
