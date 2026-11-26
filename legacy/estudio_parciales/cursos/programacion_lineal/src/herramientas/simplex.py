"""Simplex con aritmética exacta (fracciones) para diseñar y verificar ejercicios.

Convenciones (las del curso):
  * Todo se resuelve como MINIMIZACIÓN; un máximo se pasa a min(-z).
  * Tableau con fila de costos reducidos; entra el más negativo (Dantzig);
    empates de entrada y de salida con la regla de Bland (menor índice).
  * Dos fases: artificiales solo en filas >= o =; las filas <= usan su holgura.
"""
from fractions import Fraction as F

# ----------------------------------------------------------------------------- álgebra exacta
def frac_matriz(M):
    return [[F(v) for v in fila] for fila in M]

def inversa(M):
    """Inversa por Gauss-Jordan con fracciones. Lanza ValueError si es singular."""
    n = len(M)
    A = [list(map(F, fila)) + [F(int(i == j)) for j in range(n)] for i, fila in enumerate(M)]
    for c in range(n):
        p = next((r for r in range(c, n) if A[r][c] != 0), None)
        if p is None:
            raise ValueError('matriz singular')
        A[c], A[p] = A[p], A[c]
        piv = A[c][c]
        A[c] = [v / piv for v in A[c]]
        for r in range(n):
            if r != c and A[r][c] != 0:
                f = A[r][c]
                A[r] = [a - f * b for a, b in zip(A[r], A[c])]
    return [fila[n:] for fila in A]

def matvec(M, v):
    return [sum(a * b for a, b in zip(fila, v)) for fila in M]

def columna(A, j):
    return [fila[j] for fila in A]

# ----------------------------------------------------------------------------- formato estándar
def forma_estandar(filas, c, maximizar=False):
    """filas: lista de (coeficientes, sentido, rhs) con sentido en {'<=', '>=', '='}.
    Devuelve A, b, costos (de minimización) y nombres. Holgura +1 en <=, exceso -1 en >=."""
    n = len(c)
    k = sum(1 for f in filas if f[1] != '=')
    A, b, nombres = [], [], [f'x{j + 1}' for j in range(n)]
    j = 0
    for coefs, sentido, rhs in filas:
        extra = [0] * k
        if sentido != '=':
            extra[j] = 1 if sentido == '<=' else -1
            j += 1
        A.append(list(coefs) + extra)
        b.append(rhs)
    nombres += [f's{i + 1}' for i in range(k)]
    costos = [(-v if maximizar else v) for v in c] + [0] * k
    return frac_matriz(A), [F(v) for v in b], [F(v) for v in costos], nombres

# ----------------------------------------------------------------------------- una base
def analiza_base(A, b, c, base):
    """Para una base (lista de índices): B^-1, x_B, y = c_B^T B^-1, costos reducidos y z."""
    B = [[A[i][j] for j in base] for i in range(len(A))]
    Bi = inversa(B)
    xB = matvec(Bi, b)
    cB = [c[j] for j in base]
    y = [sum(cB[k] * Bi[k][i] for k in range(len(base))) for i in range(len(A))]
    red = {j: c[j] - sum(y[i] * A[i][j] for i in range(len(A))) for j in range(len(c)) if j not in base}
    z = sum(cB[k] * xB[k] for k in range(len(base)))
    return {'Binv': Bi, 'xB': xB, 'y': y, 'red': red, 'z': z}

# ----------------------------------------------------------------------------- simplex primal
def simplex_primal(A, b, c, base, max_iter=50):
    """Simplex de mínimo desde una base factible. Devuelve (estado, bitácora).
    estado: 'optimo', 'no_acotado' o 'ciclo'. La bitácora guarda cada base y cada pivote."""
    base = list(base); log = []
    for _ in range(max_iter):
        info = analiza_base(A, b, c, base)
        log.append(('base', list(base), info))
        neg = [j for j, r in info['red'].items() if r < 0]
        if not neg:
            return 'optimo', log
        m = min(info['red'][j] for j in neg)
        t = min(j for j in neg if info['red'][j] == m)             # Dantzig + Bland en empate
        d = matvec(info['Binv'], columna(A, t))                   # columna B^-1 A_t
        filas = [(info['xB'][i] / d[i], base[i], i) for i in range(len(base)) if d[i] > 0]
        if not filas:
            log.append(('no_acotado', t))
            return 'no_acotado', log
        r = min(f[0] for f in filas)
        empate = [f for f in filas if f[0] == r]
        _, sale, i = min(empate, key=lambda f: f[1])                # Bland en la salida
        log.append(('pivote', {'entra': t, 'sale': sale, 'razon': r, 'empate': len(empate) > 1}))
        base[i] = t
    return 'ciclo', log

