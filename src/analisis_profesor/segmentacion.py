"""Paso 3 del protocolo: segmentación de `02_texto/*.md` en ítems JSONL."""
from __future__ import annotations

import re
from pathlib import Path

from analisis_profesor.esquemas import Item, escribir_jsonl

_PATRON_PREGUNTA = r"^##\s+Pregunta\s+(\d+)(?:\s*\((\d+(?:\.\d+)?)\s*(?:puntos?|pts?\.?)\))?\s*$"
_PATRON_EJERCICIO = r"^##\s+Ejercicio\s+(\d+[a-zA-Z]?)\b.*$"
_PATRON_SECCION = r"^##\s+(.+?)\s*$"
_PATRON_INCISO = r"^###\s+([a-z]|[ivx]+)\)\s*$"


def _limpiar_calificaciones(valor: str) -> list[float] | None:
    sin_com = re.split(r"\s*(?:<-|#)", valor, maxsplit=1)[0].strip()
    if not sin_com:
        return None
    return [float(parte.strip()) for parte in sin_com.split(",") if parte.strip()]


def _parsear_cabecera(
    texto: str, doc_id: str
) -> tuple[str, str, str, list[float] | None, str]:
    corte = re.search(r"^##\s", texto, re.MULTILINE)
    cabecera = texto[: corte.start()] if corte else texto
    cuerpo = texto[corte.start() :] if corte else ""

    lineas = cabecera.splitlines()
    titulo_h1 = next((ln[1:].strip() for ln in lineas if ln.startswith("#")), "")
    m_fecha = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", titulo_h1)
    if m_fecha and m_fecha.group(1) != "0000-00-00":
        fecha = m_fecha.group(1)
    else:
        m_doc = re.search(r"(20\d{2}-\d{2}-\d{2})", doc_id)
        fecha = m_doc.group(1) if m_doc else ""

    parcial = ""
    partes_h1 = [p.strip() for p in titulo_h1.split(" - ")]
    if len(partes_h1) >= 2 and re.match(r"^(?:P[1-9]\d*|final)$", partes_h1[1], re.I):
        val = partes_h1[1]
        parcial = "final" if val.lower() == "final" else val.upper()
    elif m_par := re.match(r"^(P[1-9]\d*)(?:_|$)", doc_id, re.I):
        parcial = m_par.group(1).upper()

    tipo = "otro"
    calificaciones: list[float] | None = None
    for ln in lineas:
        if ln.startswith("#") or ":" not in ln:
            continue
        clave, valor = ln.split(":", maxsplit=1)
        clave_n = clave.strip().lower()
        if clave_n == "tipo":
            tipo = valor.strip().lower() or "otro"
        elif clave_n == "calificacion_alumno":
            calificaciones = _limpiar_calificaciones(valor)

    return tipo, fecha, parcial, calificaciones, cuerpo


def _bloques_h2(cuerpo: str, patron: str) -> list[tuple[re.Match[str], str]]:
    cabeceras = list(re.finditer(patron, cuerpo, re.MULTILINE))
    bloques: list[tuple[re.Match[str], str]] = []
    for idx, m in enumerate(cabeceras):
        fin = cabeceras[idx + 1].start() if idx + 1 < len(cabeceras) else len(cuerpo)
        bloques.append((m, cuerpo[m.end() : fin]))
    return bloques


def _partir_incisos(cuerpo: str) -> tuple[str, list[tuple[str, str]]]:
    cabeceras = list(re.finditer(_PATRON_INCISO, cuerpo, re.MULTILINE | re.IGNORECASE))
    if not cabeceras:
        return cuerpo.strip(), []
    comun = cuerpo[: cabeceras[0].start()].strip()
    incisos: list[tuple[str, str]] = []
    for idx, m in enumerate(cabeceras):
        fin = cabeceras[idx + 1].start() if idx + 1 < len(cabeceras) else len(cuerpo)
        incisos.append((m.group(1).lower(), cuerpo[m.end() : fin].strip()))
    return comun, incisos


