import os
import re
import shutil
from collections import Counter
from pathlib import Path

import pytest

from analisis_profesor.cli import main
from analisis_profesor.esquemas import Item, leer_jsonl

RAIZ = Path(__file__).resolve().parents[1]


def _convertir_corpus_sd2(sd2_dir: Path, destino_texto: Path) -> None:
    destino_texto.mkdir(parents=True, exist_ok=True)
    califs = {"P2_2026-05-04": "0.5, 1, 0.5, 0", "P2_2026-10-19": "2.5, 2, 1, 1.5"}
    corpus = sd2_dir / "corpus"

    for nombre in ("P1_2026-03-04", "P2_2020-04-29", "P2_2026-05-04", "P2_2026-10-19"):
        parcial, fecha = nombre.split("_", maxsplit=1)
        raw = (corpus / "examenes" / f"{nombre}.txt").read_text(encoding="utf-8")
        partes = re.split(r"^Pregunta\s+(\d+)\s*(?:\([^)]+\))?\s*", raw, flags=re.M)
        out = [f"# Sistemas Dinámicos II - {parcial} - {fecha}", "tipo: examen", "duracion_min: 90"]
        if nombre in califs:
            out.append(f"calificacion_alumno: {califs[nombre]}")
        out.append("")
        for i in range(1, len(partes), 2):
            out.extend([f"## Pregunta {partes[i]} (2.5 puntos)", partes[i + 1].strip(), ""])
        (destino_texto / f"{nombre}.md").write_text("\n".join(out), encoding="utf-8")

    for n in range(1, 6):
        lineas = (corpus / "tareas" / f"Tarea_{n}.txt").read_text(encoding="utf-8").splitlines()
        idx = [k for k, line in enumerate(lineas) if re.match(r"^\s{0,4}\d{1,2}\.\s", line)]
        bloques = [
            "\n".join(lineas[a:b]) for a, b in zip(idx, idx[1:] + [len(lineas)], strict=True)
        ]
        if n == 4:
            bloques = bloques[:-2] + [bloques[-2] + "\n" + bloques[-1]]
        out = [f"# Sistemas Dinámicos II - Tarea {n} - 0000-00-00", "tipo: tarea", ""]
        for k, bloque in enumerate(bloques, 1):
            cuerpo = re.sub(r"^\s{0,4}\d{1,2}\.\s*", "", bloque, count=1).strip()
            out.extend([f"## Ejercicio {k}", cuerpo, ""])
        (destino_texto / f"T{n}.md").write_text("\n".join(out), encoding="utf-8")


def test_segmentar_fixture_mini(mini_dir: Path, tmp_path: Path):
    import csv

    from analisis_profesor.segmentacion import segmentar_carpeta

    raiz_trabajo = tmp_path / "trabajo"
    shutil.copytree(mini_dir, raiz_trabajo / "mini")

    items = segmentar_carpeta("mini", raiz_trabajo=raiz_trabajo)
    ruta_jsonl = raiz_trabajo / "mini" / "03_items.jsonl"
    assert ruta_jsonl.is_file()
    assert list(leer_jsonl(ruta_jsonl, Item)) == items

    etiquetables = [it for it in items if not it.padre_id]
    with open(mini_dir / "05_etiquetas.csv", encoding="utf-8", newline="") as f:
        ids_csv = {fila["item_id"] for fila in csv.DictReader(f)}
    assert {it.id for it in etiquetables} == ids_csv

    por_id = {it.id: it for it in items}
    hijos_p25 = [it for it in items if it.documento_id == "P1_2025-04-10" and it.padre_id]
    assert {it.id for it in hijos_p25} == {
        "P1_2025-04-10:Q1a",
        "P1_2025-04-10:Q1b",
        "P1_2025-04-10:Q2a",
        "P1_2025-04-10:Q2b",
    }
    assert por_id["P1_2025-04-10:Q1a"].padre_id == "P1_2025-04-10:Q1"
    for q in range(1, 5):
        it = por_id[f"P1_2025-04-10:Q{q}"]
        assert it.puntos_max == 2.5
        assert it.puntos_obtenidos is None

    hijos_p26 = [it for it in items if it.documento_id == "P1_2026-04-15" and it.padre_id]
    assert {it.id for it in hijos_p26} == {
        "P1_2026-04-15:Q1a",
        "P1_2026-04-15:Q1b",
        "P1_2026-04-15:Q2a",
        "P1_2026-04-15:Q2b",
        "P1_2026-04-15:Q3a",
        "P1_2026-04-15:Q3b",
    }
    assert [por_id[f"P1_2026-04-15:Q{q}"].puntos_obtenidos for q in range(1, 5)] == [
        2.5,
        2.0,
        1.5,
        0.5,
    ]

    t1_items = [it for it in items if it.documento_id == "T1"]
    assert [it.id for it in t1_items] == ["T1:1", "T1:2a", "T1:2b", "T1:3", "T1:4", "T1:5"]
    assert all(not it.padre_id for it in t1_items)
    assert "condición de Hall" in por_id["T1:2a"].texto

    assert [it.id for it in items if it.documento_id == "T2"] == [f"T2:{i}" for i in range(1, 6)]
    c1_items = [it for it in items if it.documento_id == "C1_grafos"]
    assert [it.id for it in c1_items] == ["C1_grafos:1", "C1_grafos:2", "C1_grafos:3"]
    assert all(it.tipo_doc == "clase" for it in c1_items)


