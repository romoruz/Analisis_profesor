"""Paso 5 del protocolo: plantilla, lectura/escritura de `05_etiquetas.csv` y migración legacy."""
from __future__ import annotations

import csv
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from analisis_profesor.config import RASGOS_LEGACY_SD2, leer_config_materia
from analisis_profesor.esquemas import Etiqueta, Item, leer_jsonl

_COLUMNAS_FIJAS = frozenset(
    {
        "item_id",
        "arquetipo",
        "fuente",
        "nivel",
        "bloom",
        "dok",
        "minutos",
        "puntos",
        "pasada",
        "examinable",
    }
)
_TIPOS_NO_EXAMINABLES = frozenset({"clase", "notas", "temario", "pauta", "otro"})
_ROMANOS = {"i": "a", "ii": "b", "iii": "c", "iv": "d"}
_NIVEL_LEGACY = {"adaptacion": "adaptación"}


def columnas_etiquetas(
    rasgos: Mapping[str, tuple[float, int, int]], *, incluir_examinable: bool = False
) -> list[str]:
    """Encabezado estándar de `05_etiquetas.csv` según los rasgos configurados."""
    cols = [
        "item_id",
        "arquetipo",
        "fuente",
        "nivel",
        *rasgos.keys(),
        "bloom",
        "dok",
        "minutos",
        "puntos",
        "pasada",
    ]
    if incluir_examinable:
        cols.append("examinable")
    return cols


def _formatear_float(valor: float | None, *, entero_si_exacto: bool = False) -> str:
    if valor is None:
        return ""
    f = float(valor)
    if entero_si_exacto and f.is_integer():
        return str(int(f))
    return str(f)


def leer_etiquetas(
    ruta_csv: Path, rasgos: Mapping[str, tuple[float, int, int]] | None = None
) -> list[Etiqueta]:
    """Lee `05_etiquetas.csv` y valida campos y cotas de rasgos."""
    with open(ruta_csv, encoding="utf-8", newline="") as f:
        lector = csv.DictReader(f)
        campos = list(lector.fieldnames or [])
        if "item_id" not in campos:
            raise ValueError(f"{ruta_csv.name}: falta la columna obligatoria `item_id`")
        if rasgos is None:
            nombres_rasgos = [c for c in campos if c not in _COLUMNAS_FIJAS]
        else:
            faltantes = [r for r in rasgos if r not in campos]
            if faltantes:
                raise ValueError(f"{ruta_csv.name}: faltan columnas de rasgos {faltantes}")
            nombres_rasgos = list(rasgos.keys())

        etiquetas: list[Etiqueta] = []
        for idx, fila in enumerate(lector, start=2):
            item_id = (fila.get("item_id") or "").strip()
            if not item_id:
                raise ValueError(f"{ruta_csv.name}:{idx}: `item_id` vacío")

            valores_rasgos: dict[str, int] = {}
            for nombre in nombres_rasgos:
                raw = (fila.get(nombre) or "").strip()
                if not raw:
                    continue
                val = int(raw)
                if rasgos is not None and nombre in rasgos:
                    _, base, maximo = rasgos[nombre]
                    if not (base <= val <= maximo):
                        raise ValueError(
                            f"{item_id}.{nombre}={val} fuera de [{base}, {maximo}]"
                        )
                valores_rasgos[nombre] = val

            dok_raw = (fila.get("dok") or "").strip()
            min_raw = (fila.get("minutos") or "").strip()
            pts_raw = (fila.get("puntos") or "").strip()
            pasada_raw = (fila.get("pasada") or "").strip()
            exam_raw = (fila.get("examinable") or "").strip().lower()
            examinable = exam_raw not in ("0", "false", "no")

            etiquetas.append(
                Etiqueta(
                    item_id=item_id,
                    arquetipo=(fila.get("arquetipo") or "").strip(),
                    fuente=(fila.get("fuente") or "").strip(),
                    nivel=(fila.get("nivel") or "").strip(),
                    rasgos=valores_rasgos,
                    bloom=(fila.get("bloom") or "").strip(),
                    dok=int(dok_raw) if dok_raw else None,
                    minutos=float(min_raw) if min_raw else None,
                    pasada=int(pasada_raw) if pasada_raw else 1,
                    puntos=float(pts_raw) if pts_raw else None,
                    examinable=examinable,
                )
            )
    return etiquetas


def escribir_etiquetas(
    ruta_csv: Path,
    etiquetas: Sequence[Etiqueta],
    rasgos: Mapping[str, tuple[float, int, int]],
) -> int:
    """Escribe una secuencia de `Etiqueta` en formato `05_etiquetas.csv`."""
    incluir_examinable = any(not et.examinable for et in etiquetas)
    cols = columnas_etiquetas(rasgos, incluir_examinable=incluir_examinable)
    ruta_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta_csv, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        escritor.writeheader()
        for et in etiquetas:
            fila: dict[str, str | int] = {
                "item_id": et.item_id,
                "arquetipo": et.arquetipo,
                "fuente": et.fuente,
                "nivel": et.nivel,
                "bloom": et.bloom,
                "dok": "" if et.dok is None else str(et.dok),
                "minutos": _formatear_float(et.minutos, entero_si_exacto=True),
                "puntos": _formatear_float(et.puntos, entero_si_exacto=False),
                "pasada": str(et.pasada),
            }
            for r in rasgos:
                val = et.rasgos.get(r)
                fila[r] = "" if val is None else str(val)
            if incluir_examinable:
                fila["examinable"] = "1" if et.examinable else "0"
            escritor.writerow(fila)
    return len(etiquetas)


