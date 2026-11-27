"""Consistencia entre pasadas de etiquetado (`05_etiquetas.csv` -> `05_acuerdo.json`).

Implementa `ap.py acuerdo` (tareas 2.5 y 3.1 de `docs/ROADMAP.md` y
`docs/METODOLOGIA_ESTADISTICA.md` §4). Solo utiliza librería estándar a nivel módulo.
"""
from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from analisis_profesor.config import leer_config_materia
from analisis_profesor.esquemas import BLOOM, NIVELES_RECICLAJE, Etiqueta
from analisis_profesor.estadistica import alfa_krippendorff
from analisis_profesor.etiquetas import leer_etiquetas


def _valor_campo(et: Etiqueta, campo: str) -> int | str | None:
    if campo == "arquetipo":
        return et.arquetipo if et.arquetipo not in ("", "-") else None
    if campo == "nivel":
        niv = et.nivel.strip()
        return "adaptación" if niv == "adaptacion" else (niv or None)
    if campo == "bloom":
        return et.bloom.strip() or None
    if campo == "dok":
        return et.dok
    return et.rasgos.get(campo)


def _emparejar_etiquetas(
    etiquetas_base: Sequence[Etiqueta],
    etiquetas_contra: Sequence[Etiqueta] | None,
) -> list[tuple[str, list[Etiqueta]]]:
    """Agrupa entradas comparables por `item_id` (doble pasada o contra otro CSV)."""
    if etiquetas_contra is not None:
        p1 = {et.item_id: et for et in etiquetas_base if et.pasada == 1}
        p2: dict[str, Etiqueta] = {}
        for et in etiquetas_contra:
            if et.item_id not in p2 or et.pasada == 1:
                p2[et.item_id] = et
        comunes = [item_id for item_id in p1 if item_id in p2]
        return [(item_id, [p1[item_id], p2[item_id]]) for item_id in comunes]

    por_item: dict[str, dict[int, Etiqueta]] = defaultdict(dict)
    for et in etiquetas_base:
        por_item[et.item_id].setdefault(et.pasada, et)
    pares: list[tuple[str, list[Etiqueta]]] = []
    for item_id, pasadas in por_item.items():
        if len(pasadas) >= 2:
            ordenadas = [pasadas[p] for p in sorted(pasadas)]
            pares.append((item_id, ordenadas))
    return pares


def calcular_acuerdo(
    materia: str,
    raiz_trabajo: Path | None = None,
    *,
    ruta_contra: Path | None = None,
    semilla: int = 2026,
    usar_numpy: bool | None = None,
) -> dict:
    """Calcula α de Krippendorff por campo y desacuerdos puntuales en `05_acuerdo.json`."""
    base = (raiz_trabajo or Path("trabajo")) / materia
    cfg = leer_config_materia(base)
    rasgos_cfg = cfg["rasgos"]

    etiqs_base = leer_etiquetas(base / "05_etiquetas.csv", rasgos=rasgos_cfg)
    etiqs_contra = (
        leer_etiquetas(ruta_contra, rasgos=rasgos_cfg) if ruta_contra is not None else None
    )
    grupos = _emparejar_etiquetas(etiqs_base, etiqs_contra)

    campos_eval: list[tuple[str, str, Sequence | None]] = [
        ("arquetipo", "nominal", None),
        ("nivel", "ordinal", list(NIVELES_RECICLAJE)),
        *[(r, "ordinal", list(range(b, m + 1))) for r, (_w, b, m) in rasgos_cfg.items()],
        ("bloom", "ordinal", list(BLOOM)),
        ("dok", "ordinal", [1, 2, 3, 4]),
    ]

    por_campo: dict[str, dict] = {}
    desacuerdos: list[dict] = []
    for campo, metrica, orden in campos_eval:
        unidades: list[list[object]] = []
        for item_id, lista_et in grupos:
            vals = [_valor_campo(et, campo) for et in lista_et]
            limpios = [v for v in vals if v is not None]
            if len(limpios) >= 2:
                unidades.append(limpios)
                if len(set(limpios)) > 1:
                    desacuerdos.append({"item_id": item_id, "campo": campo, "valores": limpios})
        if len(unidades) >= 2:
            res_campo = alfa_krippendorff(
                unidades,
                metrica=metrica,
                orden_categorias=orden,
                semilla=semilla,
                usar_numpy=usar_numpy,
            )
            res_campo["alfa"] = round(res_campo["alfa"], 4)
            por_campo[campo] = res_campo

    inestables = [
        campo
        for campo, info in por_campo.items()
        if not info["varianza_nula"] and info["alfa"] < 0.67
    ]
    alfas_rasgos = [por_campo[r]["alfa"] for r in rasgos_cfg if r in por_campo]
    media_rasgos = round(sum(alfas_rasgos) / len(alfas_rasgos), 4) if alfas_rasgos else None
    n_items = len(grupos)

    salida = {
        "materia": materia,
        "modo": "contra_archivo" if ruta_contra is not None else "doble_pasada",
        "semilla": semilla,
        "n_items": n_items,
        "exploratorio": n_items < 10,
        "muestra_recomendada_ok": n_items >= 20,
        "por_campo": por_campo,
        "rasgos_inestables": inestables,
        "desacuerdos": sorted(desacuerdos, key=lambda d: (d["item_id"], d["campo"])),
        "resumen": {
            "n_campos_evaluados": len(por_campo),
            "n_rasgos_inestables": len(inestables),
            "n_desacuerdos": len(desacuerdos),
            "alfa_promedio_rasgos": media_rasgos,
        },
    }
    if n_items >= 2:
        (base / "05_acuerdo.json").write_text(
            json.dumps(salida, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return salida


__all__ = ["calcular_acuerdo"]
