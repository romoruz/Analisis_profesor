"""Modelo bayesiano de temas para la reposición del Parcial 2 + simulación Monte Carlo + sorteo de 3 exámenes.

Arquetipos (tipos de pregunta) del alcance del Parcial 2 (Clases 7-11, Tareas 2-3). Big-M excluido.
"""
import numpy as np, json, itertools, sys

import os
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, 'salidas', 'modelo_parcial2.json')
N_SORTEOS = int(sys.argv[2]) if len(sys.argv) > 2 else 3   # número de exámenes a sortear

ARQ = {
 'A': ('Dos fases (formular Fase I, resolver o base dada, Fase II)', 35),
 'B': ('Tableau o diccionario con parámetros + terminar de resolver', 35),
 'C': ('Demostración (propiedades del simplex, lemas, teoremas)', 15),
 'D': ('Prueba de optimalidad de un x* con parámetro', 25),
 'E': ('Óptimo finito según un parámetro', 15),
 'F': ('Simplex completo desde holguras (tableau o matricial)', 25),
 'G': ('Diccionario desde una base dada + iterar', 25),
 'H': ('Soluciones básicas: clasificar SF/SB/SBF, TFPL, bases', 20),
 'I': ('Construir un ejemplo (degeneración, contraejemplo)', 15),
 'J': ('Forma estándar como pregunta aislada', 10),
}
K = list(ARQ)

# ---------------- evidencia del material (tareas pesan 2, ejemplos/ejercicios de clase 1, teoremas de clase 0.5)
material = [
 # Tarea 2
 ('T2-Ej1', 'F', 2), ('T2-Ej2', 'E', 2), ('T2-Ej3', 'D', 2), ('T2-Ej4', 'I', 2), ('T2-Ej5', 'C', 2), ('T2-Ej6', 'G', 2),
 # Tarea 3
 ('T3-Ej1', 'B', 2), ('T3-Ej2', 'D', 2), ('T3-Ej3', 'B', 2), ('T3-Ej4', 'G', 2), ('T3-Ej5', 'A', 2), ('T3-Ej6', 'A', 2),
 # Clase 7 (= Clase 8)
 ('C7-TFPL', 'H', 1), ('C7-clasificar', 'H', 1), ('C7-ejemplo matricial', 'F', 1), ('C7-Ej1', 'F', 1), ('C7-Ej2', 'F', 1),
 ('C7-Ej3 base dada', 'G', 1), ('C7-Ej4', 'F', 1), ('C7-teoremas', 'C', 0.5),
 # Clase 9
 ('C9-ejemplo tableau', 'F', 1), ('C9-amigo', 'G', 1),
 # Clase 10
 ('C10-Ej1 no acotado', 'F', 1), ('C10-Ej2 multiples', 'F', 1), ('C10-Ej3 degenerado', 'F', 1),
 ('C10-propiedades', 'C', 0.5), ('C10-lema no acot.', 'C', 0.5), ('C10-convexidad', 'C', 0.5), ('C10-terminacion', 'C', 0.5),
 # Clase 11
 ('C11-Ej1', 'A', 1), ('C11-Ej2 infactible', 'A', 1), ('C11-p27 dicc. Fase I', 'A', 1), ('C11-p28', 'A', 1),
 # Tarea 1 (forma estandar y bases, solo lo que reaparece en este parcial)
 ('T1-Ej10', 'J', 0.5), ('T1-Ej11', 'H', 0.5),
]
m = np.zeros(len(K))
for _, k, w in material: m[K.index(k)] += w
mhat = m / m.sum()

# ---------------- evidencia de examen (preguntas del alcance; Prueba 1 cuenta 0.5 porque era otro parcial)
exam = {'A': 1.0, 'B': 1.0, 'C': 1.0 + 0.5, 'H': 0.5, 'J': 0.5}   # P2-Q1, P2-Q2, P2-Q3, P1-Q3(a) demostración corta, P1-Q3 bases, P1-Q2
n = np.array([exam.get(k, 0.0) for k in K])
pregunto_P2 = np.array([k in ('A', 'B', 'C') for k in K])

# ---------------- número de preguntas: Dirichlet(1,1,1) sobre {2,3,4} + observaciones (3,3)
N_vals, N_p = np.array([2, 3, 4]), np.array([1, 3, 1]) / 5

def alphas(beta, gamma, rho):
    """Escenario 'molde': repite lo que ya preguntó. Escenario 'rotación': castiga lo de la Prueba 2."""
    a_molde = beta * mhat + gamma * n
    a_rot = beta * mhat * np.where(pregunto_P2, rho, 1.0) + 0.3 * gamma * n * np.where(pregunto_P2, 0, 1)
    return a_molde + 1e-6, a_rot + 1e-6

TIME = np.array([ARQ[k][1] for k in K])

def simula(beta, gamma, rho, pi, R, rng, guardar=False):
    a_m, a_r = alphas(beta, gamma, rho)
    cuenta = np.zeros(len(K)); examenes = []
    acept = 0
    while acept < R:
        molde = rng.random() < pi
        th = rng.dirichlet(a_m if molde else a_r)
        N = rng.choice(N_vals, p=N_p)
        disp = list(range(len(K))); elig = []
        for _ in range(N):                      # Plackett-Luce: sin reemplazo, proporcional a theta
            p = th[disp] / th[disp].sum()
            j = rng.choice(disp, p=p); elig.append(j); disp.remove(j)
        t = TIME[elig].sum()
        if not (60 <= t <= 95): continue        # debe caber en 90 minutos y no ser trivial
        acept += 1
        cuenta[elig] += 1
        if guardar: examenes.append((molde, [K[j] for j in elig]))
    return cuenta / R, examenes

