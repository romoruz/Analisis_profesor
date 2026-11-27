"""El PDF es opcional: si pdflatex falla, `armar` conserva .tex/.md y no aborta."""
import os
import stat
from pathlib import Path

from analisis_profesor.salida import compilar_tex_a_pdf


def _pdflatex_falso(carpeta: Path, codigo: int) -> None:
    exe = carpeta / "pdflatex"
    exe.write_text(
        "#!/bin/sh\necho \"! LaTeX Error: File \\`lmodern.sty' not found.\"\n"
        f"touch simulacros.log\nexit {codigo}\n",
        encoding="utf-8",
    )
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)


def test_pdflatex_que_falla_no_aborta(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _pdflatex_falso(bin_dir, 1)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    tex = tmp_path / "simulacros.tex"
    tex.write_text("\\documentclass{article}\\begin{document}x\\end{document}\n")

    res = compilar_tex_a_pdf(tex)

    assert res["pdf_generado"] is False
    assert res["ruta_pdf"] is None
    assert "lmodern.sty" in res["motivo"]
    assert tex.is_file()
    assert not tex.with_suffix(".log").exists()


def test_sin_pdflatex(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    tex = tmp_path / "simulacros.tex"
    tex.write_text("x")
    assert compilar_tex_a_pdf(tex)["motivo"] == "pdflatex no disponible"
