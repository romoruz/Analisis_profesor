"""Modelo bayesiano de tipos de pregunta + Monte Carlo + sorteo de simulacros. Genérico.

Junta en un solo motor configurable lo que en el repo de PL eran dos scripts distintos
(03_modelo_parcial2.py y 04_modelo_parcial3.py). Un examen simulado se genera así:

  1. theta_mat ~ Dir(beta * m_hat * rot + s)   (m_hat: pesos del material, tareas sobre todo)
     theta_mol ~ Dir(beta * n_hat * rot + s)   (n_hat: tipos que salieron en exámenes previos
                                                del mismo parcial; 'molde')
     rot castiga lo que ya se preguntó este semestre (factor rho < 1).
  2. pi ~ Beta(a, b): probabilidad de que cada pregunta salga del molde y no del material.
  3. Con probabilidad q ~ Beta(.) se reserva un lugar para una demostración.
  4. Se llenan N lugares con tipos distintos.
  5. Se rechaza si los minutos no caen en la ventana o si no cubre los bloques anunciados
     (con probabilidad kappa).

Todo lo que es opinión (beta, pi, rho, kappa) se barre en una rejilla y se reporta mín y máx.
"""
import itertools
from collections import Counter
import numpy as np

def _norm(d, K):
    v = np.array([float(d.get(k, 0.0)) for k in K])
    return v / v.sum() if v.sum() > 0 else np.ones(len(K)) / len(K)

def prepara(cfg):
    K = list(cfg['arquetipos'])
    return {'K': K, 'm': _norm(cfg['material'], K), 'n': _norm(cfg.get('molde', {}), K),
            'hay_molde': sum(cfg.get('molde', {}).values()) > 0,
            'T': np.array([cfg['arquetipos'][k][1] for k in K], float),
            'dem': [K.index(k) for k in cfg.get('demostracion', {}).get('arquetipos', [])],
            'Nv': np.array(list(cfg['N'].keys())), 'Np': np.array(list(cfg['N'].values()), float)}

def simula(cfg, R, rng, beta=None, pi=None, rho=None, kappa=None, guardar=False):
    P = prepara(cfg); K = P['K']
    beta = cfg.get('beta', 6) if beta is None else beta
    s = cfg.get('suavizado', 0.3)
    rho = cfg.get('rho', 0.6) if rho is None else rho
    rot = np.array([rho if k in cfg.get('rotacion', []) else 1.0 for k in K])
    cob = cfg.get('cobertura')
    kappa = (cob or {}).get('kappa', 0.0) if kappa is None else kappa
    lo, hi = cfg['ventana']
    cuenta = np.zeros(len(K)); ex = []; acc = 0
    while acc < R:
        th_m = rng.dirichlet(beta * P['m'] * rot + s)
        th_n = rng.dirichlet(beta * P['n'] * rot + s) if P['hay_molde'] else th_m
        p_mol = rng.beta(*cfg['pi_molde']) if pi is None else pi
        N = int(rng.choice(P['Nv'], p=P['Np'] / P['Np'].sum()))
        elig = []
        if P['dem'] and rng.random() < rng.beta(*cfg['demostracion']['beta']):
            th = th_n if rng.random() < p_mol else th_m
            w = th[P['dem']]
            elig.append(P['dem'][int(rng.choice(len(w), p=w / w.sum()))])
        intentos = 0
        while len(elig) < N and intentos < 100:
            intentos += 1
            th = th_n if rng.random() < p_mol else th_m
            j = int(rng.choice(len(K), p=th))
            if j in elig:
                continue
            if j in P['dem'] and any(e in P['dem'] for e in elig) and cfg.get('una_demostracion', True):
                continue
            elig.append(j)
        if len(elig) < N:
            continue
        if not (lo <= P['T'][elig].sum() <= hi):
            continue
        if cob and rng.random() < kappa:
            if not all(set(K[j] for j in elig) & set(b) for b in cob['bloques']):
                continue
        acc += 1; cuenta[elig] += 1
        if guardar:
            ex.append([K[j] for j in elig])
    return cuenta / R, ex

