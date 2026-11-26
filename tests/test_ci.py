import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SDKS_PROHIBIDOS = frozenset({"openai", "anthropic", "google", "genai", "litellm"})
ARCHIVOS_SOLO_STDLIB = frozenset(
    {
        "ap.py",
        "__init__.py",
        "cli.py",
        "config.py",
        "esquemas.py",
        "etiquetas.py",
        "segmentacion.py",
        "similitud.py",
    }
)


def _paquetes_importados(nodo: ast.stmt | ast.AST) -> list[str]:
    if isinstance(nodo, ast.Import):
        return [alias.name.split(".")[0] for alias in nodo.names]
    if isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
        return [nodo.module.split(".")[0]]
    return []


def test_workflow_ci_define_tres_trabajos():
    ruta = RAIZ / ".github" / "workflows" / "ci.yml"
    assert ruta.is_file(), "Falta .github/workflows/ci.yml"
    contenido = ruta.read_text(encoding="utf-8")

    assert "push:" in contenido
    assert "pull_request:" in contenido

    # (a) Completo en Python 3.11 y 3.12
    assert "completo:" in contenido
    assert '"3.11"' in contenido and '"3.12"' in contenido
    assert ".[dev,completo]" in contenido
    assert "ruff check src tests ap.py" in contenido
    assert "pytest" in contenido

    # (b) Sandbox mínimo: solo numpy y scipy (sin completo)
    assert "sandbox-minimo:" in contenido
    assert "pip install -e ." in contenido
    assert "ap.py diagnostico" in contenido

    # (c) Python puro: sin dependencias instaladas, con python -I
    assert "python-puro:" in contenido
    assert "python -I ap.py diagnostico" in contenido
    assert "python -I ap.py items" in contenido


def test_portabilidad_imports_nivel_modulo():
    archivos = [RAIZ / "ap.py", *sorted((RAIZ / "src" / "analisis_profesor").rglob("*.py"))]
    permitidos_nucleo = sys.stdlib_module_names | {"analisis_profesor", "numpy", "scipy"}
    permitidos_stdlib = sys.stdlib_module_names | {"analisis_profesor"}

    for ruta in archivos:
        arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
        permitidos = permitidos_stdlib if ruta.name in ARCHIVOS_SOLO_STDLIB else permitidos_nucleo

        for sentencia in arbol.body:
            for pkg in _paquetes_importados(sentencia):
                assert pkg in permitidos, (
                    f"{ruta.relative_to(RAIZ)} importa {pkg!r} a nivel módulo "
                    "(solo se permite stdlib, numpy y scipy)"
                )

        for nodo in ast.walk(arbol):
            for pkg in _paquetes_importados(nodo):
                assert pkg not in SDKS_PROHIBIDOS, (
                    f"{ruta.relative_to(RAIZ)} importa SDK de LLM prohibido: {pkg!r}"
                )


def test_python_puro_diagnostico_e_items():
    r_diag = subprocess.run(
        [sys.executable, "-I", "-S", str(RAIZ / "ap.py"), "diagnostico"],
        capture_output=True,
        text=True,
        cwd=RAIZ,
    )
    assert r_diag.returncode == 0, r_diag.stderr
    datos = json.loads(r_diag.stdout.split("\n\n")[0])
    assert datos["modo"] == "reducido"
    assert not any(datos["librerias"].values())

    trabajo_id = RAIZ / "trabajo" / "_test_ci_puro"
    texto_dir = trabajo_id / "02_texto"
    try:
        texto_dir.mkdir(parents=True, exist_ok=True)
        (texto_dir / "examen.md").write_text(
            "# Curso Prueba - P1 - 2026-03-01\n"
            "tipo: examen\n"
            "duracion_min: 90\n\n"
            "## Pregunta 1 (5 puntos)\n"
            "Enunciado de prueba.\n",
            encoding="utf-8",
        )
        r_items = subprocess.run(
            [sys.executable, "-I", "-S", str(RAIZ / "ap.py"), "items", "_test_ci_puro"],
            capture_output=True,
            text=True,
            cwd=RAIZ,
        )
        from analisis_profesor.cli import PENDIENTES

        if "items" in PENDIENTES:
            assert r_items.returncode == 2, r_items.stderr
            assert "PENDIENTE:" in r_items.stdout
            assert r_items.stderr == ""
        else:
            assert r_items.returncode == 0, r_items.stderr
            assert (trabajo_id / "03_items.jsonl").is_file()
    finally:
        shutil.rmtree(trabajo_id, ignore_errors=True)
