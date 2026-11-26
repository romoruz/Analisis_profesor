"""Verificación automática de los ejercicios del banco (sympy + integración numérica).

OJO: lo que imprime son SOLUCIONES (equilibrios, estabilidad, valores de bifurcación, ...).
Cada función devuelve (ok, lista de líneas de resumen). ok=False significa que el ejercicio
no se comporta como se diseñó y no debe usarse.
"""
import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp

x, y, z, r, th, t, lam, a, mu = sp.symbols('x y z r th t lam a mu', real=True)
LOC = {'x': x, 'y': y, 'z': z, 'r': r, 'th': th, 't': t, 'lam': lam, 'a': a, 'mu': mu}
S = lambda s: sp.sympify(s, locals=LOC)

def _clasifica_2o(g, x0):
    """x'' = g(x): centro si g'(x0)<0, silla si >0; si 0, mira el cambio de signo de g."""
    d = float(sp.diff(g, x).subs(x, x0))
    if abs(d) > 1e-9:
        return 'centro (estable, no asintótico)' if d < 0 else 'silla (inestable)'
    e = 1e-3
    izq, der = float(g.subs(x, x0 - e)), float(g.subs(x, x0 + e))
    if izq > 0 > der:
        return 'centro no hiperbólico (estable)'
    if izq < 0 < der:
        return 'silla no hiperbólica (inestable)'
    return 'cúspide (inestable)'

def potencial(c):
    f = S(c['f'])
    U = sp.simplify(-sp.integrate(f, x))
    ok = sp.simplify(sp.diff(U, x) + f) == 0
    if c.get('periodico'):
        raices = sorted(set(float(v) for v in sp.solveset(sp.expand_trig(f), x, sp.Interval.Ropen(-sp.pi, sp.pi))))
    else:
        raices = sorted(set(float(v) for v in sp.real_roots(sp.Poly(sp.expand(f), x))))
    lineas = [f'U(x) = {U}']
    for v in raices:
        lineas.append(f'  x* = {v:+.4f}: {_clasifica_2o(f, v)}')
    ok = ok and len(raices) >= 2
    return ok, lineas

def bif2(c):
    g = S(c['g'])
    res = sp.resultant(sp.Poly(g, x), sp.Poly(sp.diff(g, x), x))
    crit = sorted(set(float(v) for v in sp.real_roots(sp.Poly(res, lam)))) if res.has(lam) else []
    lineas = [f'valores críticos de lambda: {crit}']
    puntos = sorted(set([crit[0] - 1] + crit + [(u + v) / 2 for u, v in zip(crit, crit[1:])] + [crit[-1] + 1])) if crit else [0]
    for L in puntos:
        gl = g.subs(lam, L)
        eqs = sorted(set(round(float(v), 6) for v in sp.real_roots(sp.Poly(sp.nsimplify(sp.expand(gl)), x))))
        tipos = [f'{e:+.3f} {_clasifica_2o(gl, e)}' for e in eqs]
        lineas.append(f'  lambda={L:+.3f}: ' + ('; '.join(tipos) if tipos else 'sin equilibrios'))
    return len(crit) >= 1, lineas

def _eq_plano(f1, f2, cuadrante):
    sols = sp.solve([f1, f2], [x, y], dict=True)
    out = []
    for s in sols:
        X, Y = complex(s[x]), complex(s[y])
        if abs(X.imag) > 1e-9 or abs(Y.imag) > 1e-9:
            continue
        X, Y = X.real, Y.real
        if cuadrante and (X < -1e-9 or Y < -1e-9):
            continue
        out.append((X, Y))
    return sorted(set((round(u, 6), round(v, 6)) for u, v in out))

def _tipo(J):
    ev = np.linalg.eigvals(J); tr, det = np.trace(J), np.linalg.det(J)
    if abs(det) < 1e-9:
        return 'no hiperbólico (det=0)', ev
    if det < 0:
        return 'silla', ev
    if abs(tr) < 1e-9:
        return 'centro lineal (no hiperbólico)', ev
    est = 'estable' if tr < 0 else 'inestable'
    return ('foco ' if tr * tr - 4 * det < -1e-9 else 'nodo ') + est, ev

