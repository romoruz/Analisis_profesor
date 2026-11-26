"""Verificación de respuestas de los simulacros (OJO: este archivo CONTIENE SOLUCIONES).

Cada caso se resuelve dos veces: con scipy (HiGHS, punto flotante) y con el simplex exacto
de herramientas/. Además se arma el dual y se revisa que z_primal = z_dual (dualidad fuerte).
Al final se revisa el problema paramétrico de la Reposición 3 barriendo el parámetro.

Uso:  python src/06_verificar_respuestas.py
Para agregar tus propios casos: añade una entrada a CASOS con la respuesta que obtuviste.
"""
from fractions import Fraction as F
import numpy as np
from scipy.optimize import linprog
from herramientas.simplex import dos_fases, forma_estandar, analiza_base
from herramientas.sensibilidad import precios_sombra

# (nombre, filas, c, maximizar, esperado)  esperado: 'infactible' | 'no_acotado' | (z, x o None)
CASOS = [
    ('P2 Simulacro A - P1', [([3, 1, 1], '<=', 8), ([1, 1, 1], '>=', 4)], [1, 4, -2], True, (32, [0, 8, 0])),
    ('P2 Simulacro A - P3', [([1, 2, 2], '=', 8), ([3, 1, 2], '<=', 10)], [2, 1, 4], True, (16, None)),
    ('P2 Sorteo 1 - P1', [([2, 2], '>=', 6), ([-1, 1], '=', 6), ([1, 3], '<=', 12)], [5, 1], True, 'infactible'),
    ('P2 Sorteo 1 - P2', [([-1, -2, 2], '<=', 8), ([3, -1, 2], '<=', 6), ([3, 0, 2], '<=', 8)], [3, 1, 4], True, 'no_acotado'),
    ('P2 Sorteo 3 - P1', [([2, 1, 0], '>=', 4), ([-1, 1, 1], '=', 8), ([2, 1, 0], '<=', 8)], [1, 1, 5], False, (8, [0, 8, 0])),
    ('P2 Sorteo 3 - P2', [([-1, 2], '<=', 8), ([1, 0], '<=', 6), ([0, 2], '<=', 8)], [1, 2], True, (14, [6, 4])),
    ('P3 Simulacro 1 - Q1', [([3, 2, 2], '<=', 150), ([2, 4, 4], '<=', 180)], [35, 50, 40], True, (2550, [30, 30, 0])),
    ('P3 Simulacro 3 - Q2', [([2, 2, 1], '<=', 180), ([1, 2, 2], '<=', 150)], [9, 5, 8], True, (950, [70, 0, 40])),
    ('P3 Simulacro 4 - Q2', [([3, 4, 2], '<=', 180), ([3, 2, 1], '<=', 120)], [8, 6, 4], True, (400, [20, 0, 60])),
    ('P3 Simulacro 4 - Q2 con x3<=50', [([3, 4, 2], '<=', 180), ([3, 2, 1], '<=', 120), ([0, 0, 1], '<=', 50)],
     [8, 6, 4], True, (390, [20, 5, 50])),
    ('P3 Simulacro 4 - Q3', [([-1, 2], '>=', 3), ([1, 1], '>=', 6), ([1, 4], '>=', 2)], [1, 2], False, (9, [3, 3])),
]

def scipy_resuelve(filas, c, maximizar):
    Aub, bub, Aeq, beq = [], [], [], []
    for a, s, r in filas:
        if s == '<=': Aub.append(a); bub.append(r)
        elif s == '>=': Aub.append([-v for v in a]); bub.append(-r)
        else: Aeq.append(a); beq.append(r)
    res = linprog([-v for v in c] if maximizar else c, A_ub=Aub or None, b_ub=bub or None,
                  A_eq=Aeq or None, b_eq=beq or None, bounds=[(0, None)] * len(c), method='highs')
    estado = {0: 'optimo', 2: 'infactible', 3: 'no_acotado'}.get(res.status, f'status {res.status}')
    z = (-res.fun if maximizar else res.fun) if res.status == 0 else None
    return estado, z, res.x if res.status == 0 else None

