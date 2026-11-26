"""Lectura y verificación aislada por subproceso del banco de ejercicios `08_banco.md`.

Implementa el paso 7 de `PROTOCOLO.md` §7 y la tarea 1.9 de `docs/ROADMAP.md`.
Solo utiliza librería estándar a nivel de módulo para funcionar en modo reducido.
"""
from __future__ import annotations

import ast
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

CLAVES_SECCION = frozenset(
    {
        "arquetipo",
        "nivel",
        "familia",
        "basado_en",
        "rasgos",
        "enunciado",
        "solucion",
        "verificacion",
    }
)
_RE_BLOQUE = re.compile(r"^##\s+(\S+)\s*$")
_RE_CLAVE = re.compile(r"^([a-z_]+):\s*(.*)$")
_EQUIV_NIVEL = {
    "casi copia": "casi copia",
    "casi_copia": "casi copia",
    "adaptacion": "adaptación",
    "adaptación": "adaptación",
    "nueva": "nueva",
}


def normalizar_nivel(nivel: str) -> str:
    """Normaliza variantes de nivel (`casi_copia`/`casi copia`, `adaptacion`/`adaptación`)."""
    limpio = " ".join(nivel.strip().lower().split())
    return _EQUIV_NIVEL.get(limpio, limpio)


def parsear_rasgos(texto: str) -> dict[str, int]:
    """Convierte `'entregables=4, algebra=1'` en diccionario entero de rasgos."""
    rasgos: dict[str, int] = {}
    for parte in texto.split(","):
        trozo = parte.strip()
        if not trozo:
            continue
        if "=" not in trozo:
            raise ValueError(f"Rasgo sin '=' en banco: {trozo!r}")
        clave, val = trozo.split("=", maxsplit=1)
        rasgos[clave.strip()] = int(val.strip())
    return rasgos


@dataclass
class EjercicioBanco:
    """Representa una entrada de `08_banco.md`."""

    id: str
    arquetipo: str
    nivel: str = ""
    familia: str = ""
    basado_en: str = ""
    rasgos: dict[str, int] = field(default_factory=dict)
    enunciado: str = ""
    solucion: str = ""
    verificacion: str = ""

    @property
    def es_manual(self) -> bool:
        """Indica si el ejercicio carece de script y requiere revisión manual."""
        val = self.verificacion.strip().lower()
        return val in ("", "manual")

    @property
    def familia_efectiva(self) -> str:
        """Identificador de familia para penalizar repeticiones entre simulacros."""
        return self.familia or self.basado_en or self.id


def _cerrar_campo_multilinea(actual: dict, campo: str | None, lineas: list[str]) -> None:
    if campo is None:
        return
    while lineas and not lineas[-1].strip():
        lineas.pop()
    while lineas and not lineas[0].strip():
        lineas.pop(0)
    actual[campo] = "\n".join(lineas)


def _desindentar_dos(linea: str) -> str:
    if linea.startswith("  "):
        return linea[2:]
    if linea.startswith("\t"):
        return linea[1:]
    return linea.lstrip(" ") if not linea.strip() else linea


def leer_banco(ruta: Path) -> list[EjercicioBanco]:
    """Lee un archivo `08_banco.md` siguiendo la especificación de `PROTOCOLO.md` §7."""
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el banco de ejercicios {ruta}")

    ejercicios: list[EjercicioBanco] = []
    actual: dict | None = None
    campo_multi: str | None = None
    buf_multi: list[str] = []

    def _volcar_actual() -> None:
        nonlocal actual, campo_multi, buf_multi
        if actual is None:
            return
        _cerrar_campo_multilinea(actual, campo_multi, buf_multi)
        campo_multi = None
        buf_multi = []
        ejercicios.append(
            EjercicioBanco(
                id=actual["id"],
                arquetipo=actual.get("arquetipo", ""),
                nivel=actual.get("nivel", ""),
                familia=actual.get("familia", ""),
                basado_en=actual.get("basado_en", ""),
                rasgos=actual.get("rasgos", {}),
                enunciado=actual.get("enunciado", ""),
                solucion=actual.get("solucion", ""),
                verificacion=actual.get("verificacion", ""),
            )
        )
        actual = None

    for raw in ruta.read_text(encoding="utf-8").splitlines():
        m_bloque = _RE_BLOQUE.match(raw)
        if m_bloque and not raw.startswith((" ", "\t")):
            _volcar_actual()
            actual = {"id": m_bloque.group(1)}
            continue
        if actual is None:
            continue

        # Una clave de cabecera solo abre sección nueva si viene sin indentación.
        if not raw.startswith((" ", "\t")):
            m_clave = _RE_CLAVE.match(raw)
            if m_clave and m_clave.group(1) in CLAVES_SECCION:
                _cerrar_campo_multilinea(actual, campo_multi, buf_multi)
                campo_multi = None
                buf_multi = []
                clave, resto = m_clave.group(1), m_clave.group(2).strip()
                if clave in ("enunciado", "solucion", "verificacion") and resto == "|":
                    campo_multi = clave
                    buf_multi = []
                elif clave == "rasgos":
                    actual["rasgos"] = parsear_rasgos(resto)
                else:
                    actual[clave] = resto
                continue

        if campo_multi is not None:
            buf_multi.append(_desindentar_dos(raw))

    _volcar_actual()
    return ejercicios