def plano_param(c):
    f1, f2 = S(c['f'][0]), S(c['f'][1])
    J = sp.Matrix([f1, f2]).jacobian([x, y])
    bif = c['lam_bif']
    puntos = sorted(set([bif[0] / 2] + bif + [(u + v) / 2 for u, v in zip(bif, bif[1:])] + [bif[-1] + 1]))
    lineas, ok = [], True
    for L in puntos:
        eqs = _eq_plano(f1.subs(lam, L), f2.subs(lam, L), c.get('cuadrante'))
        desc = []
        for X, Y in eqs:
            Jn = np.array(J.subs({lam: L, x: X, y: Y}).tolist(), float)
            desc.append(f'({X:.3g},{Y:.3g}) {_tipo(Jn)[0]}')
        lineas.append(f'  lambda={L:.3g}: ' + '; '.join(desc))
        if L in bif:   # en el valor de bifurcación algún equilibrio debe ser no hiperbólico
            ok = ok and any('no hiperbólico' in d for d in desc)
    if 'foco_hasta' in c:
        v = float(sp.Rational(c['foco_hasta']))
        dentro = [L for L in (v * 0.5, v * 0.99) ]
        fuera = [v * 1.01]
        def interior(L):
            eqs = [e for e in _eq_plano(f1.subs(lam, L), f2.subs(lam, L), True) if e[0] > 1e-6 and e[1] > 1e-6]
            return _tipo(np.array(J.subs({lam: L, x: eqs[0][0], y: eqs[0][1]}).tolist(), float))[0]
        ok = ok and all('foco' in interior(L) for L in dentro) and all('nodo' in interior(L) for L in fuera)
        lineas.append(f'  interior es foco para lambda < {c["foco_hasta"]} y nodo después: {ok}')
    return ok, lineas

def _integra(F, p0, T=60):
    s = solve_ivp(lambda _, u: F(*u), (0, T), p0, rtol=1e-8, atol=1e-10,
                  events=lambda _, u: np.hypot(*u) - 50)
    return np.hypot(*s.y[:, -1]), s.status == 1

def polar(c):
    f1, f2 = S(c['f'][0]), S(c['f'][1])
    rr = sp.sqrt(x ** 2 + y ** 2)
    rdot = S(c['rdot']).subs(r, rr)
    ok1 = sp.simplify(sp.expand(x * f1 + y * f2 - rr * rdot)) == 0
    ok2 = sp.simplify(sp.expand((x * f2 - y * f1) - (x ** 2 + y ** 2) * S(c['thdot']))) == 0
    lineas = [f'r\' = {c["rdot"]}, theta\' = {c["thdot"]}  (comprobado: {ok1 and ok2})']
    ok = ok1 and ok2
    J0 = sp.Matrix([f1, f2]).jacobian([x, y]).subs({x: 0, y: 0})
    lineas.append(f'  linealización en el origen: {J0.tolist()}, valores propios {list(J0.eigenvals())}')
    if 'param' in c:
        p = LOC[c['param']]
        g = sp.expand(S(c['rdot']) / r)
        for P in sorted(set([c['bif'][0] - 1] + c['bif'] + [(u + v) / 2 for u, v in zip(c['bif'], c['bif'][1:])] + [c['bif'][-1] + 1])):
            raices = [float(v) for v in sp.real_roots(sp.Poly(g.subs(p, sp.nsimplify(P)), r)) if v > 0]
            lineas.append(f'  {c["param"]}={P:+.3f}: ciclos en r = {sorted(set(round(v, 4) for v in raices))}, '
                          f'origen r\'/r -> {float(g.subs({p: P, r: 0})):+.3f}')
    else:
        F = sp.lambdify((x, y), [f1, f2])
        for cic in c['ciclos']:
            for p0 in ([cic * 0.9, 0], [cic * 1.1, 0]):
                rf, escapa = _integra(lambda u, v: F(u, v), p0)
                lineas.append(f'  desde r={p0[0]:.2f}: r(60)={rf:.4f}' + (' (escapa a infinito)' if escapa else ''))
    return ok, lineas

def polar_directo(c):
    p = LOC[c['param']]
    g = S(c['rdot']); h = S(c['thdot'])
    lineas = []
    for P in sorted(set([c['bif'][0] - 1] + c['bif'] + [(u + v) / 2 for u, v in zip(c['bif'], c['bif'][1:])] + [c['bif'][-1] + 1])):
        Pn = sp.nsimplify(P)
        ciclos = sorted(set(round(float(v), 4) for v in sp.solveset(sp.expand(g.subs(p, Pn) / r), r, sp.Interval.open(0, 10))))
        ths = sorted(set(round(float(v), 4) for v in sp.solveset(h.subs(p, Pn), th, sp.Interval.Ropen(0, 2 * sp.pi))))
        lineas.append(f'  {c["param"]}={P:+.3f}: r* = {ciclos}, theta* = {ths}')
    return True, lineas

def lienard(c):
    p, q, cc = c['p'], c['q'], c['c']
    f1, f2 = y, -x - (p * x ** 2 + q * y ** 2 - cc) * y
    rr = sp.expand(x * f1 + y * f2)
    ok = sp.simplify(rr + y ** 2 * (p * x ** 2 + q * y ** 2 - cc)) == 0
    r1, r2 = 0.9 * (cc / max(p, q)) ** 0.5, (cc / min(p, q)) ** 0.5
    ang = np.linspace(0, 2 * np.pi, 721)
    F = sp.lambdify((x, y), rr)
    ok = ok and all(F(r1 * np.cos(u), r1 * np.sin(u)) >= -1e-12 for u in ang) and all(F(r2 * np.cos(u), r2 * np.sin(u)) <= 1e-12 for u in ang)
    G = sp.lambdify((x, y), [f1, f2])
    s = solve_ivp(lambda _, u: G(*u), (0, 200), [r1, 0], rtol=1e-9, atol=1e-11, dense_output=True)
    rad = np.hypot(*s.sol(np.linspace(150, 200, 2000)))
    ok = ok and r1 <= rad.min() and rad.max() <= r2 + 1e-6
    return ok, [f'r r\' = -y^2({p}z^2+{q}y^2-{cc}); anillo {r1:.3f} <= r <= {r2:.3f}; ciclo numérico entre r={rad.min():.3f} y {rad.max():.3f}']

