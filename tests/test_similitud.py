import importlib.util
import json
import os
import re
import shutil
from pathlib import Path

import pytest

from analisis_profesor.cli import main
from analisis_profesor.esquemas import Item, leer_jsonl
from analisis_profesor.segmentacion import segmentar_carpeta

RAIZ = Path(__file__).resolve().parents[1]
_EXAMENES_LEGACY = (
    ("P2_2020-04-29", "E20"),
    ("P1_2026-03-04", "E26m"),
    ("P2_2026-05-04", "E26a"),
    ("P2_2026-10-19", "E26b"),
)


def _legacy_ejercicios_tarea(corpus: Path, n: int) -> list[tuple[str, str]]:
    lineas = (corpus / "tareas" / f"Tarea_{n}.txt").read_text(encoding="utf-8").splitlines()
    idx = [k for k, ln in enumerate(lineas) if re.match(r"^\s{0,4}\d{1,2}\.\s", ln)]
    bloques = ["\n".join(lineas[a:b]) for a, b in zip(idx, idx[1:] + [len(lineas)], strict=True)]
    if n == 4:
        bloques = bloques[:-2] + [bloques[-2] + "\n" + bloques[-1]]
    return [(f"T{n}-{k + 1}", b) for k, b in enumerate(bloques)]


def _legacy_preguntas_examen(corpus: Path, nombre: str, prefijo: str) -> list[tuple[str, str]]:
    t = (corpus / "examenes" / f"{nombre}.txt").read_text(encoding="utf-8")
    partes = re.split(r"^Pregunta\s+(\d)", t, flags=re.M)
    return [(f"{prefijo}-{partes[i]}", partes[i + 1]) for i in range(1, len(partes), 2)]


def _preparar_sd2_paso2(sd2_dir: Path, destino_texto: Path) -> None:
    preconvertido = RAIZ / "entrada" / "sd2_paso2" / "02_texto"
    if preconvertido.is_dir() and not os.environ.get("AP_SD2_ZIP"):
        shutil.copytree(preconvertido, destino_texto)
        return
    destino_texto.mkdir(parents=True, exist_ok=True)
    corpus = sd2_dir / "corpus"
    romanos = {"i": "a", "ii": "b", "iii": "c"}
    for nombre, _ in _EXAMENES_LEGACY:
        parcial, fecha = nombre.split("_", maxsplit=1)
        raw = (corpus / "examenes" / f"{nombre}.txt").read_text(encoding="utf-8")
        partes = re.split(r"^Pregunta\s+(\d+)\s*(?:\([^)]+\))?\s*", raw, flags=re.M)
        out = [
            f"# Sistemas Dinámicos II - {parcial} - {fecha}",
            "tipo: examen",
            "duracion_min: 90",
            "",
        ]
        for i in range(1, len(partes), 2):
            out.extend([f"## Pregunta {partes[i]} (2.5 puntos)", partes[i + 1].strip(), ""])
        (destino_texto / f"{nombre}.md").write_text("\n".join(out), encoding="utf-8")
    for n in range(1, 6):
        ejercicios = _legacy_ejercicios_tarea(corpus, n)
        out = [f"# Sistemas Dinámicos II - Tarea {n} - 0000-00-00", "tipo: tarea", ""]
        for k, (_, bloque) in enumerate(ejercicios, 1):
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


def test_similitud_puro_y_sklearn_en_mini(mini_dir: Path, tmp_path: Path):
    from analisis_profesor.similitud import calcular_similitud

    raiz_trabajo = tmp_path / "trabajo"
    shutil.copytree(mini_dir, raiz_trabajo / "mini")
    segmentar_carpeta("mini", raiz_trabajo=raiz_trabajo)

    res_puro = calcular_similitud("mini", raiz_trabajo=raiz_trabajo, usar_sklearn=False)
    ruta_json = raiz_trabajo / "mini" / "04_similitud.json"
    assert ruta_json.is_file()
    assert json.loads(ruta_json.read_text(encoding="utf-8")) == res_puro

    for clave in ("linea_base", "preguntas_examen", "tareas_entre_si"):
        assert clave in res_puro
    assert {"n_items", "n_pares", "media", "p95"}.issubset(res_puro["linea_base"])

    q1 = res_puro["preguntas_examen"]["P1_2026-04-15:Q1"]
    assert q1["mas_parecidos"][0][0] == "T2:1"
    assert q1["clasificacion"] == "casi copia"

    q2 = res_puro["preguntas_examen"]["P1_2026-04-15:Q2"]
    assert q2["clasificacion"] == "casi copia"
    cands_q2 = dict(q2["mas_parecidos"])
    assert "P1_2025-04-10:Q2" in cands_q2 and cands_q2["P1_2025-04-10:Q2"] > 0.5

    for qid, entrada in res_puro["preguntas_examen"].items():
        if qid.startswith("P1_2025-04-10:"):
            assert all(
                not cand.startswith("P1_2026-04-15:") for cand, _ in entrada["mas_parecidos"]
            )

    if importlib.util.find_spec("sklearn") is not None:
        res_sk = calcular_similitud("mini", raiz_trabajo=raiz_trabajo, usar_sklearn=True)
        assert abs(res_sk["linea_base"]["p95"] - res_puro["linea_base"]["p95"]) <= 1e-3
        for qid, e_puro in res_puro["preguntas_examen"].items():
            e_sk = res_sk["preguntas_examen"][qid]
            assert e_sk["clasificacion"] == e_puro["clasificacion"]
            pares = zip(e_puro["mas_parecidos"], e_sk["mas_parecidos"], strict=True)
            for (c1, s1), (c2, s2) in pares:
                assert c1 == c2
                assert abs(s1 - s2) <= 1e-3


