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


def test_pendiente_devuelve_2():
    from analisis_profesor.cli import main
    assert main(["ingesta", "x.zip"]) == 2