def dual_de(filas, c, maximizar):
    """Dual por la tabla de correspondencias (primal con x >= 0)."""
    m = len(filas); n = len(c)
    # pasamos todo a max con <= / = para leer signos: >= en max -> y <= 0 ; <= en min -> y <= 0
    cotas = []
    for _, s, _ in filas:
        if s == '=':
            cotas.append((None, None))
        elif (s == '<=') == maximizar:
            cotas.append((0, None))
        else:
            cotas.append((None, 0))
    At = [[filas[i][0][j] for i in range(m)] for j in range(n)]
    b = [f[2] for f in filas]
    # max c x, x>=0  ->  min b y,  A^T y >= c ;  min c x  ->  max b y,  A^T y <= c
    if maximizar:
        res = linprog(b, A_ub=[[-v for v in fila] for fila in At], b_ub=[-v for v in c], bounds=cotas, method='highs')
        return res.status, (res.fun if res.status == 0 else None)
    res = linprog([-v for v in b], A_ub=At, b_ub=c, bounds=cotas, method='highs')
    return res.status, (-res.fun if res.status == 0 else None)

def revisa(nombre, filas, c, maximizar, esperado):
    est_s, z_s, x_s = scipy_resuelve(filas, c, maximizar)
    ex = dos_fases(filas, c, maximizar)
    est_e = ex['estado']
    ok = True
    if isinstance(esperado, str):
        ok = est_s == esperado and est_e == esperado
        detalle = f'{est_s}/{est_e}' + (f", w*={ex['w']}" if est_e == 'infactible' else '')
    else:
        z_esp, x_esp = esperado
        ok = est_s == est_e == 'optimo' and abs(z_s - z_esp) < 1e-7 and ex['z'] == z_esp
        if x_esp is not None and ok:
            ok = all(abs(a - b) < 1e-7 for a, b in zip(x_s, x_esp)) or ex['multiples']
        st, zd = dual_de(filas, c, maximizar)
        ok = ok and st == 0 and abs(zd - z_esp) < 1e-7
        detalle = f"z={ex['z']} x={[str(v) for v in ex['x']]} dual={zd:g}" + (' (óptimos múltiples)' if ex['multiples'] else '')
    print(f"{'OK ' if ok else 'XX '} {nombre:34s} {detalle}")
    return ok

def parametrico_reposicion3():
    """R3-P2: c = (a,1,-2,a^2+2,4,2a); x* = (1,2,1,0,0,0) óptimo para a en [-3,-2] U [1,3]."""
    A = [[1, 1, 0, 1, 0, 2], [0, 1, 1, 1, 1, 0], [0, 1, 2, 0, 1, 1]]; b = [3, 3, 4]
    xs = np.array([1, 2, 1, 0, 0, 0])
    optimo_en = []
    for a in np.round(np.arange(-5, 5.0001, 0.25), 2):
        c = np.array([a, 1, -2, a * a + 2, 4, 2 * a])
        r = linprog(c, A_eq=A, b_eq=b, bounds=[(0, None)] * 6, method='highs')
        if r.status == 0 and abs(c @ xs - r.fun) < 1e-8:
            optimo_en.append(float(a))
    esperado = [a for a in np.round(np.arange(-5, 5.0001, 0.25), 2) if -3 <= a <= -2 or 1 <= a <= 3]
    ok = optimo_en == [float(a) for a in esperado]
    print(f"{'OK ' if ok else 'XX '} {'P2 Reposición 3 - P2 (paramétrico)':34s} x* óptimo en a = {optimo_en[0]}..{optimo_en[-1]} (rejilla 0.25)")
    r = linprog([0, 1, -2, 2, 4, 0], A_eq=A, b_eq=b, bounds=[(0, None)] * 6, method='highs')
    print(f"    con a=0: z={r.fun:g}, x={np.round(r.x, 6)}")
    return ok

if __name__ == '__main__':
    print('Verificación (scipy + simplex exacto + dualidad fuerte)\n')
    res = [revisa(*caso) for caso in CASOS]
    res.append(parametrico_reposicion3())
    print(f'\n{sum(res)}/{len(res)} casos coinciden.')
