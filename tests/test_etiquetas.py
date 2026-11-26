import csv
import json
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

from analisis_profesor.cli import main
from analisis_profesor.esquemas import Etiqueta, Item, leer_jsonl
from analisis_profesor.segmentacion import segmentar_carpeta

RAIZ = Path(__file__).resolve().parents[1]


def test_leer_config_materia_y_respaldos(mini_dir: Path, tmp_path: Path):
    from analisis_profesor.config import (
        MODELO_POR_DEFECTO,
        RASGOS_POR_DEFECTO,
        _parsear_toml_basico,
        leer_config_materia,
    )

    cfg = leer_config_materia(mini_dir)
    assert cfg["id"] == "mini"
    assert cfg["nombre"] == "Grafos y Redes Discretas"
    assert cfg["semestre"] == "2026-II"
    assert cfg["objetivo"]["parcial"] == "P1"
    assert cfg["objetivo"]["molde"] == ["P1_2025-04-10", "P1_2026-04-15"]
    assert cfg["formato"]["preguntas"] == {"4": 1.0}
    assert cfg["formato"]["minutos"] == [75, 95]
    assert len(cfg["arquetipos"]) == 6
    assert cfg["arquetipos"]["A"][1] == 20
    assert cfg["rasgos"] == RASGOS_POR_DEFECTO
    assert cfg["modelo"] == MODELO_POR_DEFECTO

    texto_mini = (mini_dir / "materia.toml").read_text(encoding="utf-8")
    parseo_basico = _parsear_toml_basico(texto_mini)
    if sys.version_info >= (3, 11):
        import tomllib

        assert parseo_basico == tomllib.loads(texto_mini)

    carpeta_custom = tmp_path / "custom"
    carpeta_custom.mkdir()
    (carpeta_custom / "materia.toml").write_text(
        'id = "custom"\n'
        'nombre = "Prueba"\n'
        "[rasgos]\n"
        "pasos = [0.6, 1, 5]\n"
        "parametro = [1.2, 0, 2]\n",
        encoding="utf-8",
    )
    cfg_custom = leer_config_materia(carpeta_custom)
    assert cfg_custom["rasgos"] == {"pasos": (0.6, 1, 5), "parametro": (1.2, 0, 2)}

    carpeta_json = tmp_path / "json_cfg"
    carpeta_json.mkdir()
    (carpeta_json / "materia.json").write_text(
        json.dumps({"id": "desde_json", "modelo": {"semilla": 99}}), encoding="utf-8"
    )
    cfg_json = leer_config_materia(carpeta_json)
    assert cfg_json["id"] == "desde_json"
    assert cfg_json["rasgos"] == RASGOS_POR_DEFECTO
    assert cfg_json["modelo"]["semilla"] == 99

    carpeta_vacia = tmp_path / "vacia"
    carpeta_vacia.mkdir()
    cfg_vacia = leer_config_materia(carpeta_vacia)
    assert cfg_vacia["rasgos"] == RASGOS_POR_DEFECTO
    assert cfg_vacia["modelo"] == MODELO_POR_DEFECTO


