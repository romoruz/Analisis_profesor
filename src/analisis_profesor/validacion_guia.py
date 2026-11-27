"""Paso 9 del protocolo: validación de citas de ítems y cifras en `GUIA_PARCIAL.md`."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from analisis_profesor.esquemas import Item, leer_jsonl

_PATRON_URL = re.compile(r"https?://[^\s)\]>]+")
_PATRON_ID = re.compile(
    r"(?<![:/\\\w.])"
    r"([A-Za-z](?:[A-Za-z0-9_-]|\.(?=[A-Za-z0-9_-]))*:(?:Q\d+|\d+)[a-z]{0,2})"
    r"(?![\w:/%-]|\.\d)"
)
_PATRON_SECCION_3 = re.compile(
    r"^##\s+(?:3\b.*|.*temas\s+por\s+probabilidad\b.*)$",
    re.IGNORECASE | re.MULTILINE,
)
_PATRON_H2 = re.compile(r"^##\s", re.MULTILINE)
_PATRON_SEPARADOR = re.compile(r"^[\s|:-]+$")
_PATRON_NUM_SIMPLE = re.compile(r"^[~≈]?\s*(\d+(?:[.,]\d+)?|\.\d+)\s*(%?)$")
_PATRON_INTERVALO = re.compile(
    r"^[\[(]?\s*(\d+(?:[.,]\d+)?|\.\d+)\s*%?\s*"
    r"(,|;|–|—|-|\ba\b)\s*"
    r"(\d+(?:[.,]\d+)?|\.\d+)\s*%?\s*[\])]?\s*%?$"
)


def extraer_ids_citados(texto: str) -> list[str]:
    """Extrae todos los identificadores con formato de ítem (`<doc>:<n>` o `<doc>:Q<n>`)."""
    limpio = _PATRON_URL.sub(" ", texto)
    return sorted(set(_PATRON_ID.findall(limpio)))


def _extraer_seccion_temas(texto: str) -> str | None:
    m = _PATRON_SECCION_3.search(texto)
    if m is None:
        return None
    resto = texto[m.end() :]
    siguiente = _PATRON_H2.search(resto)
    return resto[: siguiente.start()] if siguiente else resto


def _dividir_fila_md(linea: str) -> list[str]:
    recortada = linea.strip()
    if recortada.startswith("|"):
        recortada = recortada[1:]
    if recortada.endswith("|"):
        recortada = recortada[:-1]
    return [celda.strip() for celda in recortada.split("|")]


def _parsear_tabla_markdown(seccion: str) -> tuple[list[str], list[list[str]]] | None:
    bloque: list[str] = []
    for ln in seccion.splitlines():
        s = ln.strip()
        if s.startswith("|"):
            bloque.append(s)
        elif bloque:
            break
    if not bloque:
        return None

    cabecera = _dividir_fila_md(bloque[0])
    filas: list[list[str]] = []
    for idx, ln in enumerate(bloque[1:], start=1):
        if idx == 1 and "-" in ln and _PATRON_SEPARADOR.match(ln):
            continue
        filas.append(_dividir_fila_md(ln))
    return cabecera, filas


def _limpiar_celda_num(celda: str) -> str:
    return celda.replace("`", "").replace("*", "").strip()


def _parsear_numero(celda: str) -> float | None:
    limpia = _limpiar_celda_num(celda)
    m = _PATRON_NUM_SIMPLE.match(limpia)
    if m is None:
        return None
    val = float(m.group(1).replace(",", "."))
    return val / 100.0 if m.group(2) == "%" else val


def _parsear_intervalo(celda: str) -> tuple[float, float] | None:
    limpia = _limpiar_celda_num(celda)
    m = _PATRON_INTERVALO.match(limpia)
    if m is None:
        return None
    txt_a, sep, txt_b = m.group(1), m.group(2), m.group(3)
    if sep == "," and ("," in txt_a or "," in txt_b):
        return None
    a = float(txt_a.replace(",", "."))
    b = float(txt_b.replace(",", "."))
    if "%" in limpia:
        a /= 100.0
        b /= 100.0
    return a, b


def _validar_cabecera_intervalo(cabecera: str) -> str | None:
    nums = tuple(re.findall(r"\d+(?:\.\d+)?", cabecera))
    if nums and nums not in {("90",), ("5", "95"), ("0.05", "0.95")}:
        return (
            f"La cabecera del intervalo en la tabla dice '{cabecera}', pero "
            "07_modelo.json reporta cuantiles 5-95 % (Intervalo 90 %)."
        )
    return None


def _localizar_columnas(cabecera: list[str]) -> dict[str, int]:
    cols: dict[str, int] = {}
    for idx, cruda in enumerate(cabecera):
        h = cruda.replace("`", "").replace("*", "").strip().lower()
        if "tipo" not in cols and (
            h in {"tipo", "arquetipo", "clave", "tema"}
            or h.startswith(("tipo ", "arquetipo "))
        ):
            cols["tipo"] = idx
        elif "p" not in cols and re.fullmatch(r"p(?:\s*\(.*\))?|p_base|prob(?:abilidad)?", h):
            cols["p"] = idx
        elif "ic" not in cols and ("intervalo" in h or h.startswith("ic")):
            cols["ic"] = idx
        elif "sensibilidad" not in cols and ("sensibilidad" in h or "mín" in h or "min" in h):
            cols["sensibilidad"] = idx
        elif "evidencia" not in cols and ("evidencia" in h or "ids" in h or "citas" in h):
            cols["evidencia"] = idx
    return cols


def _verificar_par_modelo(
    k: str,
    campo: str,
    celda: str,
    ref_lo: float,
    ref_hi: float,
    tolerancia: float,
    discrepancias: list[dict[str, Any]],
) -> None:
    par = _parsear_intervalo(celda)
    ref = [round(float(ref_lo), 4), round(float(ref_hi), 4)]
    if par is None:
        discrepancias.append(
            {
                "arquetipo": k,
                "campo": campo,
                "guia": celda,
                "modelo": ref,
                "motivo": "formato de intervalo no reconocido",
            }
        )
        return
    if abs(par[0] - ref_lo) > tolerancia or abs(par[1] - ref_hi) > tolerancia:
        discrepancias.append(
            {
                "arquetipo": k,
                "campo": campo,
                "guia": [round(par[0], 4), round(par[1], 4)],
                "modelo": ref,
            }
        )


def _validar_tabla_temas(
    texto_guia: str,
    modelo: dict[str, Any],
    ids_validos: set[str],
    tolerancia: float,
) -> tuple[list[str], list[str], list[dict[str, Any]], list[str], list[str]]:
    errores: list[str] = []
    discrepancias: list[dict[str, Any]] = []
    en_tabla: list[str] = []
    sin_evidencia: list[str] = []

    seccion = _extraer_seccion_temas(texto_guia)
    if seccion is None:
        errores.append("Falta la sección '## 3. Temas por probabilidad' en la guía.")
        return en_tabla, list(modelo.get("K", [])), discrepancias, sin_evidencia, errores

    tabla = _parsear_tabla_markdown(seccion)
    if tabla is None:
        errores.append("No se encontró tabla Markdown en '## 3. Temas por probabilidad'.")
        return en_tabla, list(modelo.get("K", [])), discrepancias, sin_evidencia, errores

    cabecera, filas = tabla
    if not filas:
        errores.append("La tabla de temas está vacía.")
        return en_tabla, list(modelo.get("K", [])), discrepancias, sin_evidencia, errores

    cols = _localizar_columnas(cabecera)
    requeridas = ["tipo", "p", "evidencia"]
    if "p_q05" in modelo and "p_q95" in modelo:
        requeridas.append("ic")
    if "p_min" in modelo and "p_max" in modelo:
        requeridas.append("sensibilidad")
    faltan_cols = [c for c in requeridas if c not in cols]
    if faltan_cols:
        errores.append(f"Faltan columnas esperadas en la tabla de temas: {', '.join(faltan_cols)}.")
        return en_tabla, list(modelo.get("K", [])), discrepancias, sin_evidencia, errores

    if "ic" in cols:
        err_ic = _validar_cabecera_intervalo(cabecera[cols["ic"]])
        if err_ic:
            errores.append(err_ic)

    k_lista = list(modelo.get("K", []))
    k_set = set(k_lista)
    vistos: set[str] = set()
    p_base = modelo.get("p_base", {})
    p_q05, p_q95 = modelo.get("p_q05", {}), modelo.get("p_q95", {})
    p_min, p_max = modelo.get("p_min", {}), modelo.get("p_max", {})

    for fila in filas:
        if len(fila) < len(cabecera):
            errores.append(f"Fila incompleta en tabla de temas: {fila}.")
            continue
        k = fila[cols["tipo"]].replace("`", "").replace("*", "").strip()
        if k not in k_set:
            errores.append(f"Arquetipo desconocido en tabla de temas: '{k}'.")
            continue
        if k in vistos:
            errores.append(f"Arquetipo duplicado en tabla de temas: '{k}'.")
            continue
        vistos.add(k)
        en_tabla.append(k)

        celda_p = fila[cols["p"]]
        val_p = _parsear_numero(celda_p)
        ref_p = float(p_base[k])
        if val_p is None:
            discrepancias.append(
                {
                    "arquetipo": k,
                    "campo": "p",
                    "guia": celda_p,
                    "modelo": round(ref_p, 4),
                    "motivo": "formato numérico no reconocido",
                }
            )
        elif abs(val_p - ref_p) > tolerancia:
            discrepancias.append(
                {
                    "arquetipo": k,
                    "campo": "p",
                    "guia": round(val_p, 4),
                    "modelo": round(ref_p, 4),
                }
            )

        if "ic" in cols and k in p_q05 and k in p_q95:
            _verificar_par_modelo(
                k, "intervalo_90", fila[cols["ic"]], float(p_q05[k]), float(p_q95[k]),
                tolerancia, discrepancias,
            )
        if "sensibilidad" in cols and k in p_min and k in p_max:
            _verificar_par_modelo(
                k, "sensibilidad", fila[cols["sensibilidad"]], float(p_min[k]), float(p_max[k]),
                tolerancia, discrepancias,
            )

        citas_fila = [
            cid for cid in extraer_ids_citados(fila[cols["evidencia"]]) if cid in ids_validos
        ]
        if not citas_fila:
            sin_evidencia.append(k)

    faltantes = [k for k in k_lista if k not in vistos]
    if faltantes:
        errores.append(
            f"Faltan arquetipos de 07_modelo.json en la tabla de temas: {', '.join(faltantes)}."
        )
    if sin_evidencia:
        errores.append(
            "Filas sin ningún ítem existente citado en Evidencia: "
            + ", ".join(sin_evidencia)
            + "."
        )
    if discrepancias:
        errores.append(
            f"Hay {len(discrepancias)} discrepancia(s) numérica(s) respecto a 07_modelo.json."
        )
    return en_tabla, faltantes, discrepancias, sin_evidencia, errores


def validar_guia(
    materia: str,
    raiz_trabajo: Path | None = None,
    ruta_guia: Path | None = None,
    tolerancia: float = 0.011,
) -> dict[str, Any]:
    """Comprueba que las citas y cifras de `GUIA_PARCIAL.md` coincidan con los JSON/JSONL."""
    trabajo_dir = (raiz_trabajo or Path("trabajo")) / materia
    ruta_items = trabajo_dir / "03_items.jsonl"
    ruta_modelo = trabajo_dir / "07_modelo.json"
    guia_path = ruta_guia or (trabajo_dir / "entregables" / "GUIA_PARCIAL.md")

    for ruta in (ruta_items, ruta_modelo, guia_path):
        if not ruta.is_file():
            raise FileNotFoundError(f"No existe el archivo requerido: {ruta}")

    ids_validos = {it.id for it in leer_jsonl(ruta_items, Item)}
    modelo = json.loads(ruta_modelo.read_text(encoding="utf-8"))
    texto_guia = guia_path.read_text(encoding="utf-8")

    ids_citados = extraer_ids_citados(texto_guia)
    ids_inexistentes = [cid for cid in ids_citados if cid not in ids_validos]

    errores: list[str] = []
    if ids_inexistentes:
        errores.append(
            f"IDs citados inexistentes en 03_items.jsonl ({len(ids_inexistentes)}): "
            + ", ".join(ids_inexistentes)
            + "."
        )

    en_tabla, faltantes, discrepancias, sin_evidencia, err_tabla = _validar_tabla_temas(
        texto_guia, modelo, ids_validos, tolerancia
    )
    errores.extend(err_tabla)

    temas_malos = {d["arquetipo"] for d in discrepancias} | set(sin_evidencia)
    temas_validados = sum(1 for k in en_tabla if k not in temas_malos)
    avisos: list[str] = []
    if not ids_citados:
        avisos.append("La guía no cita ningún ID de ítem.")

    resultado: dict[str, Any] = {
        "materia": materia,
        "guia": str(guia_path),
        "valida": len(errores) == 0,
        "tolerancia": tolerancia,
        "n_items_disponibles": len(ids_validos),
        "n_ids_citados": len(ids_citados),
        "ids_citados": ids_citados,
        "ids_inexistentes": ids_inexistentes,
        "temas_validados": temas_validados,
        "arquetipos_en_tabla": en_tabla,
        "arquetipos_faltantes": faltantes,
        "discrepancias_modelo": discrepancias,
        "filas_sin_evidencia": sin_evidencia,
        "avisos": avisos,
        "errores": errores,
    }
    (trabajo_dir / "09_validacion_guia.json").write_text(
        json.dumps(resultado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return resultado


__all__ = ["extraer_ids_citados", "validar_guia"]
