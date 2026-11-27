"""Funciones estadísticas para muestras pequeñas, con respaldo en Python puro."""
from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Sequence
from statistics import NormalDist

try:
    import numpy as np
except ImportError:  # pragma: no cover - entorno sin numpy
    np = None  # type: ignore[assignment]


def _hay_numpy(usar_numpy: bool | None) -> bool:
    if usar_numpy is False:
        return False
    return np is not None


def _importar_scipy_stats(usar_scipy: bool | None):
    if usar_scipy is False:
        return None
    try:
        from scipy import stats

        return stats
    except ImportError:  # pragma: no cover - entorno sin scipy
        return None


def _cuantil_lineal(ordenados: Sequence[float], q: float) -> float:
    if not ordenados:
        return 0.0
    if q <= 0.0:
        return float(ordenados[0])
    if q >= 1.0:
        return float(ordenados[-1])
    pos = q * (len(ordenados) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    return float(ordenados[lo] + (pos - lo) * (ordenados[hi] - ordenados[lo]))


def _mediana_lista(ordenados: Sequence[float]) -> float:
    n = len(ordenados)
    mitad = n // 2
    if n % 2 == 1:
        return float(ordenados[mitad])
    return 0.5 * float(ordenados[mitad - 1] + ordenados[mitad])


def _evaluar_estadistico(valores: Sequence[float], estadistico: str) -> float:
    if estadistico == "media":
        return float(sum(valores) / len(valores))
    if estadistico == "mediana":
        return _mediana_lista(sorted(valores))
    raise ValueError(f"Estadístico no soportado: {estadistico!r}")


def _rangos_promedio(valores: Sequence[float]) -> list[float]:
    n = len(valores)
    orden = sorted(range(n), key=lambda i: valores[i])
    rangos = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and valores[orden[j + 1]] == valores[orden[i]]:
            j += 1
        rango_medio = 0.5 * (i + j) + 1.0
        for k in range(i, j + 1):
            rangos[orden[k]] = rango_medio
        i = j + 1
    return rangos


def _pearson(a: Sequence[float], b: Sequence[float]) -> float:
    n = len(a)
    ma = sum(a) / n
    mb = sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b, strict=True))
    da = sum((x - ma) ** 2 for x in a)
    db = sum((y - mb) ** 2 for y in b)
    den = math.sqrt(da * db)
    if den <= 0.0:
        return 0.0
    return max(-1.0, min(1.0, num / den))


