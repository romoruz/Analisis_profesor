#!/bin/sh
# Corre el pipeline completo de SD-II en orden. Desde esta carpeta: sh correr_todo.sh
set -e
cd "$(dirname "$0")/src"
python3 01_extraer_textos.py
python3 02_similitud.py
python3 03_dificultad.py
python3 04_modelo_parcial3.py 5
python3 06_verificar.py > /dev/null      # escribe salidas/verificacion.txt (OJO: soluciones)
python3 05_armar_simulacros.py
python3 07_pdf_simulacros.py
