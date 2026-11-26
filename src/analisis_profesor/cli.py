"""CLI de `ap.py`. Un subcomando por paso [script] de PROTOCOLO.md. Solo librería estándar aquí.

Los subcomandos PENDIENTE los implementa el agente de código según docs/ROADMAP.md.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import sys
from pathlib import Path

from analisis_profesor import __version__

PENDIENTES = {
    "items": ("Fase 1", "02_texto/*.md -> 03_items.jsonl"),
    "similitud": ("Fase 1", "03_items.jsonl -> 04_similitud.json"),
    "plantilla-etiquetas": ("Fase 1", "-> 05_etiquetas.csv con una fila por ítem"),
    "acuerdo": ("Fase 3", "consistencia entre las dos pasadas de etiquetado"),
    "dificultad": ("Fase 1", "-> 06_dificultad.json"),
    "modelo": ("Fase 1", "-> 07_modelo.json"),
    "verificar": ("Fase 1", "ejecuta los bloques `verificacion` de 08_banco.md"),
    "armar": ("Fase 1", "-> entregables/SIMULACROS.md, SOLUCIONES.md, simulacros.tex"),
}

LIBRERIAS = {  # nombre de import: para qué sirve
    "numpy": "obligatoria para el modo completo",
    "scipy": "obligatoria para el modo completo (pruebas, bootstrap)",
    "sklearn": "opcional: TF-IDF rápido (si falta, versión en Python puro)",
    "sympy": "opcional: verificación simbólica y similitud de fórmulas",
    "fitz": "opcional: texto de PDF con PyMuPDF",
    "pypdf": "opcional: texto de PDF (alternativa)",
    "pdfplumber": "opcional: texto de PDF (alternativa)",
}


def diagnostico() -> dict:
    libs = {n: importlib.util.find_spec(n) is not None for n in LIBRERIAS}
    pdf = [n for n in ("fitz", "pypdf", "pdfplumber") if libs[n]]
    herramientas = {h: shutil.which(h) is not None for h in ("pdftotext", "pdflatex")}
    modo = "completo" if libs["numpy"] and libs["scipy"] else "reducido"
    return {
        "version_kit": __version__,
        "python": platform.python_version(),
        "python_ok": sys.version_info >= (3, 10),
        "librerias": libs,
        "herramientas": herramientas,
        "lector_pdf": pdf[0] if pdf else ("pdftotext" if herramientas["pdftotext"] else None),
        "modo": modo,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ap.py", description="Kit de análisis de profesor")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version")
    sub.add_parser("diagnostico", help="qué modo del PROTOCOLO se puede usar aquí")
    s_ingesta = sub.add_parser(
        "ingesta", help="zip -> 00_crudo, 01_inventario.csv, 02_texto/, pendientes"
    )
    s_ingesta.add_argument("zip", help="ruta al archivo .zip con el material")
    s_ingesta.add_argument("--materia", "-m", default="", help="id corto para trabajo/<id>/")
    for nombre, (_fase, ayuda) in PENDIENTES.items():
        s = sub.add_parser(nombre, help=ayuda)
        s.add_argument("args", nargs="*")
    a = p.parse_args(argv)

    if a.cmd == "version":
        print(__version__)
        return 0
    if a.cmd == "diagnostico":
        d = diagnostico()
        print(json.dumps(d, indent=2, ensure_ascii=False))
        print(f"\nModo del PROTOCOLO: {d['modo'].upper()}")
        if not d["lector_pdf"]:
            print("Sin lector de PDF: transcribe los PDFs mirándolos (paso 2).")
        return 0
    if a.cmd == "ingesta":
        ruta_zip = Path(a.zip)
        if not ruta_zip.is_file():
            print(f"Error: no existe el archivo {ruta_zip}", file=sys.stderr)
            return 1
        materia = a.materia or ruta_zip.stem
        from analisis_profesor.ingesta import ingestar

        docs = ingestar(ruta_zip, materia)
        n_pend = sum(1 for d in docs if d.necesita_transcripcion)
        print(f"Ingesta completa en trabajo/{materia}/: {len(docs)} archivos, {n_pend} pendientes.")
        return 0
    fase, _ = PENDIENTES[a.cmd]
    print(f"PENDIENTE: `{a.cmd}` se implementa en la {fase} (docs/ROADMAP.md). "
          "Mientras tanto, haz este paso a mano según el Anexo C de PROTOCOLO.md.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
