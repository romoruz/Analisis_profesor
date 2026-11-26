"""Modelo de temas para el Parcial 3 (dualidad, interpretación económica, sensibilidad, simplex dual).

No hay examen previo de este parcial: la evidencia sobre el profesor viene de las Pruebas 1 y 2
(origen de cada pregunta: 5 de 6 salieron de la tarea, 1 de la clase; 1 de 2 exámenes tuvo una
pregunta completa de demostración; teoría corta en 2 de 2).
"""
import numpy as np, json, itertools, sys

import os
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, 'salidas', 'modelo_parcial3.json')
N_SORTEOS = int(sys.argv[2]) if len(sys.argv) > 2 else 5   # número de exámenes a sortear

ARQ = {
 'A': ('Formular el dual (pregunta propia)', 15),
 'B': ('Relación primal-dual: verificar optimalidad de un x* sin simplex / clasificar pares', 20),
 'C': ('Holguras complementarias con información parcial', 25),
 'D': ('Dual gráfico (2 variables duales) + holguras', 20),
 'E': ('Problema en contexto: modelo, dual y precios sombra (¿conviene comprar/vender?)', 30),
 'F': ('Sensibilidad leyendo un diccionario o tableau óptimo', 30),
 'G': ('Sensibilidad con B^{-1}: rangos y nuevas soluciones', 35),
 'H': ('Simplex dual (resolver o reoptimizar)', 25),
 'I': ('Demostración de teoría de dualidad', 15),
 'J': ('Usar dualidad en un problema estructurado (dimensión n)', 20),
 'K': ('Punto interior (conceptual)', 10),
}
K = list(ARQ)

# ------------- tarea 4 (etiquetas fraccionarias cuando un ejercicio mezcla tipos)
tarea = {'A': 1.0, 'B': 1.0, 'C': 1.5, 'D': 1.0, 'E': 0.9, 'F': 0.6, 'G': 0.8, 'H': 0.2, 'I': 1.0, 'J': 1.0, 'K': 0.0}
#   Ej1 A | Ej2 B | Ej3 C | Ej4 D | Ej5 J | Ej6 I | Ej7 C .5 + E .5 | Ej8 F .6 + E .4 | Ej9 G .8 + H .2
# ------------- clases 12-16 (ejemplo/ejercicio = 1, teorema = 0.5; punto interior multiplicado por 0.3 por el temario)
clase = {'A': 4.0,   # C12: ej1, ej2, bloques, forma estandar
         'B': 1.0,   # C13: ejemplos 1 y 2 (pares no acotado/infactible)
         'C': 2.0,   # C13 ej3, C15 ej2 (.5), Cerealinc (.5)
         'D': 0.0,
         'E': 4.0,   # C14 Reddy Mikks, BagCo, NWAC; C15 ej2 (.5), Cerealinc (.5)
         'F': 1.0,   # C15 ej1
         'G': 0.5,   # C15 resumen de fórmulas
         'H': 2.0,   # C16 ej1 + derivación de la razón dual
         'I': 3.0,   # débil, corolarios, fuerte, HC, lema dual del dual, Farkas, equivalencia
         'J': 0.0,
         'K': 0.3 * 3}
t = np.array([tarea[k] for k in K]); c = np.array([clase[k] for k in K])
t_hat, c_hat = t / t.sum(), c / c.sum()
TIME = np.array([ARQ[k][1] for k in K])
N_vals, N_p = np.array([2, 3, 4]), np.array([1, 3, 1]) / 5
# origen: Beta(1,1) + 5 de 6 preguntas desde la tarea
PI_A, PI_B = 1 + 5, 1 + 1
# pregunta de demostración: 1 de 2 exámenes
DEM_A, DEM_B = 1 + 1, 1 + 1

SENS = {K.index(k) for k in ('E', 'F', 'G', 'H')}
DUAL = {K.index(k) for k in ('A', 'B', 'C', 'D', 'I', 'J')}

def simula(beta, R, rng, guardar=False, pi_fijo=None, kappa=0.8):
    cuenta = np.zeros(len(K)); ex = []
    acc = 0
    while acc < R:
        th_t = rng.dirichlet(beta * t_hat + 0.3)
        th_c = rng.dirichlet(beta * c_hat + 0.3)
        pi = pi_fijo if pi_fijo is not None else rng.beta(PI_A, PI_B)
        N = rng.choice(N_vals, p=N_p)
        elig = []
        if rng.random() < rng.beta(DEM_A, DEM_B):
            elig.append(K.index('I'))
        intentos = 0
        while len(elig) < N and intentos < 50:
            intentos += 1
            th = th_t if rng.random() < pi else th_c
            j = rng.choice(len(K), p=th)
            if j not in elig: elig.append(j)
        if len(elig) < N: continue
        tt = TIME[elig].sum()
        if not (60 <= tt <= 95): continue
        cubre = bool(set(elig) & SENS) and bool(set(elig) & DUAL)
        if rng.random() < kappa and not cubre: continue   # el profe anunció ambos bloques
        acc += 1; cuenta[elig] += 1
        if guardar: ex.append([K[j] for j in elig])
    return cuenta / R, ex

