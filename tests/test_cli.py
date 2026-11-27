import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_ap_py_sin_instalar():
    """ap.py debe correr con `python -I` (sin el paquete instalado), como en un sandbox de chat."""
    r = subprocess.run([sys.executable, "-I", str(RAIZ / "ap.py"), "diagnostico"],
                       capture_output=True, text=True, cwd=RAIZ)
    assert r.returncode == 0, r.stderr
    assert "Modo del PROTOCOLO" in r.stdout


def test_pendiente_devuelve_2(capsys):
    from analisis_profesor.cli import PENDIENTES, main

    if PENDIENTES:
        cmd = next(iter(PENDIENTES))
        assert main([cmd, "x"]) == 2
        return

    assert PENDIENTES == {}
    import pytest

    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    ayuda = capsys.readouterr().out
    for sub in (
        "ingesta",
        "items",
        "similitud",
        "acuerdo",
        "dificultad",
        "modelo",
        "verificar",
        "armar",
    ):
        assert sub in ayuda
