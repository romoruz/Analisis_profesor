#!/usr/bin/env bash
# Ejecuta todos los pasos [script] de PROTOCOLO.md sobre trabajo/<id>/.
# Uso:
#   bash scripts/e2e.sh <id> [--zip <ruta.zip>] [--raiz-trabajo <dir>] [--semilla <int>] [--sin-pdf] [--aislado]
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Uso: bash scripts/e2e.sh <id> [--zip <ruta.zip>] [--raiz-trabajo <dir>] [--semilla <int>] [--sin-pdf] [--aislado]" >&2
  exit 2
fi

MATERIA="$1"
shift

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ZIP_PATH=""
RAIZ_TRABAJO="$REPO_ROOT"
SEMILLA="2026"
SIN_PDF=0
AISLADO=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --zip)
      ZIP_PATH="${2:?Falta ruta tras --zip}"
      shift 2
      ;;
    --raiz-trabajo)
      RAIZ_TRABAJO="${2:?Falta directorio tras --raiz-trabajo}"
      shift 2
      ;;
    --semilla)
      SEMILLA="${2:?Falta entero tras --semilla}"
      shift 2
      ;;
    --sin-pdf)
      SIN_PDF=1
      shift
      ;;
    --aislado)
      AISLADO=1
      shift
      ;;
    -h|--help)
      echo "Uso: bash scripts/e2e.sh <id> [--zip <ruta.zip>] [--raiz-trabajo <dir>] [--semilla <int>] [--sin-pdf] [--aislado]"
      exit 0
      ;;
    *)
      echo "Argumento no reconocido: $1" >&2
      exit 2
      ;;
  esac
done

if [ -n "${PYTHON:-}" ]; then
  PY_BIN="$PYTHON"
elif [ -x "$REPO_ROOT/.venv/bin/python" ]; then
  PY_BIN="$REPO_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY_BIN="$(command -v python3)"
else
  PY_BIN="$(command -v python)"
fi

PY_ARGS=()
if [ "$AISLADO" -eq 1 ]; then
  PY_ARGS+=("-I")
fi

AP_PY="$REPO_ROOT/ap.py"

if [ -n "$ZIP_PATH" ]; then
  if [ ! -f "$ZIP_PATH" ]; then
    echo "Error: no existe el archivo zip '$ZIP_PATH'" >&2
    exit 1
  fi
  ZIP_ABS="$(cd "$(dirname "$ZIP_PATH")" && pwd)/$(basename "$ZIP_PATH")"
else
  ZIP_ABS=""
fi

mkdir -p "$RAIZ_TRABAJO"
cd "$RAIZ_TRABAJO"

correr_ap() {
  echo "==> ap.py $*"
  "$PY_BIN" "${PY_ARGS[@]}" "$AP_PY" "$@"
}

correr_ap diagnostico

if [ -n "$ZIP_ABS" ]; then
  correr_ap ingesta "$ZIP_ABS" --materia "$MATERIA"
fi

TRABAJO_MAT="trabajo/$MATERIA"
if [ ! -d "$TRABAJO_MAT" ]; then
  echo "Error: no existe $RAIZ_TRABAJO/$TRABAJO_MAT" >&2
  exit 1
fi

if [ -d "$TRABAJO_MAT/02_texto" ] && compgen -G "$TRABAJO_MAT/02_texto/*.md" >/dev/null; then
  correr_ap items "$MATERIA"
  correr_ap similitud "$MATERIA"
  correr_ap plantilla-etiquetas "$MATERIA"
else
  echo "Aviso: sin archivos .md en $TRABAJO_MAT/02_texto/; se omiten items, similitud y plantilla-etiquetas."
fi

if [ -f "$TRABAJO_MAT/05_etiquetas.csv" ] && [ -f "$TRABAJO_MAT/materia.toml" ]; then
  correr_ap dificultad "$MATERIA" --semilla "$SEMILLA"
  correr_ap modelo "$MATERIA" --semilla "$SEMILLA"
else
  echo "Error: faltan $TRABAJO_MAT/05_etiquetas.csv o $TRABAJO_MAT/materia.toml" >&2
  exit 1
fi

if [ -f "$TRABAJO_MAT/08_banco.md" ]; then
  correr_ap verificar "$MATERIA"
  ARMAR_ARGS=(armar "$MATERIA" --n 5 --semilla "$SEMILLA")
  if [ "$SIN_PDF" -eq 1 ]; then
    ARMAR_ARGS+=(--sin-pdf)
  fi
  correr_ap "${ARMAR_ARGS[@]}"
else
  echo "Aviso: no existe $TRABAJO_MAT/08_banco.md; se omiten verificar y armar."
fi

echo "Pipeline E2E completado en $RAIZ_TRABAJO/$TRABAJO_MAT"