def segmentar_documento(ruta: Path) -> list[Item]:
    """Segmenta un archivo `02_texto/<doc>.md` según la regla del paso 3."""
    texto = ruta.read_text(encoding="utf-8")
    doc_id = ruta.stem
    tipo, fecha, parcial, calificaciones, cuerpo = _parsear_cabecera(texto, doc_id)
    items: list[Item] = []

    if tipo == "examen":
        bloques = _bloques_h2(cuerpo, _PATRON_PREGUNTA)
        if calificaciones is not None and len(calificaciones) != len(bloques):
            raise ValueError(
                f"{ruta.name}: calificacion_alumno tiene {len(calificaciones)} valores "
                f"pero hay {len(bloques)} preguntas"
            )
        for idx, (m, bloque) in enumerate(bloques):
            n = m.group(1)
            pts_max = float(m.group(2)) if m.group(2) else None
            pts_obt = calificaciones[idx] if calificaciones is not None else None
            preg_id = f"{doc_id}:Q{n}"
            items.append(
                Item(
                    id=preg_id,
                    documento_id=doc_id,
                    tipo_doc="examen",
                    numero=n,
                    texto=bloque.strip(),
                    padre_id="",
                    fecha=fecha,
                    parcial=parcial,
                    puntos_max=pts_max,
                    puntos_obtenidos=pts_obt,
                )
            )
            _, incisos = _partir_incisos(bloque)
            for inc_id, inc_texto in incisos:
                items.append(
                    Item(
                        id=f"{preg_id}{inc_id}",
                        documento_id=doc_id,
                        tipo_doc="examen",
                        numero=f"{n}{inc_id}",
                        texto=inc_texto,
                        padre_id=preg_id,
                        fecha=fecha,
                        parcial=parcial,
                    )
                )
        return items

    if tipo == "tarea":
        for m, bloque in _bloques_h2(cuerpo, _PATRON_EJERCICIO):
            n = m.group(1)
            comun, incisos = _partir_incisos(bloque)
            if incisos:
                for inc_id, inc_texto in incisos:
                    texto_inc = f"{comun}\n{inc_texto}".strip() if comun else inc_texto
                    items.append(
                        Item(
                            id=f"{doc_id}:{n}{inc_id}",
                            documento_id=doc_id,
                            tipo_doc="tarea",
                            numero=f"{n}{inc_id}",
                            texto=texto_inc,
                            padre_id="",
                            fecha=fecha,
                            parcial=parcial,
                        )
                    )
            else:
                items.append(
                    Item(
                        id=f"{doc_id}:{n}",
                        documento_id=doc_id,
                        tipo_doc="tarea",
                        numero=n,
                        texto=bloque.strip(),
                        padre_id="",
                        fecha=fecha,
                        parcial=parcial,
                    )
                )
        return items

    for idx, (m, bloque) in enumerate(_bloques_h2(cuerpo, _PATRON_SECCION)):
        titulo = m.group(1).strip()
        m_num = re.match(r"^(?:Tema|Secci[oó]n)\s+(\d+)\b", titulo, re.IGNORECASE)
        if not m_num:
            m_num = re.match(r"^(\d+)[\.:]\s", titulo)
        n = m_num.group(1) if m_num else str(idx + 1)
        cuerpo_sec = bloque.strip()
        texto_sec = f"{titulo}\n{cuerpo_sec}" if cuerpo_sec else titulo
        items.append(
            Item(
                id=f"{doc_id}:{n}",
                documento_id=doc_id,
                tipo_doc=tipo,
                numero=n,
                texto=texto_sec,
                padre_id="",
                fecha=fecha,
                parcial=parcial,
            )
        )
    return items


def segmentar_carpeta(materia: str, raiz_trabajo: Path | None = None) -> list[Item]:
    """Segmenta todos los `.md` en `trabajo/<materia>/02_texto/` y escribe `03_items.jsonl`."""
    base = (raiz_trabajo or Path("trabajo")) / materia
    texto_dir = base / "02_texto"
    items: list[Item] = []
    for ruta in sorted(texto_dir.glob("*.md")):
        items.extend(segmentar_documento(ruta))
    escribir_jsonl(base / "03_items.jsonl", items)
    return items
