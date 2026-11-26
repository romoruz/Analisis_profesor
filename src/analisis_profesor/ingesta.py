"""Paso 1 del protocolo: ingesta de .zip, inventario y extracción inicial de texto."""
from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
import zipfile
from collections.abc import Iterable
from dataclasses import asdict, fields
from pathlib import Path, PurePosixPath

from analisis_profesor.esquemas import Documento
from analisis_profesor.pdf import extraer_pdf

EXTENSIONES_IMAGEN = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp", ".gif", ".heic"}
)
NOMBRES_IGNORADOS = frozenset({".DS_Store", "Thumbs.db", "desktop.ini", ".gitkeep"})
MIN_CHARS_POR_PAGINA = 200

MESES_ES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

_REGLAS_TIPO_RUTA: tuple[tuple[str, str, str | None], ...] = (
    ("pauta", r"(?:^|[^a-z0-9])(pauta|solucion(?:es|ario)?|resuelto)(?:[^a-z0-9]|$)", None),
    ("temario", r"(?:^|[^a-z0-9])(temario|syllabus|programa|calendario)(?:[^a-z0-9]|$)", None),
    (
        "examen",
        r"(?:^|[^a-z0-9])(examen(?:es)?|parcial(?:es)?|prueba(?:s)?|ordinario|extraordinario|final|quiz)(?:[^a-z0-9]|$)",
        r"^p[1-9](?:[^a-z0-9]|$)",
    ),
    (
        "tarea",
        r"(?:^|[^a-z0-9])(tarea(?:s)?|problemario|practica(?:s)?|hoja|serie|ejercicios)(?:[^a-z0-9]|$)",
        r"^t[1-9]\d*(?:[^a-z0-9]|$)",
    ),
    (
        "clase",
        r"(?:^|[^a-z0-9])(clase(?:s)?|lamina(?:s)?|presentacion(?:es)?|diapositiva(?:s)?|slides?)(?:[^a-z0-9]|$)",
        r"^c[1-9]\d*(?:[^a-z0-9]|$)",
    ),
    ("notas", r"(?:^|[^a-z0-9])(nota(?:s)?|apunte(?:s)?|resumen|formulario)(?:[^a-z0-9]|$)", None),
)

_REGLAS_TIPO_TEXTO: tuple[tuple[str, str], ...] = (
    ("pauta", r"(?:^|[^a-z0-9])(pauta|solucionario)(?:[^a-z0-9]|$)"),
    ("temario", r"(?:^|[^a-z0-9])(temario|bibliografia|syllabus)(?:[^a-z0-9]|$)"),
    (
        "examen",
        r"(?:^|[^a-z0-9])(examen\s+(?:parcial|final)|(?:primer|segundo|tercer)\s+parcial|pregunta\s+1)(?:[^a-z0-9]|$)",
    ),
    ("tarea", r"(?:^|[^a-z0-9])(tarea\s+\d+|problemario)(?:[^a-z0-9]|$)"),
    ("clase", r"(?:^|[^a-z0-9])(clase\s+\d+|diapositiva)(?:[^a-z0-9]|$)"),
    ("notas", r"(?:^|[^a-z0-9])(apuntes|notas\s+de\s+clase)(?:[^a-z0-9]|$)"),
)


def _sin_acentos(texto: str) -> str:
    norm = unicodedata.normalize("NFKD", texto)
    return "".join(ch for ch in norm if not unicodedata.combining(ch)).lower()


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        while bloque := f.read(65536):
            h.update(bloque)
    return h.hexdigest()


def _descomprimir_seguro(ruta_zip: Path, destino: Path) -> list[Path]:
    """Descomprime `ruta_zip` en `destino` validando zip-slip y filtrando archivos basura."""
    destino_abs = destino.resolve()
    rutas: list[Path] = []
    with zipfile.ZipFile(ruta_zip) as zf:
        for info in zf.infolist():
            objetivo = (destino_abs / info.filename).resolve()
            if not objetivo.is_relative_to(destino_abs):
                raise ValueError(f"Entrada peligrosa en zip: {info.filename!r}")
            if info.is_dir():
                continue
            partes = PurePosixPath(info.filename).parts
            if not partes or "__MACOSX" in partes:
                continue
            nombre = partes[-1]
            if nombre in NOMBRES_IGNORADOS or nombre.startswith("._"):
                continue
            rel = Path(*partes)
            salida = destino_abs / rel
            salida.parent.mkdir(parents=True, exist_ok=True)
            salida.write_bytes(zf.read(info))
            rutas.append(rel)
    return sorted(rutas, key=lambda p: p.as_posix())


