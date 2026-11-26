import numpy as np
from scipy import stats


def test_bootstrap_bca_contra_scipy_y_respaldo():
    from analisis_profesor.estadistica import _bca_desde_remuestras_puro, bootstrap_bca

    muestras = [
        [-0.6135, 0.0, 2.454, 0.9816, 0.0, 0.3681, 0.0, 0.0],
        [
            -0.6135, 0.0, 2.454, 0.9816, 0.0, 0.3681, 0.0, 0.0,
            0.0, 0.0, -1.9632, -2.454, -1.5951, -0.7362, -0.5521,
        ],
        [0.4, 0.9, 1.8, 2.7, 4.1, 6.2, 9.5, 13.0],
    ]
    for datos in muestras:
        arr = np.asarray(datos, dtype=float)
        ref = stats.bootstrap(
            (arr,),
            np.mean,
            n_resamples=10_000,
            confidence_level=0.95,
            method="BCa",
            random_state=np.random.default_rng(2026),
        ).confidence_interval
        res_np = bootstrap_bca(datos, n_remuestras=10_000, semilla=2026, usar_numpy=True)
        res_py = bootstrap_bca(datos, n_remuestras=10_000, semilla=2026, usar_numpy=False)

        assert res_np["n"] == len(datos)
        assert res_np["metodo"] == "BCa"
        assert res_np["exploratorio"] is (len(datos) < 10)
        assert abs(res_np["ic"][0] - float(ref.low)) <= 0.02
        assert abs(res_np["ic"][1] - float(ref.high)) <= 0.02

        # Con las mismas remuestras, la fórmula BCa en Python puro coincide <= 1e-9 con scipy
        # cuando no hay discrepancia de redondeo en suma flotante, y <= 0.04 en decimales.
        rng_ref = np.random.default_rng(2026)
        idx = rng_ref.integers(0, len(datos), size=(10_000, len(datos)))
        remuestras_py = arr[idx].tolist()
        lo_puro, hi_puro = _bca_desde_remuestras_puro(
            datos, sum(datos) / len(datos), remuestras_py, "media", 0.95
        )
        amplitud = max(datos) - min(datos)
        assert abs(lo_puro - float(ref.low)) <= 0.01 * amplitud
        assert abs(hi_puro - float(ref.high)) <= 0.01 * amplitud

        # En ejecución independiente con random.Random, se mantiene dentro del rango Monte Carlo
        assert abs(res_py["ic"][0] - float(ref.low)) <= 0.015 * amplitud
        assert abs(res_py["ic"][1] - float(ref.high)) <= 0.015 * amplitud

    diadica = [1.0, 2.0, 4.0, 8.0, 16.0]
    arr_d = np.asarray(diadica, dtype=float)
    ref_d = stats.bootstrap(
        (arr_d,),
        np.mean,
        n_resamples=10_000,
        confidence_level=0.95,
        method="BCa",
        random_state=np.random.default_rng(2026),
    ).confidence_interval
    idx_d = np.random.default_rng(2026).integers(0, len(diadica), size=(10_000, len(diadica)))
    lo_d, hi_d = _bca_desde_remuestras_puro(
        diadica, sum(diadica) / len(diadica), arr_d[idx_d].tolist(), "media", 0.95
    )
    assert abs(lo_d - float(ref_d.low)) < 1e-12
    assert abs(hi_d - float(ref_d.high)) < 1e-12

    r1 = bootstrap_bca(muestras[0], semilla=123, usar_numpy=True)
    r2 = bootstrap_bca(muestras[0], semilla=123, usar_numpy=True)
    assert r1 == r2

    constante = bootstrap_bca([2.0, 2.0, 2.0, 2.0, 2.0], semilla=2026)
    assert constante["ic"] == [2.0, 2.0]


