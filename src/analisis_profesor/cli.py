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
from collections import Counter
from pathlib import Path

from analisis_profesor import __version__

PENDIENTES = {
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
    s_items = sub.add_parser("items", help="02_texto/*.md -> 03_items.jsonl")
    s_items.add_argument("materia", help="id de la materia en trabajo/<id>/")
    s_sim = sub.add_parser("similitud", help="03_items.jsonl -> 04_similitud.json")
    s_sim.add_argument("materia", help="id de la materia en trabajo/<id>/")
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
    if a.cmd == "items":
        texto_dir = Path("trabajo") / a.materia / "02_texto"
        if not texto_dir.is_dir():
            print(f"Error: no existe {texto_dir}", file=sys.stderr)
            return 1
        from analisis_profesor.segmentacion import segmentar_carpeta

        items = segmentar_carpeta(a.materia)
        etiquetables = [it for it in items if not it.padre_id]
        hijos = [it for it in items if it.padre_id]
        conteo_etiq = Counter(it.documento_id for it in etiquetables)
        conteo_hijos = Counter(it.documento_id for it in hijos)
        for doc_id, n in conteo_etiq.items():
            extra = f" (+{conteo_hijos[doc_id]} incisos)" if conteo_hijos[doc_id] else ""
            print(f"  {doc_id}: {n} ítems{extra}")
        print(
            f"Total: {len(etiquetables)} ítems etiquetables en trabajo/{a.materia}/03_items.jsonl"
        )
        return 0
    if a.cmd == "similitud":
        ruta_items = Path("trabajo") / a.materia / "03_items.jsonl"
        if not ruta_items.is_file():
            print(f"Error: no existe {ruta_items}", file=sys.stderr)
            return 1
        from analisis_profesor.similitud import calcular_similitud

        res = calcular_similitud(a.materia)
        lb = res["linea_base"]
        print(
            f"Línea base material (n_pares={lb['n_pares']}): "
            f"media={lb['media']:.3f}, p95={lb['p95']:.3f}"
        )
        for qid, entrada in res["preguntas_examen"].items():
            cand, sim = entrada["mas_parecidos"][0] if entrada["mas_parecidos"] else ("-", 0.0)
            print(f"  {qid} -> {cand} ({sim:.3f}) [{entrada['clasificacion']}]")
        return 0
    fase, _ = PENDIENTES[a.cmd]
    print(f"PENDIENTE: `{a.cmd}` se implementa en la {fase} (docs/ROADMAP.md). "
          "Mientras tanto, haz este paso a mano según el Anexo C de PROTOCOLO.md.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
