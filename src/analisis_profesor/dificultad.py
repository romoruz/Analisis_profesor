"""Paso 6 del protocolo: score de dificultad por rasgos, calibración e inferencia."""
from __future__ import annotations

import json
import math
import random
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from analisis_profesor.config import RASGOS_POR_DEFECTO, leer_config_materia
from analisis_profesor.esquemas import Etiqueta, Item, leer_jsonl
from analisis_profesor.estadistica import (
    bootstrap_bca,
    bootstrap_diferencia_medias,
    correlacion_spearman,
    intervalo_jeffreys,
    permutacion_cambio_signo,
    wilcoxon_pareado,
)
from analisis_profesor.etiquetas import leer_etiquetas

try:
    import numpy as np
except ImportError:  # pragma: no cover - entorno sin numpy
    np = None  # type: ignore[assignment]


@dataclass(frozen=True)
class _RegistroDificultad:
    item_id: str
    tipo: str
    origen: str
    arquetipo: str
    examinable: bool
    rasgos: dict[str, int]
    fuente: str
    nivel: str
    puntos: float | None
    puntos_max: float | None


def _cuantil_lineal(ordenados: Sequence[float], q: float) -> float:
    if not ordenados:
        return 0.0
    pos = q * (len(ordenados) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    return float(ordenados[lo] + (pos - lo) * (ordenados[hi] - ordenados[lo]))


def score_item(
    rasgos_item: Mapping[str, int],
    rasgos_cfg: Mapping[str, tuple[float, int, int]] | None = None,
    pesos: Mapping[str, float] | None = None,
) -> float:
    """Score ponderado de dificultad en escala 0-10.

    Fuente: `legacy/estudio_parciales/nucleo/dificultad.py` (`score`) y Anexo A de
    `PROTOCOLO.md`: ``10 * sum(w_k * (x_k - base_k)) / sum(w_k * (max_k - base_k))``.
    """
    cfg = rasgos_cfg or RASGOS_POR_DEFECTO
    w = pesos or {k: v[0] for k, v in cfg.items()}
    num = sum(w[k] * (rasgos_item[k] - cfg[k][1]) for k in cfg)
    den = sum(w[k] * (cfg[k][2] - cfg[k][1]) for k in cfg)
    if den == 0.0:
        return 0.0
    return 10.0 * num / den


def _resumen_grupo(valores: Sequence[float], *, usar_numpy: bool | None = None) -> dict:
    n = len(valores)
    if n == 0:
        return {
            "n": 0,
            "media": None,
            "mediana": None,
            "p25": None,
            "p75": None,
            "rango": None,
            "exploratorio": True,
        }
    if usar_numpy is not False and np is not None:
        arr = np.asarray(valores, dtype=float)
        media = float(arr.mean())
        mediana = float(np.median(arr))
        p25 = float(np.percentile(arr, 25))
        p75 = float(np.percentile(arr, 75))
        vmin, vmax = float(arr.min()), float(arr.max())
    else:
        ord_v = sorted(float(x) for x in valores)
        media = sum(ord_v) / n
        mediana = _cuantil_lineal(ord_v, 0.5)
        p25 = _cuantil_lineal(ord_v, 0.25)
        p75 = _cuantil_lineal(ord_v, 0.75)
        vmin, vmax = ord_v[0], ord_v[-1]
    return {
        "n": n,
        "media": round(media, 2),
        "mediana": round(mediana, 2),
        "p25": round(p25, 2),
        "p75": round(p75, 2),
        "rango": [round(vmin, 2), round(vmax, 2)],
        "exploratorio": n < 10,
    }


def _clasificar_tipo_documento(et: Etiqueta, items_por_id: Mapping[str, Item]) -> str:
    if it := items_por_id.get(et.item_id):
        return it.tipo_doc
    doc_id, _, resto = et.item_id.partition(":")
    if resto.upper().startswith("Q") or re.match(r"^(?:P\d+|final)\b", doc_id, re.I):
        return "examen"
    if re.match(r"^T\d+$", doc_id, re.I):
        return "tarea"
    if et.fuente or et.nivel or et.puntos is not None:
        return "examen"
    return "clase"


def _construir_registros(
    etiquetas: Sequence[Etiqueta],
    rasgos_cfg: Mapping[str, tuple[float, int, int]],
    items_por_id: Mapping[str, Item],
) -> list[_RegistroDificultad]:
    requeridos = set(rasgos_cfg)
    registros: list[_RegistroDificultad] = []
    vistos: set[str] = set()
    for et in etiquetas:
        if et.pasada != 1 or et.item_id in vistos:
            continue
        vistos.add(et.item_id)
        tipo = _clasificar_tipo_documento(et, items_por_id)
        if tipo not in ("tarea", "examen"):
            continue
        if not requeridos.issubset(et.rasgos):
            continue
        origen = et.item_id.split(":", 1)[0]
        it = items_por_id.get(et.item_id)
        puntos = et.puntos if et.puntos is not None else (it.puntos_obtenidos if it else None)
        registros.append(
            _RegistroDificultad(
                item_id=et.item_id,
                tipo=tipo,
                origen=origen,
                arquetipo=et.arquetipo,
                examinable=et.examinable,
                rasgos=dict(et.rasgos),
                fuente=et.fuente,
                nivel=et.nivel,
                puntos=puntos,
                puntos_max=it.puntos_max if it else None,
            )
        )
    return registros


def conclusion_comparacion(
    ic_bca: Sequence[float] | None,
    p_permutacion: float | None,
    *,
    umbral_p: float = 0.05,
) -> str:
    """Clasifica una comparación según su IC BCa y su p-valor de permutación.

    Devuelve ``"distinguible de cero"`` únicamente cuando el intervalo BCa excluye
    estrictamente el 0 (``lo > 0`` o ``hi < 0``) y ``p_permutacion < umbral_p``;
    en otro caso devuelve ``"no concluyente"``.
    """
    if ic_bca is None or p_permutacion is None or len(ic_bca) != 2:
        return "no concluyente"
    lo, hi = float(ic_bca[0]), float(ic_bca[1])
    excluye_cero = lo > 0.0 or hi < 0.0
    if excluye_cero and float(p_permutacion) < umbral_p:
        return "distinguible de cero"
    return "no concluyente"


def calibra(
    registros: Sequence[_RegistroDificultad],
    rasgos_cfg: Mapping[str, tuple[float, int, int]],
    pesos: Mapping[str, float] | None = None,
    filtro: Callable[[_RegistroDificultad], bool] = lambda _: True,
    *,
    semilla: int = 2026,
    incluir_inferencia: bool = True,
    usar_numpy: bool | None = None,
    usar_scipy: bool | None = None,
) -> dict:
    """Compara tareas y exámenes globalmente y por pares (pregunta contra fuente).

    Fuente: `legacy/estudio_parciales/nucleo/dificultad.py` (`calibra`), extendido con
    inferencia no paramétrica e incertidumbre de `docs/METODOLOGIA_ESTADISTICA.md` §1-2.
    """
    scores = {r.item_id: score_item(r.rasgos, rasgos_cfg, pesos) for r in registros}
    tipos_por_id = {r.item_id: r.tipo for r in registros}
    tareas = [r for r in registros if r.tipo == "tarea" and r.examinable and filtro(r)]
    examenes = [r for r in registros if r.tipo == "examen" and filtro(r)]

    st = [scores[r.item_id] for r in tareas]
    se = [scores[r.item_id] for r in examenes]
    pct = (
        {
            r.item_id: round(100.0 * (sum(1 for x in st if x <= scores[r.item_id]) / len(st)), 1)
            for r in examenes
        }
        if st
        else {}
    )

    pares: list[dict] = []
    pares_omitidos: list[dict] = []
    deltas_exactos: list[float] = []
    for r in examenes:
        if r.fuente in scores:
            d_exacto = scores[r.item_id] - scores[r.fuente]
            deltas_exactos.append(d_exacto)
            pares.append(
                {
                    "examen": r.item_id,
                    "fuente": r.fuente,
                    "nivel": r.nivel,
                    "score_examen": round(scores[r.item_id], 2),
                    "score_fuente": round(scores[r.fuente], 2),
                    "delta": round(d_exacto, 2),
                }
            )
        else:
            pares_omitidos.append(
                {
                    "examen": r.item_id,
                    "fuente": r.fuente,
                    "nivel": r.nivel,
                }
            )

    delta_medias = round((sum(se) / len(se)) - (sum(st) / len(st)), 2) if se and st else None
    delta_pares_media = (
        round(sum(p["delta"] for p in pares) / len(pares), 2) if pares else None
    )

    salida: dict = {
        "scores": {k: round(v, 2) for k, v in scores.items()},
        "tareas": _resumen_grupo(st, usar_numpy=usar_numpy),
        "examenes": _resumen_grupo(se, usar_numpy=usar_numpy),
        "delta_medias": delta_medias,
        "percentil_examen_en_tareas": pct,
        "pares": pares,
        "pares_omitidos": {
            "n": len(pares_omitidos),
            "items": pares_omitidos,
        },
        "delta_pares_media": delta_pares_media,
    }
    if not incluir_inferencia:
        return salida

    comp_medias = bootstrap_diferencia_medias(
        se, st, semilla=semilla, usar_numpy=usar_numpy
    )
    comp_medias["conclusion"] = conclusion_comparacion(
        comp_medias["ic_bca"], comp_medias["p_permutacion"]
    )
    salida["comparacion_medias"] = comp_medias
    if deltas_exactos:
        bca = bootstrap_bca(
            deltas_exactos, n_remuestras=10_000, semilla=semilla, usar_numpy=usar_numpy
        )
        perm = permutacion_cambio_signo(
            deltas_exactos, semilla=semilla, usar_numpy=usar_numpy
        )
        wilc = wilcoxon_pareado(deltas_exactos, usar_scipy=usar_scipy)
        if len(deltas_exactos) >= 2:
            total_d = sum(deltas_exactos)
            n_d = len(deltas_exactos)
            jk = [(total_d - d) / (n_d - 1) for d in deltas_exactos]
            jackknife_rango = [round(min(jk), 3), round(max(jk), 3)]
        else:
            jackknife_rango = [round(deltas_exactos[0], 3), round(deltas_exactos[0], 3)]
        ic_bca_rep = [round(v, 3) for v in bca["ic"]]
        p_perm_rep = round(perm["p_valor"], 4)
        salida["delta_pares_inferencia"] = {
            "n": len(deltas_exactos),
            "n_omitidos": len(pares_omitidos),
            "media": round(sum(deltas_exactos) / len(deltas_exactos), 2),
            "mediana": round(_cuantil_lineal(sorted(deltas_exactos), 0.5), 2),
            "ic_bca": ic_bca_rep,
            "nivel_ic": bca["nivel"],
            "n_remuestras": bca["n_remuestras"],
            "p_permutacion": p_perm_rep,
            "p_minimo_alcanzable": perm["p_minimo_alcanzable"],
            "metodo_permutacion": perm["metodo"],
            "wilcoxon_estadistico": wilc["estadistico"],
            "p_wilcoxon": round(wilc["p_valor"], 4),
            "jackknife_rango": jackknife_rango,
            "exploratorio": len(deltas_exactos) < 10,
            "conclusion": conclusion_comparacion(ic_bca_rep, p_perm_rep),
        }
    else:
        salida["delta_pares_inferencia"] = {
            "n": 0,
            "n_omitidos": len(pares_omitidos),
            "media": None,
            "mediana": None,
            "ic_bca": None,
            "nivel_ic": 0.95,
            "n_remuestras": 0,
            "p_permutacion": None,
            "p_minimo_alcanzable": None,
            "metodo_permutacion": None,
            "wilcoxon_estadistico": None,
            "p_wilcoxon": None,
            "jackknife_rango": None,
            "exploratorio": True,
            "conclusion": "no concluyente",
        }

    n_ex = len(examenes)
    de_tarea = sum(1 for r in examenes if tipos_por_id.get(r.fuente) == "tarea")
    de_examen = sum(1 for r in examenes if tipos_por_id.get(r.fuente) == "examen")
    no_item = len(pares_omitidos)
    salida["reciclaje_por_fuente"] = {
        "n_examenes": n_ex,
        "desde_tarea": intervalo_jeffreys(de_tarea, n_ex, usar_scipy=usar_scipy),
        "desde_examen_previo": intervalo_jeffreys(de_examen, n_ex, usar_scipy=usar_scipy),
        "fuente_no_item": intervalo_jeffreys(no_item, n_ex, usar_scipy=usar_scipy),
    }
    return salida


def por_arquetipo(
    registros: Sequence[_RegistroDificultad],
    rasgos_cfg: Mapping[str, tuple[float, int, int]],
    pesos: Mapping[str, float] | None = None,
) -> dict[str, dict[str, list[float]]]:
    """Agrupa los scores por arquetipo y tipo (`tarea` / `examen`), como en `legacy`."""
    scores = {r.item_id: score_item(r.rasgos, rasgos_cfg, pesos) for r in registros}
    salida: dict[str, dict[str, list[float]]] = {}
    for r in registros:
        if r.arquetipo in ("", "-") or not r.examinable:
            continue
        bloque = salida.setdefault(r.arquetipo, {"tarea": [], "examen": []})
        bloque[r.tipo].append(round(scores[r.item_id], 2))
    return salida


def robustez(
    registros: Sequence[_RegistroDificultad],
    rasgos_cfg: Mapping[str, tuple[float, int, int]],
    *,
    n: int = 2000,
    semilla: int = 0,
    rango: tuple[float, float] = (0.5, 1.5),
    filtro: Callable[[_RegistroDificultad], bool] = lambda _: True,
    usar_numpy: bool | None = None,
) -> dict:
    """Repite la calibración multiplicando cada peso por $U(\\text{rango})$.

    Fuente: `legacy/estudio_parciales/nucleo/dificultad.py` (`robustez`). Además reporta
    `frac_mismo_signo_medias` y `frac_mismo_signo_pares` respecto al delta observado.
    """
    base_cal = calibra(
        registros,
        rasgos_cfg,
        filtro=filtro,
        incluir_inferencia=False,
        usar_numpy=usar_numpy,
    )
    obs_dm = base_cal["delta_medias"]
    obs_dp = base_cal["delta_pares_media"]

    nombres = list(rasgos_cfg.keys())
    base_pesos = {k: rasgos_cfg[k][0] for k in nombres}
    use_np = usar_numpy is not False and np is not None
    rng_np = np.random.default_rng(semilla) if use_np else None
    rng_py = random.Random(semilla) if not use_np else None

    dm: list[float] = []
    dp: list[float] = []
    for _ in range(n):
        if rng_np is not None:
            w = {k: base_pesos[k] * float(rng_np.uniform(*rango)) for k in nombres}
        else:
            assert rng_py is not None
            w = {k: base_pesos[k] * rng_py.uniform(*rango) for k in nombres}
        c = calibra(
            registros,
            rasgos_cfg,
            w,
            filtro=filtro,
            incluir_inferencia=False,
            usar_numpy=usar_numpy,
        )
        if c["delta_medias"] is not None:
            dm.append(float(c["delta_medias"]))
        if c["delta_pares_media"] is not None:
            dp.append(float(c["delta_pares_media"]))

    def _percentiles(vals: Sequence[float]) -> list[float] | None:
        if not vals:
            return None
        if use_np:
            assert np is not None
            return [round(float(np.percentile(vals, q)), 2) for q in (5, 50, 95)]
        ord_v = sorted(vals)
        return [round(_cuantil_lineal(ord_v, q / 100.0), 2) for q in (5, 50, 95)]

    def _frac_mismo_signo(vals: Sequence[float], obs: float | None) -> float | None:
        if not vals or obs is None or obs == 0.0:
            return None
        cnt = sum(1 for v in vals if (v > 0.0 if obs > 0.0 else v < 0.0))
        return round(cnt / len(vals), 3)

    return {
        "n_perturbaciones": n,
        "n_pares": len(base_cal["pares"]),
        "rango_pesos": [rango[0], rango[1]],
        "delta_medias_p5_p50_p95": _percentiles(dm),
        "delta_pares_p5_p50_p95": _percentiles(dp),
        "frac_examen_mas_dificil_medias": (
            round(sum(1 for v in dm if v > 0.0) / len(dm), 3) if dm else None
        ),
        "frac_examen_mas_dificil_pares": (
            round(sum(1 for v in dp if v > 0.0) / len(dp), 3) if dp else None
        ),
        "frac_mismo_signo_medias": _frac_mismo_signo(dm, obs_dm),
        "frac_mismo_signo_pares": _frac_mismo_signo(dp, obs_dp),
        "exploratorio": len(base_cal["pares"]) < 10,
    }


def contra_calificaciones(
    registros: Sequence[_RegistroDificultad],
    rasgos_cfg: Mapping[str, tuple[float, int, int]],
    pesos: Mapping[str, float] | None = None,
    *,
    puntos_max_defecto: float = 2.5,
    semilla: int = 2026,
    usar_numpy: bool | None = None,
    usar_scipy: bool | None = None,
) -> dict | None:
    """Correlación de Spearman entre score y fracción de puntos perdida en calificaciones.

    Fuente: `legacy/estudio_parciales/nucleo/dificultad.py` (`contra_calificaciones`) y
    `docs/METODOLOGIA_ESTADISTICA.md` §3 (IC bootstrap y $p$ de permutación).
    """
    pares: list[tuple[float, float]] = []
    for r in registros:
        if r.puntos is None:
            continue
        pmax = r.puntos_max if r.puntos_max and r.puntos_max > 0 else puntos_max_defecto
        pares.append((score_item(r.rasgos, rasgos_cfg, pesos), 1.0 - r.puntos / pmax))
    if len(pares) < 4:
        return None
    res = correlacion_spearman(
        [a for a, _ in pares],
        [b for _, b in pares],
        semilla=semilla,
        usar_numpy=usar_numpy,
        usar_scipy=usar_scipy,
    )
    ic_bca_rep = [round(v, 3) for v in res["ic_bca"]]
    p_perm_rep = round(res["p_permutacion"], 4)
    return {
        "n": res["n"],
        "spearman": round(res["spearman"], 3),
        "p_valor": round(res["p_valor"], 3),
        "ic_bootstrap": [round(v, 3) for v in res["ic_bootstrap"]],
        "ic_bca": ic_bca_rep,
        "nivel_ic": res["nivel_ic"],
        "p_permutacion": p_perm_rep,
        "n_remuestras": res["n_remuestras"],
        "exploratorio": res["exploratorio"],
        "conclusion": conclusion_comparacion(ic_bca_rep, p_perm_rep),
    }


def calcular_dificultad(
    materia: str,
    raiz_trabajo: Path | None = None,
    *,
    semilla: int = 2026,
    semilla_robustez_todo: int = 1,
    semilla_robustez_alcance: int = 2,
    usar_numpy: bool | None = None,
    usar_scipy: bool | None = None,
) -> dict:
    """Calcula `06_dificultad.json` en `trabajo/<materia>/` usando `05_etiquetas.csv`."""
    base = (raiz_trabajo or Path("trabajo")) / materia
    cfg = leer_config_materia(base)
    rasgos_cfg = cfg["rasgos"]

    ruta_items = base / "03_items.jsonl"
    items_por_id = (
        {it.id: it for it in leer_jsonl(ruta_items, Item)} if ruta_items.is_file() else {}
    )
    etiquetas = leer_etiquetas(base / "05_etiquetas.csv", rasgos=rasgos_cfg)
    registros = _construir_registros(etiquetas, rasgos_cfg, items_por_id)

    def _en_alcance(r: _RegistroDificultad) -> bool:
        return r.arquetipo not in ("", "-")

    todo = calibra(
        registros,
        rasgos_cfg,
        semilla=semilla,
        usar_numpy=usar_numpy,
        usar_scipy=usar_scipy,
    )
    alcance = calibra(
        registros,
        rasgos_cfg,
        filtro=_en_alcance,
        semilla=semilla,
        usar_numpy=usar_numpy,
        usar_scipy=usar_scipy,
    )
    arq = por_arquetipo(registros, rasgos_cfg)
    rob_todo = robustez(
        registros,
        rasgos_cfg,
        n=2000,
        semilla=semilla_robustez_todo,
        usar_numpy=usar_numpy,
    )
    rob_alcance = robustez(
        registros,
        rasgos_cfg,
        n=2000,
        semilla=semilla_robustez_alcance,
        filtro=_en_alcance,
        usar_numpy=usar_numpy,
    )

    pts_cfg = cfg["formato"].get("puntos_por_pregunta") or []
    puntos_max_def = float(pts_cfg[0]) if pts_cfg else 2.5
    emp = contra_calificaciones(
        registros,
        rasgos_cfg,
        puntos_max_defecto=puntos_max_def,
        semilla=semilla,
        usar_numpy=usar_numpy,
        usar_scipy=usar_scipy,
    )

    dp = alcance["delta_pares_media"] or 0.0
    objetivo: dict[str, dict] = {}
    for k in sorted(arq):
        d = arq[k]
        tarea_media = round(sum(d["tarea"]) / len(d["tarea"]), 2) if d["tarea"] else None
        if d["examen"]:
            base_vals = d["examen"]
            objetivo[k] = {
                "objetivo": round(sum(base_vals) / len(base_vals), 2),
                "base": "examen",
                "n": len(base_vals),
                "rango": [min(base_vals), max(base_vals)],
                "exploratorio": len(base_vals) < 10,
                "tarea_media": tarea_media,
            }
        else:
            base_vals = d["tarea"]
            objetivo[k] = {
                "objetivo": round((sum(base_vals) / len(base_vals)) + dp, 2),
                "base": "tarea+delta",
                "n": len(base_vals),
                "rango": [min(base_vals), max(base_vals)],
                "exploratorio": len(base_vals) < 10,
                "tarea_media": tarea_media,
            }

    totales_lista: dict[str, list[float]] = {}
    for r in registros:
        if r.tipo == "examen":
            totales_lista.setdefault(r.origen, []).append(todo["scores"][r.item_id])
    dificultad_total_examen = {k: round(sum(v), 2) for k, v in totales_lista.items()}
    examenes_detalle = {
        k: {
            "total": round(sum(v), 2),
            "n_preguntas": len(v),
            "rango_preguntas": [round(min(v), 2), round(max(v), 2)],
            "exploratorio": len(v) < 10,
        }
        for k, v in totales_lista.items()
    }

    claves_alcance = (
        "tareas",
        "examenes",
        "delta_medias",
        "comparacion_medias",
        "pares",
        "pares_omitidos",
        "delta_pares_media",
        "delta_pares_inferencia",
        "reciclaje_por_fuente",
        "percentil_examen_en_tareas",
    )
    resultado = {
        "semilla": semilla,
        "rasgos": {k: {"peso": v[0], "base": v[1], "max": v[2]} for k, v in rasgos_cfg.items()},
        "todo_el_curso": todo,
        "alcance_objetivo": {k: alcance[k] for k in claves_alcance},
        "robustez_todo": rob_todo,
        "robustez_alcance": rob_alcance,
        "por_arquetipo": arq,
        "objetivo": objetivo,
        "dificultad_total_examen": dificultad_total_examen,
        "examenes_detalle": examenes_detalle,
        "contra_calificaciones": emp,
    }
    (base / "06_dificultad.json").write_text(
        json.dumps(resultado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return resultado
