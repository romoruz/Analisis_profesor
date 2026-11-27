import csv
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import pdflatex_funcional

from analisis_profesor.config import RASGOS_LEGACY_SD2

RAIZ = Path(__file__).resolve().parents[1]


def _escribir_toml_sd2_completo(destino: Path) -> None:
    lineas = [
        'id = "sd2"',
        'nombre = "Sistemas Dinámicos II"',
        'profesor = "SD-II"',
        'semestre = "2026-II"',
        "",
        "[objetivo]",
        'parcial = "P3"',
        'molde = ["P2_2020-04-29", "P2_2026-05-04"]',
        "",
        "[formato]",
        'preguntas = { "4" = 1.0 }',
        "minutos = [75, 100]",
        "puntos_por_pregunta = [2.5, 2.5, 2.5, 2.5]",
        "",
        "[arquetipos]",
        'A = ["Método del potencial: U, equilibrios, estabilidad, retrato fase", 25]',
        'B = ["Bifurcación en EDO de 2o orden o escalar: lambda_0, retratos y diagrama", 25]',
        'C = ["Bifurcación en sistema plano: ceroclinas, equilibrios según el parámetro", 30]',
        'D = ["Sistema polarizable sin parámetro: ciclos límite, omega y alfa límites", 25]',
        'E = ["Sistema en polares con parámetro: valores de bifurcación y retratos", 30]',
        'F = ["Existencia o no de órbitas periódicas (anillo atrapante, Dulac, energía)", 20]',
        'G = ["Demostración sobre conjuntos límite (omega(p))", 15]',
        'H = ["Demostración tipo Poincaré-Bendixson / no existencia de órbitas", 15]',
        'I = ["Existencia, unicidad e intervalo maximal; simetría de soluciones", 20]',
        'J = ["Funciones de Lyapunov: estabilidad y cuenca", 20]',
        "",
        "[rasgos]",
    ]
    for nombre, (peso, base, maximo) in RASGOS_LEGACY_SD2.items():
        lineas.append(f"{nombre} = [{peso}, {base}, {maximo}]")
    lineas.extend(
        [
            "",
            "[modelo]",
            "semilla = 2026",
            "beta = 6",
            "suavizado = 0.3",
            "rho = 0.6",
        ]
    )
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def test_e2e_mini_pipeline_completo(mini_dir: Path, tmp_path: Path):
    ruta_script = RAIZ / "scripts" / "e2e.sh"
    assert ruta_script.is_file(), "Falta scripts/e2e.sh"

    trabajo_mini = tmp_path / "trabajo" / "mini"
    shutil.copytree(mini_dir, trabajo_mini)
    etiquetas_antes = (trabajo_mini / "05_etiquetas.csv").read_text(encoding="utf-8")

    proc = subprocess.run(
        ["bash", str(ruta_script), "mini", "--raiz-trabajo", str(tmp_path), "--semilla", "2026"],
        env={**os.environ, "PYTHON": os.sys.executable},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"

    assert (trabajo_mini / "03_items.jsonl").is_file()
    assert (trabajo_mini / "04_similitud.json").is_file()
    assert (trabajo_mini / "06_dificultad.json").is_file()
    assert (trabajo_mini / "07_modelo.json").is_file()
    assert (trabajo_mini / "08_verificacion.json").is_file()
    assert (trabajo_mini / "simulacros.json").is_file()

    # Verifica que plantilla-etiquetas no sobrescribió etiquetas ya llenas
    filas_despues = {
        f["item_id"]: f
        for f in csv.DictReader(
            (trabajo_mini / "05_etiquetas.csv").read_text(encoding="utf-8").splitlines()
        )
    }
    filas_antes = {f["item_id"]: f for f in csv.DictReader(etiquetas_antes.splitlines())}
    assert len(filas_despues) == len(filas_antes) == 22
    assert filas_despues == filas_antes

    dif = json.loads((trabajo_mini / "06_dificultad.json").read_text(encoding="utf-8"))
    assert "conclusion" in dif["todo_el_curso"]["delta_pares_inferencia"]

    mod = json.loads((trabajo_mini / "07_modelo.json").read_text(encoding="utf-8"))
    for k in mod["K"]:
        assert abs(mod["p_muestras_media"][k] - mod["p_base"][k]) <= 0.03

    verif = json.loads((trabajo_mini / "08_verificacion.json").read_text(encoding="utf-8"))
    assert verif["verificados"] == 26 and verif["todos_ok"] is True

    sim = json.loads((trabajo_mini / "simulacros.json").read_text(encoding="utf-8"))
    assert len(sim["examenes"]) == 5
    ent = trabajo_mini / "entregables"
    assert (ent / "SIMULACROS.md").is_file()
    assert (ent / "SOLUCIONES.md").is_file()
    assert (ent / "simulacros.tex").is_file()
    if pdflatex_funcional():
        assert (ent / "simulacros.pdf").is_file()

    # Comprueba también la rama --zip ejecutando ingesta dentro del flujo e2e sobre copia limpia
    import zipfile

    zip_path = tmp_path / "mini_extra.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("notas/Notas_Extra.txt", "Notas de ejemplo sobre árboles generadores.")

    tmp2 = tmp_path / "con_zip"
    shutil.copytree(mini_dir, tmp2 / "trabajo" / "mini")
    proc_zip = subprocess.run(
        [
            "bash",
            str(ruta_script),
            "mini",
            "--zip",
            str(zip_path),
            "--raiz-trabajo",
            str(tmp2),
            "--semilla",
            "2026",
            "--sin-pdf",
        ],
        env={**os.environ, "PYTHON": os.sys.executable},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_zip.returncode == 0, f"STDOUT:\n{proc_zip.stdout}\nSTDERR:\n{proc_zip.stderr}"
    assert (tmp2 / "trabajo" / "mini" / "01_inventario.csv").is_file()
    assert (tmp2 / "trabajo" / "mini" / "simulacros.json").is_file()


@pytest.mark.real
def test_e2e_sd2_real(sd2_dir: Path, tmp_path: Path):
    pytest.importorskip("sympy")
    from analisis_profesor.banco import convertir_banco_legacy_sd2
    from analisis_profesor.etiquetas import convertir_legacy_csv
    from analisis_profesor.ingesta import ingestar

    ruta_zip = Path(os.environ.get("AP_SD2_ZIP") or (RAIZ / "entrada" / "estudio_parciales.zip"))
    if not ruta_zip.is_file():
        pytest.skip(f"No existe zip real en {ruta_zip}")

    ingestar(ruta_zip, "sd2", raiz_trabajo=tmp_path / "trabajo")

    carpeta = tmp_path / "trabajo" / "sd2"
    destino_texto = carpeta / "02_texto"
    shutil.rmtree(destino_texto, ignore_errors=True)
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

    _escribir_toml_sd2_completo(carpeta / "materia.toml")
    convertir_legacy_csv(sd2_dir / "rasgos_dificultad.csv", carpeta / "05_etiquetas.csv")
    convertir_banco_legacy_sd2(sd2_dir, carpeta / "08_banco.md")

    proc = subprocess.run(
        [
            "bash",
            str(RAIZ / "scripts" / "e2e.sh"),
            "sd2",
            "--raiz-trabajo",
            str(tmp_path),
            "--semilla",
            "2026",
        ],
        env={**os.environ, "PYTHON": os.sys.executable},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"

    assert (carpeta / "01_inventario.csv").is_file()
    dif = json.loads((carpeta / "06_dificultad.json").read_text(encoding="utf-8"))
    assert dif["todo_el_curso"]["delta_pares_media"] == -0.27
    assert dif["alcance_objetivo"]["delta_pares_media"] == 0.4

    verif = json.loads((carpeta / "08_verificacion.json").read_text(encoding="utf-8"))
    assert verif["total"] == 44 and verif["automaticos_ok"] == 38 and verif["manuales"] == 6

    sim = json.loads((carpeta / "simulacros.json").read_text(encoding="utf-8"))
    assert len(sim["examenes"]) == 5
    if pdflatex_funcional():
        assert (carpeta / "entregables" / "simulacros.pdf").is_file()
