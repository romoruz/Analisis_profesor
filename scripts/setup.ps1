# Prepara el entorno en Windows (PowerShell). Uso:  .\scripts\setup.ps1 [-Extras "dev,llm"]
param([string]$Extras = "dev,llm")
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (Get-Command uv -ErrorAction SilentlyContinue) {
    if (-not (Test-Path .venv)) { uv venv .venv --python 3.12 }
    uv pip install --python .venv -e ".[$Extras]"
} else {
    if (-not (Test-Path .venv)) { py -3.12 -m venv .venv }
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -e ".[$Extras]"
}

if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m pytest -q
Write-Host "Listo. Activa con: .\.venv\Scripts\Activate.ps1   y prueba: ap --help"
