"""Plantilla: dificultad + modelo + sorteo balanceado con el núcleo genérico.
Uso: python3 correr.py [n_sorteos]"""
import json, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); CURSO = os.path.dirname(AQUI)
sys.path.insert(0, os.path.dirname(os.path.dirname(CURSO)))
from nucleo import dificultad as D
from nucleo.modelo import corre, sortea
from config_parcial import CFG, MALLA, SEMILLA_SORTEO, NIVELES

filas = D.leer_csv(os.path.join(CURSO, 'rasgos_dificultad.csv'))
cal = D.calibra(filas)
print('tareas', cal['tareas'], '\nexámenes', cal['examenes'], '\ndelta por pares', cal['delta_pares_media'])
n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
out = corre(CFG, R=10000, R_rejilla=2000, malla=MALLA)
niv, pn = list(NIVELES), list(NIVELES.values())
out['sorteos'] = sortea(CFG, n, SEMILLA_SORTEO, decora=lambda k, r: {'nivel': str(r.choice(niv, p=pn))},
                        balancear=out['p_base'])
for k in sorted(out['K'], key=lambda k: -out['p_base'][k]):
    print(k, out['nombres'][k], out['p_base'][k], out['p_min'][k], out['p_max'][k])
for i, s in enumerate(out['sorteos'], 1):
    print('Sorteo', i, [(q['arquetipo'], q['nivel']) for q in s['preguntas']])
json.dump({'dificultad': cal, 'modelo': out}, open(os.path.join(CURSO, 'salidas', 'resultado.json'), 'w'),
          ensure_ascii=False, indent=1)
