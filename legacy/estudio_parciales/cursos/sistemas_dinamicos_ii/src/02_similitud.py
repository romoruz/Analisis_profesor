"""Paso 2. ¿Cuánto recicla el profe? Cada pregunta de examen contra (a) los ejercicios de las
Tareas 1-4 y (b) las preguntas de exámenes anteriores. La Tarea 5 se excluye de la base porque
repite literalmente los ejercicios 3-12 de la Tarea 4."""
import json
from comun import *
from nucleo.similitud import compara

tareas = sum((ejercicios_tarea(n) for n in (1, 2, 3, 4)), [])
t5 = ejercicios_tarea(5)
res = {}
# Tarea 5 contra Tarea 4 (confirma que es un subconjunto)
r = compara(t5, ejercicios_tarea(4))
res['tarea5_vs_tarea4'] = {k: v['mas_parecidos'][0] for k, v in r['top'].items()}
anteriores = []
for nombre, pref in EXAMENES:
    qs = preguntas_examen(nombre, pref)
    a = compara(qs, tareas)
    b = compara(qs, anteriores) if len(anteriores) >= 4 else None
    for i, _ in qs:
        res[i] = {'vs_tareas': a['top'][i]}
        if b:
            res[i]['vs_examenes_previos'] = b['top'][i]
    res.setdefault('linea_base_tareas', {'media': a['linea_base_media'], 'p95': a['linea_base_p95']})
    anteriores += qs
for k, v in res.items():
    if k.startswith('E'):
        t = v['vs_tareas']['mas_parecidos'][0]
        e = v.get('vs_examenes_previos', {}).get('mas_parecidos', [('-', 0)])[0]
        print(f"{k:7s} tarea: {t[0]:7s} {t[1]:.3f} [{v['vs_tareas']['clasificacion']:10s}]   examen previo: {e[0]:7s} {e[1]:.3f}")
print('T5 vs T4:', {k: v[0] for k, v in res['tarea5_vs_tarea4'].items()})
print('Línea base entre ejercicios de tarea:', res['linea_base_tareas'])
json.dump(res, open(os.path.join(SALIDAS, 'similitud.json'), 'w'), ensure_ascii=False, indent=1)
