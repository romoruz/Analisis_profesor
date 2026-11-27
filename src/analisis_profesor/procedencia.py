"""Verificación de procedencia (hashes sha256) entre entradas y salidas JSON."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

SALIDAS_CON_PROCEDENCIA: tuple[str, ...] = (
    "04_similitud.json",
    "06_dificultad.json",
    "07_modelo.json",
    "simulacros.json",
)


def sha256_archivo(ruta: Path) -> str:
    """Calcula el resumen SHA-256 hexadecimal de un archivo leyendo por bloques."""
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def construir_procedencia(base_dir: Path, entradas: Sequence[str]) -> dict[str, dict[str, str]]:
    """Registra los hashes SHA-256 actuales de las entradas existentes en `base_dir`."""
    hashes: dict[str, str] = {}
    for nombre in entradas:
        ruta = base_dir / nombre
        if ruta.is_file():
            hashes[nombre] = sha256_archivo(ruta)
    return {"entradas_sha256": hashes}


def verificar_procedencia_trabajo(
    base_dir: Path,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Comprueba si alguna salida JSON quedó desfasada respecto a sus entradas registradas."""
    desfasadas: list[dict[str, Any]] = []
    avisos: list[str] = []
    errores: list[str] = []

    for nombre_salida in SALIDAS_CON_PROCEDENCIA:
        ruta_salida = base_dir / nombre_salida
        if not ruta_salida.is_file():
            continue
        try:
            datos = json.loads(ruta_salida.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errores.append(f"No se pudo leer {nombre_salida} al verificar procedencia: {exc}.")
            continue

        proc = datos.get("procedencia") if isinstance(datos, dict) else None
        hashes = proc.get("entradas_sha256") if isinstance(proc, dict) else None
        if not isinstance(hashes, dict) or not hashes:
            avisos.append(f"{nombre_salida} no incluye registro de procedencia.")
            continue

        for nombre_ent, sha_reg in hashes.items():
            ruta_ent = base_dir / nombre_ent
            if not ruta_ent.is_file():
                desfasadas.append(
                    {
                        "salida": nombre_salida,
                        "entrada": nombre_ent,
                        "motivo": "faltante",
                        "sha256_registrado": sha_reg,
                        "sha256_actual": None,
                    }
                )
                errores.append(
                    f"Salida desfasada {nombre_salida}: falta la entrada {nombre_ent}."
                )
                continue
            sha_act = sha256_archivo(ruta_ent)
            if sha_act != sha_reg:
                desfasadas.append(
                    {
                        "salida": nombre_salida,
                        "entrada": nombre_ent,
                        "motivo": "modificada",
                        "sha256_registrado": sha_reg,
                        "sha256_actual": sha_act,
                    }
                )
                errores.append(
                    f"Salida desfasada {nombre_salida}: la entrada {nombre_ent} cambió "
                    "después de generarla."
                )

    return desfasadas, avisos, errores


__all__ = [
    "SALIDAS_CON_PROCEDENCIA",
    "construir_procedencia",
    "sha256_archivo",
    "verificar_procedencia_trabajo",
]
