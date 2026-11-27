import csv
import json
import shutil
from pathlib import Path

import pytest

from analisis_profesor.cli import main


def test_acuerdo_doble_pasada_detecta_rasgos_inestables_y_cli(
    mini_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    from analisis_profesor.acuerdo import calcular_acuerdo

    raiz_trabajo = tmp_path / "trabajo"
    carpeta = raiz_trabajo / "mini"
    shutil.copytree(mini_dir, carpeta)

    # Agregamos una segunda pasada (pasada=2) sobre 10 ítems:
    # acuerdo alto en arquetipo/entregables, fuerte desacuerdo en algebra.
    ruta_csv = carpeta / "05_etiquetas.csv"
    with open(ruta_csv, encoding="utf-8", newline="") as f:
        lector = csv.DictReader(f)
        campos = list(lector.fieldnames or [])
        filas_base = [fila for fila in lector if (fila.get("arquetipo") or "-") != "-"]

    nuevas_filas = []
    for idx, fila in enumerate(filas_base[:10]):
        copia = dict(fila)
        copia["pasada"] = "2"
        if idx % 2 == 0 and fila.get("algebra"):
            copia["algebra"] = "2" if fila["algebra"] == "0" else "0"
        if idx == 1:
            copia["dok"] = "4" if fila["dok"] != "4" else "1"
        nuevas_filas.append(copia)

    with open(ruta_csv, "a", encoding="utf-8", newline="") as f:
        esc = csv.DictWriter(f, fieldnames=campos)
        for fila in nuevas_filas:
            esc.writerow(fila)

    res1 = calcular_acuerdo("mini", raiz_trabajo=raiz_trabajo, semilla=2026)
    ruta_json = carpeta / "05_acuerdo.json"
    bytes1 = ruta_json.read_text(encoding="utf-8")
    res2 = calcular_acuerdo("mini", raiz_trabajo=raiz_trabajo, semilla=2026)
    assert res1 == res2
    assert ruta_json.read_text(encoding="utf-8") == bytes1

    assert res1["n_items"] == 10
    assert res1["exploratorio"] is False
    assert res1["muestra_recomendada_ok"] is False
    assert "algebra" in res1["rasgos_inestables"]
    assert res1["por_campo"]["arquetipo"]["alfa"] == 1.0
    assert res1["por_campo"]["entregables"]["alfa"] == 1.0
    assert any(d["campo"] == "algebra" for d in res1["desacuerdos"])

    res_py = calcular_acuerdo("mini", raiz_trabajo=raiz_trabajo, semilla=2026, usar_numpy=False)
    assert abs(res_py["por_campo"]["algebra"]["alfa"] - res1["por_campo"]["algebra"]["alfa"]) < 1e-9

    monkeypatch.chdir(tmp_path)
    assert main(["acuerdo", "mini", "--semilla", "2026"]) == 0
    salida = capsys.readouterr().out
    assert "05_acuerdo.json" in salida
    assert "algebra" in salida


def test_acuerdo_contra_etiquetas_externas_y_error_sin_segunda_pasada(
    mini_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    from analisis_profesor.acuerdo import calcular_acuerdo

    raiz_trabajo = tmp_path / "trabajo"
    carpeta = raiz_trabajo / "mini"
    shutil.copytree(mini_dir, carpeta)

    # Con solo 1 pasada debe avisar claramente y devolver código 1 en CLI
    monkeypatch.chdir(tmp_path)
    assert main(["acuerdo", "mini"]) == 1
    assert "pasada" in capsys.readouterr().err.lower()

    # Comparación contra archivo humano (--contra)
    contra = tmp_path / "humano.csv"
    with open(carpeta / "05_etiquetas.csv", encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
        campos = list(filas[0].keys())
    for fila in filas:
        if fila["item_id"] == "P1_2025-04-10:Q1":
            fila["tecnica"] = "3"
    with open(contra, "w", encoding="utf-8", newline="") as f:
        esc = csv.DictWriter(f, fieldnames=campos)
        esc.writeheader()
        esc.writerows(filas)

    res = calcular_acuerdo("mini", raiz_trabajo=raiz_trabajo, ruta_contra=contra, semilla=2026)
    assert res["n_items"] >= 10
    assert any(
        d["item_id"] == "P1_2025-04-10:Q1" and d["campo"] == "tecnica"
        for d in res["desacuerdos"]
    )
    assert main(["acuerdo", "mini", "--contra", str(contra)]) == 0
    assert (carpeta / "05_acuerdo.json").is_file()
    assert json.loads((carpeta / "05_acuerdo.json").read_text(encoding="utf-8")) == res
