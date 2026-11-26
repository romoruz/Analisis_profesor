import json
import os
import re
import shutil
from pathlib import Path

import pytest

from analisis_profesor.cli import main
from analisis_profesor.config import RASGOS_LEGACY_SD2, RASGOS_POR_DEFECTO
from analisis_profesor.etiquetas import convertir_legacy_csv
from analisis_profesor.segmentacion import segmentar_carpeta

RAIZ = Path(__file__).resolve().parents[1]


def _escribir_toml_sd2_legacy(destino: Path) -> None:
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
        'A = ["Potencial", 25]',
        'B = ["Bifurcación 2o orden", 25]',
        'C = ["Bifurcación plano", 30]',
        'D = ["Polares sin parámetro", 25]',
        'E = ["Polares con parámetro", 30]',
        'F = ["Órbitas periódicas", 20]',
        'G = ["Conjuntos límite", 15]',
        'H = ["Poincaré-Bendixson", 15]',
        'I = ["Existencia y unicidad", 20]',
        'J = ["Lyapunov", 20]',
        "",
        "[rasgos]",
    ]
    for nombre, (peso, base, maximo) in RASGOS_LEGACY_SD2.items():
        lineas.append(f"{nombre} = [{peso}, {base}, {maximo}]")
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def test_score_item_calculado_a_mano():
    from analisis_profesor.dificultad import score_item

    # Anexo A: den = 0.6*4 + 1.2*2 + 0.5*3 + 1.2*3 + 1.0*2 + 0.6*2 + 0.5*2 + 0.4*3 = 15.3
    # Con entregables=3 (delta 2), parametro=1 (delta 1), dimension=2 (delta 1), resto en base:
    # num = 0.6*2 + 1.2*1 + 0.5*1 = 2.9 -> score = 10 * 2.9 / 15.3
    rasgos_item = {
        "entregables": 3,
        "parametro": 1,
        "dimension": 2,
        "tecnica": 0,
        "demostracion": 0,
        "algebra": 0,
        "computo": 0,
        "casos": 1,
    }
    esperado = 10.0 * 2.9 / 15.3
    assert abs(score_item(rasgos_item, RASGOS_POR_DEFECTO) - esperado) < 1e-12


