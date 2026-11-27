"""Generación de entregables finales (`SIMULACROS.md`, `SOLUCIONES.md`, `.tex` y `.pdf`).

Implementa la salida del paso 8 de `PROTOCOLO.md` §8 y la tarea 1.10 de `docs/ROADMAP.md`.
Solo utiliza librería estándar a nivel de módulo.
"""
from __future__ import annotations

import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

from analisis_profesor.banco import EjercicioBanco

_CABECERA_TEX = r"""\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{amsmath,amssymb}
\usepackage[letterpaper,margin=2.3cm]{geometry}
\setlength{\parindent}{0pt}
\pagestyle{plain}
\begin{document}
"""


def _escapar_latex_texto(texto: str) -> str:
    """Escapa caracteres especiales de LaTeX únicamente en metadatos de encabezado."""
    reemplazos = (
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
    )
    out = texto
    for src, dst in reemplazos:
        out = out.replace(src, dst)
    return out


def _formatear_puntos(puntos: float) -> str:
    return f"{puntos:g}"


def generar_markdown_simulacros(
    cfg_materia: Mapping,
    resultado_simulacros: Mapping,
) -> str:
    """Construye el contenido de `entregables/SIMULACROS.md` (sin soluciones)."""
    nombre = str(cfg_materia.get("nombre") or cfg_materia.get("id") or "Curso")
    parcial = str(cfg_materia.get("objetivo", {}).get("parcial", "")).strip()
    encabezado_parcial = f" ({parcial})" if parcial else ""
    lineas = [
        f"# Simulacros — {nombre}{encabezado_parcial}",
        "",
        "Resuelve cada examen completo con cronómetro antes de abrir `SOLUCIONES.md`.",
        "",
    ]
    for ex in resultado_simulacros["examenes"]:
        lineas.extend(
            [
                f"## Simulacro {ex['numero']}",
                "",
                f"- **Tiempo:** {ex['minutos']} minutos",
                f"- **Preguntas:** {len(ex['preguntas'])}",
                "",
            ]
        )
        for idx, q in enumerate(ex["preguntas"], 1):
            pts = _formatear_puntos(float(q.get("puntos", 2.5)))
            lineas.append(f"### Pregunta {idx} ({pts} puntos)")
            lineas.append("")
            lineas.append(str(q["tex"]).strip())
            lineas.append("")
    return "\n".join(lineas).rstrip() + "\n"


def generar_markdown_soluciones(
    cfg_materia: Mapping,
    resultado_simulacros: Mapping,
    ejercicios_por_id: Mapping[str, EjercicioBanco],
) -> str:
    """Construye el contenido separado de `entregables/SOLUCIONES.md`."""
    nombre = str(cfg_materia.get("nombre") or cfg_materia.get("id") or "Curso")
    parcial = str(cfg_materia.get("objetivo", {}).get("parcial", "")).strip()
    encabezado_parcial = f" ({parcial})" if parcial else ""
    lineas = [
        f"# Soluciones de los simulacros — {nombre}{encabezado_parcial}",
        "",
        "> **OJO:** no abras este archivo antes de resolver cada simulacro con cronómetro.",
        "",
        f"Meta de dificultad total: **{resultado_simulacros['meta_dificultad_total']:.2f}**",
        "",
    ]
    for ex in resultado_simulacros["examenes"]:
        lineas.extend(
            [
                f"## Simulacro {ex['numero']} (dificultad total: {ex['dificultad_total']:.2f})",
                "",
            ]
        )
        for idx, q in enumerate(ex["preguntas"], 1):
            ej = ejercicios_por_id.get(q["id"])
            sol_txt = ej.solucion.strip() if ej and ej.solucion.strip() else (
                "*(Sin solución redactada en el banco.)*"
            )
            lineas.extend(
                [
                    (
                        f"### Pregunta {idx} — `{q['id']}` "
                        f"[{q['arq']}, {q['nivel']}, "
                        f"score={q['score']:.2f}/obj={q['objetivo']:.2f}]"
                    ),
                    "",
                    sol_txt,
                    "",
                ]
            )
    return "\n".join(lineas).rstrip() + "\n"


