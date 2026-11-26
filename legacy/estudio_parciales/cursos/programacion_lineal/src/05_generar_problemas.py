"""Generador de ejercicios por búsqueda aleatoria con restricciones.

Idea: se proponen problemas pequeños con coeficientes enteros chicos, se filtran rápido con
scipy (linprog) y los que pasan se confirman con aritmética exacta (herramientas/simplex.py).
Cada 'receta' pide un desenlace concreto: infactible en fase I, no acotado, óptimos
múltiples, pivote degenerado, o un problema de sensibilidad con números limpios.

Uso:
    python src/05_generar_problemas.py RECETA [SEMILLA] [CUANTOS]
    RECETA en {infactible, no_acotado, multiples, degenerado, sensibilidad, dual_simplex}
Ejemplo:
    python src/05_generar_problemas.py sensibilidad 7 3
"""
import sys, random
from fractions import Fraction as F
import numpy as np
from scipy.optimize import linprog
from herramientas.simplex import dos_fases, forma_estandar, analiza_base, simplex_dual
from herramientas.sensibilidad import rango_costo, rango_rhs, precios_sombra, fmt

def denominador_max(valores):
    return max((F(v).denominator for v in valores), default=1)

def limpio(valores, tope=6):
    """Números 'de examen': denominadores chicos."""
    return denominador_max(valores) <= tope

def propone(rng, m, n, sentidos, coef=(-2, 4), rhs=(2, 12), costo=(-3, 6)):
    filas = []
    for s in sentidos:
        a = [rng.randint(*coef) for _ in range(n)]
        if all(v == 0 for v in a):
            a[0] = 1
        filas.append((a, s, rng.randint(*rhs) * 2 // 2))
    c = [rng.randint(*costo) for _ in range(n)]
    return filas, c

def a_linprog(filas, c, maximizar):
    Aub, bub, Aeq, beq = [], [], [], []
    for a, s, r in filas:
        if s == '<=':
            Aub.append(a); bub.append(r)
        elif s == '>=':
            Aub.append([-v for v in a]); bub.append(-r)
        else:
            Aeq.append(a); beq.append(r)
    cc = [-v for v in c] if maximizar else c
    return linprog(cc, A_ub=Aub or None, b_ub=bub or None, A_eq=Aeq or None, b_eq=beq or None,
                   bounds=[(0, None)] * len(c), method='highs')

# ----------------------------------------------------------------------------- recetas
def receta(nombre, rng):
    """Devuelve (filas, c, maximizar, resultado_exacto) o None si el candidato no sirve."""
    maximizar = rng.random() < 0.5
    if nombre in ('infactible', 'no_acotado', 'multiples', 'degenerado'):
        sentidos = rng.choice([['>=', '=', '<='], ['>=', '>=', '<='], ['=', '>=', '<='], ['<=', '>=']])
        filas, c = propone(rng, len(sentidos), 3 if len(sentidos) == 3 else 2, sentidos)
        res = a_linprog(filas, c, maximizar)
        quiere = {'infactible': 2, 'no_acotado': 3}.get(nombre, 0)
        if res.status != quiere:
            return None
        ex = dos_fases(filas, c, maximizar)
        if nombre == 'infactible':
            return (filas, c, maximizar, ex) if ex['estado'] == 'infactible' and limpio([ex['w']]) else None
        if nombre == 'no_acotado':
            return (filas, c, maximizar, ex) if ex['estado'] == 'no_acotado' else None
        if ex['estado'] != 'optimo' or not limpio(ex['x'] + [ex['z']]):
            return None
        if nombre == 'multiples':
            return (filas, c, maximizar, ex) if ex['multiples'] else None
        hubo_empate = any(e[0] == 'pivote' and (e[1]['empate'] or e[1]['razon'] == 0)
                          for e in ex['fase1'] + ex.get('fase2', []))
        return (filas, c, maximizar, ex) if hubo_empate else None

    if nombre == 'sensibilidad':                 # max con <=: producción, 2 recursos, 3 productos
        filas, c = propone(rng, 2, 3, ['<=', '<='], coef=(1, 5), rhs=(6, 20), costo=(3, 12))
        filas = [(a, s, r * 10) for a, s, r in filas]
        ex = dos_fases(filas, c, True)
        if ex['estado'] != 'optimo' or ex['multiples']:
            return None
        base = ex['fase2'][-1][1]
        A, b, cm, _ = forma_estandar(filas, c, True)
        y = precios_sombra(A, b, cm, base, True)
        if not all(v > 0 for v in y):            # que ambos recursos tengan precio sombra
            return None
        if sum(1 for v in ex['x'] if v > 0) != 2:  # dos productos activos, uno fuera
            return None
        rangos = {f'c{j + 1}': rango_costo(A, b, cm, base, j, True) for j in range(3)}
        rangos.update({f'b{i + 1}': rango_rhs(A, b, cm, base, i) for i in range(2)})
        nums = ex['x'] + y + [v for iv in rangos.values() for v in iv if v is not None]
        if not limpio(nums, 3):
            return None
        ex.update(y=y, rangos=rangos)
        return filas, c, True, ex

    if nombre == 'dual_simplex':                 # min con >= y costos positivos: arranque dual factible
        filas, c = propone(rng, 2, 3, ['>=', '>='], coef=(0, 4), rhs=(3, 10), costo=(1, 8))
        A, b, cm, nombres = forma_estandar(filas, c)
        A = [[-v for v in fila] for fila in A]; b = [-v for v in b]   # multiplicar por -1
        estado, log = simplex_dual(A, b, cm, [3, 4])
        piv = sum(1 for e in log if e[0] == 'pivote')
        if estado != 'optimo' or piv < 2:
            return None
        info = log[-1][2]
        if not limpio(info['xB'] + [info['z']]):
            return None
        return filas, c, False, {'estado': 'optimo', 'pivotes': piv, 'base': log[-1][1],
                                  'xB': info['xB'], 'z': info['z']}
    raise ValueError(nombre)

def expr(coefs):
    t = [f'{v}x{j + 1}' for j, v in enumerate(coefs) if v != 0]
    return (' + '.join(t) or '0').replace('+ -', '- ')

def muestra(filas, c, maximizar, ex):
    obj = expr(c)
    print(f"  {'max' if maximizar else 'min'} {obj}")
    for a, s, r in filas:
        print(f'    {expr(a)} {s} {r}')
    resumen = {k: v for k, v in ex.items() if k in ('estado', 'w', 'x', 'z', 'multiples', 'y', 'pivotes', 'xB')}
    print('   ', {k: (list(map(str, v)) if isinstance(v, list) else str(v)) for k, v in resumen.items()})
    if 'rangos' in ex:
        print('    rangos:', {k: fmt(v) for k, v in ex['rangos'].items()})

if __name__ == '__main__':
    nombre = sys.argv[1] if len(sys.argv) > 1 else 'sensibilidad'
    semilla = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    cuantos = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    rng = random.Random(semilla)
    hallados, intentos = 0, 0
    while hallados < cuantos and intentos < 200000:
        intentos += 1
        r = receta(nombre, rng)
        if r:
            hallados += 1
            print(f'[{nombre} #{hallados}] (intento {intentos})')
            muestra(*r)
    if hallados < cuantos:
        print(f'Solo hallé {hallados} en {intentos} intentos; afloja las restricciones.')
