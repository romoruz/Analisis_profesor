"""Paso 4. Probabilidad de cada tipo de pregunta en el Parcial 3 y sorteo de simulacros.

Uso: python 04_modelo_parcial3.py [n_sorteos]   (default 5; pedir más conserva los primeros)
"""
import json, sys
from comun import *
from nucleo.modelo import corre, sortea
from config_parcial3 import CFG, MALLA, SEMILLA_SORTEO, NIVELES

n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
out = corre(CFG, R=20000, R_rejilla=3000, semilla=2026, malla=MALLA)
niv, pn = list(NIVELES), list(NIVELES.values())
dec = lambda k, rng: {'nivel': str(rng.choice(niv, p=pn))}
out['sorteos_independientes'] = sortea(CFG, n, SEMILLA_SORTEO, decora=dec)            # estilo repo PL
out['sorteos'] = sortea(CFG, n, SEMILLA_SORTEO, decora=dec, balancear=out['p_base'])  # los que se usan
from collections import Counter
for nombre in ('sorteos_independientes', 'sorteos'):
    c = Counter(q['arquetipo'] for s in out[nombre] for q in s['preguntas'])
    print(nombre, 'apariciones por tipo:', dict(sorted(c.items())), ' esperado:', {k: round(n * v, 1) for k, v in sorted(out['p_base'].items())})
json.dump(out, open(os.path.join(SALIDAS, 'modelo_parcial3.json'), 'w'), ensure_ascii=False, indent=1)
print(f"{'':3s}{'Tipo':74s} base   mín   máx")
for k in sorted(out['K'], key=lambda k: -out['p_base'][k]):
    print(f"{k}  {out['nombres'][k]:72s} {out['p_base'][k]:.2f}  {out['p_min'][k]:.2f}  {out['p_max'][k]:.2f}")
print('Combinaciones más frecuentes:', out['combinaciones_top'][:5])
for i, s in enumerate(out['sorteos'], 1):
    print(f'Sorteo {i}:', [(q['arquetipo'], q['nivel']) for q in s['preguntas']], s['minutos'], 'min')