def generar_tex_simulacros(
    cfg_materia: Mapping,
    resultado_simulacros: Mapping,
) -> str:
    """Construye `entregables/simulacros.tex` fiel al formato de `07_pdf_simulacros.py`."""
    nombre = _escapar_latex_texto(
        str(cfg_materia.get("nombre") or cfg_materia.get("id") or "Examen")
    )
    parcial = _escapar_latex_texto(str(cfg_materia.get("objetivo", {}).get("parcial", "")).strip())
    prefijo = f"{parcial} -- " if parcial else ""

    bloques: list[str] = []
    for ex in resultado_simulacros["examenes"]:
        items_tex: list[str] = []
        for q in ex["preguntas"]:
            pts = _formatear_puntos(float(q.get("puntos", 2.5)))
            cuerpo = str(q["tex"]).strip()
            items_tex.append(f"\\item ({pts} puntos) {cuerpo}\n\\vspace{{0.15cm}}\n")
        preguntas_str = "\n".join(items_tex)
        bloque = (
            f"\\textbf{{{nombre}}}\\\\\n"
            f"\\textbf{{{prefijo}Simulacro {ex['numero']}}}\n\n"
            "\\vspace{0.6cm}\n"
            "Nombre: \\underline{\\hspace{9cm}} \\quad Clave: \\underline{\\hspace{3cm}}\n\n"
            "\\vspace{0.5cm}\n"
            "\\begin{center}\n"
            "JUSTIFICA CON DETALLE TUS RESPUESTAS\\\\\n"
            "NO se permiten libros, apuntes, calculadoras, celulares o tabletas\\\\\n"
            f"Tiempo: {ex['minutos']} minutos\n"
            "\\end{center}\n"
            "\\vspace{-0.2cm}\n"
            "\\rule{\\textwidth}{0.4pt}\n"
            "\\vspace{0.2cm}\n\n"
            "\\begin{enumerate}\n"
            f"{preguntas_str}"
            "\\end{enumerate}\n\n"
            "\\vspace{0.5cm}\n"
            "\\begin{center}\n"
            "\\Large Buena suerte!!\n"
            "\\end{center}\n"
        )
        bloques.append(bloque)
    return _CABECERA_TEX + "\n\\newpage\n".join(bloques) + "\n\\end{document}\n"


def compilar_tex_a_pdf(ruta_tex: Path, *, timeout_s: float = 60.0) -> dict:
    """Compila un `.tex` a `.pdf` con `pdflatex` si está instalado."""
    if shutil.which("pdflatex") is None:
        return {"pdf_generado": False, "ruta_pdf": None, "motivo": "pdflatex no disponible"}

    for _ in range(2):
        proc = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", ruta_tex.name],
            cwd=ruta_tex.parent,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        if proc.returncode != 0:
            detalle = (proc.stdout or proc.stderr)[-2000:]
            raise RuntimeError(f"pdflatex falló en {ruta_tex}:\n{detalle}")

    for ext in (".aux", ".log"):
        aux = ruta_tex.with_suffix(ext)
        if aux.exists():
            aux.unlink()
    ruta_pdf = ruta_tex.with_suffix(".pdf")
    return {"pdf_generado": ruta_pdf.is_file(), "ruta_pdf": str(ruta_pdf), "motivo": "ok"}


def escribir_entregables(
    cfg_materia: Mapping,
    resultado_simulacros: Mapping,
    ejercicios_por_id: Mapping[str, EjercicioBanco],
    ruta_entregables: Path,
    *,
    compilar_pdf: bool = True,
) -> dict:
    """Escribe `SIMULACROS.md`, `SOLUCIONES.md`, `simulacros.tex` y opcionalmente `.pdf`."""
    ruta_entregables.mkdir(parents=True, exist_ok=True)
    ruta_sim = ruta_entregables / "SIMULACROS.md"
    ruta_sol = ruta_entregables / "SOLUCIONES.md"
    ruta_tex = ruta_entregables / "simulacros.tex"

    ruta_sim.write_text(
        generar_markdown_simulacros(cfg_materia, resultado_simulacros), encoding="utf-8"
    )
    ruta_sol.write_text(
        generar_markdown_soluciones(cfg_materia, resultado_simulacros, ejercicios_por_id),
        encoding="utf-8",
    )
    ruta_tex.write_text(
        generar_tex_simulacros(cfg_materia, resultado_simulacros), encoding="utf-8"
    )

    info_pdf = (
        compilar_tex_a_pdf(ruta_tex)
        if compilar_pdf
        else {"pdf_generado": False, "ruta_pdf": None, "motivo": "omitido"}
    )
    return {
        "simulacros_md": str(ruta_sim),
        "soluciones_md": str(ruta_sol),
        "simulacros_tex": str(ruta_tex),
        **info_pdf,
    }


__all__ = [
    "compilar_tex_a_pdf",
    "escribir_entregables",
    "generar_markdown_simulacros",
    "generar_markdown_soluciones",
    "generar_tex_simulacros",
]
