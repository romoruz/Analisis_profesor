"""Armado optimizado de simulacros desde el banco verificado (paso 8 de PROTOCOLO.md).

Fuente: `legacy/estudio_parciales/cursos/sistemas_dinamicos_ii/src/05_armar_simulacros.py`
y `docs/METODOLOGIA_ESTADISTICA.md` §7-8 (banda de dificultad ±tol respecto al objetivo y
penalización por repetición de familia con desempate aleatorio reproducible).
"""
from __future__ import annotations

import itertools
import json
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from analisis_profesor.banco import (
    EjercicioBanco,
    leer_banco,
    normalizar_nivel,
    verificar_banco,
)
from analisis_profesor.config import leer_config_materia
from analisis_profesor.dificultad import score_item
from analisis_profesor.modelo import calcular_modelo
from analisis_profesor.salida import escribir_entregables

try:
    import numpy as np
except ImportError:  # pragma: no cover - entorno sin numpy
    np = None  # type: ignore[assignment]


@dataclass
class _CandidatoArmado:
    ej: EjercicioBanco
    score: float


def _crear_rng_armado(semilla: int, *, usar_numpy: bool | None = None):
    if usar_numpy is not False and np is not None:
        return np.random.default_rng(semilla)
    return random.Random(semilla)


def _cargar_verificacion(
    materia: str,
    raiz_trabajo: Path | None,
    base: Path,
) -> dict:
    ruta_verif = base / "08_verificacion.json"
    if ruta_verif.is_file():
        return json.loads(ruta_verif.read_text(encoding="utf-8"))
    return verificar_banco(materia, raiz_trabajo=raiz_trabajo)


def _calcular_meta_dificultad(
    cfg_materia: Mapping,
    dif: Mapping,
    objetivos: Mapping[str, float],
    n_preguntas_defecto: int,
) -> float:
    totales = dif.get("dificultad_total_examen", {})
    molde_ids = list(cfg_materia.get("objetivo", {}).get("molde", []))
    valores = [float(totales[m]) for m in molde_ids if m in totales]
    if not valores:
        valores = [float(v) for v in totales.values()]
    if valores:
        return sum(valores) / len(valores)
    if objetivos:
        return (sum(objetivos.values()) / len(objetivos)) * max(1, n_preguntas_defecto)
    return 0.0


def _seleccionar_pool_pregunta(
    cands: Sequence[_CandidatoArmado],
    arquetipo: str,
    nivel: str,
    objetivo_k: float,
    usados: set[str],
    tolerancia: float,
    num_simulacro: int,
) -> tuple[list[_CandidatoArmado], str | None]:
    niv_norm = normalizar_nivel(nivel)
    estricto = [
        c
        for c in cands
        if c.ej.arquetipo == arquetipo
        and normalizar_nivel(c.ej.nivel) == niv_norm
        and c.ej.id not in usados
        and abs(c.score - objetivo_k) <= tolerancia
    ]
    if estricto:
        return estricto, None

    aviso = (
        f"simulacro {num_simulacro}, arquetipo {arquetipo} nivel {nivel}: "
        "se relajó el filtro"
    )
    sin_nivel = [
        c
        for c in cands
        if c.ej.arquetipo == arquetipo
        and c.ej.id not in usados
        and abs(c.score - objetivo_k) <= tolerancia
    ]
    if sin_nivel:
        return sin_nivel, aviso

    sin_banda = [c for c in cands if c.ej.arquetipo == arquetipo and c.ej.id not in usados]
    if sin_banda:
        return sin_banda, aviso

    mismo_arq = [c for c in cands if c.ej.arquetipo == arquetipo]
    if mismo_arq:
        return mismo_arq, aviso + " (reutilizado)"
    raise ValueError(f"No hay ejercicios verificados disponibles para el arquetipo {arquetipo!r}")


