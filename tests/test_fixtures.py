import csv
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from analisis_profesor.esquemas import NIVELES_RECICLAJE, Etiqueta

RAIZ = Path(__file__).resolve().parents[1]

RASGOS_ANEXO_A: dict[str, tuple[int, int]] = {
    "entregables": (1, 5),
    "parametro": (0, 2),
    "dimension": (1, 4),
    "tecnica": (0, 3),
    "demostracion": (0, 2),
    "algebra": (0, 2),
    "computo": (0, 2),
    "casos": (1, 4),
}

COLUMNAS_ETIQUETAS = [
    "item_id",
    "arquetipo",
    "fuente",
    "nivel",
    *RASGOS_ANEXO_A.keys(),
    "bloom",
    "dok",
    "minutos",
    "puntos",
    "pasada",
]


def _extraer_items_md(ruta: Path) -> tuple[str, list[str]]:
    texto = ruta.read_text(encoding="utf-8")
    lineas = texto.splitlines()
    assert lineas, f"{ruta.name} está vacío"
    assert re.match(r"^# .+ - .+ - \d{4}-\d{2}-\d{2}$", lineas[0]), (
        f"Encabezado inválido en {ruta.name}: {lineas[0]!r}"
    )
    m_tipo = re.search(r"^tipo:\s*(\S+)\s*$", texto, re.MULTILINE)
    assert m_tipo, f"Falta `tipo:` en {ruta.name}"
    tipo = m_tipo.group(1)

    if tipo == "examen":
        assert re.search(r"^duracion_min:\s*\d+\s*$", texto, re.MULTILINE), (
            f"Falta `duracion_min:` en {ruta.name}"
        )
        nums = re.findall(r"^## Pregunta (\d+)\s*\(\d+(?:\.\d+)? puntos\)", texto, re.MULTILINE)
        assert nums, f"Sin preguntas válidas en {ruta.name}"
        return tipo, [f"{ruta.stem}:Q{n}" for n in nums]
    if tipo == "tarea":
        nums = re.findall(r"^## Ejercicio (\d+)\b", texto, re.MULTILINE)
        assert nums, f"Sin ejercicios válidos en {ruta.name}"
        return tipo, [f"{ruta.stem}:{n}" for n in nums]
    if tipo == "clase":
        nums = re.findall(r"^## Tema (\d+)\b", texto, re.MULTILINE)
        assert nums, f"Sin temas válidos en {ruta.name}"
        return tipo, [f"{ruta.stem}:{n}" for n in nums]
    raise AssertionError(f"Tipo inesperado en {ruta.name}: {tipo!r}")


def test_fixture_mini_documentos_paso2(mini_dir: Path):
    toml_ruta = mini_dir / "materia.toml"
    assert toml_ruta.is_file(), "Falta tests/fixtures/mini/materia.toml"
    if sys.version_info >= (3, 11):
        import tomllib

        cfg = tomllib.loads(toml_ruta.read_text(encoding="utf-8"))
        assert cfg["id"] == "mini"
        for seccion in ("objetivo", "formato", "arquetipos", "modelo"):
            assert seccion in cfg, f"Falta [{seccion}] en materia.toml"
        assert 6 <= len(cfg["arquetipos"]) <= 12

    texto_dir = mini_dir / "02_texto"
    archivos_md = sorted(texto_dir.glob("*.md"))
    assert len(archivos_md) == 5

    conteos = {"examen": 0, "tarea": 0, "clase": 0}
    tiene_calificacion = False
    for ruta in archivos_md:
        tipo, _ = _extraer_items_md(ruta)
        conteos[tipo] += 1
        if tipo == "examen" and "calificacion_alumno:" in ruta.read_text(encoding="utf-8"):
            tiene_calificacion = True

    assert conteos == {"examen": 2, "tarea": 2, "clase": 1}
    assert tiene_calificacion, "Al menos un examen debe incluir `calificacion_alumno:`"