def _betacf_puro(a: float, b: float, x: float) -> float:
    """Fracción continua de Lentz modificada para la beta incompleta (Numerical Recipes §6.4)."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, 250):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        c = 1.0 + aa / c
        d = 1e-30 if abs(d) < 1e-30 else d
        c = 1e-30 if abs(c) < 1e-30 else c
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        c = 1.0 + aa / c
        d = 1e-30 if abs(d) < 1e-30 else d
        c = 1e-30 if abs(c) < 1e-30 else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return h


def _betainc_puro(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf_puro(a, b, x) / a
    return 1.0 - bt * _betacf_puro(b, a, 1.0 - x) / b


def _beta_ppf_puro(q: float, a: float, b: float) -> float:
    if q <= 0.0:
        return 0.0
    if q >= 1.0:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        if _betainc_puro(a, b, mid) < q:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _aceleracion_desde_influencias(influencias: Sequence[float]) -> float:
    """Coeficiente de aceleración BCa a partir de influencias empíricas `U_i`."""
    den = 6.0 * (sum(u * u for u in influencias) ** 1.5)
    return sum(u**3 for u in influencias) / den if den > 0.0 else 0.0


def _cuantiles_bca_desde_aceleracion(
    estimador: float,
    boot_orden: Sequence[float],
    a_hat: float,
    nivel: float,
) -> tuple[float, float]:
    n_rem = len(boot_orden)
    c_lt = sum(1 for v in boot_orden if v < estimador)
    c_le = sum(1 for v in boot_orden if v <= estimador)
    pct = (c_lt + c_le) / (2.0 * n_rem)
    eps = 1.0 / (2.0 * n_rem)
    pct = max(eps, min(1.0 - eps, pct))

    nd = NormalDist()
    z0 = nd.inv_cdf(pct)
    z_a = nd.inv_cdf((1.0 - nivel) / 2.0)

    cuantiles: list[float] = []
    for z, defecto in ((z_a, 0.0), (-z_a, 1.0)):
        num = z0 + z
        den_q = 1.0 - a_hat * num
        q = defecto if den_q <= 0.0 else nd.cdf(z0 + num / den_q)
        cuantiles.append(max(0.0, min(1.0, q)))
    return cuantiles[0], cuantiles[1]


def _limites_cuantiles_bca(
    n: int,
    estimador: float,
    boot_orden: Sequence[float],
    jk_valores: Sequence[float],
    nivel: float,
) -> tuple[float, float]:
    jk_bar = sum(jk_valores) / n
    a_hat = _aceleracion_desde_influencias([jk_bar - v for v in jk_valores])
    return _cuantiles_bca_desde_aceleracion(estimador, boot_orden, a_hat, nivel)


def _bca_desde_remuestras_puro(
    datos: Sequence[float],
    estimador: float,
    remuestras: Sequence[Sequence[float]],
    estadistico: str,
    nivel: float,
) -> tuple[float, float]:
    n = len(datos)
    boot_orden = sorted(_evaluar_estadistico(muestra, estadistico) for muestra in remuestras)
    if estadistico == "media":
        suma = sum(datos)
        jk = [(suma - datos[i]) / (n - 1) for i in range(n)]
    else:
        jk = [_mediana_lista(sorted(list(datos[:i]) + list(datos[i + 1 :]))) for i in range(n)]
    q_lo, q_hi = _limites_cuantiles_bca(n, estimador, boot_orden, jk, nivel)
    return _cuantil_lineal(boot_orden, q_lo), _cuantil_lineal(boot_orden, q_hi)


def bootstrap_bca(
    valores: Sequence[float],
    *,
    estadistico: str = "media",
    nivel: float = 0.95,
    n_remuestras: int = 10_000,
    semilla: int = 2026,
    usar_numpy: bool | None = None,
) -> dict:
    """Intervalo de confianza bootstrap BCa (Bias-Corrected and Accelerated).

    Fuente de la fórmula: Efron (1987); Efron y Tibshirani (1993, cap. 14.3, ec. 14.15);
    `docs/METODOLOGIA_ESTADISTICA.md` §2; `docs/INVESTIGACION.md` (`arXiv:2511.19794`).
    Contrastable directamente con `scipy.stats.bootstrap(..., method="BCa")`.
    """
    datos = [float(x) for x in valores]
    n = len(datos)
    if n == 0:
        return {
            "n": 0,
            "estadistico": estadistico,
            "estimador": 0.0,
            "ic": [0.0, 0.0],
            "nivel": nivel,
            "n_remuestras": n_remuestras,
            "metodo": "BCa",
            "exploratorio": True,
        }
    estimador = _evaluar_estadistico(datos, estadistico)
    if n < 2 or max(datos) == min(datos):
        return {
            "n": n,
            "estadistico": estadistico,
            "estimador": float(estimador),
            "ic": [float(estimador), float(estimador)],
            "nivel": nivel,
            "n_remuestras": n_remuestras,
            "metodo": "BCa",
            "exploratorio": n < 10,
        }

    if _hay_numpy(usar_numpy):
        arr = np.asarray(datos, dtype=float)
        if estadistico == "media":
            estimador = float(arr.mean())
        elif estadistico == "mediana":
            estimador = float(np.median(arr))
        else:
            raise ValueError(f"Estadístico no soportado: {estadistico!r}")
        rng = np.random.default_rng(semilla)
        idx = rng.integers(0, n, size=(n_remuestras, n))
        muestras = arr[idx]
        boot_arr = muestras.mean(axis=1) if estadistico == "media" else np.median(muestras, axis=1)
        boot_orden = np.sort(boot_arr)
        pct = float(
            (np.count_nonzero(boot_arr < estimador) + np.count_nonzero(boot_arr <= estimador))
            / (2.0 * n_remuestras)
        )
        eps = 1.0 / (2.0 * n_remuestras)
        pct = max(eps, min(1.0 - eps, pct))
        if estadistico == "media":
            suma = float(arr.sum())
            jk_arr = (suma - arr) / (n - 1)
        else:
            jk_arr = np.array([np.median(np.delete(arr, i)) for i in range(n)], dtype=float)
        dif_jk = jk_arr.mean() - jk_arr
        den = 6.0 * float(np.sum(dif_jk**2) ** 1.5)
        a_hat = float(np.sum(dif_jk**3) / den) if den > 0.0 else 0.0
        nd = NormalDist()
        z0 = nd.inv_cdf(pct)
        z_a = nd.inv_cdf((1.0 - nivel) / 2.0)
        cuantiles: list[float] = []
        for z, defecto in ((z_a, 0.0), (-z_a, 1.0)):
            num = z0 + z
            den_q = 1.0 - a_hat * num
            q = defecto if den_q <= 0.0 else nd.cdf(z0 + num / den_q)
            cuantiles.append(max(0.0, min(1.0, q)))
        lo, hi = np.quantile(boot_orden, cuantiles)
    else:
        rng_py = random.Random(semilla)
        remuestras = [[datos[rng_py.randrange(n)] for _ in range(n)] for _ in range(n_remuestras)]
        lo, hi = _bca_desde_remuestras_puro(datos, estimador, remuestras, estadistico, nivel)

    return {
        "n": n,
        "estadistico": estadistico,
        "estimador": float(estimador),
        "ic": [float(lo), float(hi)],
        "nivel": nivel,
        "n_remuestras": n_remuestras,
        "metodo": "BCa",
        "exploratorio": n < 10,
    }


def bootstrap_diferencia_medias(
    grupo_a: Sequence[float],
    grupo_b: Sequence[float],
    *,
    nivel: float = 0.95,
    n_remuestras: int = 5000,
    n_permutaciones: int = 5000,
    semilla: int = 2026,
    usar_numpy: bool | None = None,
) -> dict:
    """Intervalos bootstrap (percentil y BCa) y $p$ de permutación para `media(A) - media(B)`.

    Fuente de la fórmula BCa de dos muestras: Efron y Tibshirani (1993, cap. 15, ec. 15.36);
    contrastable contra `scipy.stats.bootstrap((a, b), ..., method="BCa")`. Prueba de
    permutación bilateral de dos muestras (Good, 2005); `docs/METODOLOGIA_ESTADISTICA.md` §2.
    """
    a = [float(x) for x in grupo_a]
    b = [float(x) for x in grupo_b]
    na, nb = len(a), len(b)
    if na == 0 or nb == 0:
        return {
            "n_a": na,
            "n_b": nb,
            "diferencia": 0.0,
            "ic_bootstrap": [0.0, 0.0],
            "ic_bca": [0.0, 0.0],
            "p_permutacion": 1.0,
            "nivel": nivel,
            "n_remuestras": n_remuestras,
            "n_permutaciones": n_permutaciones,
            "exploratorio": True,
        }
    ma_obs = sum(a) / na
    mb_obs = sum(b) / nb
    dif_obs = ma_obs - mb_obs
    alpha = (1.0 - nivel) / 2.0

    # Aceleración jackknife de dos muestras (Efron & Tibshirani, ec. 15.36)
    influencias = [(x - ma_obs) / na for x in a] + [(mb_obs - y) / nb for y in b]
    a_hat = _aceleracion_desde_influencias(influencias)

    if _hay_numpy(usar_numpy):
        arr_a = np.asarray(a, dtype=float)
        arr_b = np.asarray(b, dtype=float)
        rng = np.random.default_rng(semilla)
        ma = arr_a[rng.integers(0, na, size=(n_remuestras, na))].mean(axis=1)
        mb = arr_b[rng.integers(0, nb, size=(n_remuestras, nb))].mean(axis=1)
        difs_arr = ma - mb
        lo, hi = np.quantile(difs_arr, [alpha, 1.0 - alpha])
        boot_orden = np.sort(difs_arr).tolist()
        q_lo, q_hi = _cuantiles_bca_desde_aceleracion(dif_obs, boot_orden, a_hat, nivel)
        bca_lo, bca_hi = np.quantile(difs_arr, [q_lo, q_hi])

        # Permutación bilateral de dos muestras (equivalente en dos muestras a permutar A/B)
        combinado = np.concatenate([arr_a, arr_b])
        conteo_perm = 0
        for _ in range(n_permutaciones):
            perm = rng.permutation(combinado)
            dif_p = abs(float(perm[:na].mean() - perm[na:].mean()))
            if dif_p >= abs(dif_obs) - 1e-12:
                conteo_perm += 1
    else:
        rng_py = random.Random(semilla)
        boot_orden = sorted(
            (sum(a[rng_py.randrange(na)] for _ in range(na)) / na)
            - (sum(b[rng_py.randrange(nb)] for _ in range(nb)) / nb)
            for _ in range(n_remuestras)
        )
        lo = _cuantil_lineal(boot_orden, alpha)
        hi = _cuantil_lineal(boot_orden, 1.0 - alpha)
        q_lo, q_hi = _cuantiles_bca_desde_aceleracion(dif_obs, boot_orden, a_hat, nivel)
        bca_lo = _cuantil_lineal(boot_orden, q_lo)
        bca_hi = _cuantil_lineal(boot_orden, q_hi)

        combinado_l = a + b
        conteo_perm = 0
        for _ in range(n_permutaciones):
            rng_py.shuffle(combinado_l)
            dif_p = abs((sum(combinado_l[:na]) / na) - (sum(combinado_l[na:]) / nb))
            if dif_p >= abs(dif_obs) - 1e-12:
                conteo_perm += 1

    if len(set(a)) <= 1 and len(set(b)) <= 1:
        bca_lo = bca_hi = dif_obs
    p_perm = float((conteo_perm + 1) / (n_permutaciones + 1))

    return {
        "n_a": na,
        "n_b": nb,
        "diferencia": round(float(dif_obs), 4),
        "ic_bootstrap": [round(float(lo), 4), round(float(hi), 4)],
        "ic_bca": [round(float(bca_lo), 4), round(float(bca_hi), 4)],
        "p_permutacion": round(p_perm, 4),
        "nivel": nivel,
        "n_remuestras": n_remuestras,
        "n_permutaciones": n_permutaciones,
        "exploratorio": na < 10 or nb < 10,
    }


def permutacion_cambio_signo(
    diferencias: Sequence[float],
    *,
    alternativa: str = "bilateral",
    n_remuestras: int = 10_000,
    semilla: int = 2026,
    usar_numpy: bool | None = None,
) -> dict:
    """Prueba de permutación por cambio de signo para diferencias pareadas.

    Enumera exactamente las $2^n$ configuraciones si $n \\le 20$ y usa Monte Carlo con semilla
    si $n > 20$. Fuente: Fisher (1935); `docs/METODOLOGIA_ESTADISTICA.md` §2; `docs/ROADMAP.md`;
    `docs/INVESTIGACION.md` (`arXiv:2511.19794`, `arXiv:2609.35815`).
    """
    datos = [float(x) for x in diferencias]
    n = len(datos)
    if n == 0:
        return {
            "n": 0,
            "media_observada": 0.0,
            "mediana_observada": 0.0,
            "p_valor": 1.0,
            "p_minimo_alcanzable": 1.0,
            "metodo": "exacta",
            "n_configuraciones": 0,
            "exploratorio": True,
        }
    if alternativa not in ("bilateral", "mayor", "menor"):
        raise ValueError(f"Alternativa inválida: {alternativa!r}")

    obs_sum = sum(datos)
    media_obs = obs_sum / n
    mediana_obs = _mediana_lista(sorted(datos))
    tol = 1e-12

    if n <= 20:
        n_conf = 1 << n
        if _hay_numpy(usar_numpy):
            sumas = np.array([0.0], dtype=float)
            for v in datos:
                sumas = np.concatenate((sumas - v, sumas + v))
            if alternativa == "bilateral":
                extremos = int(np.count_nonzero(np.abs(sumas) >= abs(obs_sum) - tol))
                p_min = 2.0 / n_conf
            elif alternativa == "mayor":
                extremos = int(np.count_nonzero(sumas >= obs_sum - tol))
                p_min = 1.0 / n_conf
            else:
                extremos = int(np.count_nonzero(sumas <= obs_sum + tol))
                p_min = 1.0 / n_conf
        else:
            sumas_py = [0.0]
            for v in datos:
                sumas_py = [s - v for s in sumas_py] + [s + v for s in sumas_py]
            if alternativa == "bilateral":
                umbral = abs(obs_sum) - tol
                extremos = sum(1 for s in sumas_py if abs(s) >= umbral)
                p_min = 2.0 / n_conf
            elif alternativa == "mayor":
                umbral = obs_sum - tol
                extremos = sum(1 for s in sumas_py if s >= umbral)
                p_min = 1.0 / n_conf
            else:
                umbral = obs_sum + tol
                extremos = sum(1 for s in sumas_py if s <= umbral)
                p_min = 1.0 / n_conf
        return {
            "n": n,
            "media_observada": round(float(media_obs), 4),
            "mediana_observada": round(float(mediana_obs), 4),
            "p_valor": float(extremos / n_conf),
            "p_minimo_alcanzable": float(min(1.0, p_min)),
            "metodo": "exacta",
            "n_configuraciones": n_conf,
            "exploratorio": n < 10,
        }

    # Monte Carlo con semilla fija para n > 20 (Phipson & Smyth 2010: (k + 1) / (R + 1))
    if _hay_numpy(usar_numpy):
        arr = np.asarray(datos, dtype=float)
        rng = np.random.default_rng(semilla)
        signos = rng.choice((-1.0, 1.0), size=(n_remuestras, n))
        sumas_mc = signos @ arr
        if alternativa == "bilateral":
            conteo = int(np.count_nonzero(np.abs(sumas_mc) >= abs(obs_sum) - tol))
        elif alternativa == "mayor":
            conteo = int(np.count_nonzero(sumas_mc >= obs_sum - tol))
        else:
            conteo = int(np.count_nonzero(sumas_mc <= obs_sum + tol))
    else:
        rng_py = random.Random(semilla)
        conteo = 0
        for _ in range(n_remuestras):
            s = sum(v if rng_py.random() >= 0.5 else -v for v in datos)
            if alternativa == "bilateral":
                ok = abs(s) >= abs(obs_sum) - tol
            elif alternativa == "mayor":
                ok = s >= obs_sum - tol
            else:
                ok = s <= obs_sum + tol
            if ok:
                conteo += 1
    p_val = float((conteo + 1) / (n_remuestras + 1))
    return {
        "n": n,
        "media_observada": round(float(media_obs), 4),
        "mediana_observada": round(float(mediana_obs), 4),
        "p_valor": p_val,
        "p_minimo_alcanzable": float(1.0 / (n_remuestras + 1)),
        "metodo": "monte_carlo",
        "n_configuraciones": n_remuestras,
        "exploratorio": n < 10,
    }


def wilcoxon_pareado(
    diferencias: Sequence[float], *, usar_scipy: bool | None = None
) -> dict:
    """Prueba de rangos con signo de Wilcoxon para muestras pareadas.

    Fuente: Wilcoxon (1945); `scipy.stats.wilcoxon(zero_method="wilcox")`;
    `docs/METODOLOGIA_ESTADISTICA.md` §2; `docs/INVESTIGACION.md` (`arXiv:2609.35815`).
    """
    datos = [float(x) for x in diferencias]
    n = len(datos)
    nz = [x for x in datos if x != 0.0]
    m = len(nz)
    if m == 0:
        return {
            "n": n,
            "n_no_ceros": 0,
            "estadistico": 0.0,
            "p_valor": 1.0,
            "exploratorio": n < 10,
        }

    stats = _importar_scipy_stats(usar_scipy)
    if stats is not None:
        res = stats.wilcoxon(datos)
        return {
            "n": n,
            "n_no_ceros": m,
            "estadistico": float(res.statistic),
            "p_valor": float(res.pvalue),
            "exploratorio": n < 10,
        }

    abs_nz = [abs(x) for x in nz]
    rangos = _rangos_promedio(abs_nz)
    total_r = sum(rangos)
    w_pos = sum(r for x, r in zip(nz, rangos, strict=True) if x > 0.0)
    stat = min(w_pos, total_r - w_pos)
    cuentas = Counter(abs_nz)
    hay_empates = any(t > 1 for t in cuentas.values())
    hay_ceros = m < n

    if (not hay_empates and not hay_ceros and m <= 20) or (n <= 13 and m <= 20):
        sumas = [0.0]
        for r in rangos:
            sumas = sumas + [s + r for s in sumas]
        extremos = sum(1 for s in sumas if min(s, total_r - s) <= stat + 1e-12)
        p_val = extremos / len(sumas)
    else:
        empates = sum(t * t * t - t for t in cuentas.values())
        mu = m * (m + 1.0) / 4.0
        var = (m * (m + 1.0) * (2.0 * m + 1.0) - 0.5 * empates) / 24.0
        if var <= 0.0:
            p_val = 1.0
        else:
            z = abs(w_pos - mu) / math.sqrt(var)
            p_val = min(1.0, 2.0 * (1.0 - NormalDist().cdf(z)))

    return {
        "n": n,
        "n_no_ceros": m,
        "estadistico": float(stat),
        "p_valor": float(p_val),
        "exploratorio": n < 10,
    }


def correlacion_spearman(
    x: Sequence[float],
    y: Sequence[float],
    *,
    nivel: float = 0.95,
    n_remuestras: int = 2000,
    n_permutaciones: int = 2000,
    semilla: int = 2026,
    usar_numpy: bool | None = None,
    usar_scipy: bool | None = None,
) -> dict:
    """Correlación de Spearman con p-valor exacto t, IC bootstrap y p de permutación.

    Fuente: Spearman (1904); `scipy.stats.spearmanr`; `docs/METODOLOGIA_ESTADISTICA.md` §3
    (marca `"exploratorio": True` cuando $n < 10$).
    """
    vx = [float(a) for a in x]
    vy = [float(b) for b in y]
    if len(vx) != len(vy):
        raise ValueError("x e y deben tener la misma longitud")
    n = len(vx)
    if n < 3 or len(set(vx)) <= 1 or len(set(vy)) <= 1:
        return {
            "n": n,
            "spearman": 0.0,
            "p_valor": 1.0,
            "ic_bootstrap": [0.0, 0.0],
            "ic_bca": [0.0, 0.0],
            "nivel_ic": nivel,
            "p_permutacion": 1.0,
            "n_remuestras": 0,
            "exploratorio": n < 10,
        }

    def _rho_simple(ax: Sequence[float], ay: Sequence[float]) -> float:
        return _pearson(_rangos_promedio(ax), _rangos_promedio(ay))

    stats = _importar_scipy_stats(usar_scipy)
    if stats is not None:
        res_sp = stats.spearmanr(vx, vy)
        rho_obs = float(res_sp.statistic)
        p_val = float(res_sp.pvalue)
    else:
        rho_obs = _rho_simple(vx, vy)
        if abs(rho_obs) >= 1.0 - 1e-12:
            p_val = 0.0
        else:
            gl = n - 2
            t_val = rho_obs * math.sqrt(gl / (1.0 - rho_obs * rho_obs))
            p_val = _betainc_puro(gl / 2.0, 0.5, gl / (gl + t_val * t_val))

    if _hay_numpy(usar_numpy):
        ax = np.asarray(vx, dtype=float)
        ay = np.asarray(vy, dtype=float)
        rng = np.random.default_rng(semilla)
        rhos_boot: list[float] = []
        for _ in range(n_remuestras):
            idx = rng.integers(0, n, size=n)
            bx = ax[idx]
            by = ay[idx]
            if np.ptp(bx) == 0.0 or np.ptp(by) == 0.0:
                continue
            r = (
                float(stats.spearmanr(bx, by).statistic)
                if stats is not None
                else _rho_simple(bx.tolist(), by.tolist())
            )
            if not math.isnan(r):
                rhos_boot.append(r)

        conteo_perm = 0
        rx = np.asarray(_rangos_promedio(vx), dtype=float)
        rx_c = rx - rx.mean()
        ry = np.asarray(_rangos_promedio(vy), dtype=float)
        ry_c = ry - ry.mean()
        den_r = float(np.sqrt(np.sum(rx_c**2) * np.sum(ry_c**2)))
        for _ in range(n_permutaciones):
            perm_ry = rng.permutation(ry_c)
            rho_p = abs(float(np.dot(rx_c, perm_ry)) / den_r) if den_r > 0 else 0.0
            if rho_p >= abs(rho_obs) - 1e-12:
                conteo_perm += 1
    else:
        rng_py = random.Random(semilla)
        rhos_boot = []
        for _ in range(n_remuestras):
            indices = [rng_py.randrange(n) for _ in range(n)]
            bx = [vx[i] for i in indices]
            by = [vy[i] for i in indices]
            if len(set(bx)) <= 1 or len(set(by)) <= 1:
                continue
            rhos_boot.append(_rho_simple(bx, by))

        rx_l = _rangos_promedio(vx)
        ry_l = list(_rangos_promedio(vy))
        conteo_perm = 0
        for _ in range(n_permutaciones):
            rng_py.shuffle(ry_l)
            if abs(_pearson(rx_l, ry_l)) >= abs(rho_obs) - 1e-12:
                conteo_perm += 1

    if rhos_boot:
        rhos_orden = sorted(rhos_boot)
        alpha = (1.0 - nivel) / 2.0
        ic_bajo = _cuantil_lineal(rhos_orden, alpha)
        ic_alto = _cuantil_lineal(rhos_orden, 1.0 - alpha)
        if n >= 4:
            jk_rhos = [
                _rho_simple(vx[:i] + vx[i + 1 :], vy[:i] + vy[i + 1 :]) for i in range(n)
            ]
            q_lo, q_hi = _limites_cuantiles_bca(n, rho_obs, rhos_orden, jk_rhos, nivel)
            bca_bajo = _cuantil_lineal(rhos_orden, q_lo)
            bca_alto = _cuantil_lineal(rhos_orden, q_hi)
        else:
            bca_bajo, bca_alto = ic_bajo, ic_alto
    else:
        ic_bajo = ic_alto = bca_bajo = bca_alto = rho_obs

    p_perm = float((conteo_perm + 1) / (n_permutaciones + 1))
    return {
        "n": n,
        "spearman": float(rho_obs),
        "p_valor": float(p_val),
        "ic_bootstrap": [float(ic_bajo), float(ic_alto)],
        "ic_bca": [float(bca_bajo), float(bca_alto)],
        "nivel_ic": nivel,
        "p_permutacion": float(p_perm),
        "n_remuestras": len(rhos_boot),
        "exploratorio": n < 10,
    }


def intervalo_jeffreys(
    exitos: int,
    total: int,
    *,
    nivel: float = 0.95,
    usar_scipy: bool | None = None,
) -> dict:
    """Intervalo creíble binomial de Jeffreys con prior $\\text{Beta}(x + 1/2, n - x + 1/2)$.

    Fuente: Jeffreys (1946); Brown, Cai y DasGupta (2001); `docs/METODOLOGIA_ESTADISTICA.md` §1.
    Contrastable directamente con `scipy.stats.beta.ppf`.
    """
    if total <= 0:
        return {
            "exitos": int(exitos),
            "n": 0,
            "proporcion": 0.0,
            "ic": [0.0, 1.0],
            "nivel": nivel,
            "metodo": "jeffreys",
            "exploratorio": True,
        }
    if not (0 <= exitos <= total):
        raise ValueError(f"exitos={exitos} fuera de [0, {total}]")

    a = exitos + 0.5
    b = (total - exitos) + 0.5
    alpha = (1.0 - nivel) / 2.0
    stats = _importar_scipy_stats(usar_scipy)
    if stats is not None:
        lo, hi = stats.beta.ppf([alpha, 1.0 - alpha], a, b)
    else:
        lo = _beta_ppf_puro(alpha, a, b)
        hi = _beta_ppf_puro(1.0 - alpha, a, b)

    return {
        "exitos": int(exitos),
        "n": int(total),
        "proporcion": round(float(exitos / total), 4),
        "ic": [float(lo), float(hi)],
        "nivel": nivel,
        "metodo": "jeffreys",
        "exploratorio": total < 10,
    }


def _ordenar_categorias_krippendorff(
    valores: Sequence[object], orden_categorias: Sequence[object] | None
) -> list[object]:
    vistos: list[object] = []
    for v in valores:
        if v not in vistos:
            vistos.append(v)
    if orden_categorias is not None:
        base = [c for c in orden_categorias if c in vistos]
        extras = [c for c in vistos if c not in base]
        return base + sorted(extras, key=str)
    es_num = all(isinstance(v, int | float) and not isinstance(v, bool) for v in vistos)
    return sorted(vistos, key=float if es_num else str)


def _evaluar_alfa_desde_indices(
    unidades_idx: Sequence[tuple[int, ...]], k: int, metrica: str
) -> tuple[float, float, float, float, bool]:
    matriz_o = [[0.0] * k for _ in range(k)]
    pares_totales = 0
    pares_iguales = 0
    for unidad in unidades_idx:
        m = len(unidad)
        if m < 2:
            continue
        peso = 1.0 / (m - 1)
        pares_totales += m * (m - 1)
        for idx_a, ca in enumerate(unidad):
            for idx_b, cb in enumerate(unidad):
                if idx_a != idx_b:
                    matriz_o[ca][cb] += peso
                    if ca == cb:
                        pares_iguales += 1

    acuerdo_exacto = (pares_iguales / pares_totales) if pares_totales > 0 else 1.0
    nc = [sum(fila) for fila in matriz_o]
    n_total = sum(nc)
    if n_total <= 1.0 or sum(1 for c in nc if c > 0.0) <= 1:
        return 1.0, 0.0, 0.0, acuerdo_exacto, True

    acum = [0.0] * (k + 1)
    for idx in range(k):
        acum[idx + 1] = acum[idx] + nc[idx]

    d_obs_num = 0.0
    d_esp_num = 0.0
    for i in range(k):
        for j in range(k):
            if i == j:
                continue
            if metrica == "nominal":
                delta2 = 1.0
            elif metrica == "ordinal":
                lo_idx, hi_idx = (i, j) if i < j else (j, i)
                s_ij = (acum[hi_idx + 1] - acum[lo_idx]) - 0.5 * (nc[i] + nc[j])
                delta2 = s_ij * s_ij
            else:
                raise ValueError(f"Métrica no soportada en Krippendorff: {metrica!r}")
            d_obs_num += matriz_o[i][j] * delta2
            d_esp_num += nc[i] * nc[j] * delta2

    d_obs = d_obs_num / n_total
    d_esp = d_esp_num / (n_total * (n_total - 1.0))
    if d_esp <= 1e-15:
        return 1.0, 0.0, 0.0, acuerdo_exacto, True
    return 1.0 - (d_obs / d_esp), d_obs, d_esp, acuerdo_exacto, False


def alfa_krippendorff(
    unidades: Sequence[Sequence[object]],
    *,
    metrica: str = "ordinal",
    orden_categorias: Sequence[object] | None = None,
    nivel: float = 0.95,
    n_remuestras: int = 2000,
    semilla: int = 2026,
    usar_numpy: bool | None = None,
) -> dict:
    """Coeficiente $\\alpha$ de Krippendorff para fiabilidad entre codificadores/pasadas.

    Fuente: Krippendorff (2004; 2011, *Computing Krippendorff's Alpha-Reliability*);
    `docs/METODOLOGIA_ESTADISTICA.md` §4 (umbrales ≥ 0.80 confiable, 0.67-0.80 tentativo,
    < 0.67 inestable; `arXiv:2510.06658` en `docs/INVESTIGACION.md`). Soporta valores
    faltantes (`None`, `""`), métrica `"nominal"` y `"ordinal"`, e IC bootstrap sobre unidades.
    """
    unidades_limpias: list[list[object]] = []
    todos_vals: list[object] = []
    for unidad in unidades:
        limpia = [
            v
            for v in unidad
            if v is not None
            and v != ""
            and not (isinstance(v, float) and math.isnan(v))
        ]
        if len(limpia) >= 2:
            unidades_limpias.append(limpia)
            todos_vals.extend(limpia)

    n_u = len(unidades_limpias)
    if n_u == 0:
        return {
            "n_unidades": 0,
            "n_valores": 0,
            "alfa": 0.0,
            "acuerdo_exacto": 0.0,
            "ic_bootstrap": [0.0, 0.0],
            "nivel_ic": nivel,
            "n_remuestras": 0,
            "metrica": metrica,
            "clasificacion": "sin_datos",
            "varianza_nula": True,
            "exploratorio": True,
        }

    cats = _ordenar_categorias_krippendorff(todos_vals, orden_categorias)
    mapa = {c: idx for idx, c in enumerate(cats)}
    unidades_idx = [tuple(mapa[v] for v in u) for u in unidades_limpias]
    k = len(cats)

    alfa_obs, _do, _de, acuerdo_ex, var_nula = _evaluar_alfa_desde_indices(
        unidades_idx, k, metrica
    )

    alfas_boot: list[float] = []
    if not var_nula and n_remuestras > 0 and n_u >= 2:
        if _hay_numpy(usar_numpy):
            rng = np.random.default_rng(semilla)
            matriz_idx = rng.integers(0, n_u, size=(n_remuestras, n_u))
            for fila in matriz_idx:
                muestra = [unidades_idx[int(i)] for i in fila]
                a_b, _, _, _, vn_b = _evaluar_alfa_desde_indices(muestra, k, metrica)
                if not vn_b:
                    alfas_boot.append(a_b)
        else:
            rng_py = random.Random(semilla)
            for _ in range(n_remuestras):
                muestra = [unidades_idx[rng_py.randrange(n_u)] for _ in range(n_u)]
                a_b, _, _, _, vn_b = _evaluar_alfa_desde_indices(muestra, k, metrica)
                if not vn_b:
                    alfas_boot.append(a_b)

    if alfas_boot:
        orden_boot = sorted(alfas_boot)
        alpha = (1.0 - nivel) / 2.0
        ic_lo = _cuantil_lineal(orden_boot, alpha)
        ic_hi = _cuantil_lineal(orden_boot, 1.0 - alpha)
    else:
        ic_lo = ic_hi = alfa_obs

    if alfa_obs >= 0.80:
        clasif = "confiable"
    elif alfa_obs >= 0.67:
        clasif = "tentativo"
    else:
        clasif = "inestable"

    return {
        "n_unidades": n_u,
        "n_valores": len(todos_vals),
        "alfa": float(alfa_obs),
        "acuerdo_exacto": round(float(acuerdo_ex), 4),
        "ic_bootstrap": [round(float(ic_lo), 4), round(float(ic_hi), 4)],
        "nivel_ic": nivel,
        "n_remuestras": len(alfas_boot),
        "metrica": metrica,
        "clasificacion": clasif,
        "varianza_nula": var_nula,
        "exploratorio": n_u < 10,
    }