def test_calificacion_alumno_longitud_invalida(tmp_path: Path):
    from analisis_profesor.segmentacion import segmentar_documento

    ruta = tmp_path / "P1_2026-01-01.md"
    ruta.write_text(
        "# Curso - P1 - 2026-01-01\n"
        "tipo: examen\n"
        "duracion_min: 60\n"
        "calificacion_alumno: 2.0, 1.0\n\n"
        "## Pregunta 1 (2.5 puntos)\nUno.\n\n"
        "## Pregunta 2 (2.5 puntos)\nDos.\n\n"
        "## Pregunta 3 (2.5 puntos)\nTres.\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        segmentar_documento(ruta)


def test_cli_items_conteo_salida(
    mini_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    shutil.copytree(mini_dir / "02_texto", tmp_path / "trabajo" / "mini" / "02_texto")
    monkeypatch.chdir(tmp_path)

    assert main(["items", "mini"]) == 0
    salida = capsys.readouterr().out
    assert "P1_2025-04-10" in salida
    assert "T1" in salida
    assert (tmp_path / "trabajo" / "mini" / "03_items.jsonl").is_file()


@pytest.mark.real
def test_items_sd2_real(sd2_dir: Path, tmp_path: Path):
    from analisis_profesor.segmentacion import segmentar_carpeta

    raiz_trabajo = tmp_path / "trabajo"
    destino_texto = raiz_trabajo / "sd2" / "02_texto"
    preconvertido = RAIZ / "entrada" / "sd2_paso2" / "02_texto"
    if preconvertido.is_dir() and not os.environ.get("AP_SD2_ZIP"):
        shutil.copytree(preconvertido, destino_texto)
    else:
        _convertir_corpus_sd2(sd2_dir, destino_texto)

    items = segmentar_carpeta("sd2", raiz_trabajo=raiz_trabajo)
    etiquetables = [it for it in items if not it.padre_id]
    conteos = Counter(it.documento_id for it in etiquetables)

    assert conteos["P1_2026-03-04"] == 4
    assert conteos["P2_2020-04-29"] == 4
    assert conteos["P2_2026-05-04"] == 4
    assert conteos["P2_2026-10-19"] == 4

    por_id = {it.id: it for it in etiquetables}
    assert [por_id[f"P2_2026-05-04:Q{q}"].puntos_obtenidos for q in range(1, 5)] == [
        0.5,
        1.0,
        0.5,
        0.0,
    ]
    assert [por_id[f"P2_2026-10-19:Q{q}"].puntos_obtenidos for q in range(1, 5)] == [
        2.5,
        2.0,
        1.0,
        1.5,
    ]

    assert conteos["T1"] == 19
    assert conteos["T2"] == 8
    assert conteos["T3"] == 11
    assert conteos["T4"] == 14
    assert conteos["T5"] == 10
