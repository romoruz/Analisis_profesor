"""CLI `ap`. Cada subcomando corresponde a una fase del docs/ROADMAP.md.

Los subcomandos marcados PENDIENTE los implementa el agente de código en su fase.
"""
from pathlib import Path

import typer

from analisis_profesor import __version__

app = typer.Typer(
    help="Análisis de profesor: ingesta -> reciclaje -> dificultad -> modelo -> simulacros"
)


def _pendiente(fase: str) -> None:
    typer.echo(f"PENDIENTE: se implementa en la {fase} (ver docs/ROADMAP.md)")
    raise typer.Exit(code=2)


@app.command()
def version() -> None:
    """Muestra la versión."""
    typer.echo(__version__)


@app.command()
def nueva(materia: str) -> None:
    """Crea materias/<materia> a partir de materias/_plantilla."""
    _pendiente("Fase 0")


@app.command()
def ingesta(materia: str, zip_path: Path = typer.Option(None, "--zip")) -> None:
    """Descomprime el .zip, inventaría, extrae texto/LaTeX y segmenta en ítems."""
    _pendiente("Fase 1")


@app.command()
def reciclaje(materia: str) -> None:
    """Similitud léxica + semántica + de fórmulas, con línea base nula."""
    _pendiente("Fase 2")


@app.command()
def etiquetar(materia: str) -> None:
    """Arquetipos, rasgos de dificultad, Bloom/DOK (LLM + revisión humana)."""
    _pendiente("Fases 3-4")


@app.command()
def dificultad(materia: str) -> None:
    """Score de dificultad, comparación tarea vs examen con pruebas e intervalos."""
    _pendiente("Fase 4")


@app.command()
def modelo(materia: str, parcial: str) -> None:
    """Probabilidad por arquetipo + backtesting."""
    _pendiente("Fase 5")


@app.command()
def simulacros(materia: str, parcial: str, n: int = 5) -> None:
    """Genera, verifica y arma n simulacros (LaTeX/PDF)."""
    _pendiente("Fase 6")


@app.command()
def todo(materia: str, parcial: str) -> None:
    """Corre todas las fases en orden."""
    _pendiente("Fase 7")


if __name__ == "__main__":
    app()