def test_csv_ida_y_vuelta_etiquetas(mini_dir: Path, tmp_path: Path):
    from analisis_profesor.config import RASGOS_POR_DEFECTO
    from analisis_profesor.etiquetas import (
        columnas_etiquetas,
        escribir_etiquetas,
        leer_etiquetas,
    )

    ruta_mini_csv = mini_dir / "05_etiquetas.csv"
    etiquetas = leer_etiquetas(ruta_mini_csv, rasgos=RASGOS_POR_DEFECTO)
    assert len(etiquetas) == 22
    por_id = {e.item_id: e for e in etiquetas}
    assert por_id["P1_2025-04-10:Q1"].puntos is None
    assert [por_id[f"P1_2026-04-15:Q{q}"].puntos for q in range(1, 5)] == [2.5, 2.0, 1.5, 0.5]
    assert por_id["T1:2a"].rasgos["tecnica"] == 1
    assert por_id["C1_grafos:1"].arquetipo == "-"
    assert por_id["C1_grafos:1"].rasgos == {}

    copia_csv = tmp_path / "05_etiquetas.csv"
    escritas = escribir_etiquetas(copia_csv, etiquetas, RASGOS_POR_DEFECTO)
    assert escritas == 22
    assert copia_csv.read_text(encoding="utf-8") == ruta_mini_csv.read_text(encoding="utf-8")
    assert leer_etiquetas(copia_csv, rasgos=RASGOS_POR_DEFECTO) == etiquetas

    etiquetas_con_no_ex = [
        Etiqueta(
            item_id="T1:1",
            arquetipo="A",
            rasgos={k: b for k, (_, b, _) in RASGOS_POR_DEFECTO.items()},
            examinable=False,
        )
    ]
    ruta_ex = tmp_path / "con_examinable.csv"
    escribir_etiquetas(ruta_ex, etiquetas_con_no_ex, RASGOS_POR_DEFECTO)
    assert "examinable" in columnas_etiquetas(RASGOS_POR_DEFECTO, incluir_examinable=True)
    re_ex = leer_etiquetas(ruta_ex, rasgos=RASGOS_POR_DEFECTO)
    assert len(re_ex) == 1
    assert re_ex[0].examinable is False

    ruta_invalida = tmp_path / "invalido.csv"
    cols = columnas_etiquetas(RASGOS_POR_DEFECTO)
    with open(ruta_invalida, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerow({"item_id": "T1:1", "entregables": "99", "pasada": "1"})
    with pytest.raises(ValueError, match="entregables"):
        leer_etiquetas(ruta_invalida, rasgos=RASGOS_POR_DEFECTO)


def test_generar_plantilla_etiquetas_y_cli(
    mini_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    from analisis_profesor.config import RASGOS_POR_DEFECTO
    from analisis_profesor.etiquetas import (
        columnas_etiquetas,
        generar_plantilla_etiquetas,
        leer_etiquetas,
    )

    raiz_trabajo = tmp_path / "trabajo"
    shutil.copytree(mini_dir / "02_texto", raiz_trabajo / "mini" / "02_texto")
    shutil.copy2(mini_dir / "materia.toml", raiz_trabajo / "mini" / "materia.toml")
    segmentar_carpeta("mini", raiz_trabajo=raiz_trabajo)

    monkeypatch.chdir(tmp_path)
    assert main(["plantilla-etiquetas", "mini"]) == 0
    salida_cli = capsys.readouterr().out
    assert "05_etiquetas.csv" in salida_cli

    ruta_csv = raiz_trabajo / "mini" / "05_etiquetas.csv"
    assert ruta_csv.is_file()
    with open(ruta_csv, encoding="utf-8", newline="") as f:
        lector = csv.DictReader(f)
        assert lector.fieldnames == columnas_etiquetas(RASGOS_POR_DEFECTO)
        filas = list(lector)
    assert len(filas) == 22
    ids = {fl["item_id"] for fl in filas}
    assert "P1_2025-04-10:Q1a" not in ids
    assert {"T1:2a", "T1:2b"}.issubset(ids)

    por_id = {fl["item_id"]: fl for fl in filas}
    assert por_id["C1_grafos:1"]["arquetipo"] == "-"
    assert por_id["P1_2026-04-15:Q1"]["puntos"] == "2.5"
    assert por_id["P1_2026-04-15:Q4"]["puntos"] == "0.5"

    etiquetas = leer_etiquetas(ruta_csv, rasgos=RASGOS_POR_DEFECTO)
    assert len(etiquetas) == 22

    por_id["T1:1"]["arquetipo"] = "A"
    cols = columnas_etiquetas(RASGOS_POR_DEFECTO)
    with open(ruta_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(filas)

    generar_plantilla_etiquetas("mini", raiz_trabajo=raiz_trabajo, sobrescribir=False)
    et_conservadas = {
        e.item_id: e for e in leer_etiquetas(ruta_csv, rasgos=RASGOS_POR_DEFECTO)
    }
    assert et_conservadas["T1:1"].arquetipo == "A"

    generar_plantilla_etiquetas("mini", raiz_trabajo=raiz_trabajo, sobrescribir=True)
    et_limpias = {e.item_id: e for e in leer_etiquetas(ruta_csv, rasgos=RASGOS_POR_DEFECTO)}
    assert et_limpias["T1:1"].arquetipo == ""


def test_convertir_legacy_csv_sd2(tmp_path: Path):
    from analisis_profesor.config import RASGOS_LEGACY_SD2
    from analisis_profesor.etiquetas import convertir_legacy_csv, leer_etiquetas

    ruta_legacy = (
        RAIZ
        / "legacy"
        / "estudio_parciales"
        / "cursos"
        / "sistemas_dinamicos_ii"
        / "rasgos_dificultad.csv"
    )
    ruta_salida = tmp_path / "05_etiquetas.csv"
    etiquetas, rasgos = convertir_legacy_csv(ruta_legacy, ruta_salida)

    assert rasgos == RASGOS_LEGACY_SD2
    assert len(etiquetas) == 72
    assert ruta_salida.is_file()

    por_id = {e.item_id: e for e in etiquetas}
    assert {"T4:3a", "T4:13a", "T4:13b", "T4:13c", "T4:14a", "T4:14b"}.issubset(por_id)
    assert por_id["P2_2020-04-29:Q1"].fuente == "T4:13b"
    assert por_id["P2_2020-04-29:Q2"].fuente == "T4:14a"
    assert por_id["P2_2020-04-29:Q4"].fuente == "clase"
    assert por_id["P2_2026-05-04:Q3"].fuente == "P2_2020-04-29:Q2"
    assert por_id["P2_2026-05-04:Q4"].fuente == "P2_2020-04-29:Q4"
    assert por_id["P2_2026-10-19:Q2"].fuente == "P1_2026-03-04:Q3"
    assert por_id["P1_2026-03-04:Q1"].fuente == "T1:19"

    niveles = {e.nivel for e in etiquetas if e.nivel}
    assert niveles == {"casi copia", "adaptación", "nueva"}

    assert por_id["T4:2"].examinable is False
    assert sum(1 for e in etiquetas if not e.examinable) == 1
    assert [por_id[f"P2_2026-05-04:Q{q}"].puntos for q in range(1, 5)] == [0.5, 1.0, 0.5, 0.0]
    assert [por_id[f"P2_2026-10-19:Q{q}"].puntos for q in range(1, 5)] == [2.5, 2.0, 1.0, 1.5]

    assert leer_etiquetas(ruta_salida, rasgos=rasgos) == etiquetas


@pytest.mark.real
def test_convertir_legacy_csv_sd2_real(sd2_dir: Path, tmp_path: Path):
    from analisis_profesor.etiquetas import convertir_legacy_csv

    raiz_trabajo = tmp_path / "trabajo"
    destino_texto = raiz_trabajo / "sd2" / "02_texto"
    preconvertido = RAIZ / "entrada" / "sd2_paso2" / "02_texto"
    if preconvertido.is_dir() and not os.environ.get("AP_SD2_ZIP"):
        shutil.copytree(preconvertido, destino_texto)
    else:
        destino_texto.mkdir(parents=True, exist_ok=True)
        corpus = sd2_dir / "corpus"
        romanos = {"i": "a", "ii": "b", "iii": "c"}
        for nombre in ("P1_2026-03-04", "P2_2020-04-29", "P2_2026-05-04", "P2_2026-10-19"):
            parcial, fecha = nombre.split("_", maxsplit=1)
            raw = (corpus / "examenes" / f"{nombre}.txt").read_text(encoding="utf-8")
            partes = re.split(r"^Pregunta\s+(\d+)\s*(?:\([^)]+\))?\s*", raw, flags=re.M)
            out = [f"# SD-II - {parcial} - {fecha}", "tipo: examen", "duracion_min: 90", ""]
            for i in range(1, len(partes), 2):
                out.extend([f"## Pregunta {partes[i]} (2.5 puntos)", partes[i + 1].strip(), ""])
            (destino_texto / f"{nombre}.md").write_text("\n".join(out), encoding="utf-8")
        for n in range(1, 6):
            lineas = (corpus / "tareas" / f"Tarea_{n}.txt").read_text(encoding="utf-8").splitlines()
            idx = [k for k, ln in enumerate(lineas) if re.match(r"^\s{0,4}\d{1,2}\.\s", ln)]
            bloques = [
                "\n".join(lineas[a:b]) for a, b in zip(idx, idx[1:] + [len(lineas)], strict=True)
            ]
            if n == 4:
                bloques = bloques[:-2] + [bloques[-2] + "\n" + bloques[-1]]
            out = [f"# SD-II - Tarea {n} - 0000-00-00", "tipo: tarea", ""]
            for k, bloque in enumerate(bloques, 1):
                cuerpo = re.sub(r"^\s{0,4}\d{1,2}\.\s*", "", bloque, count=1).strip()
                if n == 4 and k == 3:
                    cuerpo = re.sub(r"(?m)^\s*\(([ab])\)\s*$", r"### \1)", cuerpo)
                elif n == 4 and k in (13, 14):
                    cuerpo = re.sub(
                        r"(?m)^(?:\s*14\.)?\s*(i{1,3})\)\s*",
                        lambda m: f"\n### {romanos[m.group(1)]})\n",
                        cuerpo,
                    )
                out.extend([f"## Ejercicio {k}", cuerpo.strip(), ""])
            (destino_texto / f"T{n}.md").write_text("\n".join(out), encoding="utf-8")

    segmentar_carpeta("sd2", raiz_trabajo=raiz_trabajo)
    items = [
        it for it in leer_jsonl(raiz_trabajo / "sd2" / "03_items.jsonl", Item) if not it.padre_id
    ]
    ids_items = {it.id for it in items}

    etiquetas, _ = convertir_legacy_csv(sd2_dir / "rasgos_dificultad.csv")
    ids_legacy = {e.item_id for e in etiquetas}
    assert ids_legacy.issubset(ids_items)