def rejilla(cfg, malla, R, rng):
    """malla: dict nombre -> lista de valores (beta, pi, rho, kappa). Devuelve mín y máx por tipo."""
    nombres = list(malla)
    tabla = []
    for vals in itertools.product(*[malla[n] for n in nombres]):
        p, _ = simula(cfg, R, rng, **dict(zip(nombres, vals)))
        tabla.append(p)
    tabla = np.array(tabla)
    return tabla.min(0), tabla.max(0), len(tabla)

def corre(cfg, R=20000, R_rejilla=3000, semilla=2026, malla=None):
    rng = np.random.default_rng(semilla)
    K = list(cfg['arquetipos'])
    base, ex = simula(cfg, R, rng, guardar=True)
    out = {'K': K, 'nombres': {k: cfg['arquetipos'][k][0] for k in K},
           'minutos': {k: cfg['arquetipos'][k][1] for k in K},
           'p_base': dict(zip(K, base.round(3).tolist()))}
    if malla:
        mn, mx, n = rejilla(cfg, malla, R_rejilla, rng)
        out.update(p_min=dict(zip(K, mn.round(3).tolist())), p_max=dict(zip(K, mx.round(3).tolist())),
                   combinaciones_rejilla=n)
    out['combinaciones_top'] = [(list(k), round(v / len(ex), 3))
                                for k, v in Counter(tuple(sorted(e)) for e in ex).most_common(8)]
    return out

def _balancea(pool, p, n, rs, intentos=20000):
    """Elige n exámenes del pool cuya suma de apariciones por tipo quede lo más cerca posible
    de n * p (lo esperado). Así el conjunto de simulacros cubre los temas en proporción a su
    probabilidad en vez de depender de la suerte de cinco sorteos independientes."""
    K = list(p); objetivo = np.array([n * p[k] for k in K])
    M = np.array([[k in e for k in K] for e in pool], float)
    mejor, perdida = None, np.inf
    for _ in range(intentos):
        idx = rs.choice(len(pool), size=n, replace=False)
        d = ((M[idx].sum(0) - objetivo) ** 2).sum()
        if d < perdida:
            mejor, perdida = sorted(idx.tolist()), d
    return [pool[i] for i in mejor], float(perdida)

def sortea(cfg, n, semilla, decora=None, balancear=None, pool=150):
    """Sortea n exámenes distintos (como conjuntos de tipos) con semilla fija.
    - balancear=None: sorteos independientes (como en el repo de PL); pedir más conserva los primeros.
    - balancear=p_base (dict tipo -> probabilidad): se sortea un pool de exámenes distintos y se
      eligen los n que mejor reproducen las probabilidades en conjunto.
    `decora(k, rng)` agrega rasgos a cada pregunta. Las demostraciones van al final, como hace el profe."""
    rs = np.random.default_rng(semilla)
    dem = set(cfg.get('demostracion', {}).get('arquetipos', []))
    candidatos, vistos, repetidos = [], set(), 0
    meta = pool if balancear else n
    while len(candidatos) < meta and repetidos < 2000:   # el número de combinaciones es finito
        _, e = simula(cfg, 1, rs, guardar=True)
        clave = tuple(sorted(e[0]))
        if clave in vistos:
            repetidos += 1
            continue
        repetidos = 0
        vistos.add(clave); candidatos.append(e[0])
    if len(candidatos) < n:
        raise ValueError(f'solo hay {len(candidatos)} combinaciones distintas de tipos y pediste {n} sorteos: '
                         'agrega tipos, cambia N o amplía la ventana de minutos')
    if balancear:
        candidatos, _ = _balancea(candidatos, balancear, n, rs)
    sorteos = []
    for arq in candidatos:
        arq = [k for k in arq if k not in dem] + [k for k in arq if k in dem]
        preguntas = []
        for k in arq:
            q = {'arquetipo': k}
            if decora:
                q.update(decora(k, rs))
            preguntas.append(q)
        sorteos.append({'preguntas': preguntas,
                        'minutos': int(sum(cfg['arquetipos'][q['arquetipo']][1] for q in preguntas))})
    return sorteos