# ----------------------------------------------------------------------------- dos fases
def dos_fases(filas, c, maximizar=False):
    """Método de dos fases. Devuelve dict con 'estado' en
    {'optimo', 'no_acotado', 'infactible', 'artificial_en_cero'} y las bitácoras de cada fase."""
    A, b, costos, nombres = forma_estandar(filas, c, maximizar)
    m, n = len(A), len(A[0])
    for i in range(m):                                           # rhs >= 0
        if b[i] < 0:
            A[i] = [-v for v in A[i]]; b[i] = -b[i]
    base, arts = [], []
    for i in range(m):
        holg = [j for j in range(len(c), n) if A[i][j] == 1 and all(A[k][j] == 0 for k in range(m) if k != i)]
        if holg:
            base.append(holg[0])
        else:
            arts.append(i); base.append(n + len(arts) - 1)
    Aart = [fila + [F(int(i == arts[k])) for k in range(len(arts))] for i, fila in enumerate(A)]
    c1 = [F(0)] * n + [F(1)] * len(arts)
    est1, log1 = simplex_primal(Aart, b, c1, base)
    info1 = log1[-1][2] if log1[-1][0] == 'base' else None
    base1 = log1[-1][1] if log1[-1][0] == 'base' else None
    res = {'nombres': nombres + [f'a{k + 1}' for k in range(len(arts))], 'fase1': log1}
    w = info1['z']
    if w > 0:
        res.update(estado='infactible', w=w); return res
    if any(j >= n for j in base1):
        res.update(estado='artificial_en_cero', w=w, base_fase1=base1); return res
    est2, log2 = simplex_primal(A, b, costos, base1)
    res.update(estado='optimo' if est2 == 'optimo' else est2, fase2=log2)
    if est2 == 'optimo':
        info = log2[-1][2]; base2 = log2[-1][1]
        x = [F(0)] * n
        for k, j in enumerate(base2):
            x[j] = info['xB'][k]
        res.update(x=x[:len(c)], z=(-info['z'] if maximizar else info['z']),
                   multiples=any(r == 0 for r in info['red'].values()))
    return res

# ----------------------------------------------------------------------------- simplex dual
def simplex_dual(A, b, c, base, max_iter=50):
    """Simplex dual de mínimo desde una base DUAL factible (costos reducidos >= 0).
    Sale el rhs más negativo; entra la de menor razón red_j / |a_sj| con a_sj < 0."""
    base = list(base); log = []
    for _ in range(max_iter):
        info = analiza_base(A, b, c, base)
        log.append(('base', list(base), info))
        neg = [i for i in range(len(base)) if info['xB'][i] < 0]
        if not neg:
            return 'optimo', log
        s = min(neg, key=lambda i: (info['xB'][i], base[i]))
        fila_s = {j: sum(info['Binv'][s][i] * A[i][j] for i in range(len(A))) for j in info['red']}
        cand = [j for j, v in fila_s.items() if v < 0]
        if not cand:
            log.append(('infactible', base[s]))
            return 'infactible', log
        t = min(cand, key=lambda j: (info['red'][j] / -fila_s[j], j))
        log.append(('pivote', {'sale': base[s], 'entra': t, 'razon': info['red'][t] / -fila_s[t]}))
        base[s] = t
    return 'ciclo', log

# ----------------------------------------------------------------------------- impresión
def imprime_bitacora(log, nombres, maximizar=False):
    for e in log:
        if e[0] == 'base':
            _, base, info = e
            xb = ', '.join(f'{nombres[j]}={info["xB"][k]}' for k, j in enumerate(base))
            red = ', '.join(f'{nombres[j]}:{r}' for j, r in sorted(info['red'].items()))
            z = -info['z'] if maximizar else info['z']
            print(f'  base [{xb}]  z={z}  costos reducidos (min) {{{red}}}')
        elif e[0] == 'pivote':
            p = e[1]
            extra = ' (EMPATE, Bland)' if p.get('empate') else ''
            print(f'  -> entra {nombres[p["entra"]]}, sale {nombres[p["sale"]]}, razón {p["razon"]}{extra}')
        else:
            print('  ->', e[0], nombres[e[1]])