def test_permutacion_cambio_signo_exacta_mano_y_monte_carlo():
    from analisis_profesor.estadistica import permutacion_cambio_signo

    # Ejemplo a mano (n=4): (+,+,+,+) y (-,-,-,-) alcanzan |media| >= 2.5 => p = 2/16 = 0.125
    datos_n4 = [1.0, 2.0, 3.0, 4.0]
    exacto_np = permutacion_cambio_signo(datos_n4, usar_numpy=True)
    exacto_py = permutacion_cambio_signo(datos_n4, usar_numpy=False)
    assert exacto_np["metodo"] == "exacta"
    assert exacto_np["n_configuraciones"] == 16
    assert abs(exacto_np["p_valor"] - 0.125) < 1e-12
    assert abs(exacto_np["p_minimo_alcanzable"] - 0.125) < 1e-12
    assert exacto_np["exploratorio"] is True
    assert exacto_np == exacto_py

    # n=6: p_minimo_alcanzable = 2/2^6 = 0.03125
    datos_n6 = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    r_n6 = permutacion_cambio_signo(datos_n6)
    assert r_n6["metodo"] == "exacta"
    assert r_n6["n_configuraciones"] == 64
    assert abs(r_n6["p_minimo_alcanzable"] - 2.0 / 64) < 1e-12

    # n > 20 -> Monte Carlo con semilla y reproducible
    datos_n25 = [0.2 * (i + 1) - 1.5 for i in range(25)]
    mc1 = permutacion_cambio_signo(datos_n25, n_remuestras=5000, semilla=77, usar_numpy=True)
    mc2 = permutacion_cambio_signo(datos_n25, n_remuestras=5000, semilla=77, usar_numpy=True)
    mc_py = permutacion_cambio_signo(datos_n25, n_remuestras=5000, semilla=77, usar_numpy=False)
    assert mc1["metodo"] == "monte_carlo"
    assert mc1["n_configuraciones"] == 5000
    assert mc1["exploratorio"] is False
    assert mc1 == mc2
    assert abs(mc1["p_valor"] - mc_py["p_valor"]) <= 0.03


def test_wilcoxon_pareado_contra_scipy_y_respaldo():
    from analisis_profesor.estadistica import wilcoxon_pareado

    casos = [
        [1.2, -0.5, 2.3, 0.8, -0.1, 3.1, 1.9, -0.4],
        [-0.6135, 0.0, 2.454, 0.9816, 0.0, 0.3681, 0.0, 0.0],
        [
            -0.6135, 0.0, 2.454, 0.9816, 0.0, 0.3681, 0.0, 0.0,
            0.0, 0.0, -1.9632, -2.454, -1.5951, -0.7362, -0.5521,
        ],
    ]
    for d in casos:
        ref = stats.wilcoxon(d)
        res_sp = wilcoxon_pareado(d, usar_scipy=True)
        res_py = wilcoxon_pareado(d, usar_scipy=False)

        assert res_sp["n"] == len(d)
        assert abs(res_sp["estadistico"] - float(ref.statistic)) < 1e-9
        assert abs(res_sp["p_valor"] - float(ref.pvalue)) < 1e-9
        assert abs(res_py["estadistico"] - float(ref.statistic)) < 1e-9
        assert abs(res_py["p_valor"] - float(ref.pvalue)) < 1e-9


def test_correlacion_spearman_contra_scipy_y_respaldo():
    from analisis_profesor.estadistica import correlacion_spearman

    x = [3.01, 2.45, 3.93, 2.88, 2.02, 2.58, 2.02, 1.35]
    y = [0.8, 0.6, 0.8, 1.0, 0.0, 0.2, 0.6, 0.4]
    ref = stats.spearmanr(x, y)

    res_full = correlacion_spearman(x, y, semilla=2026, usar_numpy=True, usar_scipy=True)
    res_puro = correlacion_spearman(x, y, semilla=2026, usar_numpy=False, usar_scipy=False)

    assert res_full["n"] == 8
    assert res_full["exploratorio"] is True
    assert abs(res_full["spearman"] - float(ref.statistic)) < 1e-9
    assert abs(res_full["p_valor"] - float(ref.pvalue)) < 1e-9
    assert res_full["ic_bootstrap"][0] <= res_full["spearman"] <= res_full["ic_bootstrap"][1]
    assert 0.0 <= res_full["p_permutacion"] <= 1.0

    assert abs(res_puro["spearman"] - float(ref.statistic)) < 1e-9
    assert abs(res_puro["p_valor"] - float(ref.pvalue)) < 1e-9
    assert abs(res_puro["ic_bootstrap"][0] - res_full["ic_bootstrap"][0]) <= 0.15
    assert abs(res_puro["ic_bootstrap"][1] - res_full["ic_bootstrap"][1]) <= 0.15
    assert res_full["ic_bca"][0] <= res_full["spearman"] <= res_full["ic_bca"][1]
    assert res_puro["ic_bca"][0] <= res_puro["spearman"] <= res_puro["ic_bca"][1]