def generar_plantilla_etiquetas(
    materia: str, raiz_trabajo: Path | None = None, *, sobrescribir: bool = False
) -> Path:
    """Genera `trabajo/<materia>/05_etiquetas.csv` desde `03_items.jsonl` y `materia.toml`."""
    base = (raiz_trabajo or Path("trabajo")) / materia
    cfg = leer_config_materia(base)
    rasgos = cfg["rasgos"]
    items = list(leer_jsonl(base / "03_items.jsonl", Item))
    etiquetables = [it for it in items if not it.padre_id]

    ruta_csv = base / "05_etiquetas.csv"
    existentes_por_id: dict[str, list[Etiqueta]] = {}
    if ruta_csv.is_file() and not sobrescribir:
        for et in leer_etiquetas(ruta_csv, rasgos=rasgos):
            existentes_por_id.setdefault(et.item_id, []).append(et)

    salida: list[Etiqueta] = []
    vistos: set[str] = set()
    for it in etiquetables:
        vistos.add(it.id)
        if it.id in existentes_por_id:
            salida.extend(existentes_por_id[it.id])
            continue
        es_clase = it.tipo_doc in _TIPOS_NO_EXAMINABLES
        salida.append(
            Etiqueta(
                item_id=it.id,
                arquetipo="-" if es_clase else "",
                puntos=it.puntos_obtenidos,
                pasada=1,
            )
        )
    for item_id, lista in existentes_por_id.items():
        if item_id not in vistos:
            salida.extend(lista)

    escribir_etiquetas(ruta_csv, salida, rasgos)
    return ruta_csv


def _mapear_id_legacy(fila: Mapping[str, str]) -> str:
    id_legacy = fila["id"].strip()
    tipo = fila["tipo"].strip().lower()
    origen = fila["origen"].strip()
    if tipo == "examen":
        m_ex = re.fullmatch(r"[^-]+-(\d+)", id_legacy)
        if m_ex and origen:
            return f"{origen}:Q{m_ex.group(1)}"
    if m_tar := re.fullmatch(r"(T\d+)-(\d+)(i{1,3}|iv|[a-z])?", id_legacy):
        doc, num, suf = m_tar.group(1), m_tar.group(2), m_tar.group(3) or ""
        return f"{doc}:{num}{_ROMANOS.get(suf, suf)}"
    return id_legacy


def _mapear_fuente_legacy(fuente: str, mapa_ids: Mapping[str, str]) -> str:
    limpio = fuente.strip()
    if not limpio or limpio == "clase":
        return limpio
    if limpio in mapa_ids:
        return mapa_ids[limpio]
    if m_tar := re.fullmatch(r"(T\d+)-(\d+)(i{1,3}|iv|[a-z])?", limpio):
        doc, num, suf = m_tar.group(1), m_tar.group(2), m_tar.group(3) or ""
        return f"{doc}:{num}{_ROMANOS.get(suf, suf)}"
    return limpio


def convertir_legacy_csv(
    ruta_legacy: Path, ruta_salida: Path | None = None
) -> tuple[list[Etiqueta], dict[str, tuple[float, int, int]]]:
    """Convierte un `rasgos_dificultad.csv` de `legacy/` a `list[Etiqueta]` (y escribe CSV)."""
    with open(ruta_legacy, encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))

    mapa_ids = {fila["id"].strip(): _mapear_id_legacy(fila) for fila in filas}
    rasgos = dict(RASGOS_LEGACY_SD2)
    etiquetas: list[Etiqueta] = []
    for fila in filas:
        item_id = mapa_ids[fila["id"].strip()]
        fuente = _mapear_fuente_legacy(fila.get("fuente") or "", mapa_ids)
        nivel_raw = (fila.get("nivel") or "").strip()
        nivel = _NIVEL_LEGACY.get(nivel_raw, nivel_raw)
        valores_rasgos = {r: int(fila[r]) for r in rasgos if (fila.get(r) or "").strip()}
        pts_raw = (fila.get("puntos") or "").strip()
        exam_raw = (fila.get("examinable") or "1").strip().lower()
        etiquetas.append(
            Etiqueta(
                item_id=item_id,
                arquetipo=(fila.get("arq") or "").strip(),
                fuente=fuente,
                nivel=nivel,
                rasgos=valores_rasgos,
                puntos=float(pts_raw) if pts_raw else None,
                examinable=exam_raw not in ("0", "false", "no"),
                pasada=1,
            )
        )

    if ruta_salida is not None:
        escribir_etiquetas(ruta_salida, etiquetas, rasgos)
    return etiquetas, rasgos
