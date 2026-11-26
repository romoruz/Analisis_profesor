#!/usr/bin/env bash
# Entorno local (Linux/macOS) para desarrollar el kit. Uso:  bash scripts/setup.sh [extras]
#   por defecto: dev,completo        con embeddings: bash scripts/setup.sh dev,completo,nlp
set -euo pipefail
EXTRAS="${1:-dev,completo}"
cd "$(dirname "$0")/.."
if command -v uv >/dev/null 2>&1; then
  [ -d .venv ] || uv venv .venv --python 3.12
  uv pip install --python .venv -e ".[${EXTRAS}]"
else
  [ -d .venv ] || python3 -m venv .venv
  .venv/bin/python -m pip install -e ".[${EXTRAS}]"
fi
.venv/bin/python -m pytest -q
.venv/bin/python ap.py diagnostico | tail -1
echo "Listo. Activa con: source .venv/bin/activate"
