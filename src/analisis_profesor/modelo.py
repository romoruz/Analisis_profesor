"""Paso 6 del protocolo: modelo bayesiano Dirichlet-multinomial y sorteo de simulacros."""
from __future__ import annotations

import itertools
import json
import math
import random
import re
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from pathlib import Path

from analisis_profesor.config import leer_config_materia
from analisis_profesor.esquemas import Etiqueta, Item, Prediccion, leer_jsonl
from analisis_profesor.estadistica import intervalo_jeffreys
from analisis_profesor.etiquetas import leer_etiquetas

try:
    import numpy as np
except ImportError:  # pragma: no cover - entorno sin numpy
    np = None  # type: ignore[assignment]

_MALLA_POR_DEFECTO: dict[str, list[float]] = {
    "beta": [3.0, 6.0, 12.0],
    "pi": [0.2, 0.4, 0.6],
    "rho": [0.3, 0.6, 1.0],
}
_NIVELES_POR_DEFECTO: tuple[str, ...] = ("casi copia", "adaptación", "nueva")


class _RngPuro:
    """Generador pseudoaleatorio en Python puro compatible con `simula` y `sortea`."""

    def __init__(self, semilla: int) -> None:
        self._rng = random.Random(semilla)

    def random(self) -> float:
        return self._rng.random()

    def beta(self, a: float, b: float) -> float:
        return self._rng.betavariate(float(a), float(b))

    def dirichlet(self, alpha: Sequence[float]) -> list[float]:
        gammas = [self._rng.gammavariate(max(float(a), 1e-12), 1.0) for a in alpha]
        total = sum(gammas)
        if total <= 0.0:
            n = len(gammas)
            return [1.0 / n] * n
        return [g / total for g in gammas]

    def choice(
        self,
        a: int | Sequence,
        size: int | None = None,
        replace: bool = True,
        p: Sequence[float] | None = None,
    ):
        valores = list(range(a)) if isinstance(a, int) else list(a)
        if size is not None:
            if replace:
                pesos = list(p) if p is not None else None
                return self._rng.choices(valores, weights=pesos, k=size)
            return self._rng.sample(valores, k=size)
        if p is None:
            return self._rng.choice(valores)
        total = float(sum(p))
        u = self._rng.random() * total
        acum = 0.0
        for idx, peso in enumerate(p):
            acum += float(peso)
            if u <= acum:
                return valores[idx]
        return valores[-1]


