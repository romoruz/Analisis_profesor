#!/usr/bin/env bash
# Prepara el entorno en Linux/macOS. Uso:  bash scripts/setup.sh [extras]
#   extras por defecto: dev,llm      ejemplo completo: bash scripts/setup.sh dev,llm,nlp,bayes
set -euo pipefail
EXTRAS="${1:-dev,llm}"
cd "$(dirname "$0")/.."

if command -v uv >/dev/null 2>&1; then
  [ -d .venv ] || uv venv .venv --python 3.12
  uv pip install --python .venv -e ".[${EXTRAS}]"
else
  [ -d .venv ] || python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -e ".[${EXTRAS}]"
fi

[ -f .env ] || cp .env.example .env
.venv/bin/python -m pytest -q
echo "Listo. Activa con: source .venv/bin/activate   y prueba: ap --help"
