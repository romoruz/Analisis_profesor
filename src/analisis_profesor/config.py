"""Lectura de `materia.toml` con respaldo JSON/Python puro y valores del Anexo A."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

# Rubrica por defecto del Anexo A de PROTOCOLO.md: rasgo -> (peso, base, maximo)
RASGOS_POR_DEFECTO: dict[str, tuple[float, int, int]] = {
    "entregables": (0.6, 1, 5),
    "parametro": (1.2, 0, 2),
    "dimension": (0.5, 1, 4),
    "tecnica": (1.2, 0, 3),
    "demostracion": (1.0, 0, 2),
    "algebra": (0.6, 0, 2),
    "computo": (0.5, 0, 2),
    "casos": (0.4, 1, 4),
}

# Rubrica usada en `legacy/estudio_parciales/nucleo/dificultad.py` (SD-II)
RASGOS_LEGACY_SD2: dict[str, tuple[float, int, int]] = {
    "pasos": (0.6, 1, 5),
    "parametro": (1.2, 0, 2),
    "dim": (0.5, 1, 4),
    "tecnica": (1.2, 0, 3),
    "no_hiperbolico": (1.0, 0, 1),
    "demostracion": (1.0, 0, 2),
    "algebra": (0.6, 0, 2),
    "global": (1.0, 0, 1),
    "casos": (0.4, 1, 4),
}

MODELO_POR_DEFECTO: dict[str, Any] = {
    "semilla": 2026,
    "beta": 6,
    "suavizado": 0.3,
    "rho": 0.6,
}


def _quitar_comentario(linea: str) -> str:
    en_doble = False
    en_simple = False
    escape = False
    for idx, ch in enumerate(linea):
        if escape:
            escape = False
            continue
        if en_doble:
            if ch == "\\":
                escape = True
            elif ch == '"':
                en_doble = False
            continue
        if en_simple:
            if ch == "'":
                en_simple = False
            continue
        if ch == '"':
            en_doble = True
        elif ch == "'":
            en_simple = True
        elif ch == "#":
            return linea[:idx]
    return linea


def _partir_fuera_de_comillas(texto: str, separador: str) -> list[str]:
    partes: list[str] = []
    inicio = 0
    prof_corchete = 0
    prof_llave = 0
    en_doble = False
    en_simple = False
    escape = False
    for idx, ch in enumerate(texto):
        if escape:
            escape = False
            continue
        if en_doble:
            if ch == "\\":
                escape = True
            elif ch == '"':
                en_doble = False
            continue
        if en_simple:
            if ch == "'":
                en_simple = False
            continue
        if ch == '"':
            en_doble = True
        elif ch == "'":
            en_simple = True
        elif ch == "[":
            prof_corchete += 1
        elif ch == "]":
            prof_corchete -= 1
        elif ch == "{":
            prof_llave += 1
        elif ch == "}":
            prof_llave -= 1
        elif ch == separador and prof_corchete == 0 and prof_llave == 0:
            partes.append(texto[inicio:idx])
            inicio = idx + 1
    partes.append(texto[inicio:])
    return partes


def _contar_balance(texto: str) -> int:
    balance = 0
    en_doble = False
    en_simple = False
    escape = False
    for ch in texto:
        if escape:
            escape = False
            continue
        if en_doble:
            if ch == "\\":
                escape = True
            elif ch == '"':
                en_doble = False
            continue
        if en_simple:
            if ch == "'":
                en_simple = False
            continue
        if ch == '"':
            en_doble = True
        elif ch == "'":
            en_simple = True
        elif ch in "[{":
            balance += 1
        elif ch in "]}":
            balance -= 1
    return balance


def _limpiar_clave(clave: str) -> str:
    k = clave.strip()
    if (k.startswith('"') and k.endswith('"')) or (k.startswith("'") and k.endswith("'")):
        return str(ast.literal_eval(k))
    return k


def _parsear_valor_toml(raw: str) -> Any:
    val = raw.strip()
    if not val:
        raise ValueError("Valor TOML vacío")
    if val == "true":
        return True
    if val == "false":
        return False
    if val.startswith('"') and val.endswith('"'):
        return ast.literal_eval(val)
    if val.startswith("'") and val.endswith("'"):
        return val[1:-1]
    if val.startswith("[") and val.endswith("]"):
        interior = val[1:-1].strip()
        if not interior:
            return []
        elementos = [el.strip() for el in _partir_fuera_de_comillas(interior, ",")]
        return [_parsear_valor_toml(el) for el in elementos if el]
    if val.startswith("{") and val.endswith("}"):
        interior = val[1:-1].strip()
        tabla: dict[str, Any] = {}
        if not interior:
            return tabla
        for entrada in _partir_fuera_de_comillas(interior, ","):
            if not entrada.strip():
                continue
            k_raw, v_raw = _partir_fuera_de_comillas(entrada, "=")
            tabla[_limpiar_clave(k_raw)] = _parsear_valor_toml(v_raw)
        return tabla
    limpio = val.replace("_", "")
    if re.fullmatch(r"[+-]?\d+", limpio):
        return int(limpio)
    if re.fullmatch(r"[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?", limpio):
        return float(limpio)
    raise ValueError(f"Valor TOML no soportado: {raw!r}")


def _parsear_toml_basico(texto: str) -> dict[str, Any]:
    """Parser en Python puro para el subconjunto TOML de `materia.toml` (Python 3.10)."""
    datos: dict[str, Any] = {}
    actual = datos
    lineas_sin_com = [_quitar_comentario(ln).strip() for ln in texto.splitlines()]
    idx = 0
    while idx < len(lineas_sin_com):
        ln = lineas_sin_com[idx]
        idx += 1
        if not ln:
            continue
        if ln.startswith("[") and ln.endswith("]"):
            actual = datos
            for parte in ln[1:-1].split("."):
                actual = actual.setdefault(_limpiar_clave(parte), {})
            continue
        while _contar_balance(ln) > 0 and idx < len(lineas_sin_com):
            ln = f"{ln} {lineas_sin_com[idx]}".strip()
            idx += 1
        partes = _partir_fuera_de_comillas(ln, "=")
        if len(partes) < 2:
            raise ValueError(f"Línea TOML inválida: {ln!r}")
        clave = _limpiar_clave(partes[0])
        valor_raw = "=".join(partes[1:]).strip()
        actual[clave] = _parsear_valor_toml(valor_raw)
    return datos


def cargar_toml(texto: str) -> dict[str, Any]:
    """Carga TOML usando `tomllib` (3.11+), `tomli` o el parser básico en Python puro."""
    try:
        import tomllib  # estándar desde Python 3.11

        return tomllib.loads(texto)
    except ModuleNotFoundError:
        try:
            import tomli  # respaldo opcional en Python 3.10

            return tomli.loads(texto)
        except ModuleNotFoundError:
            return _parsear_toml_basico(texto)


def leer_config_materia(ruta_o_carpeta: Path) -> dict[str, Any]:
    """Lee `materia.toml` (o `materia.json`) y rellena los valores por defecto del Anexo A."""
    ruta_toml: Path | None = None
    ruta_json: Path | None = None
    if ruta_o_carpeta.is_dir():
        if (cand_toml := ruta_o_carpeta / "materia.toml").is_file():
            ruta_toml = cand_toml
        elif (cand_json := ruta_o_carpeta / "materia.json").is_file():
            ruta_json = cand_json
    elif ruta_o_carpeta.is_file():
        if ruta_o_carpeta.suffix.lower() == ".json":
            ruta_json = ruta_o_carpeta
        else:
            ruta_toml = ruta_o_carpeta

    crudo: dict[str, Any] = {}
    if ruta_toml is not None:
        crudo = cargar_toml(ruta_toml.read_text(encoding="utf-8"))
    elif ruta_json is not None:
        crudo = json.loads(ruta_json.read_text(encoding="utf-8"))

    rasgos_raw = crudo.get("rasgos") or {}
    if rasgos_raw:
        rasgos = {
            str(nombre): (float(vals[0]), int(vals[1]), int(vals[2]))
            for nombre, vals in rasgos_raw.items()
        }
    else:
        rasgos = dict(RASGOS_POR_DEFECTO)

    arquetipos_raw = crudo.get("arquetipos") or {}
    arquetipos = {
        str(k): (str(v[0]), float(v[1])) for k, v in arquetipos_raw.items()
    }

    objetivo_raw = crudo.get("objetivo") or {}
    objetivo = {
        "parcial": str(objetivo_raw.get("parcial", "")),
        "fecha": str(objetivo_raw.get("fecha", "")),
        "inicio_semestre": str(
            objetivo_raw.get("inicio_semestre") or crudo.get("inicio_semestre") or ""
        ),
        "temas": [str(t) for t in objetivo_raw.get("temas", [])],
        "molde": [str(m) for m in objetivo_raw.get("molde", [])],
        "ya_examinado_este_semestre": [
            str(a) for a in objetivo_raw.get("ya_examinado_este_semestre", [])
        ],
    }

    formato_raw = crudo.get("formato") or {}
    preguntas_raw = formato_raw.get("preguntas") or {"4": 1.0}
    formato = {
        "preguntas": {str(k): float(v) for k, v in preguntas_raw.items()},
        "minutos": [float(m) for m in formato_raw.get("minutos", [])],
        "puntos_por_pregunta": [float(p) for p in formato_raw.get("puntos_por_pregunta", [])],
    }

    modelo_raw = crudo.get("modelo") or {}
    modelo = {**MODELO_POR_DEFECTO, **modelo_raw}
    modelo["semilla"] = int(modelo["semilla"])
    modelo["beta"] = float(modelo["beta"])
    modelo["suavizado"] = float(modelo["suavizado"])
    modelo["rho"] = float(modelo["rho"])

    return {
        "id": str(crudo.get("id", "")),
        "nombre": str(crudo.get("nombre", "")),
        "profesor": str(crudo.get("profesor", "")),
        "semestre": str(crudo.get("semestre", "")),
        "objetivo": objetivo,
        "formato": formato,
        "arquetipos": arquetipos,
        "rasgos": rasgos,
        "modelo": modelo,
    }