def test_cli_similitud(
    mini_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    shutil.copytree(mini_dir / "02_texto", tmp_path / "trabajo" / "mini" / "02_texto")
    monkeypatch.chdir(tmp_path)

    assert main(["items", "mini"]) == 0
    assert main(["similitud", "mini"]) == 0
    salida = capsys.readouterr().out
    assert "p95" in salida
    assert "P1_2026-04-15:Q1" in salida
    assert (tmp_path / "trabajo" / "mini" / "04_similitud.json").is_file()


def _verificar_regresion_legacy(corpus: Path, ref: dict, *, usar_sklearn: bool) -> None:
    from analisis_profesor.similitud import compara

    tareas = sum((_legacy_ejercicios_tarea(corpus, n) for n in (1, 2, 3, 4)), [])
    r_t5 = compara(
        _legacy_ejercicios_tarea(corpus, 5),
        _legacy_ejercicios_tarea(corpus, 4),
        usar_sklearn=usar_sklearn,
    )
    for k, (cid, sc) in ref["tarea5_vs_tarea4"].items():
        got_id, got_sc = r_t5["top"][k]["mas_parecidos"][0]
        assert got_id == cid
        assert abs(got_sc - sc) <= 0.01

    anteriores: list[tuple[str, str]] = []
    for nombre, pref in _EXAMENES_LEGACY:
        qs = _legacy_preguntas_examen(corpus, nombre, pref)
        a = compara(qs, tareas, usar_sklearn=usar_sklearn)
        b = compara(qs, anteriores, usar_sklearn=usar_sklearn) if len(anteriores) >= 4 else None
        if nombre == "P2_2020-04-29":
            assert abs(a["linea_base_media"] - ref["linea_base_tareas"]["media"]) <= 0.01
            assert abs(a["linea_base_p95"] - ref["linea_base_tareas"]["p95"]) <= 0.01
        for qid, _ in qs:
            assert a["top"][qid]["clasificacion"] == ref[qid]["vs_tareas"]["clasificacion"]
            pares_t = zip(
                a["top"][qid]["mas_parecidos"],
                ref[qid]["vs_tareas"]["mas_parecidos"],
                strict=True,
            )
            for (c1, s1), (c2, s2) in pares_t:
                assert c1 == c2 and abs(s1 - s2) <= 0.01
            if b:
                assert (
                    b["top"][qid]["clasificacion"]
                    == ref[qid]["vs_examenes_previos"]["clasificacion"]
                )
                for (c1, s1), (c2, s2) in zip(
                    b["top"][qid]["mas_parecidos"],
                    ref[qid]["vs_examenes_previos"]["mas_parecidos"],
                    strict=True,
                ):
                    assert c1 == c2 and abs(s1 - s2) <= 0.01
        anteriores.extend(qs)


@pytest.mark.real
def test_regresion_legacy_similitud_sd2(sd2_dir: Path):
    ruta_ref = (
        RAIZ / "legacy" / "estudio_parciales" / "cursos"
        / "sistemas_dinamicos_ii" / "salidas" / "similitud.json"
    )
    ref = json.loads(ruta_ref.read_text(encoding="utf-8"))
    corpus = sd2_dir / "corpus"

    _verificar_regresion_legacy(corpus, ref, usar_sklearn=False)
    if importlib.util.find_spec("sklearn") is not None:
        _verificar_regresion_legacy(corpus, ref, usar_sklearn=True)


@pytest.mark.real
def test_hallazgos_items_nuevos_sd2(sd2_dir: Path, tmp_path: Path):
    from analisis_profesor.similitud import calcular_similitud, compara

    raiz_trabajo = tmp_path / "trabajo"
    _preparar_sd2_paso2(sd2_dir, raiz_trabajo / "sd2" / "02_texto")
    segmentar_carpeta("sd2", raiz_trabajo=raiz_trabajo)
    res = calcular_similitud("sd2", raiz_trabajo=raiz_trabajo)

    etiq = [
        it for it in leer_jsonl(raiz_trabajo / "sd2" / "03_items.jsonl", Item) if not it.padre_id
    ]
    t4 = [(it.id, it.texto) for it in etiq if it.documento_id == "T4"]
    t5 = [(it.id, it.texto) for it in etiq if it.documento_id == "T5"]
    r_t5 = compara(t5, t4)
    assert len(r_t5["top"]) == 10
    assert all(v["clasificacion"] == "casi copia" for v in r_t5["top"].values())
    assert all(v["clasificacion"] == "casi copia" for v in res["tareas_entre_si"]["T5"].values())

    q2_oct = res["preguntas_examen"]["P2_2026-10-19:Q2"]
    assert q2_oct["mas_parecidos"][0][0] == "P1_2026-03-04:Q3"
    assert q2_oct["mas_parecidos"][0][1] > 0.9

    q2_may = res["preguntas_examen"]["P2_2026-05-04:Q2"]
    assert q2_may["mas_parecidos"][0][0] == "P2_2020-04-29:Q1"
    assert q2_may["mas_parecidos"][0][1] > q2_may["linea_base_p95"]

    q3_may = res["preguntas_examen"]["P2_2026-05-04:Q3"]
    assert q3_may["mas_parecidos"][0][0] == "P2_2020-04-29:Q2"
    assert q3_may["mas_parecidos"][0][1] > q3_may["linea_base_p95"]
