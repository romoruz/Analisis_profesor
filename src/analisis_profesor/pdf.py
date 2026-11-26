"""Extracción de texto desde PDF con cadena de respaldos sin dependencias obligatorias."""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TextoPDF:
    """Resultado de extraer texto de un PDF por página."""

    paginas: list[str]
    metodo: str

    @property
    def texto(self) -> str:
        """Texto completo uniendo páginas no vacías."""
        return "\n\n".join(p.strip() for p in self.paginas if p.strip())

    @property
    def chars_por_pagina(self) -> float:
        """Promedio de caracteres útiles por página."""
        if not self.paginas:
            return 0.0
        return sum(len(p.strip()) for p in self.paginas) / len(self.paginas)


def _con_fitz(ruta: Path) -> list[str] | None:
    try:
        import pymupdf as fitz  # PyMuPDF >= 1.24 evita FutureWarning de `import fitz`
    except ImportError:
        try:
            import fitz
        except ImportError:
            return None
    try:
        with fitz.open(ruta) as doc:
            return [pagina.get_text() or "" for pagina in doc]
    except Exception:
        return None


def _con_pypdf(ruta: Path) -> list[str] | None:
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        lector = PdfReader(str(ruta))
        return [pagina.extract_text() or "" for pagina in lector.pages]
    except Exception:
        return None


def _con_pdfplumber(ruta: Path) -> list[str] | None:
    try:
        import pdfplumber
    except ImportError:
        return None
    try:
        with pdfplumber.open(ruta) as pdf:
            return [pagina.extract_text() or "" for pagina in pdf.pages]
    except Exception:
        return None


def _con_pdftotext(ruta: Path) -> list[str] | None:
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    r = subprocess.run(
        [exe, "-layout", str(ruta), "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if r.returncode != 0:
        return None
    paginas = r.stdout.split("\f")
    if paginas and not paginas[-1].strip():
        paginas = paginas[:-1]
    return paginas


def extraer_pdf(ruta: Path) -> TextoPDF:
    """Extrae texto por página probando fitz -> pypdf -> pdfplumber -> pdftotext -> nada."""
    respaldos = (
        ("pymupdf", _con_fitz),
        ("pypdf", _con_pypdf),
        ("pdfplumber", _con_pdfplumber),
        ("pdftotext", _con_pdftotext),
    )
    for metodo, extractor in respaldos:
        paginas = extractor(ruta)
        if paginas is not None:
            return TextoPDF(paginas=paginas, metodo=metodo)
    return TextoPDF(paginas=[], metodo="")
