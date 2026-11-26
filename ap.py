#!/usr/bin/env python3
"""Punto de entrada sin instalación: `python ap.py <comando>`. Ver PROTOCOLO.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from analisis_profesor.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