def _formatear_bloque_multilinea(clave: str, texto: str) -> list[str]:
    out = [f"{clave}: |"]
    for ln in texto.splitlines():
        out.append(f"  {ln}" if ln else "")
    return out


def escribir_banco(ejercicios: Sequence[EjercicioBanco], destino: Path) -> Path:
    """Serializa una secuencia de `EjercicioBanco` en formato `08_banco.md`."""
    lineas: list[str] = []
    for ej in ejercicios:
        if lineas:
            lineas.append("")
        lineas.append(f"## {ej.id}")
        lineas.append(f"arquetipo: {ej.arquetipo}")
        if ej.nivel:
            lineas.append(f"nivel: {ej.nivel}")
        if ej.familia:
            lineas.append(f"familia: {ej.familia}")
        if ej.basado_en:
            lineas.append(f"basado_en: {ej.basado_en}")
        rasgos_txt = ", ".join(f"{k}={v}" for k, v in ej.rasgos.items())
        lineas.append(f"rasgos: {rasgos_txt}")
        lineas.extend(_formatear_bloque_multilinea("enunciado", ej.enunciado))
        lineas.extend(_formatear_bloque_multilinea("solucion", ej.solucion))
        if ej.es_manual:
            lineas.append("verificacion: manual")
        else:
            lineas.extend(_formatear_bloque_multilinea("verificacion", ej.verificacion))
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return destino


def verificar_ejercicio(ej: EjercicioBanco, *, timeout_s: float = 15.0) -> dict:
    """Ejecuta el bloque `verificacion` de un ejercicio en un subproceso aislado."""
    if ej.es_manual:
        return {
            "id": ej.id,
            "arquetipo": ej.arquetipo,
            "nivel": ej.nivel,
            "tipo_verificacion": "manual",
            "estado": "manual",
            "verificado": True,
            "codigo_salida": 0,
            "duracion_s": 0.0,
            "salida": "revisión manual requerida",
            "error": "",
        }

    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, "-c", ej.verificacion],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        dur = round(time.monotonic() - t0, 4)
        ok = proc.returncode == 0
        return {
            "id": ej.id,
            "arquetipo": ej.arquetipo,
            "nivel": ej.nivel,
            "tipo_verificacion": "automatico",
            "estado": "ok" if ok else "fallo",
            "verificado": ok,
            "codigo_salida": proc.returncode,
            "duracion_s": dur,
            "salida": proc.stdout.strip(),
            "error": proc.stderr.strip(),
        }
    except subprocess.TimeoutExpired as exc:
        dur = round(time.monotonic() - t0, 4)
        stderr_txt = exc.stderr.decode("utf-8", errors="replace") if isinstance(
            exc.stderr, bytes
        ) else (exc.stderr or "")
        return {
            "id": ej.id,
            "arquetipo": ej.arquetipo,
            "nivel": ej.nivel,
            "tipo_verificacion": "automatico",
            "estado": "timeout",
            "verificado": False,
            "codigo_salida": -1,
            "duracion_s": dur,
            "salida": "",
            "error": stderr_txt.strip() or f"tiempo excedido ({timeout_s} s)",
        }