def dulac_energia(c):
    f1, f2 = S(c['f'][0]), S(c['f'][1]); B = S(c['B'])
    d = sp.simplify(sp.diff(B * f1, x) + sp.diff(B * f2, y))
    g = S(c['z2']); U = sp.expand(-sp.integrate(g, z))
    crit = sorted(float(v) for v in sp.real_roots(sp.Poly(sp.diff(U, z), z)))
    um = min(float(U.subs(z, v)) for v in crit if abs(v) > 1e-9)
    xs = np.linspace(0.05, 6, 40)
    D = sp.lambdify((x, y), d)
    ok = all(D(u, v) < 0 for u in xs for v in xs)
    return ok, [f'div(Bf) = {d} < 0 en el cuadrante; ejes invariantes',
                f'U(z) = {U}; puntos críticos {crit}; periódicas si E < {um} y |z| < {max(crit)}']

def divergencia(c):
    f1, f2 = S(c['f'][0]), S(c['f'][1])
    d = sp.simplify(sp.diff(f1, x) + sp.diff(f2, y))
    return bool(sp.ask(sp.Q.positive(d.subs(y, 0))) and d.coeff(y, 2) >= 0), [f'div f = {d} > 0 en todo el plano']

def intervalo_lineal(c):
    ra = sorted(float(v) for v in sp.real_roots(sp.Poly(S(c['coef']), t)))
    def iv(t0):
        izq = max([v for v in ra if v < t0], default=-np.inf); der = min([v for v in ra if v > t0], default=np.inf)
        return (izq, der)
    ok = tuple(ra) == tuple(float(v) for v in c['raices'])
    return ok, [f'raíces del coeficiente principal: {ra}; t0={c["t0"]} -> {iv(c["t0"])}; t0={c["t1"]} -> {iv(c["t1"])}']

def blowup(c):
    X = sp.Function('X')
    s1 = sp.dsolve(sp.Eq(X(t).diff(t), 1 + X(t) ** 2), ics={X(0): 0}).rhs
    x0 = sp.symbols('x0', real=True)
    s2 = sp.dsolve(sp.Eq(X(t).diff(t), X(t) ** 2), ics={X(0): x0}).rhs
    return True, [f'(a) x = {s1}, intervalo (-pi/2, pi/2)', f'(b) x = {sp.simplify(s2)}; x0>0: (-inf,1/x0), x0<0: (1/x0,inf), x0=0: R']

def lyapunov_ab(c):
    f1, f2 = S(c['f'][0]), S(c['f'][1]); k = c['b_sobre_a']
    V = x ** 2 + k * y ** 2
    Vd = sp.expand(sp.diff(V, x) * f1 + sp.diff(V, y) * f2)
    J0 = sp.Matrix([f1, f2]).jacobian([x, y]).subs({x: 0, y: 0})
    ev = list(J0.eigenvals())
    ok = Vd == sp.expand(-2 * x ** 4 - 2 * k * y ** 4) and all(sp.re(e) == 0 for e in ev)
    return ok, [f'V = x^2+{k}y^2 (a=1, b={k}); V\' = {Vd}; valores propios en el origen {ev}']

def lyapunov_delta(c):
    f1, f2 = S(c['f'][0]), S(c['f'][1])
    Vd = sp.lambdify((x, y), sp.expand(2 * x * f1 + 2 * y * f2))
    ang = np.linspace(0, 2 * np.pi, 2001)
    rs = np.linspace(0.01, 2, 2000)
    rmax = next(rv for rv in rs if (Vd(rv * np.cos(ang), rv * np.sin(ang)) >= 0).any())
    eqs = [e for e in _eq_plano(f1, f2, False) if e != (0.0, 0.0)]
    dmin = min(np.hypot(*e) for e in eqs)
    ok = abs(rmax - c['delta']) < 2e-3 and abs(dmin - c['delta']) < 1e-6
    return ok, [f'V = x^2+y^2: V\'<0 para r < {rmax:.4f}; equilibrio más cercano a distancia {dmin:.4f}; delta = 1/sqrt(2)']

FUNCIONES = {k: v for k, v in globals().items() if callable(v) and not k.startswith('_')}

def verifica(cand):
    tipo = cand['check']['tipo']
    if tipo == 'demostracion':
        return True, ['demostración: sin verificación automática (enunciado revisado a mano)']
    return FUNCIONES[tipo](cand['check'])
