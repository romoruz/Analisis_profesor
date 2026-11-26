"""Paso 5. Del sorteo al examen: llena cada hueco (tipo, nivel) con un ejercicio del banco.

Reglas:
  1. Mismo tipo y mismo nivel que pide el sorteo.
  2. Score de dificultad dentro de objetivo[tipo] +- TOL (objetivo calculado en el paso 3:
     media de las preguntas de examen de ese tipo, o media de la tarea + delta examen-tarea).
  3. Entre las combinaciones que cumplen, la que deja la dificultad total del examen más cerca
     de la de los Parciales 2 viejos (desempate aleatorio con semilla fija), penalizando repetir
     familia en otro simulacro.
  4. Solo ejercicios que pasaron la verificación del paso 6.
Salida: salidas/simulacros.json (sin soluciones).
"""
import itertools, json
import numpy as np
from comun import *
from nucleo.dificultad import score
from banco_ejercicios import banco
from verificacion import verifica

TOL = 1.0
SEMILLA = 13112026
dif = json.load(open(os.path.join(SALIDAS, 'dificultad.json')))
mod = json.load(open(os.path.join(SALIDAS, 'modelo_parcial3.json')))
obj = {k: v['objetivo'] for k, v in dif['objetivo'].items()}
viejos = [v for k, v in dif['dificultad_total_examen'].items() if k in ('P2_2020-04-29', 'P2_2026-05-04')]
META = float(np.mean(viejos))

cands = []
for c in banco():
    ok, _ = verifica(c)
    if ok:
        c['score'] = round(score(c['rasgos']), 2)
        cands.append(c)
rng = np.random.default_rng(SEMILLA)
usados, familias, examenes = set(), set(), []
for n, s in enumerate(mod['sorteos'], 1):
    opciones = []
    for q in s['preguntas']:
        k, niv = q['arquetipo'], q['nivel']
        pool = [c for c in cands if c['arq'] == k and c['nivel'] == niv and c['id'] not in usados
                and abs(c['score'] - obj[k]) <= TOL]
        if not pool:   # relajar: cualquier nivel del tipo dentro de la banda, luego sin banda
            pool = [c for c in cands if c['arq'] == k and c['id'] not in usados and abs(c['score'] - obj[k]) <= TOL] or \
                   [c for c in cands if c['arq'] == k and c['id'] not in usados]
            print(f'  aviso: simulacro {n}, tipo {k} nivel {niv}: se relajó el filtro')
        opciones.append(pool)
    mejor, costo = None, np.inf
    for combo in itertools.product(*opciones):
        if len({c['id'] for c in combo}) < len(combo):
            continue
        tot = sum(c['score'] for c in combo)
        cst = abs(tot - META) + 0.5 * sum(c['familia'] in familias for c in combo) + rng.uniform(0, 0.3)
        if cst < costo:
            mejor, costo = combo, cst
    for c in mejor:
        usados.add(c['id']); familias.add(c['familia'])
    examenes.append({'numero': n, 'minutos': s['minutos'],
                     'dificultad_total': round(sum(c['score'] for c in mejor), 2),
                     'preguntas': [{'id': c['id'], 'arq': c['arq'], 'nivel': c['nivel'], 'score': c['score'],
                                    'objetivo': obj[c['arq']], 'tex': c['tex']} for c in mejor]})
json.dump({'meta_dificultad_total': round(META, 2), 'tolerancia': TOL, 'examenes': examenes},
          open(os.path.join(SALIDAS, 'simulacros.json'), 'w'), ensure_ascii=False, indent=1)
print(f'Meta de dificultad total (media de los Parciales 2 viejos): {META:.2f}')
for e in examenes:
    print(f"Simulacro {e['numero']}: total {e['dificultad_total']:5.2f}  " +
          '  '.join(f"{q['arq']}:{q['id']}({q['score']:.2f}/{q['objetivo']:.2f})" for q in e['preguntas']))
