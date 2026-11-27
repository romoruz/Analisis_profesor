#!/usr/bin/env bash
# Arma dist/kit_analisis_profesor.zip: lo mínimo que una IA de chat necesita para seguir
# PROTOCOLO.md. NO incluye legacy/ ni tests/ (traen resultados reales que contaminarían una
# prueba a ciegas) ni nada de entrada/ o trabajo/.
set -euo pipefail
cd "$(dirname "$0")/.."
SALIDA="dist/kit_analisis_profesor.zip"
mkdir -p dist
rm -f "$SALIDA"
git archive --format=zip --prefix=kit_analisis_profesor/ -o "$SALIDA" HEAD \
  PROTOCOLO.md README.md ap.py pyproject.toml src plantillas materias
python3 - "$SALIDA" <<'PY'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
malos = [n for n in z.namelist() if "/legacy/" in n or "/tests/" in n or "/entrada/" in n]
assert not malos, malos
print(f"{sys.argv[1]}: {len(z.namelist())} archivos, sin legacy/tests/entrada")
PY