def test_dificultad_mini_reproducible_y_respaldo_puro(
    mini_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    from analisis_profesor.dificultad import calcular_dificultad

    raiz_trabajo = tmp_path / "trabajo"
    shutil.copytree(mini_dir, raiz_trabajo / "mini")

    res1 = calcular_dificultad("mini", raiz_trabajo=raiz_trabajo, semilla=2026)
    ruta_json = raiz_trabajo / "mini" / "06_dificultad.json"
    bytes1 = ruta_json.read_text(encoding="utf-8")

    res2 = calcular_dificultad("mini", raiz_trabajo=raiz_trabajo, semilla=2026)
    bytes2 = ruta_json.read_text(encoding="utf-8")
    assert res1 == res2
    assert bytes1 == bytes2

    for bloque in ("todo_el_curso", "alcance_objetivo"):
        sec = res1[bloque]
        assert "ic_bootstrap" in sec["comparacion_medias"]
        assert "n" in sec["delta_pares_inferencia"]
        assert "ic_bca" in sec["delta_pares_inferencia"]
        assert "p_permutacion" in sec["delta_pares_inferencia"]
        assert "p_wilcoxon" in sec["delta_pares_inferencia"]
        assert sec["delta_pares_inferencia"]["exploratorio"] is True
        assert sec["examenes"]["exploratorio"] is True

    omit_mini = {
        "n": 1,
        "items": [{"examen": "P1_2026-04-15:Q4", "fuente": "C1_grafos:3", "nivel": "nueva"}],
    }
    assert res1["todo_el_curso"]["pares_omitidos"] == omit_mini
    assert res1["alcance_objetivo"]["pares_omitidos"] == omit_mini
    assert res1["todo_el_curso"]["delta_pares_inferencia"]["n"] == 7
    assert res1["todo_el_curso"]["delta_pares_inferencia"]["n_omitidos"] == 1
    assert res1["todo_el_curso"]["reciclaje_por_fuente"]["desde_examen_previo"]["exitos"] == 1
    assert res1["todo_el_curso"]["reciclaje_por_fuente"]["fuente_no_item"]["exitos"] == 1

    assert res1["contra_calificaciones"]["n"] == 4
    assert res1["contra_calificaciones"]["exploratorio"] is True
    assert "ic_bootstrap" in res1["contra_calificaciones"]

    res_puro = calcular_dificultad(
        "mini", raiz_trabajo=raiz_trabajo, semilla=2026, usar_numpy=False, usar_scipy=False
    )
    assert res_puro["todo_el_curso"]["scores"] == res1["todo_el_curso"]["scores"]
    assert res_puro["dificultad_total_examen"] == res1["dificultad_total_examen"]
    assert (
        abs(
            res_puro["contra_calificaciones"]["spearman"]
            - res1["contra_calificaciones"]["spearman"]
        )
        <= 1e-6
    )

    monkeypatch.chdir(tmp_path)
    assert main(["dificultad", "mini", "--semilla", "2026"]) == 0
    salida_cli = capsys.readouterr().out
    assert "06_dificultad.json" in salida_cli
    assert "BCa" in salida_cli or "IC" in salida_cli


def test_regresion_legacy_dificultad_sd2(tmp_path: Path):
    from analisis_profesor.dificultad import calcular_dificultad

    ruta_legacy_csv = (
        RAIZ
        / "legacy"
        / "estudio_parciales"
        / "cursos"
        / "sistemas_dinamicos_ii"
        / "rasgos_dificultad.csv"
    )
    ruta_legacy_json = (
        RAIZ
        / "legacy"
        / "estudio_parciales"
        / "cursos"
        / "sistemas_dinamicos_ii"
        / "salidas"
        / "dificultad.json"
    )
    ref = json.loads(ruta_legacy_json.read_text(encoding="utf-8"))

    raiz_trabajo = tmp_path / "trabajo"
    carpeta_sd2 = raiz_trabajo / "sd2"
    carpeta_sd2.mkdir(parents=True)
    _escribir_toml_sd2_legacy(carpeta_sd2 / "materia.toml")
    convertir_legacy_csv(ruta_legacy_csv, carpeta_sd2 / "05_etiquetas.csv")

    res = calcular_dificultad("sd2", raiz_trabajo=raiz_trabajo, semilla=2026)

    # 1. Totales por examen: 13.37 (13.4), 12.27 (12.3), 7.97 (8.0), 8.35 (8.4)
    assert res["dificultad_total_examen"] == ref["dificultad_total_examen"]

    # 2. Deltas por pares y medias globales
    assert res["todo_el_curso"]["tareas"]["n"] == ref["todo_el_curso"]["tareas"]["n"]
    assert res["todo_el_curso"]["tareas"]["media"] == ref["todo_el_curso"]["tareas"]["media"]
    assert res["todo_el_curso"]["examenes"]["n"] == ref["todo_el_curso"]["examenes"]["n"]
    assert res["todo_el_curso"]["examenes"]["media"] == ref["todo_el_curso"]["examenes"]["media"]
    assert res["todo_el_curso"]["delta_medias"] == ref["todo_el_curso"]["delta_medias"]
    assert res["todo_el_curso"]["delta_pares_media"] == ref["todo_el_curso"]["delta_pares_media"]
    assert abs(res["todo_el_curso"]["delta_pares_media"]) == 0.27

    alc = res["alcance_objetivo"]
    ref_p3 = ref["alcance_parcial3"]
    assert alc["tareas"]["n"] == ref_p3["tareas"]["n"]
    assert alc["tareas"]["media"] == ref_p3["tareas"]["media"]
    assert alc["examenes"]["n"] == ref_p3["examenes"]["n"]
    assert alc["examenes"]["media"] == ref_p3["examenes"]["media"]
    assert alc["delta_medias"] == ref_p3["delta_medias"]
    assert alc["delta_pares_media"] == ref_p3["delta_pares_media"] == 0.4

    # 3. Inferencia agregada con incertidumbre y bandera exploratorio
    omit_sd2 = {
        "n": 1,
        "items": [{"examen": "P2_2020-04-29:Q4", "fuente": "clase", "nivel": "nueva"}],
    }
    assert res["todo_el_curso"]["pares_omitidos"] == omit_sd2
    assert alc["pares_omitidos"] == omit_sd2
    assert res["todo_el_curso"]["reciclaje_por_fuente"]["fuente_no_item"]["exitos"] == 1
    assert alc["reciclaje_por_fuente"]["fuente_no_item"]["exitos"] == 1

    inf_todo = res["todo_el_curso"]["delta_pares_inferencia"]
    assert inf_todo["n"] == 15
    assert inf_todo["n_omitidos"] == 1
    assert inf_todo["exploratorio"] is False
    assert inf_todo["metodo_permutacion"] == "exacta"
    assert inf_todo["ic_bca"][0] <= inf_todo["media"] <= inf_todo["ic_bca"][1]

    inf_alc = alc["delta_pares_inferencia"]
    assert inf_alc["n"] == 8
    assert inf_alc["n_omitidos"] == 1
    assert inf_alc["exploratorio"] is True
    assert inf_alc["metodo_permutacion"] == "exacta"
    assert abs(inf_alc["p_minimo_alcanzable"] - 2.0 / 256) < 1e-12

    # 4. Robustez de pesos: >= 0.99 con el mismo signo
    assert res["robustez_todo"]["n_pares"] == 15
    assert res["robustez_todo"]["exploratorio"] is False
    assert res["robustez_alcance"]["n_pares"] == 8
    assert res["robustez_alcance"]["exploratorio"] is True
    assert res["robustez_todo"]["frac_mismo_signo_pares"] >= 0.99
    assert res["robustez_alcance"]["frac_mismo_signo_pares"] >= 0.99
    assert (
        res["robustez_todo"]["delta_pares_p5_p50_p95"]
        == ref["robustez_todo"]["delta_pares_p5_p50_p95"]
    )
    assert (
        res["robustez_alcance"]["delta_pares_p5_p50_p95"]
        == ref["robustez_parcial3"]["delta_pares_p5_p50_p95"]
    )

    # 5. Por arquetipo, objetivo y Spearman contra calificaciones
    assert res["por_arquetipo"] == ref["por_arquetipo"]
    for arq_id, obj_ref in ref["objetivo"].items():
        for k, v in obj_ref.items():
            assert res["objetivo"][arq_id][k] == v

    cal = res["contra_calificaciones"]
    assert cal["n"] == ref["contra_calificaciones"]["n"] == 8
    assert cal["spearman"] == ref["contra_calificaciones"]["spearman"] == 0.685
    assert cal["p_valor"] == ref["contra_calificaciones"]["p_valor"] == 0.061
    assert cal["exploratorio"] is True
    assert cal["ic_bootstrap"][0] <= cal["spearman"] <= cal["ic_bootstrap"][1]


@pytest.mark.real
def test_dificultad_sd2_con_items_reales(sd2_dir: Path, tmp_path: Path):
    from analisis_profesor.dificultad import calcular_dificultad

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
    _escribir_toml_sd2_legacy(raiz_trabajo / "sd2" / "materia.toml")
    convertir_legacy_csv(
        sd2_dir / "rasgos_dificultad.csv", raiz_trabajo / "sd2" / "05_etiquetas.csv"
    )

    res = calcular_dificultad("sd2", raiz_trabajo=raiz_trabajo, semilla=2026)
    assert res["alcance_objetivo"]["delta_pares_media"] == 0.4
    assert res["todo_el_curso"]["delta_pares_media"] == -0.27
    assert res["dificultad_total_examen"]["P2_2020-04-29"] == 13.37