def test_fixture_mini_etiquetas_validas(mini_dir: Path):
    ids_esperados: set[str] = set()
    tipos_por_id: dict[str, str] = {}
    for ruta in sorted((mini_dir / "02_texto").glob("*.md")):
        tipo, ids = _extraer_items_md(ruta)
        for item_id in ids:
            ids_esperados.add(item_id)
            tipos_por_id[item_id] = tipo

    csv_ruta = mini_dir / "05_etiquetas.csv"
    assert csv_ruta.is_file(), "Falta tests/fixtures/mini/05_etiquetas.csv"
    with open(csv_ruta, encoding="utf-8", newline="") as f:
        lector = csv.DictReader(f)
        assert lector.fieldnames == COLUMNAS_ETIQUETAS
        filas = list(lector)

    ids_csv = [fila["item_id"] for fila in filas]
    assert len(ids_csv) == len(set(ids_csv)), "Hay item_id duplicados en 05_etiquetas.csv"
    assert set(ids_csv) == ids_esperados

    niveles_vistos: set[str] = set()
    for fila in filas:
        item_id = fila["item_id"]
        rasgos: dict[str, int] = {}
        for rasgo, (base, maximo) in RASGOS_ANEXO_A.items():
            val_str = fila[rasgo].strip()
            if val_str:
                val = int(val_str)
                assert base <= val <= maximo, f"{item_id}.{rasgo}={val} fuera de [{base}, {maximo}]"
                rasgos[rasgo] = val

        if tipos_por_id[item_id] in ("examen", "tarea") and fila["arquetipo"] not in ("", "-"):
            assert set(rasgos) == set(RASGOS_ANEXO_A), f"Faltan rasgos en {item_id}"

        if fila["fuente"]:
            assert fila["fuente"] in ids_esperados, f"Fuente desconocida en {item_id}"
        if fila["nivel"]:
            niveles_vistos.add(fila["nivel"])

        Etiqueta(
            item_id=item_id,
            arquetipo=fila["arquetipo"],
            fuente=fila["fuente"],
            nivel=fila["nivel"],
            rasgos=rasgos,
            bloom=fila["bloom"],
            dok=int(fila["dok"]) if fila["dok"] else None,
            minutos=float(fila["minutos"]) if fila["minutos"] else None,
            pasada=int(fila["pasada"]) if fila["pasada"] else 1,
        )

    assert set(NIVELES_RECICLAJE).issubset(niveles_vistos)


def test_sd2_se_salta_si_no_existe_zip(tmp_path: Path):
    env = {**os.environ, "AP_SD2_ZIP": str(tmp_path / "no_existe.zip")}
    r = subprocess.run(
        [sys.executable, "-m", "pytest", str(Path(__file__)), "-k", "test_sd2_real", "-rs"],
        capture_output=True,
        text=True,
        cwd=RAIZ,
        env=env,
    )
    assert r.returncode == 0, r.stderr
    assert "skipped" in r.stdout.lower()


@pytest.mark.real
def test_sd2_real_descomprime_en_temporal(sd2_dir: Path):
    assert sd2_dir.name == "sistemas_dinamicos_ii"
    assert RAIZ not in sd2_dir.parents

    fotos = sorted(p.name for p in (sd2_dir / "datos" / "examenes").glob("*.jpg"))
    assert fotos == [
        "P1_2026-03-04.jpg",
        "P2_2020-04-29.jpg",
        "P2_2026-05-04.jpg",
        "P2_2026-10-19.jpg",
    ]
    tareas_pdf = sorted(p.name for p in (sd2_dir / "datos" / "tareas").glob("*.pdf"))
    assert tareas_pdf == [f"Tarea_{i}.pdf" for i in range(1, 6)]

    assert len(list((sd2_dir / "corpus" / "examenes").glob("*.txt"))) == 4
    assert len(list((sd2_dir / "corpus" / "tareas").glob("*.txt"))) == 5
    assert (sd2_dir / "rasgos_dificultad.csv").is_file()
