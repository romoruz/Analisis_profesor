"""Análisis de sensibilidad exacto a partir de una base óptima (problema en forma de mínimo).

rango_rhs(i):    intervalo de b_i en el que la base sigue siendo factible (y por tanto óptima).
rango_costo(j):  intervalo de c_j en el que la base sigue siendo óptima.
Si el problema original era de máximo, pasa maximizar=True y los rangos se devuelven en
términos del costo original (no del negado).
"""
from fractions import Fraction as F
from .simplex import analiza_base, matvec, columna

INF = None  # None = infinito

def _intervalo(lo, hi):
    return (lo, hi)

def rango_rhs(A, b, c, base, i):
    info = analiza_base(A, b, c, base)
    d = [fila[i] for fila in info['Binv']]          # columna i de B^-1
    lo, hi = INF, INF
    for xb, dk in zip(info['xB'], d):               # xB + delta*d >= 0
        if dk > 0:
            t = -xb / dk; lo = t if lo is None else max(lo, t)
        elif dk < 0:
            t = -xb / dk; hi = t if hi is None else min(hi, t)
    return _intervalo(None if lo is None else b[i] + lo, None if hi is None else b[i] + hi)

def rango_costo(A, b, c, base, j, maximizar=False):
    info = analiza_base(A, b, c, base)
    if j not in base:                                # no básica: solo importa su costo reducido
        r = info['red'][j]
        lo, hi = c[j] - r, None                      # c_j puede subir sin límite, bajar hasta red=0
    else:
        k = base.index(j)
        fila = {jj: sum(info['Binv'][k][i] * A[i][jj] for i in range(len(A))) for jj in info['red']}
        lo, hi = None, None                          # red_jj - delta*fila_jj >= 0
        for jj, a in fila.items():
            if a > 0:
                t = info['red'][jj] / a; hi = t if hi is None else min(hi, t)
            elif a < 0:
                t = info['red'][jj] / a; lo = t if lo is None else max(lo, t)
        lo = None if lo is None else c[j] + lo
        hi = None if hi is None else c[j] + hi
    if maximizar:                                    # c_min = -c_max  ->  el intervalo se voltea
        lo, hi = (None if hi is None else -hi), (None if lo is None else -lo)
    return _intervalo(lo, hi)

def precios_sombra(A, b, c, base, maximizar=False):
    y = analiza_base(A, b, c, base)['y']
    return [-v for v in y] if maximizar else y

def fmt(iv):
    lo, hi = iv
    return f"[{'-inf' if lo is None else lo}, {'+inf' if hi is None else hi}]"