def verificar_banco(
    materia: str,
    raiz_trabajo: Path | None = None,
    *,
    timeout_s: float = 15.0,
    ids: Sequence[str] | None = None,
    ruta_banco: Path | None = None,
) -> dict:
    """Verifica todos los ejercicios (o un subconjunto `ids`) y escribe `08_verificacion.json`."""
    base = (raiz_trabajo or Path("trabajo")) / materia
    ruta_md = ruta_banco or (base / "08_banco.md")
    ejercicios = leer_banco(ruta_md)

    if ids:
        objetivo_ids = set(ids)
        disponibles = {ej.id for ej in ejercicios}
        faltantes = sorted(objetivo_ids - disponibles)
        if faltantes:
            raise ValueError(f"IDs no encontrados en {ruta_md}: {faltantes}")
        seleccionados = [ej for ej in ejercicios if ej.id in objetivo_ids]
    else:
        seleccionados = ejercicios

    n_auto = sum(1 for ej in seleccionados if not ej.es_manual)
    if n_auto >= 6:
        max_hilos = min(4, max(1, os.cpu_count() or 1))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_hilos) as pool:
            resultados = list(
                pool.map(lambda ej: verificar_ejercicio(ej, timeout_s=timeout_s), seleccionados)
            )
    else:
        resultados = [verificar_ejercicio(ej, timeout_s=timeout_s) for ej in seleccionados]

    auto_ok = sum(1 for r in resultados if r["estado"] == "ok")
    auto_fallo = sum(1 for r in resultados if r["estado"] in ("fallo", "timeout"))
    manuales = sum(1 for r in resultados if r["estado"] == "manual")
    verificados = sum(1 for r in resultados if r["verificado"])
    salida = {
        "materia": materia,
        "timeout_s": timeout_s,
        "total": len(resultados),
        "automaticos_ok": auto_ok,
        "automaticos_fallidos": auto_fallo,
        "manuales": manuales,
        "verificados": verificados,
        "todos_ok": auto_fallo == 0 and len(resultados) > 0,
        "resultados": resultados,
    }
    if not ids:
        (base / "08_verificacion.json").write_text(
            json.dumps(salida, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return salida


def _extraer_dependencias_verificacion(ruta_verif: Path) -> tuple[str, dict[str, str]]:
    """Extrae el preámbulo y bloques autocontenidos por tipo desde `verificacion.py` legacy."""
    fuente = ruta_verif.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(ruta_verif))
    lineas = fuente.splitlines()

    funcs_ast = {
        nodo.name: nodo
        for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef)
    }
    funcs_src = {
        nombre: "\n".join(lineas[nodo.lineno - 1 : nodo.end_lineno])
        for nombre, nodo in funcs_ast.items()
    }

    preambulo_fin = min(nodo.lineno for nodo in funcs_ast.values()) - 1
    preambulo = "\n".join(lineas[:preambulo_fin]).strip()

    bloques: dict[str, str] = {}
    privadas = {n for n in funcs_ast if n.startswith("_")}
    for nombre, nodo in funcs_ast.items():
        if nombre.startswith("_") or nombre == "verifica":
            continue
        usadas: list[str] = []
        por_visitar = [nodo]
        vistas: set[str] = set()
        while por_visitar:
            actual_nodo = por_visitar.pop()
            for sub in ast.walk(actual_nodo):
                if isinstance(sub, ast.Name) and sub.id in privadas and sub.id not in vistas:
                    vistas.add(sub.id)
                    usadas.append(sub.id)
                    por_visitar.append(funcs_ast[sub.id])
        partes = [preambulo] + [funcs_src[u] for u in sorted(usadas)] + [funcs_src[nombre]]
        bloques[nombre] = "\n\n".join(partes)
    return preambulo, bloques


def convertir_banco_legacy_sd2(ruta_curso_legacy: Path, destino_md: Path) -> list[EjercicioBanco]:
    """Convierte `banco_ejercicios.py` + `verificacion.py` de SD-II a `08_banco.md`."""
    ruta_src = ruta_curso_legacy / "src"
    ruta_banco_py = ruta_src / "banco_ejercicios.py"
    ruta_verif_py = ruta_src / "verificacion.py"

    ns: dict = {}
    exec(compile(ruta_banco_py.read_text(encoding="utf-8"), str(ruta_banco_py), "exec"), ns)
    crudos = ns["banco"]()
    _, bloques_verif = _extraer_dependencias_verificacion(ruta_verif_py)

    ejercicios: list[EjercicioBanco] = []
    for cand in crudos:
        check = dict(cand["check"])
        tipo = check["tipo"]
        if tipo == "demostracion":
            verif_txt = "manual"
        else:
            cuerpo_func = bloques_verif[tipo]
            verif_txt = "\n".join(
                [
                    "import json",
                    cuerpo_func,
                    f"_CHECK = json.loads({json.dumps(json.dumps(check, ensure_ascii=False))})",
                    f"_ok, _lineas = {tipo}(_CHECK)",
                    "for _ln in _lineas:",
                    "    print(_ln)",
                    "assert _ok, '\\n'.join(_lineas)",
                ]
            )
        ejercicios.append(
            EjercicioBanco(
                id=str(cand["id"]),
                arquetipo=str(cand["arq"]),
                nivel=str(cand.get("nivel", "")),
                familia=str(cand.get("familia", "")),
                basado_en="",
                rasgos={str(k): int(v) for k, v in cand["rasgos"].items()},
                enunciado=str(cand["tex"]),
                solucion="",
                verificacion=verif_txt,
            )
        )
    escribir_banco(ejercicios, destino_md)
    return ejercicios


__all__ = [
    "EjercicioBanco",
    "convertir_banco_legacy_sd2",
    "escribir_banco",
    "leer_banco",
    "normalizar_nivel",
    "parsear_rasgos",
    "verificar_banco",
    "verificar_ejercicio",
    "asdict",
]
