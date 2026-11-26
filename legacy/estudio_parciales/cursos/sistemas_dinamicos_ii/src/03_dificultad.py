"""Paso 3. Score de dificultad: tareas vs exámenes, global y pregunta por pregunta.

Rasgos etiquetados a mano en rasgos_dificultad.csv (una fila por ejercicio o inciso).
Salida: salidas/dificultad.json, que el generador (paso 5) usa como banda objetivo.
"""
import json
import numpy as np
from comun import *
from nucleo import dificultad as D

filas = D.leer_csv(os.path.join(CURSO, 'rasgos_dificultad.csv'))
P3 = lambda r: r['arq'] not in ('', '-')              # alcance del Parcial 3 (temas 4.3-4.6)
todo = D.calibra(filas)
p3 = D.calibra(filas, filtro=P3)
arq = D.por_arquetipo(filas)
rob = D.robustez(filas, n=2000, semilla=1)
rob3 = D.robustez(filas, n=2000, semilla=2, filtro=P3)
emp = D.contra_calificaciones(filas)

# banda objetivo por tipo de pregunta: si hay preguntas de examen del tipo, su media;
# si no, la media de la tarea del tipo + el delta medio por pares (examen - fuente).
dp = p3['delta_pares_media']
objetivo = {}
for k, d in sorted(arq.items()):
    if d['examen']:
        objetivo[k] = {'objetivo': round(float(np.mean(d['examen'])), 2), 'base': 'examen', 'n': len(d['examen'])}
    else:
        objetivo[k] = {'objetivo': round(float(np.mean(d['tarea'])) + dp, 2), 'base': 'tarea+delta', 'n': len(d['tarea'])}
    objetivo[k]['tarea_media'] = round(float(np.mean(d['tarea'])), 2) if d['tarea'] else None

# dificultad total de cada examen (suma de sus preguntas)
tot = {}
for r in filas:
    if r['tipo'] == 'examen':
        tot.setdefault(r['origen'], []).append(todo['scores'][r['id']])
tot = {k: round(sum(v), 2) for k, v in tot.items()}

out = {'rasgos': {k: {'peso': v[0], 'base': v[1], 'max': v[2]} for k, v in D.RASGOS.items()},
       'todo_el_curso': todo, 'alcance_parcial3': {k: p3[k] for k in ('tareas', 'examenes', 'delta_medias', 'pares', 'delta_pares_media', 'percentil_examen_en_tareas')},
       'robustez_todo': rob, 'robustez_parcial3': rob3, 'por_arquetipo': arq, 'objetivo': objetivo,
       'dificultad_total_examen': tot, 'contra_calificaciones': emp}
json.dump(out, open(os.path.join(SALIDAS, 'dificultad.json'), 'w'), ensure_ascii=False, indent=1)

print('Todo el curso   tareas', todo['tareas'], '\n                examenes', todo['examenes'], '\n                delta medias', todo['delta_medias'], ' delta por pares', todo['delta_pares_media'])
print('Alcance P3      tareas', p3['tareas'], '\n                examenes', p3['examenes'], '\n                delta medias', p3['delta_medias'], ' delta por pares', p3['delta_pares_media'])
print('\nPares examen vs fuente:')
for p in todo['pares']:
    print(f"  {p['examen']:7s} <- {p['fuente']:9s} {p['nivel']:11s} {p['score_examen']:5.2f} vs {p['score_fuente']:5.2f}  delta {p['delta']:+.2f}")
print('\nPercentil de cada pregunta de examen dentro de las tareas:', todo['percentil_examen_en_tareas'])
print('\nRobustez (pesos x U(0.5,1.5), 2000 veces):', rob, '\n  alcance P3:', rob3)
print('\nObjetivo por tipo:', json.dumps(objetivo, ensure_ascii=False))
print('\nDificultad total por examen:', tot)
print('Score vs fracción perdida (alumno, 8 preguntas):', emp)