def adivinar_tipo(ruta_rel: str, texto: str = "") -> str:
    """Clasifica un documento por ruta/nombre y, si no decide, por los primeros caracteres."""
    ruta_norm = _sin_acentos(ruta_rel)
    stem_norm = _sin_acentos(Path(ruta_rel).stem)
    for tipo, patron_ruta, patron_stem in _REGLAS_TIPO_RUTA:
        if re.search(patron_ruta, ruta_norm):
            return tipo
        if patron_stem and re.search(patron_stem, stem_norm):
            return tipo
    if texto:
        muestra = _sin_acentos(texto[:1500])
        for tipo, patron in _REGLAS_TIPO_TEXTO:
            if re.search(patron, muestra):
                return tipo
    return "otro"


def _fecha_en_texto(texto: str) -> str:
    m = re.search(r"(20\d{2})[-_](\d{2})[-_](\d{2})", texto)
    if m:
        anio, mes, dia = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mes <= 12 and 1 <= dia <= 31:
            return f"{anio:04d}-{mes:02d}-{dia:02d}"
    m = re.search(r"(?:^|[^\d])(\d{1,2})[-/](\d{1,2})[-/](20\d{2})(?:[^\d]|$)", texto)
    if m:
        dia, mes, anio = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mes <= 12 and 1 <= dia <= 31:
            return f"{anio:04d}-{mes:02d}-{dia:02d}"
    meses = "|".join(MESES_ES)
    m = re.search(rf"(\d{{1,2}})\s+de\s+({meses})\s+de(?:l)?\s+(20\d{{2}})", _sin_acentos(texto))
    if m:
        dia, mes, anio = int(m.group(1)), MESES_ES[m.group(2)], int(m.group(3))
        if 1 <= dia <= 31:
            return f"{anio:04d}-{mes:02d}-{dia:02d}"
    return ""


def adivinar_fecha(ruta_rel: str, texto: str = "") -> str:
    """Extrae una fecha AAAA-MM-DD de la ruta o del encabezado del texto."""
    return _fecha_en_texto(ruta_rel) or _fecha_en_texto(texto[:1500])


def _parcial_en_texto(texto: str) -> str:
    norm = _sin_acentos(texto)
    for patron in (
        r"(?:^|[^a-z0-9])p([1-9])(?:[^a-z0-9]|$)",
        r"(?:parcial|prueba)\s*[_-]?\s*([1-9])(?:[^a-z0-9]|$)",
    ):
        m = re.search(patron, norm)
        if m:
            return f"P{m.group(1)}"
    ordinales = (
        (r"(?:primer|1er)\s+parcial", "P1"),
        (r"(?:segundo|2do)\s+parcial", "P2"),
        (r"(?:tercer|3er)\s+parcial", "P3"),
    )
    for patron, etiqueta in ordinales:
        if re.search(patron, norm):
            return etiqueta
    if re.search(r"(?:^|[^a-z0-9])(final|ordinario|extraordinario)(?:[^a-z0-9]|$)", norm):
        return "final"
    return ""


def adivinar_parcial(ruta_rel: str, texto: str = "") -> str:
    """Deduce el parcial (P1, P2, final) de la ruta o del inicio del texto."""
    return _parcial_en_texto(ruta_rel) or _parcial_en_texto(texto[:1500])


def _id_unico(stem: str, usados: set[str]) -> str:
    limpio = re.sub(r"\s+", "_", stem.strip())
    limpio = re.sub(r"[^A-Za-z0-9._-]", "_", limpio).strip("_-") or "doc"
    candidato = limpio
    sufijo = 2
    while candidato in usados:
        candidato = f"{limpio}_{sufijo}"
        sufijo += 1
    usados.add(candidato)
    return candidato