def test_bootstrap_diferencia_medias_bca_y_permutacion_contra_scipy():
    from analisis_profesor.estadistica import bootstrap_diferencia_medias

    a = [1.2, 2.5, 3.1, 4.0, 2.8, 5.5, 6.2]
    b = [0.8, 1.5, 1.9, 2.1, 3.0, 2.4, 3.8, 4.1, 1.7]
    ref = stats.bootstrap(
        (np.asarray(a, dtype=float), np.asarray(b, dtype=float)),
        lambda x, y, axis=-1: np.mean(x, axis=axis) - np.mean(y, axis=axis),
        n_resamples=5000,
        confidence_level=0.95,
        method="BCa",
        random_state=np.random.default_rng(2026),
    ).confidence_interval

    res_np = bootstrap_diferencia_medias(
        a, b, n_remuestras=5000, semilla=2026, usar_numpy=True
    )
    res_py = bootstrap_diferencia_medias(
        a, b, n_remuestras=5000, semilla=2026, usar_numpy=False
    )
    assert res_np == bootstrap_diferencia_medias(
        a, b, n_remuestras=5000, semilla=2026, usar_numpy=True
    )
    assert abs(res_np["ic_bca"][0] - float(ref.low)) <= 0.08
    assert abs(res_np["ic_bca"][1] - float(ref.high)) <= 0.08
    assert abs(res_py["ic_bca"][0] - float(ref.low)) <= 0.12
    assert abs(res_py["ic_bca"][1] - float(ref.high)) <= 0.12
    assert 0.0 < res_np["p_permutacion"] <= 1.0
    assert abs(res_py["p_permutacion"] - res_np["p_permutacion"]) <= 0.04

    sep = bootstrap_diferencia_medias(
        [10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
        [1.0, 2.0, 1.5, 2.5, 3.0, 2.2],
        n_remuestras=2000,
        semilla=2026,
    )
    assert sep["ic_bca"][0] > 0.0
    assert sep["p_permutacion"] < 0.01


def test_intervalo_jeffreys_contra_scipy_y_cobertura():
    from analisis_profesor.estadistica import intervalo_jeffreys

    for exitos, total in [(0, 5), (5, 5), (9, 13), (3, 8), (1, 4)]:
        ref_lo, ref_hi = stats.beta.ppf([0.025, 0.975], exitos + 0.5, total - exitos + 0.5)
        res_sp = intervalo_jeffreys(exitos, total, nivel=0.95, usar_scipy=True)
        res_py = intervalo_jeffreys(exitos, total, nivel=0.95, usar_scipy=False)

        assert res_sp["n"] == total
        assert res_sp["exitos"] == exitos
        assert res_sp["exploratorio"] is (total < 10)
        assert abs(res_sp["ic"][0] - float(ref_lo)) < 1e-9
        assert abs(res_sp["ic"][1] - float(ref_hi)) < 1e-9
        assert abs(res_py["ic"][0] - float(ref_lo)) < 1e-9
        assert abs(res_py["ic"][1] - float(ref_hi)) < 1e-9

    # Simulación de cobertura del IC al 90 % con Jeffreys para p verdadera = 0.3, n = 20
    rng = np.random.default_rng(2026)
    p_verdadera = 0.3
    exitos_sim = rng.binomial(20, p_verdadera, size=2000)
    cache = {k: intervalo_jeffreys(k, 20, nivel=0.90)["ic"] for k in range(21)}
    cubre = sum(1 for k in exitos_sim if cache[int(k)][0] <= p_verdadera <= cache[int(k)][1])
    cobertura = cubre / len(exitos_sim)
    assert 0.85 <= cobertura <= 0.95