def _cuantil_lineal(ordenados: Sequence[float], q: float) -> float:
    if not ordenados:
        return 0.0
    pos = q * (len(ordenados) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    return float(ordenados[lo] + (pos - lo) * (ordenados[hi] - ordenados[lo]))


def _norm_vector(d: Mapping[str, float], k_lista: Sequence[str], *, usar_np: bool):
    vals = [float(d.get(k, 0.0)) for k in k_lista]
    s = sum(vals)
    normed = [v / s for v in vals] if s > 0.0 else [1.0 / len(k_lista)] * len(k_lista)
    if usar_np and np is not None:
        return np.array(normed, dtype=float)
    return normed


def _crear_rng(semilla: int, *, usar_numpy: bool | None = None):
    if usar_numpy is not False and np is not None:
        return np.random.default_rng(semilla)
    return _RngPuro(semilla)


def prepara(cfg: Mapping, *, usar_numpy: bool | None = None) -> dict:
    """Normaliza vectores del material, molde, tiempos y longitudes desde `cfg`.

    Fuente: `legacy/estudio_parciales/nucleo/modelo.py` (`prepara`) y
    `docs/METODOLOGIA_ESTADISTICA.md` §5.
    """
    usar_np = usar_numpy is not False and np is not None
    k_lista = list(cfg["arquetipos"])
    molde_dict = cfg.get("molde", {})
    n_dict = cfg["N"]
    nv_list = [int(k) for k in n_dict]
    np_list = [float(n_dict[k]) for k in n_dict]
    t_list = [float(cfg["arquetipos"][k][1]) for k in k_lista]
    if usar_np:
        t_out = np.array(t_list, dtype=float)
        nv_out = np.array(nv_list)
        np_out = np.array(np_list, dtype=float)
    else:
        t_out = t_list
        nv_out = nv_list
        np_out = np_list
    return {
        "K": k_lista,
        "m": _norm_vector(cfg["material"], k_lista, usar_np=usar_np),
        "n": _norm_vector(molde_dict, k_lista, usar_np=usar_np),
        "hay_molde": sum(molde_dict.values()) > 0,
        "T": t_out,
        "dem": [k_lista.index(k) for k in cfg.get("demostracion", {}).get("arquetipos", [])],
        "Nv": nv_out,
        "Np": np_out,
    }


def _preparar_contexto_simulacion(
    cfg: Mapping,
    *,
    beta: float | None = None,
    rho: float | None = None,
    kappa: float | None = None,
    usar_np: bool = False,
) -> dict:
    """Prepara parámetros vectorizados para `simula` y simulación por bloques."""
    p = prepara(cfg, usar_numpy=usar_np)
    k_lista = p["K"]
    beta_val = cfg.get("beta", 6) if beta is None else beta
    s = cfg.get("suavizado", 0.3)
    rho_val = cfg.get("rho", 0.6) if rho is None else rho
    rot_lista = [rho_val if k in cfg.get("rotacion", []) else 1.0 for k in k_lista]
    rot = np.array(rot_lista, dtype=float) if usar_np else rot_lista

    cob = cfg.get("cobertura")
    kappa_val = (cob or {}).get("kappa", 0.0) if kappa is None else kappa
    lo, hi = cfg["ventana"]

    if usar_np:
        alpha_m = beta_val * p["m"] * rot + s
        alpha_n = beta_val * p["n"] * rot + s
        np_probs = p["Np"] / p["Np"].sum()
    else:
        alpha_m = [beta_val * m_i * r_i + s for m_i, r_i in zip(p["m"], rot, strict=True)]
        alpha_n = [beta_val * n_i * r_i + s for n_i, r_i in zip(p["n"], rot, strict=True)]
        suma_np = sum(p["Np"])
        np_probs = [val / suma_np for val in p["Np"]]

    dem_cfg = cfg.get("demostracion", {})
    return {
        "p": p,
        "K": k_lista,
        "alpha_m": alpha_m,
        "alpha_n": alpha_n,
        "np_probs": np_probs,
        "cob": cob,
        "kappa": kappa_val,
        "lo": lo,
        "hi": hi,
        "una_dem": cfg.get("una_demostracion", True),
        "dem": p["dem"],
        "beta_dem": dem_cfg.get("beta"),
        "pi_molde": cfg["pi_molde"],
        "usar_np": usar_np,
    }


def _sortear_theta(ctx: Mapping, rng, pi: float | None = None):
    """Sortea una tupla de parámetros `(th_m, th_n, p_mol)` desde los priors."""
    th_m = rng.dirichlet(ctx["alpha_m"])
    th_n = rng.dirichlet(ctx["alpha_n"]) if ctx["p"]["hay_molde"] else th_m
    p_mol = rng.beta(*ctx["pi_molde"]) if pi is None else pi
    return th_m, th_n, p_mol


def _intentar_examen_bajo_theta(
    ctx: Mapping,
    rng,
    th_m,
    th_n,
    p_mol: float,
    *,
    q_dem_fijo: float | None = None,
) -> tuple[list[int] | None, float]:
    """Intenta sortear un examen aceptado bajo `(th_m, th_n, p_mol)`."""
    p = ctx["p"]
    k_lista = ctx["K"]
    usar_np = ctx["usar_np"]
    dem_indices = ctx["dem"]
    una_dem = ctx["una_dem"]

    n_preg = int(rng.choice(p["Nv"], p=ctx["np_probs"]))
    elig: list[int] = []
    if dem_indices:
        u_dem = rng.random()
        q_usado = float(rng.beta(*ctx["beta_dem"])) if q_dem_fijo is None else q_dem_fijo
        tiene_dem = u_dem < q_usado
    else:
        q_usado = 0.0
        tiene_dem = False

    if tiene_dem:
        th = th_n if rng.random() < p_mol else th_m
        if usar_np:
            w = th[dem_indices]
            w_norm = w / w.sum()
        else:
            w = [th[idx] for idx in dem_indices]
            sw = sum(w)
            w_norm = [v / sw for v in w]
        elig.append(dem_indices[int(rng.choice(len(w), p=w_norm))])

    intentos = 0
    while len(elig) < n_preg and intentos < 100:
        intentos += 1
        th = th_n if rng.random() < p_mol else th_m
        j = int(rng.choice(len(k_lista), p=th))
        if j in elig:
            continue
        if j in dem_indices and any(e in dem_indices for e in elig) and una_dem:
            continue
        elig.append(j)
    if len(elig) < n_preg:
        return None, q_usado

    tiempo_total = float(p["T"][elig].sum()) if usar_np else sum(p["T"][j] for j in elig)
    if not (ctx["lo"] <= tiempo_total <= ctx["hi"]):
        return None, q_usado

    cob = ctx["cob"]
    if cob and rng.random() < ctx["kappa"]:
        elegidos_k = {k_lista[j] for j in elig}
        if not all(elegidos_k & set(b) for b in cob["bloques"]):
            return None, q_usado

    return elig, q_usado


def _simular_bloques_theta(
    cfg: Mapping,
    n_bloques: int,
    tam_bloque: int,
    rng,
    *,
    usar_numpy: bool | None = None,
) -> list[list[float]]:
    """Calcula frecuencias condicionales por bloque `(th_m, th_n, p_mol, q_dem)` con rechazo.

    Cada bloque se inicia aceptando conjuntamente `(theta, q_dem, E_1)` mediante el mismo
    rechazo que `simula` (para muestrear `theta` desde la posterior condicionada a la
    aceptación de la ventana temporal) y completa `tam_bloque` exámenes aceptados bajo ese
    `theta` fijo. Esto evita el sesgo de reemplazo/sin ventana que difería > 0.03 de `p_base`.
    """
    usar_np = usar_numpy is not False and np is not None and not isinstance(rng, _RngPuro)
    ctx = _preparar_contexto_simulacion(cfg, usar_np=usar_np)
    m = len(ctx["K"])
    max_intentos = max(tam_bloque * 200, 1000)
    frecuencias: list[list[float]] = []

    for _ in range(n_bloques):
        elig_1: list[int] | None = None
        while elig_1 is None:
            th_m, th_n, p_mol = _sortear_theta(ctx, rng)
            elig_1, q_bloque = _intentar_examen_bajo_theta(ctx, rng, th_m, th_n, p_mol)

        conteo = [0] * m
        for j in elig_1:
            conteo[j] += 1
        aceptados = 1
        intentos = 0
        while aceptados < tam_bloque and intentos < max_intentos:
            intentos += 1
            elig, _ = _intentar_examen_bajo_theta(
                ctx, rng, th_m, th_n, p_mol, q_dem_fijo=q_bloque
            )
            if elig is not None:
                aceptados += 1
                for j in elig:
                    conteo[j] += 1
        frecuencias.append([c / aceptados for c in conteo])
    return frecuencias


def _simula_interna(
    cfg: Mapping,
    R: int,
    rng,
    beta: float | None = None,
    pi: float | None = None,
    rho: float | None = None,
    kappa: float | None = None,
    guardar: bool = False,
):
    """Ejecuta `R` simulaciones aceptadas y devuelve `(probs, examenes, aceptados, intentos)`."""
    usar_np = np is not None and not isinstance(rng, _RngPuro)
    ctx = _preparar_contexto_simulacion(cfg, beta=beta, rho=rho, kappa=kappa, usar_np=usar_np)
    k_lista = ctx["K"]
    cuenta = np.zeros(len(k_lista)) if usar_np else [0.0] * len(k_lista)
    ex: list[list[str]] = []
    acc = 0
    intentos = 0
    max_intentos = max(R * 1000, 100_000)

    while acc < R and intentos < max_intentos:
        intentos += 1
        th_m, th_n, p_mol = _sortear_theta(ctx, rng, pi=pi)
        elig, _ = _intentar_examen_bajo_theta(ctx, rng, th_m, th_n, p_mol)
        if elig is None:
            continue
        acc += 1
        if usar_np:
            cuenta[elig] += 1
        else:
            for j in elig:
                cuenta[j] += 1.0
        if guardar:
            ex.append([k_lista[j] for j in elig])

    if acc < R:
        lo, hi = ctx["lo"], ctx["hi"]
        raise ValueError(
            f"Ventana de minutos [{lo}, {hi}] demasiado estrecha: solo {acc}/{R} exámenes "
            f"aceptados tras {intentos} intentos."
        )

    probs = cuenta / R if usar_np else [c / R for c in cuenta]
    return probs, ex, acc, intentos


def simula(
    cfg: Mapping,
    R: int,
    rng,
    beta: float | None = None,
    pi: float | None = None,
    rho: float | None = None,
    kappa: float | None = None,
    guardar: bool = False,
):
    """Simula `R` exámenes del modelo bayesiano y devuelve `(probs, examenes)`.

    Fuente: `legacy/estudio_parciales/nucleo/modelo.py` (`simula`), basado en
    Dirichlet-multinomial conjugado con mezcla Beta (`docs/METODOLOGIA_ESTADISTICA.md` §5;
    Berger, Bernardo y Sun `arXiv:1504.02689` en `docs/INVESTIGACION.md`).
    Preserva exactamente la secuencia de llamadas a `rng` respecto a `legacy/`.
    """
    probs, ex, _acc, _intentos = _simula_interna(
        cfg, R, rng, beta=beta, pi=pi, rho=rho, kappa=kappa, guardar=guardar
    )
    return probs, ex


def rejilla(cfg: Mapping, malla: Mapping[str, Sequence[float]], R: int, rng):
    """Barre una rejilla de sensibilidad sobre hiperparámetros y devuelve `(min, max, n)`.

    Fuente: `legacy/estudio_parciales/nucleo/modelo.py` (`rejilla`).
    """
    nombres = list(malla)
    tabla = []
    for vals in itertools.product(*(malla[n] for n in nombres)):
        p, _ = simula(cfg, R, rng, **dict(zip(nombres, vals, strict=True)))
        tabla.append([float(x) for x in p])
    m = len(tabla[0])
    mins = [min(fila[j] for fila in tabla) for j in range(m)]
    maxs = [max(fila[j] for fila in tabla) for j in range(m)]
    if np is not None and not isinstance(rng, _RngPuro):
        return np.array(mins), np.array(maxs), len(tabla)
    return mins, maxs, len(tabla)


def corre(
    cfg: Mapping,
    R: int = 20000,
    R_rejilla: int = 3000,
    semilla: int = 2026,
    malla: Mapping[str, Sequence[float]] | None = None,
    *,
    usar_numpy: bool | None = None,
    incluir_intervalos: bool = False,
    n_bloques_ic: int = 800,
    tam_bloque_ic: int = 25,
) -> dict:
    """Ejecuta simulación base, barrido de rejilla, intervalos por bloques y combinaciones top.

    Fuente: `legacy/estudio_parciales/nucleo/modelo.py` (`corre`) y
    `docs/METODOLOGIA_ESTADISTICA.md` §5. Cuando `incluir_intervalos=True`, estima
    `p_q05` y `p_q95` mediante bloques de `tam_bloque_ic` exámenes aceptados por cada
    sorteo aceptado de `(theta, q_dem)`, reproduciendo el mecanismo exacto con rechazo
    que produce `p_base` usando un flujo `rng` separado (`semilla + 1`) tras `simula` y
    `rejilla` para preservar la reproducibilidad exacta de `legacy`.
    """
    usar_np = usar_numpy is not False and np is not None
    rng = _crear_rng(semilla, usar_numpy=usar_np)
    k_lista = list(cfg["arquetipos"])
    base, ex, n_acc, n_intentos = _simula_interna(cfg, R, rng, guardar=True)
    tasa_acept = n_acc / n_intentos if n_intentos > 0 else 0.0
    lo_min, hi_min = float(cfg["ventana"][0]), float(cfg["ventana"][1])
    avisos_modelo: list[str] = []
    if tasa_acept < 0.05:
        avisos_modelo.append(
            f"Tasa de aceptación baja ({tasa_acept:.1%}, {n_acc}/{n_intentos} intentos) "
            f"para la ventana [{lo_min:g}, {hi_min:g}] min (< 5 %); "
            "considera ampliar la ventana de minutos."
        )
    out: dict = {
        "K": k_lista,
        "nombres": {k: cfg["arquetipos"][k][0] for k in k_lista},
        "minutos": {k: cfg["arquetipos"][k][1] for k in k_lista},
        "ventana_minutos": [lo_min, hi_min],
        "tasa_aceptacion": round(tasa_acept, 4),
        "n_aceptados_simulacion": n_acc,
        "n_intentos_simulacion": n_intentos,
        "avisos_modelo": avisos_modelo,
        "p_base": {k: round(float(v), 3) for k, v in zip(k_lista, base, strict=True)},
    }
    if malla:
        mn, mx, n_comb = rejilla(cfg, malla, R_rejilla, rng)
        out["p_min"] = {k: round(float(v), 3) for k, v in zip(k_lista, mn, strict=True)}
        out["p_max"] = {k: round(float(v), 3) for k, v in zip(k_lista, mx, strict=True)}
        out["combinaciones_rejilla"] = n_comb

    if incluir_intervalos and n_bloques_ic > 0 and tam_bloque_ic > 0:
        rng_ic = _crear_rng(semilla + 1, usar_numpy=usar_np)
        q_muestras = _simular_bloques_theta(
            cfg, n_bloques_ic, tam_bloque_ic, rng_ic, usar_numpy=usar_np
        )
        if usar_np:
            arr_q = np.asarray(q_muestras, dtype=float)
            q05 = np.quantile(arr_q, 0.05, axis=0)
            q95 = np.quantile(arr_q, 0.95, axis=0)
            medias_q = arr_q.mean(axis=0)
        else:
            q05 = [
                _cuantil_lineal(sorted(fila[j] for fila in q_muestras), 0.05)
                for j in range(len(k_lista))
            ]
            q95 = [
                _cuantil_lineal(sorted(fila[j] for fila in q_muestras), 0.95)
                for j in range(len(k_lista))
            ]
            medias_q = [
                sum(fila[j] for fila in q_muestras) / len(q_muestras)
                for j in range(len(k_lista))
            ]
        out["p_q05"] = {k: round(float(v), 3) for k, v in zip(k_lista, q05, strict=True)}
        out["p_q95"] = {k: round(float(v), 3) for k, v in zip(k_lista, q95, strict=True)}
        out["p_muestras_media"] = {
            k: round(float(v), 3) for k, v in zip(k_lista, medias_q, strict=True)
        }
        out["n_bloques_ic"] = n_bloques_ic
        out["tam_bloque_ic"] = tam_bloque_ic
        out["metodo_ic"] = "bloques_rechazo"

        dem_arqs_list = list(cfg.get("demostracion", {}).get("arquetipos", []))
        dem_set = set(dem_arqs_list)
        if dem_set and ex:
            n_con_dem = sum(1 for examen in ex if any(k in dem_set for k in examen))
            p_dem = round(n_con_dem / len(ex), 3)
            ic_dem = [
                round(v, 4)
                for v in intervalo_jeffreys(n_con_dem, len(ex), usar_scipy=usar_np)["ic"]
            ]
        else:
            p_dem = 0.0
            ic_dem = [0.0, 0.0]
        out["probabilidad_demostracion"] = p_dem
        out["demostracion_inferencia"] = {
            "arquetipos": dem_arqs_list,
            "p_base": p_dem,
            "n_simulaciones": len(ex),
            "ic_simulacion": ic_dem,
        }

    out["combinaciones_top"] = [
        (list(c), round(cnt / len(ex), 3))
        for c, cnt in Counter(tuple(sorted(e)) for e in ex).most_common(8)
    ]
    return out


def _balancea(
    pool: Sequence[list[str]],
    p: Mapping[str, float],
    n: int,
    rs,
    intentos: int = 20000,
) -> tuple[list[list[str]], float]:
    """Elige `n` exámenes del pool cuya suma de apariciones queda más cerca de `n * p`.

    Fuente: `legacy/estudio_parciales/nucleo/modelo.py` (`_balancea`) y
    `docs/METODOLOGIA_ESTADISTICA.md` §7.
    """
    k_lista = list(p)
    if np is not None and not isinstance(rs, _RngPuro):
        objetivo = np.array([n * p[k] for k in k_lista])
        mat = np.array([[k in e for k in k_lista] for e in pool], float)
        mejor: list[int] | None = None
        perdida = float(np.inf)
        for _ in range(intentos):
            idx = rs.choice(len(pool), size=n, replace=False)
            d = float(((mat[idx].sum(0) - objetivo) ** 2).sum())
            if d < perdida:
                mejor, perdida = sorted(idx.tolist()), d
        assert mejor is not None
        return [pool[i] for i in mejor], perdida

    objetivo_py = [n * float(p[k]) for k in k_lista]
    mat_py = [[1.0 if k in e else 0.0 for k in k_lista] for e in pool]
    mejor_py: list[int] | None = None
    perdida_py = float("inf")
    m_k = len(k_lista)
    for _ in range(intentos):
        idx_py = rs.choice(len(pool), size=n, replace=False)
        d = sum(
            (sum(mat_py[i][j] for i in idx_py) - objetivo_py[j]) ** 2 for j in range(m_k)
        )
        if d < perdida_py:
            mejor_py, perdida_py = sorted(idx_py), d
    assert mejor_py is not None
    return [pool[i] for i in mejor_py], float(perdida_py)


def sortea(
    cfg: Mapping,
    n: int,
    semilla: int,
    decora: Callable[[str, object], dict] | None = None,
    balancear: Mapping[str, float] | None = None,
    pool: int = 150,
    *,
    usar_numpy: bool | None = None,
) -> list[dict]:
    """Sortea `n` exámenes distintos de tipos de pregunta, con opción balanceada.

    Fuente: `legacy/estudio_parciales/nucleo/modelo.py` (`sortea`) y
    `docs/METODOLOGIA_ESTADISTICA.md` §7.
    """
    rs = _crear_rng(semilla, usar_numpy=usar_numpy)
    dem = set(cfg.get("demostracion", {}).get("arquetipos", []))
    candidatos: list[list[str]] = []
    vistos: set[tuple[str, ...]] = set()
    repetidos = 0
    meta = pool if balancear else n
    while len(candidatos) < meta and repetidos < 2000:
        _, e = simula(cfg, 1, rs, guardar=True)
        clave = tuple(sorted(e[0]))
        if clave in vistos:
            repetidos += 1
            continue
        repetidos = 0
        vistos.add(clave)
        candidatos.append(e[0])
    if len(candidatos) < n:
        raise ValueError(
            f"Solo hay {len(candidatos)} combinaciones distintas y pediste {n} sorteos: "
            "agrega tipos, cambia N o amplía la ventana de minutos"
        )
    if balancear:
        candidatos, _ = _balancea(candidatos, balancear, n, rs)

    sorteos: list[dict] = []
    for arq in candidatos:
        ordenados = [k for k in arq if k not in dem] + [k for k in arq if k in dem]
        preguntas = []
        for k in ordenados:
            q: dict = {"arquetipo": k}
            if decora:
                q.update(decora(k, rs))
            preguntas.append(q)
        sorteos.append(
            {
                "preguntas": preguntas,
                "minutos": int(sum(cfg["arquetipos"][q["arquetipo"]][1] for q in preguntas)),
            }
        )
    return sorteos


def _clasificar_item(
    et: Etiqueta, items_por_id: Mapping[str, Item]
) -> tuple[str, str, str, str]:
    if it := items_por_id.get(et.item_id):
        return it.documento_id, it.tipo_doc, it.fecha, it.parcial
    doc_id, _, resto = et.item_id.partition(":")
    m_fecha = re.search(r"(20\d{2}-\d{2}-\d{2})", doc_id)
    fecha = m_fecha.group(1) if m_fecha else ""
    m_par = re.match(r"^(P[1-9]\d*|final)(?:_|$)", doc_id, re.I)
    parcial = m_par.group(1) if m_par else ""
    if resto.upper().startswith("Q") or parcial:
        return doc_id, "examen", fecha, parcial
    if re.match(r"^T\d+$", doc_id, re.I):
        return doc_id, "tarea", fecha, parcial
    if et.fuente or et.nivel or et.puntos is not None:
        return doc_id, "examen", fecha, parcial
    return doc_id, "clase", fecha, parcial


def _base_ejercicio_tarea(item_id: str) -> str:
    return re.sub(r"[a-z]+$", "", item_id)


def _rango_semestre(semestre: str, fecha_objetivo: str = "") -> tuple[str, str] | None:
    """Devuelve `(fecha_inicio, fecha_fin)` en formato `AAAA-MM-DD` para el semestre dado."""
    texto = semestre.strip()
    if texto:
        tokens_term = r"(?:II|I|2|1|primavera|otoño|otono|fall|spring|p|o)"
        m_anio_primero = re.fullmatch(
            rf"(\d{{4}})\s*[-/\s]\s*({tokens_term})", texto, re.IGNORECASE
        )
        m_term_primero = re.fullmatch(
            rf"({tokens_term})\s*[-/\s]\s*(\d{{4}})", texto, re.IGNORECASE
        )
        if m_anio_primero:
            anio, term = m_anio_primero.group(1), m_anio_primero.group(2).lower()
            if term in ("i", "1", "primavera", "spring", "p"):
                return (f"{anio}-01-01", f"{anio}-06-30")
            return (f"{anio}-07-01", f"{anio}-12-31")
        if m_term_primero:
            term, anio = m_term_primero.group(1).lower(), m_term_primero.group(2)
            if term in ("i", "1", "primavera", "spring", "p"):
                return (f"{anio}-01-01", f"{anio}-06-30")
            return (f"{anio}-07-01", f"{anio}-12-31")
        if re.fullmatch(r"\d{4}", texto):
            return (f"{texto}-01-01", f"{texto}-12-31")
        return None
    m_obj = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", fecha_objetivo.strip())
    if m_obj:
        anio, mes = m_obj.group(1), int(m_obj.group(2))
        return (f"{anio}-01-01", f"{anio}-06-30") if mes <= 6 else (
            f"{anio}-07-01",
            f"{anio}-12-31",
        )
    return None


def examen_en_semestre_actual(
    fecha_examen: str,
    *,
    semestre: str = "",
    inicio_semestre: str = "",
    fecha_objetivo: str = "",
) -> bool:
    """Indica si `fecha_examen` corresponde al semestre en curso según `materia.toml`.

    Regla (tarea 2.6 de `docs/ROADMAP.md`): si `inicio_semestre` (`AAAA-MM-DD`) está
    definido, exige `fecha_examen >= inicio_semestre`; si no, usa el intervalo calendario
    de `semestre` (`AAAA-I`: ene-jun, `AAAA-II`: jul-dic) o deduce el ciclo de
    `fecha_objetivo`. Exámenes sin fecha real o de semestres previos devuelven `False`.
    """
    limpia = fecha_examen.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", limpia) or limpia in ("0000-00-00", "9999-99-99"):
        return False
    ini_manual = inicio_semestre.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", ini_manual):
        return limpia >= ini_manual
    rango = _rango_semestre(semestre, fecha_objetivo)
    if rango is not None:
        return rango[0] <= limpia <= rango[1]
    return False


def construir_cfg_desde_etiquetas(
    config: Mapping,
    etiquetas: Sequence[Etiqueta],
    *,
    items: Sequence[Item] | None = None,
    similitud: Mapping | None = None,
) -> tuple[dict, dict]:
    """Deriva `CFG` (`material`, `molde`, `rotacion`, `pi_molde`, `demostracion`) y niveles.

    Regla para `material`: 2 puntos por ejercicio de tarea del alcance repartidos entre sus
    incisos, +1 si el ejercicio se repite en una tarea posterior (detectado vía
    `04_similitud.json` o `fuente`), 1 por lámina/clase del alcance y 0.5 si `examinable=False`.

    Diferencia conocida frente a `legacy/.../sistemas_dinamicos_ii/src/config_parcial3.py`:
    `05_etiquetas.csv` no incluye columna `seccion` ni descuentos manuales por antigüedad a la
    Tarea 3, por lo que `material` automático asigna 2 a cada ejercicio examinable de T3
    (máxima diferencia en `p_base` de SD-II: ≤ 0.08, con pico en J ≈ +0.063 y F ≈ -0.062).
    """
    arquetipos_cfg = config.get("arquetipos", {})
    k_set = set(arquetipos_cfg)
    items_por_id = {it.id: it for it in (items or ())}

    primera_pasada: list[tuple[Etiqueta, str, str, str, str]] = []
    vistos: set[str] = set()
    for et in etiquetas:
        if et.pasada != 1 or et.item_id in vistos:
            continue
        vistos.add(et.item_id)
        doc_id, tipo_doc, fecha, parcial = _clasificar_item(et, items_por_id)
        primera_pasada.append((et, doc_id, tipo_doc, fecha, parcial))

    # 1. Detectar ejercicios repetidos en tareas posteriores
    repetidos_tarea: set[str] = set()
    copias_etiquetadas: set[str] = set()
    if similitud:
        for _doc_t, entradas in (similitud.get("tareas_entre_si") or {}).items():
            for _tid, info in entradas.items():
                if info.get("clasificacion") == "casi copia" and info.get("mas_parecidos"):
                    fuente_t = str(info["mas_parecidos"][0][0])
                    repetidos_tarea.add(fuente_t)
                    repetidos_tarea.add(_base_ejercicio_tarea(fuente_t))

    conteo_incisos: Counter[str] = Counter()
    for et, _doc_id, tipo_doc, _fecha, _par in primera_pasada:
        if tipo_doc == "tarea":
            conteo_incisos[_base_ejercicio_tarea(et.item_id)] += 1
            if et.fuente and et.fuente.startswith("T") and et.nivel == "casi copia":
                repetidos_tarea.add(et.fuente)
                repetidos_tarea.add(_base_ejercicio_tarea(et.fuente))
                copias_etiquetadas.add(et.item_id)

    # 2. Calcular MATERIAL según la regla 2 / +1 / 1 / 0.5
    material: dict[str, float] = {k: 0.0 for k in arquetipos_cfg}
    for et, _doc_id, tipo_doc, _fecha, _par in primera_pasada:
        if et.arquetipo not in k_set:
            continue
        if tipo_doc == "tarea":
            if et.item_id in copias_etiquetadas:
                continue
            if not et.examinable:
                material[et.arquetipo] += 0.5
            else:
                base_ej = _base_ejercicio_tarea(et.item_id)
                n_inc = max(1, conteo_incisos[base_ej])
                peso = 3.0 if (et.item_id in repetidos_tarea or base_ej in repetidos_tarea) else 2.0
                material[et.arquetipo] += peso / n_inc
        elif tipo_doc in ("clase", "notas"):
            material[et.arquetipo] += 1.0

    # 3. Exámenes: molde, rotación, pi_molde, demostración y niveles de reciclaje
    examenes_meta: dict[str, tuple[str, str]] = {}
    preguntas_examen: list[tuple[Etiqueta, str, str, str]] = []
    for et, doc_id, tipo_doc, fecha, parcial in primera_pasada:
        if tipo_doc != "examen":
            continue
        examenes_meta.setdefault(doc_id, (fecha or "9999-99-99", parcial))
        preguntas_examen.append((et, doc_id, fecha or "9999-99-99", parcial))

    objetivo = config.get("objetivo", {})
    molde_cfg = [m for m in objetivo.get("molde", []) if m]
    if molde_cfg:
        molde_docs = set(molde_cfg)
    else:
        parcial_obj = str(objetivo.get("parcial", "")).upper()
        molde_docs = {
            doc_id
            for doc_id, (_f, par) in examenes_meta.items()
            if not parcial_obj or par.upper() == parcial_obj
        }

    molde: Counter[str] = Counter()
    ya_visto = objetivo.get("ya_examinado_este_semestre", [])
    rotacion_set: set[str] = {k for k in ya_visto if k in k_set}
    semestre_cfg = str(config.get("semestre", ""))
    inicio_sem_cfg = str(objetivo.get("inicio_semestre", ""))
    fecha_obj_cfg = str(objetivo.get("fecha", ""))
    avisos_rotacion: list[str] = []
    if (
        semestre_cfg.strip()
        and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", inicio_sem_cfg.strip())
        and _rango_semestre(semestre_cfg) is None
    ):
        avisos_rotacion.append(
            f"semestre no reconocido ({semestre_cfg!r}): no se derivó rotación automática por fecha"
        )
    docs_rotados: set[str] = set()
    for et, doc_id, fecha, _parcial in preguntas_examen:
        if et.arquetipo not in k_set:
            continue
        if doc_id in molde_docs:
            molde[et.arquetipo] += 1
        elif examen_en_semestre_actual(
            fecha,
            semestre=semestre_cfg,
            inicio_semestre=inicio_sem_cfg,
            fecha_objetivo=fecha_obj_cfg,
        ):
            rotacion_set.add(et.arquetipo)
            docs_rotados.add(doc_id)

    # pi_molde: preguntas cuyo examen tenía al menos un examen previo del mismo parcial
    previos_por_doc: dict[str, bool] = {}
    orden_ex = sorted(examenes_meta, key=lambda d: (examenes_meta[d][0], d))
    vistos_por_parcial: dict[str, int] = Counter()
    for doc_id in orden_ex:
        _, par = examenes_meta[doc_id]
        par_norm = par.upper()
        previos_por_doc[doc_id] = vistos_por_parcial[par_norm] > 0
        vistos_por_parcial[par_norm] += 1

    ids_examen = {et.item_id for et, _d, _f, _p in preguntas_examen}
    rec_ex = 0
    rec_total = 0
    for et, doc_id, _fecha, _parcial in preguntas_examen:
        if not previos_por_doc.get(doc_id, False):
            continue
        rec_total += 1
        if et.fuente in ids_examen or ":Q" in et.fuente:
            rec_ex += 1
    pi_molde = (float(1 + rec_ex), float(1 + rec_total - rec_ex)) if rec_total > 0 else (1.0, 1.0)

    # Arquetipos de demostración: mayoría de sus ítems etiquetados tienen demostracion >= 2
    dem_totales: Counter[str] = Counter()
    dem_altos: Counter[str] = Counter()
    for et, _doc_id, _tipo, _f, _par in primera_pasada:
        if et.arquetipo not in k_set or "demostracion" not in et.rasgos:
            continue
        dem_totales[et.arquetipo] += 1
        if et.rasgos["demostracion"] >= 2:
            dem_altos[et.arquetipo] += 1
    dem_arqs = sorted(
        k for k in k_set if dem_totales[k] > 0 and dem_altos[k] / dem_totales[k] > 0.5
    )

    dem_a = 0.0
    dem_b = 0.0
    for doc_id in orden_ex:
        peso_ex = 1.0 if doc_id in molde_docs else 0.5
        tiene_dem_ex = any(
            et.arquetipo in dem_arqs
            for et, d, _f, _p in preguntas_examen
            if d == doc_id
        )
        if tiene_dem_ex:
            dem_a += peso_ex
        else:
            dem_b += peso_ex
    beta_dem = (1.0 + dem_a, 1.0 + dem_b) if orden_ex else (1.0, 1.0)

    # Distribución Laplace de niveles de reciclaje sobre exámenes del alcance (o todos si no hay)
    alcance_qs = [et for et, _d, _f, _p in preguntas_examen if et.arquetipo in k_set]
    fuente_niv = alcance_qs or [et for et, _d, _f, _p in preguntas_examen]
    conteo_niv = Counter(
        "adaptación" if et.nivel == "adaptacion" else et.nivel
        for et in fuente_niv
        if et.nivel
    )
    den_niv = len(_NIVELES_POR_DEFECTO) + sum(conteo_niv[nv] for nv in _NIVELES_POR_DEFECTO)
    niveles_probs = {nv: (1 + conteo_niv[nv]) / den_niv for nv in _NIVELES_POR_DEFECTO}

    formato = config.get("formato", {})
    preg_cfg = formato.get("preguntas") or {"4": 1.0}
    n_dist = {int(k): float(v) for k, v in preg_cfg.items()}

    minutos_por_doc: dict[str, float] = {}
    for et, doc_id, _fecha, _parcial in preguntas_examen:
        if doc_id not in molde_docs:
            continue
        if et.minutos is not None and et.minutos > 0:
            min_q = float(et.minutos)
        elif et.arquetipo in arquetipos_cfg:
            min_q = float(arquetipos_cfg[et.arquetipo][1])
        else:
            min_q = 0.0
        minutos_por_doc[doc_id] = minutos_por_doc.get(doc_id, 0.0) + min_q
    minutos_molde = {
        d: round(minutos_por_doc[d], 2) for d in sorted(minutos_por_doc) if minutos_por_doc[d] > 0
    }

    mins = formato.get("minutos") or []
    if mins:
        ventana = (float(mins[0]), float(mins[-1]))
        ventana_origen = "explicita"
    elif minutos_molde:
        vals_m = list(minutos_molde.values())
        ventana = (round(0.8 * min(vals_m), 2), round(1.15 * max(vals_m), 2))
        ventana_origen = "molde"
    else:
        ventana = (75.0, 100.0)
        ventana_origen = "defecto"
    modelo_cfg = config.get("modelo", {})

    cfg_salida = {
        "arquetipos": {k: (arquetipos_cfg[k][0], arquetipos_cfg[k][1]) for k in arquetipos_cfg},
        "material": {k: round(material[k], 4) for k in arquetipos_cfg if material[k] > 0},
        "molde": {k: molde[k] for k in arquetipos_cfg if molde[k] > 0},
        "pi_molde": pi_molde,
        "rotacion": sorted(rotacion_set),
        "rho": float(modelo_cfg.get("rho", 0.6)),
        "demostracion": {"arquetipos": dem_arqs, "beta": beta_dem},
        "N": n_dist,
        "ventana": ventana,
        "beta": float(modelo_cfg.get("beta", 6.0)),
        "suavizado": float(modelo_cfg.get("suavizado", 0.3)),
    }
    resumen_derivacion = {
        "n_examenes_molde": len(molde_docs),
        "examenes_molde": sorted(molde_docs),
        "minutos_molde": minutos_molde,
        "ventana": [ventana[0], ventana[1]],
        "ventana_origen": ventana_origen,
        "examenes_rotacion": sorted(docs_rotados),
        "avisos_rotacion": avisos_rotacion,
        "n_examenes_vistos": len(orden_ex),
        "n_tareas_repetidas": len(repetidos_tarea),
        "material": cfg_salida["material"],
        "molde": cfg_salida["molde"],
        "rotacion": cfg_salida["rotacion"],
        "pi_molde": list(pi_molde),
        "demostracion": {"arquetipos": dem_arqs, "beta": list(beta_dem)},
        "niveles": {k: round(v, 4) for k, v in niveles_probs.items()},
    }
    return cfg_salida, resumen_derivacion


def calcular_modelo(
    materia: str,
    raiz_trabajo: Path | None = None,
    *,
    semilla: int | None = None,
    semilla_sorteo: int | None = None,
    n_simulaciones: int = 20_000,
    n_rejilla: int = 3_000,
    n_sorteos: int = 5,
    usar_numpy: bool | None = None,
) -> dict:
    """Calcula `07_modelo.json` en `trabajo/<materia>/` desde `05_etiquetas.csv` y `materia.toml`.

    Fuente: `legacy/estudio_parciales/nucleo/modelo.py` + `04_modelo_parcial3.py` y
    `docs/METODOLOGIA_ESTADISTICA.md` §5, §7 y §8.
    """
    base = (raiz_trabajo or Path("trabajo")) / materia
    cfg_materia = leer_config_materia(base)
    etiquetas = leer_etiquetas(base / "05_etiquetas.csv", rasgos=cfg_materia["rasgos"])

    ruta_items = base / "03_items.jsonl"
    items = list(leer_jsonl(ruta_items, Item)) if ruta_items.is_file() else None
    ruta_sim = base / "04_similitud.json"
    similitud = json.loads(ruta_sim.read_text(encoding="utf-8")) if ruta_sim.is_file() else None

    cfg_modelo, derivacion = construir_cfg_desde_etiquetas(
        cfg_materia, etiquetas, items=items, similitud=similitud
    )

    sem = int(cfg_materia["modelo"]["semilla"] if semilla is None else semilla)
    sem_s = sem if semilla_sorteo is None else int(semilla_sorteo)
    malla = dict(_MALLA_POR_DEFECTO)

    res = corre(
        cfg_modelo,
        R=n_simulaciones,
        R_rejilla=n_rejilla,
        semilla=sem,
        malla=malla,
        usar_numpy=usar_numpy,
        incluir_intervalos=True,
    )

    niveles_prob = derivacion["niveles"]
    niv_keys = list(niveles_prob)
    niv_raw = list(niveles_prob.values())
    s_niv = sum(niv_raw)
    niv_vals = [v / s_niv for v in niv_raw] if s_niv > 0 else niv_raw

    def _decorar(_k: str, rng) -> dict:
        return {"nivel": str(rng.choice(niv_keys, p=niv_vals))}

    sorteos_indep = sortea(
        cfg_modelo, n_sorteos, sem_s, decora=_decorar, usar_numpy=usar_numpy
    )
    sorteos_bal = sortea(
        cfg_modelo,
        n_sorteos,
        sem_s,
        decora=_decorar,
        balancear=res["p_base"],
        usar_numpy=usar_numpy,
    )

    predicciones = [
        asdict(
            Prediccion(
                arquetipo=k,
                p_media=res["p_base"][k],
                p_q05=res["p_q05"][k],
                p_q95=res["p_q95"][k],
                p_min_sensibilidad=res["p_min"][k],
                p_max_sensibilidad=res["p_max"][k],
            )
        )
        for k in res["K"]
    ]

    n_molde = int(derivacion["n_examenes_molde"])
    res["demostracion_inferencia"] = {
        **res["demostracion_inferencia"],
        "n_examenes_molde": n_molde,
        "exploratorio": n_molde < 10,
    }
    salida = {
        "semilla": sem,
        "semilla_sorteo": sem_s,
        "n_simulaciones": n_simulaciones,
        "n_rejilla": n_rejilla,
        "n_examenes_molde": n_molde,
        "exploratorio": n_molde < 10,
        **res,
        "predicciones": predicciones,
        "parametros_derivados": derivacion,
        "sorteos_independientes": sorteos_indep,
        "sorteos": sorteos_bal,
    }
    (base / "07_modelo.json").write_text(
        json.dumps(salida, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return salida