def armar_simulacros(
    materia: str,
    raiz_trabajo: Path | None = None,
    *,
    n_simulacros: int = 5,
    semilla: int = 2026,
    tolerancia: float = 1.0,
    usar_numpy: bool | None = None,
    compilar_pdf: bool = True,
) -> dict:
    """Selecciona `n_simulacros` del banco verificado y genera entregables."""
    base = (raiz_trabajo or Path("trabajo")) / materia
    cfg_materia = leer_config_materia(base)

    ruta_dif = base / "06_dificultad.json"
    if not ruta_dif.is_file():
        raise FileNotFoundError(f"Falta {ruta_dif}; ejecuta antes `dificultad`.")
    dif = json.loads(ruta_dif.read_text(encoding="utf-8"))

    ruta_mod = base / "07_modelo.json"
    if not ruta_mod.is_file():
        raise FileNotFoundError(f"Falta {ruta_mod}; ejecuta antes `modelo`.")
    mod = json.loads(ruta_mod.read_text(encoding="utf-8"))

    verif = _cargar_verificacion(materia, raiz_trabajo, base)
    ids_ok = {r["id"] for r in verif.get("resultados", []) if r.get("verificado")}

    ejercicios = leer_banco(base / "08_banco.md")
    ejercicios_por_id = {ej.id: ej for ej in ejercicios}

    rasgos_cfg = cfg_materia["rasgos"]
    cands: list[_CandidatoArmado] = []
    for ej in ejercicios:
        if ej.id in ids_ok:
            cands.append(_CandidatoArmado(ej=ej, score=round(score_item(ej.rasgos, rasgos_cfg), 2)))
    if not cands:
        raise ValueError(f"No hay ejercicios verificados en {base / '08_banco.md'}")

    objetivos = {k: float(v["objetivo"]) for k, v in dif.get("objetivo", {}).items()}
    sorteos = list(mod.get("sorteos", []))
    if len(sorteos) != n_simulacros:
        if (base / "05_etiquetas.csv").is_file() and (
            n_simulacros > len(sorteos) or mod.get("sorteos") is None
        ):
            mod = calcular_modelo(
                materia,
                raiz_trabajo=raiz_trabajo,
                n_sorteos=n_simulacros,
                usar_numpy=usar_numpy,
            )
            sorteos = list(mod["sorteos"])
        else:
            sorteos = sorteos[:n_simulacros]

    n_preg_ref = len(sorteos[0]["preguntas"]) if sorteos else 4
    meta = _calcular_meta_dificultad(cfg_materia, dif, objetivos, n_preg_ref)

    puntos_cfg = [float(x) for x in cfg_materia["formato"].get("puntos_por_pregunta", [])]
    rng = _crear_rng_armado(semilla, usar_numpy=usar_numpy)
    usados: set[str] = set()
    familias: set[str] = set()
    avisos: list[str] = []
    examenes: list[dict] = []

    for num, sorteo in enumerate(sorteos, 1):
        opciones: list[list[_CandidatoArmado]] = []
        for q in sorteo["preguntas"]:
            k = str(q["arquetipo"])
            niv = str(q.get("nivel", ""))
            obj_k = objetivos.get(k, 0.0)
            pool, aviso = _seleccionar_pool_pregunta(
                cands, k, niv, obj_k, usados, tolerancia, num
            )
            if aviso:
                avisos.append(aviso)
            opciones.append(pool)

        mejor: tuple[_CandidatoArmado, ...] | None = None
        mejor_costo = float("inf")
        for combo in itertools.product(*opciones):
            if len({c.ej.id for c in combo}) < len(combo):
                continue
            tot = sum(c.score for c in combo)
            pen_fam = 0.5 * sum(c.ej.familia_efectiva in familias for c in combo)
            ruido = float(rng.uniform(0.0, 0.3))
            costo = abs(tot - meta) + pen_fam + ruido
            if costo < mejor_costo:
                mejor = combo
                mejor_costo = costo

        if mejor is None:
            raise RuntimeError(
                f"No fue posible combinar ejercicios sin repetición para el simulacro {num}."
            )

        for cand in mejor:
            usados.add(cand.ej.id)
            familias.add(cand.ej.familia_efectiva)

        preguntas_out: list[dict] = []
        for idx, cand in enumerate(mejor):
            obj_k = objetivos.get(cand.ej.arquetipo, 0.0)
            pts = (
                puntos_cfg[idx]
                if idx < len(puntos_cfg)
                else round(10.0 / max(1, len(mejor)), 2)
            )
            preguntas_out.append(
                {
                    "id": cand.ej.id,
                    "banco_id": cand.ej.id,
                    "arq": cand.ej.arquetipo,
                    "arquetipo": cand.ej.arquetipo,
                    "nivel": cand.ej.nivel,
                    "puntos": pts,
                    "score": cand.score,
                    "dificultad": cand.score,
                    "objetivo": obj_k,
                    "verificado": True,
                    "tex": cand.ej.enunciado,
                }
            )

        examenes.append(
            {
                "numero": num,
                "semilla": semilla,
                "minutos": int(sorteo["minutos"]),
                "dificultad_total": round(sum(c.score for c in mejor), 2),
                "preguntas": preguntas_out,
            }
        )

    salida = {
        "materia": materia,
        "semilla": semilla,
        "meta_dificultad_total": round(meta, 2),
        "tolerancia": tolerancia,
        "n_candidatos_verificados": len(cands),
        "avisos_relajacion": avisos,
        "examenes": examenes,
    }
    (base / "simulacros.json").write_text(
        json.dumps(salida, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    entregables = escribir_entregables(
        cfg_materia,
        salida,
        ejercicios_por_id,
        base / "entregables",
        compilar_pdf=compilar_pdf,
    )
    salida["entregables"] = entregables
    return salida


__all__ = ["armar_simulacros"]