if __name__ == '__main__':
    rng = np.random.default_rng(2026)
    R = 20000
    grid = list(itertools.product([3, 6, 12], [1, 2, 3], [0.3, 0.6], [0.3, 0.5, 0.7]))
    tabla = []
    for beta, gamma, rho, pi in grid:
        p, _ = simula(beta, gamma, rho, pi, 4000, rng)
        tabla.append(p)
    tabla = np.array(tabla)
    base, _ = simula(6, 2, 0.6, 0.5, R, rng)
    # desenlace de los ejercicios computacionales: conteos del material + suavizado, castigo a 'no acotado' (ya usado)
    des = {'único': 8, 'múltiples': 2, 'no acotado': 5, 'infactible': 2, 'degenerado/empate': 3, 'artificial en cero': 1}
    w = np.array(list(des.values()), float) + 1
    w[list(des).index('no acotado')] *= 0.5
    p_des = w / w.sum()
    # rasgos de los incisos (Beta(1,1) + observaciones)
    rasgos = {'inciso de teoría corta dentro de un ejercicio computacional': (2, 2),
              'inciso "sustituya estos valores y termine de resolver" en parámetros': (1, 1),
              'base inicial dada (no desde holguras) en dos fases/diccionario': (1, 1),
              'al menos una pregunta casi copiada de una tarea': (2, 2)}
    p_rasgo = {r: (1 + s) / (2 + t) for r, (s, t) in rasgos.items()}
    out = {'K': K, 'nombres': {k: ARQ[k][0] for k in K}, 'tiempo': {k: ARQ[k][1] for k in K},
           'material_peso': dict(zip(K, m.round(2).tolist())), 'material_share': dict(zip(K, mhat.round(3).tolist())),
           'examen_n': dict(zip(K, n.tolist())),
           'p_aparece_base': dict(zip(K, base.round(3).tolist())),
           'p_aparece_min': dict(zip(K, tabla.min(0).round(3).tolist())),
           'p_aparece_max': dict(zip(K, tabla.max(0).round(3).tolist())),
           'p_desenlace': dict(zip(des, p_des.round(3).tolist())),
           'p_rasgo': {r: round(v, 3) for r, v in p_rasgo.items()},
           'N_p': dict(zip(N_vals.tolist(), N_p.tolist()))}
    # ---------------- sorteo de los 3 simulacros (semillas fijas, sin repetir combinación)
    rs = np.random.default_rng(31102026)
    sorteos, vistos = [], set()
    while len(sorteos) < N_SORTEOS:
        _, ex = simula(6, 2, 0.6, 0.5, 1, rs, guardar=True)
        molde, arq = ex[0]
        clave = tuple(sorted(arq))
        if clave in vistos: continue
        vistos.add(clave)
        d = {'escenario': 'molde' if molde else 'rotación', 'preguntas': []}
        for k in arq:
            q = {'arquetipo': k}
            if k in ('A', 'F', 'G', 'B'):
                opciones = list(des) if k == 'A' else [x for x in des if x not in ('infactible', 'artificial en cero')]
                pp = np.array([p_des[list(des).index(x)] for x in opciones]); pp /= pp.sum()
                q['desenlace'] = str(rs.choice(opciones, p=pp))
                q['teoria_corta'] = bool(rs.random() < p_rasgo['inciso de teoría corta dentro de un ejercicio computacional'])
            if k in ('A', 'G'):
                q['base_dada'] = bool(rs.random() < p_rasgo['base inicial dada (no desde holguras) en dos fases/diccionario'])
            if k == 'B':
                q['terminar_con_valores'] = bool(rs.random() < p_rasgo['inciso "sustituya estos valores y termine de resolver" en parámetros'])
            q['nivel'] = str(rs.choice(['casi copia de tarea', 'adaptación', 'nuevo'], p=[1/3, 1/3, 1/3]))
            d['preguntas'].append(q)
        t = sum(ARQ[q['arquetipo']][1] for q in d['preguntas'])
        for q in d['preguntas']:   # puntos proporcionales al tiempo, redondeados a 0.5 y que sumen 10
            q['pts_raw'] = 10 * ARQ[q['arquetipo']][1] / t
        pts = [round(q['pts_raw'] * 2) / 2 for q in d['preguntas']]
        pts[int(np.argmax(pts))] += 10 - sum(pts)
        for q, p in zip(d['preguntas'], pts): q['pts'] = p; del q['pts_raw']
        d['minutos'] = int(t)
        sorteos.append(d)
    out['sorteos'] = sorteos
    print(json.dumps({k: out[k] for k in out if k != 'sorteos'}, indent=1, ensure_ascii=False))
    for i, d in enumerate(out['sorteos'], 1):
        print(f'Sorteo {i}:', json.dumps(d, ensure_ascii=False))
    json.dump(out, open(SALIDA, 'w'), ensure_ascii=False, indent=1)