if __name__ == '__main__':
    rng = np.random.default_rng(2026)
    base, ex = simula(6, 20000, rng, guardar=True)
    grid = []
    for beta, pi, kap in itertools.product([3, 6, 12], [0.6, 0.75, 0.9], [0.6, 0.8, 1.0]):
        p, _ = simula(beta, 3000, rng, pi_fijo=pi, kappa=kap); grid.append(p)
    grid = np.array(grid)
    S = [set(e) for e in ex]
    f = lambda cond: round(float(np.mean([cond(s) for s in S])), 3)
    agregados = {
      'Alguna pregunta de sensibilidad (F, G o H)': f(lambda s: bool(s & {'F', 'G', 'H'})),
      'Alguna pregunta de holguras/relación primal-dual (B, C, D o J)': f(lambda s: bool(s & {'B', 'C', 'D', 'J'})),
      'Problema en contexto con precios sombra (E)': f(lambda s: 'E' in s),
      'Demostración (I)': f(lambda s: 'I' in s),
      'Simplex dual como pregunta (H)': f(lambda s: 'H' in s),
    }
    # tipo de cambio en las preguntas de sensibilidad (conteos del material + 1)
    cambios = {'b dentro del rango': 6, 'b fuera del rango (simplex dual)': 1, 'costo básico (rango o nuevo óptimo)': 5,
               'costo no básico': 3, 'variable o actividad nueva': 1, 'restricción nueva': 0}
    w = np.array(list(cambios.values()), float) + 1; p_cambio = w / w.sum()
    rasgos = {'inciso de teoría corta en una pregunta de cuentas': (2, 2), 'inciso "formule el dual" dentro de otra pregunta': (6, 12),
              'al menos una pregunta casi copiada de la tarea': (2, 2)}
    p_rasgo = {r: (1 + s) / (2 + n) for r, (s, n) in rasgos.items()}
    out = {'K': K, 'nombres': {k: ARQ[k][0] for k in K}, 'tiempo': {k: ARQ[k][1] for k in K},
           'tarea': tarea, 'clase': clase,
           'p_base': dict(zip(K, base.round(3).tolist())), 'p_min': dict(zip(K, grid.min(0).round(3).tolist())),
           'p_max': dict(zip(K, grid.max(0).round(3).tolist())), 'agregados': agregados,
           'p_cambio': dict(zip(cambios, p_cambio.round(3).tolist())), 'p_rasgo': {k: round(v, 3) for k, v in p_rasgo.items()}}
    from collections import Counter
    out['ternas_top'] = [(list(k), v / len(S)) for k, v in Counter(tuple(sorted(s)) for s in S).most_common(6)]
    # ------------- sorteo de 3 simulacros
    rs = np.random.default_rng(9112026)
    sorteos, vistos = [], set()
    while len(sorteos) < N_SORTEOS:
        _, e = simula(6, 1, rs, guardar=True)
        arq = e[0]; clave = tuple(sorted(arq))
        if clave in vistos: continue
        vistos.add(clave)
        d = {'preguntas': []}
        for k in arq:
            q = {'arquetipo': k, 'nivel': str(rs.choice(['casi copia de la Tarea 4', 'adaptación', 'nueva']))}
            if k in ('F', 'G', 'E'):
                n_c = 3 if k != 'E' else 2
                q['cambios'] = [str(x) for x in rs.choice(list(cambios), size=n_c, replace=False, p=p_cambio)]
            if k in ('B', 'C', 'D', 'E', 'F', 'G', 'H', 'J'):
                q['teoria_corta'] = bool(rs.random() < p_rasgo['inciso de teoría corta en una pregunta de cuentas'])
                q['inciso_dual'] = bool(rs.random() < p_rasgo['inciso "formule el dual" dentro de otra pregunta'])
            d['preguntas'].append(q)
        tt = sum(ARQ[q['arquetipo']][1] for q in d['preguntas'])
        pts = [round(20 * ARQ[q['arquetipo']][1] / tt) / 2 for q in d['preguntas']]
        pts[int(np.argmax(pts))] += 10 - sum(pts)
        for q, p in zip(d['preguntas'], pts): q['pts'] = p
        d['minutos'] = int(tt); sorteos.append(d)
    out['sorteos'] = sorteos
    print(json.dumps({k: out[k] for k in out if k != 'sorteos'}, indent=1, ensure_ascii=False))
    for i, d in enumerate(out['sorteos'], 1):
        print(f'Sorteo {i}:', json.dumps(d, ensure_ascii=False))
    json.dump(out, open(SALIDA, 'w'), ensure_ascii=False, indent=1)