def escribir_inventario(ruta: Path, documentos: Iterable[Documento]) -> int:
    """Escribe `01_inventario.csv` con las columnas del contrato `Documento`."""
    columnas = [f.name for f in fields(Documento)]
    n = 0
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas)
        escritor.writeheader()
        for doc in documentos:
            escritor.writerow(asdict(doc))
            n += 1
    return n


def leer_inventario(ruta: Path) -> list[Documento]:
    """Lee `01_inventario.csv` devolviendo objetos `Documento`."""
    docs: list[Documento] = []
    with open(ruta, encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            nec = str(fila.get("necesita_transcripcion", "")).strip().lower() in (
                "true",
                "1",
                "si",
                "sí",
            )
            docs.append(
                Documento(
                    id=fila["id"],
                    archivo=fila["archivo"],
                    tipo=fila.get("tipo", "otro"),
                    fecha=fila.get("fecha", ""),
                    parcial=fila.get("parcial", ""),
                    metodo_texto=fila.get("metodo_texto", ""),
                    necesita_transcripcion=nec,
                    sha256=fila.get("sha256", ""),
                    notas=fila.get("notas", ""),
                )
            )
    return docs


def ingestar(
    ruta_zip: Path, materia: str, raiz_trabajo: Path | None = None
) -> list[Documento]:
    """Ejecuta el paso 1 sobre `ruta_zip` creando la carpeta `trabajo/<materia>/`."""
    base = (raiz_trabajo or Path("trabajo")) / materia
    crudo_dir = base / "00_crudo"
    texto_dir = base / "02_texto"
    crudo_dir.mkdir(parents=True, exist_ok=True)
    texto_dir.mkdir(parents=True, exist_ok=True)

    relativos = _descomprimir_seguro(ruta_zip, crudo_dir)
    docs: list[Documento] = []
    usados_id: set[str] = set()
    vistos_hash: dict[str, str] = {}

    for rel in relativos:
        abs_ruta = crudo_dir / rel
        rel_posix = rel.as_posix()
        doc_id = _id_unico(rel.stem, usados_id)
        digest = _sha256(abs_ruta)
        notas = f"duplicado de {vistos_hash[digest]}" if digest in vistos_hash else ""
        vistos_hash.setdefault(digest, doc_id)

        ext = rel.suffix.lower()
        es_pdf = ext == ".pdf"
        es_texto = ext in {".txt", ".md"}
        es_imagen = ext in EXTENSIONES_IMAGEN

        if es_pdf:
            res_pdf = extraer_pdf(abs_ruta)
            metodo = res_pdf.metodo
            texto = res_pdf.texto
            poco_texto = res_pdf.chars_por_pagina < MIN_CHARS_POR_PAGINA
        elif es_texto:
            texto = abs_ruta.read_text(encoding="utf-8", errors="replace")
            metodo = "texto"
            poco_texto = False
        else:
            texto = ""
            metodo = ""
            poco_texto = True

        tipo = adivinar_tipo(rel_posix, texto)
        fecha = adivinar_fecha(rel_posix, texto)
        parcial = adivinar_parcial(rel_posix, texto)
        necesita = es_imagen or (es_pdf and poco_texto) or (tipo == "examen") or not (
            es_pdf or es_texto
        )

        if ((es_pdf and not poco_texto) or es_texto) and texto.strip():
            etiqueta_parcial = parcial or doc_id
            etiqueta_fecha = fecha or "0000-00-00"
            cabecera = f"# {materia} - {etiqueta_parcial} - {etiqueta_fecha}\ntipo: {tipo}\n\n"
            (texto_dir / f"{doc_id}.md").write_text(
                cabecera + texto.strip() + "\n", encoding="utf-8"
            )

        docs.append(
            Documento(
                id=doc_id,
                archivo=rel_posix,
                tipo=tipo,
                fecha=fecha,
                parcial=parcial,
                metodo_texto=metodo,
                necesita_transcripcion=necesita,
                sha256=digest,
                notas=notas,
            )
        )

    escribir_inventario(base / "01_inventario.csv", docs)
    pendientes = [d.archivo for d in docs if d.necesita_transcripcion]
    contenido_pend = ("\n".join(pendientes) + "\n") if pendientes else ""
    (base / "pendientes_transcripcion.txt").write_text(contenido_pend, encoding="utf-8")
    return docs
