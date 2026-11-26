"""Score de dificultad por rasgos y calibración tarea vs examen. Genérico para cualquier materia.

Cada ejercicio (de tarea o de examen) se describe con rasgos enteros etiquetados a mano en un
CSV (ver cursos/*/rasgos_dificultad.csv). El score es una suma ponderada reescalada a 0-10:

    score = 10 * sum_f w_f * g_f(x_f) / sum_f w_f * g_f(max_f)

Con eso se responde: ¿los exámenes son más difíciles que las tareas? ¿cuánto, pregunta por
pregunta, contra el ejercicio de tarea del que salieron? Y como los pesos son opinión, se
repite todo con pesos perturbados (robustez) para ver si la conclusión aguanta.
"""
import csv
import numpy as np

# rasgo: (peso, valor que no suma, máximo). g_f(x) = x - base
RASGOS = {
    'pasos':          (0.6, 1, 5),   # entregables pedidos (equilibrios, estabilidad, retrato, límites, ...)
    'parametro':      (1.2, 0, 2),   # 0 sin parámetro, 1 un valor crítico, 2 varios valores / regímenes
    'dim':            (0.5, 1, 4),   # 1 escalar u orden 2, 2 plano, 3 R^3, 4 R^n o abstracto
    'tecnica':        (1.2, 0, 3),   # 0 receta directa, 1 cambio de variable/energía, 2 construcción, 3 argumento global
    'no_hiperbolico': (1.0, 0, 1),   # la linealización no decide
    'demostracion':   (1.0, 0, 2),   # 1 aplicar un teorema a un sistema dado, 2 demostración abstracta
    'algebra':        (0.6, 0, 2),   # carga de cuentas
    'global':         (1.0, 0, 1),   # retrato global o conjuntos límite de todo punto
    'casos':          (0.4, 1, 4),   # regímenes a dibujar o analizar
}

def leer_csv(ruta):
    with open(ruta, encoding='utf-8') as f:
        filas = list(csv.DictReader(f))
    for r in filas:
        for k in RASGOS:
            r[k] = int(r[k])
        r['examinable'] = int(r.get('examinable', 1) or 1)
        r['puntos'] = float(r['puntos']) if r.get('puntos') not in (None, '') else None
    return filas

def score(r, pesos=None):
    pesos = pesos or {k: v[0] for k, v in RASGOS.items()}
    num = sum(pesos[k] * (r[k] - RASGOS[k][1]) for k in RASGOS)
    den = sum(pesos[k] * (RASGOS[k][2] - RASGOS[k][1]) for k in RASGOS)
    return 10 * num / den

def _resumen(v):
    v = np.asarray(v, float)
    return {'n': int(len(v)), 'media': round(float(v.mean()), 2), 'mediana': round(float(np.median(v)), 2),
            'p25': round(float(np.percentile(v, 25)), 2), 'p75': round(float(np.percentile(v, 75)), 2)}

def calibra(filas, pesos=None, filtro=lambda r: True):
    """Compara tareas y exámenes. `filtro` restringe a un alcance (por ejemplo, un parcial)."""
    s = {r['id']: score(r, pesos) for r in filas}
    tareas = [r for r in filas if r['tipo'] == 'tarea' and r['examinable'] and filtro(r)]
    exams = [r for r in filas if r['tipo'] == 'examen' and filtro(r)]
    st = [s[r['id']] for r in tareas]
    se = [s[r['id']] for r in exams]
    # percentil de cada pregunta de examen dentro de la distribución de las tareas
    pct = {r['id']: round(100 * float(np.mean([x <= s[r['id']] for x in st])), 1) for r in exams}
    pares = []
    for r in exams:
        f = r.get('fuente') or ''
        if f in s:
            pares.append({'examen': r['id'], 'fuente': f, 'nivel': r.get('nivel', ''),
                          'score_examen': round(s[r['id']], 2), 'score_fuente': round(s[f], 2),
                          'delta': round(s[r['id']] - s[f], 2)})
    return {'scores': {k: round(v, 2) for k, v in s.items()},
            'tareas': _resumen(st), 'examenes': _resumen(se),
            'delta_medias': round(float(np.mean(se) - np.mean(st)), 2),
            'percentil_examen_en_tareas': pct,
            'pares': pares,
            'delta_pares_media': round(float(np.mean([p['delta'] for p in pares])), 2) if pares else None}

def por_arquetipo(filas, pesos=None):
    s = {r['id']: score(r, pesos) for r in filas}
    out = {}
    for r in filas:
        a = r.get('arq', '-')
        if a in ('', '-') or not r['examinable']:
            continue
        d = out.setdefault(a, {'tarea': [], 'examen': []})
        d[r['tipo']].append(round(s[r['id']], 2))
    return out

def robustez(filas, n=2000, semilla=0, rango=(0.5, 1.5), filtro=lambda r: True):
    """Repite la calibración con cada peso multiplicado por U(rango). Devuelve percentiles
    5/50/95 de la diferencia de medias y de la diferencia media por pares, y la fracción de
    perturbaciones en que los exámenes salen más difíciles."""
    rng = np.random.default_rng(semilla)
    base = {k: v[0] for k, v in RASGOS.items()}
    dm, dp = [], []
    for _ in range(n):
        w = {k: base[k] * rng.uniform(*rango) for k in base}
        c = calibra(filas, w, filtro)
        dm.append(c['delta_medias']); dp.append(c['delta_pares_media'] if c['delta_pares_media'] is not None else np.nan)
    q = lambda v: [round(float(np.nanpercentile(v, p)), 2) for p in (5, 50, 95)]
    return {'delta_medias_p5_p50_p95': q(dm), 'delta_pares_p5_p50_p95': q(dp),
            'frac_examen_mas_dificil_medias': round(float(np.mean(np.array(dm) > 0)), 3),
            'frac_examen_mas_dificil_pares': round(float(np.nanmean(np.array(dp) > 0)), 3)}

def contra_calificaciones(filas, pesos=None, puntos_max=2.5):
    """Correlación de Spearman entre el score y la fracción de puntos perdida (si hay calificaciones)."""
    from scipy.stats import spearmanr
    pares = [(score(r, pesos), 1 - r['puntos'] / puntos_max) for r in filas if r.get('puntos') is not None]
    if len(pares) < 4:
        return None
    rho, p = spearmanr([a for a, _ in pares], [b for _, b in pares])
    return {'n': len(pares), 'spearman': round(float(rho), 3), 'p_valor': round(float(p), 3)}
