import json
import os
import re
import shutil
from pathlib import Path

import pytest

from analisis_profesor.cli import main
from analisis_profesor.config import RASGOS_LEGACY_SD2, leer_config_materia
from analisis_profesor.esquemas import Etiqueta, Prediccion
from analisis_profesor.etiquetas import convertir_legacy_csv
from analisis_profesor.segmentacion import segmentar_carpeta
from analisis_profesor.similitud import calcular_similitud

RAIZ = Path(__file__).resolve().parents[1]


def _escribir_toml_sd2_modelo(destino: Path) -> None:
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


def test_modelo_valor_conocido_simetrico_y_respaldo_puro():
    from analisis_profesor.modelo import corre

    cfg_sim = {
        "arquetipos": {
            "A": ("Tipo A", 20),
            "B": ("Tipo B", 20),
            "C": ("Tipo C", 20),
            "D": ("Tipo D", 20),
        },
        "material": {"A": 2.0, "B": 2.0, "C": 2.0, "D": 2.0},
        "molde": {},
        "pi_molde": (1, 1),
        "rotacion": [],
        "rho": 0.6,
        "N": {2: 1.0},
        "ventana": (30, 50),
        "beta": 6,
        "suavizado": 1.0,
    }
    res_np = corre(cfg_sim, R=20_000, R_rejilla=0, semilla=2026, malla=None, usar_numpy=True)
    res_py = corre(cfg_sim, R=5_000, R_rejilla=0, semilla=2026, malla=None, usar_numpy=False)

    # Con 4 tipos simétricos y N=2 preguntas distintas por examen, P(salir k) = 2/4 = 0.5
    for k in ("A", "B", "C", "D"):
        assert abs(res_np["p_base"][k] - 0.5) <= 0.02
        assert abs(res_py["p_base"][k] - 0.5) <= 0.03
        assert abs(res_py["p_base"][k] - res_np["p_base"][k]) <= 0.03


def test_regresion_exacta_legacy_modelo_sd2():
    from analisis_profesor.modelo import corre, sortea

    ruta_cfg = (
        RAIZ
        / "legacy"
        / "estudio_parciales"
        / "cursos"
        / "sistemas_dinamicos_ii"
        / "src"
        / "config_parcial3.py"
    )
    ruta_ref = (
        RAIZ
        / "legacy"
        / "estudio_parciales"
        / "cursos"
        / "sistemas_dinamicos_ii"
        / "salidas"
        / "modelo_parcial3.json"
    )
    ref = json.loads(ruta_ref.read_text(encoding="utf-8"))

    ns: dict = {}
    exec(compile(ruta_cfg.read_text(encoding="utf-8"), str(ruta_cfg), "exec"), ns)
    cfg = ns["CFG"]
    malla = ns["MALLA"]
    semilla_sorteo = ns["SEMILLA_SORTEO"]
    niveles = ns["NIVELES"]

    out = corre(cfg, R=20_000, R_rejilla=3000, semilla=2026, malla=malla, usar_numpy=True)
    niv, pn = list(niveles), list(niveles.values())

    def _dec(_k, rng):
        return {"nivel": str(rng.choice(niv, p=pn))}

    out["sorteos_independientes"] = sortea(
        cfg, 5, semilla_sorteo, decora=_dec, usar_numpy=True
    )
    out["sorteos"] = sortea(
        cfg, 5, semilla_sorteo, decora=_dec, balancear=out["p_base"], usar_numpy=True
    )

    assert out["K"] == ref["K"]
    assert out["p_base"] == ref["p_base"]
    assert out["p_min"] == ref["p_min"]
    assert out["p_max"] == ref["p_max"]
    assert out["combinaciones_rejilla"] == ref["combinaciones_rejilla"]
    assert [list(c) for c in out["combinaciones_top"]] == ref["combinaciones_top"]
    assert out["sorteos_independientes"] == ref["sorteos_independientes"]
    assert out["sorteos"] == ref["sorteos"]


def test_modelo_mini_reproducible_cli_y_respaldo_puro(
    mini_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    from analisis_profesor.modelo import calcular_modelo

    raiz_trabajo = tmp_path / "trabajo"
    shutil.copytree(mini_dir, raiz_trabajo / "mini")

    res1 = calcular_modelo(
        "mini", raiz_trabajo=raiz_trabajo, semilla=2026, n_simulaciones=4000, n_rejilla=500
    )
    ruta_json = raiz_trabajo / "mini" / "07_modelo.json"
    bytes1 = ruta_json.read_text(encoding="utf-8")

    res2 = calcular_modelo(
        "mini", raiz_trabajo=raiz_trabajo, semilla=2026, n_simulaciones=4000, n_rejilla=500
    )
    bytes2 = ruta_json.read_text(encoding="utf-8")
    assert res1 == res2
    assert bytes1 == bytes2

    assert res1["exploratorio"] is True
    assert res1["n_simulaciones"] == 4000
    assert res1["n_examenes_molde"] == 2
    assert res1["parametros_derivados"]["pi_molde"] == [2.0, 4.0]
    dem_inf = res1["demostracion_inferencia"]
    assert dem_inf["n_simulaciones"] == 4000
    assert dem_inf["n_examenes_molde"] == 2
    assert dem_inf["exploratorio"] is True
    assert dem_inf["ic_simulacion"][0] <= dem_inf["p_base"] <= dem_inf["ic_simulacion"][1]
    assert len(res1["predicciones"]) == 6
    for pred_dict in res1["predicciones"]:
        pred = Prediccion(**pred_dict)
        assert 0.0 <= pred.p_q05 <= pred.p_media <= pred.p_q95 <= 1.0
        assert pred.p_min_sensibilidad <= pred.p_media <= pred.p_max_sensibilidad

    res_py = calcular_modelo(
        "mini",
        raiz_trabajo=raiz_trabajo,
        semilla=2026,
        n_simulaciones=2000,
        n_rejilla=300,
        usar_numpy=False,
    )
    for k in res1["K"]:
        assert abs(res_py["p_base"][k] - res1["p_base"][k]) <= 0.05

    monkeypatch.chdir(tmp_path)
    assert main(["modelo", "mini", "--simulaciones", "2000", "--rejilla", "300"]) == 0
    salida_cli = capsys.readouterr().out
    assert "07_modelo.json" in salida_cli
    assert "IC 5-95" in salida_cli


@pytest.mark.real
def test_modelo_sd2_calculado_desde_etiquetas(sd2_dir: Path, tmp_path: Path):
    from analisis_profesor.etiquetas import leer_etiquetas
    from analisis_profesor.modelo import calcular_modelo, construir_cfg_desde_etiquetas

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

    items = segmentar_carpeta("sd2", raiz_trabajo=raiz_trabajo)
    sim = calcular_similitud("sd2", raiz_trabajo=raiz_trabajo)
    _escribir_toml_sd2_modelo(raiz_trabajo / "sd2" / "materia.toml")
    convertir_legacy_csv(
        sd2_dir / "rasgos_dificultad.csv", raiz_trabajo / "sd2" / "05_etiquetas.csv"
    )

    cfg_mat = leer_config_materia(raiz_trabajo / "sd2")
    etiqs = leer_etiquetas(raiz_trabajo / "sd2" / "05_etiquetas.csv", rasgos=cfg_mat["rasgos"])
    cfg_calc, _ = construir_cfg_desde_etiquetas(
        cfg_mat, etiqs, items=items, similitud=sim
    )

    assert cfg_calc["molde"] == {"A": 2, "B": 2, "D": 1, "E": 1, "G": 2}
    assert cfg_calc["rotacion"] == ["D"]
    assert cfg_calc["pi_molde"] == (4.0, 6.0)
    assert cfg_calc["demostracion"] == {"arquetipos": ["G", "H"], "beta": (3.0, 2.0)}

    ruta_ref = (
        RAIZ
        / "legacy"
        / "estudio_parciales"
        / "cursos"
        / "sistemas_dinamicos_ii"
        / "salidas"
        / "modelo_parcial3.json"
    )
    ref = json.loads(ruta_ref.read_text(encoding="utf-8"))

    res = calcular_modelo("sd2", raiz_trabajo=raiz_trabajo, semilla=2026)
    assert res["exploratorio"] is True
    assert res["n_examenes_molde"] == 2
    diffs = {k: abs(res["p_base"][k] - ref["p_base"][k]) for k in ref["K"]}
    assert max(diffs.values()) <= 0.08
    for pred in res["predicciones"]:
        assert 0.0 <= pred["p_q05"] <= pred["p_media"] <= pred["p_q95"] <= 1.0
    for k in res["K"]:
        assert abs(res["p_muestras_media"][k] - res["p_base"][k]) <= 0.03


def test_media_muestras_ic_contra_p_base_mini_y_sd2(mini_dir: Path, tmp_path: Path):
    from analisis_profesor.modelo import calcular_modelo, corre

    raiz_trabajo = tmp_path / "trabajo"
    shutil.copytree(mini_dir, raiz_trabajo / "mini")
    res_mini = calcular_modelo(
        "mini", raiz_trabajo=raiz_trabajo, semilla=2026, n_simulaciones=20_000, n_rejilla=500
    )
    assert "p_muestras_media" in res_mini
    for k in res_mini["K"]:
        assert abs(res_mini["p_muestras_media"][k] - res_mini["p_base"][k]) <= 0.03
        assert 0.0 <= res_mini["p_q05"][k] <= res_mini["p_base"][k] <= res_mini["p_q95"][k] <= 1.0

    ruta_cfg = (
        RAIZ
        / "legacy"
        / "estudio_parciales"
        / "cursos"
        / "sistemas_dinamicos_ii"
        / "src"
        / "config_parcial3.py"
    )
    ns: dict = {}
    exec(compile(ruta_cfg.read_text(encoding="utf-8"), str(ruta_cfg), "exec"), ns)
    res_sd2 = corre(
        ns["CFG"], R=20_000, R_rejilla=0, semilla=2026, malla=None, incluir_intervalos=True
    )
    assert "p_muestras_media" in res_sd2
    for k in res_sd2["K"]:
        assert abs(res_sd2["p_muestras_media"][k] - res_sd2["p_base"][k]) <= 0.03
        assert 0.0 <= res_sd2["p_q05"][k] <= res_sd2["p_base"][k] <= res_sd2["p_q95"][k] <= 1.0


def test_rotacion_solo_semestre_en_curso_ignora_examen_viejo_otro_parcial():
    from analisis_profesor.modelo import (
        construir_cfg_desde_etiquetas,
        corre,
        examen_en_semestre_actual,
    )

    assert examen_en_semestre_actual("2026-10-19", semestre="2026-II") is True
    assert examen_en_semestre_actual("2026-03-04", semestre="2026-II") is False
    assert examen_en_semestre_actual("2026-03-04", semestre="2026-I") is True
    assert examen_en_semestre_actual("2025-10-19", semestre="2026-I") is False
    assert examen_en_semestre_actual("2026-08-20", inicio_semestre="2026-08-15") is True
    assert examen_en_semestre_actual("2026-05-04", inicio_semestre="2026-08-15") is False
    assert examen_en_semestre_actual("", semestre="2026-II") is False

    rasgos = {"r": (1.0, 0, 5)}
    cfg_mat = {
        "id": "prueba_rot",
        "semestre": "2026-II",
        "objetivo": {
            "parcial": "P3",
            "fecha": "2026-11-25",
            "molde": ["P3_2025-11-20"],
            "ya_examinado_este_semestre": [],
            "inicio_semestre": "",
        },
        "formato": {"preguntas": {"2": 1.0}, "minutos": [30, 50]},
        "arquetipos": {
            "A": ("Tema A", 20),
            "B": ("Tema B", 20),
            "C": ("Tema C", 20),
            "D": ("Tema D", 20),
        },
        "rasgos": rasgos,
        "modelo": {"semilla": 2026, "beta": 6.0, "suavizado": 0.3, "rho": 0.6},
    }
    base_et = [
        Etiqueta(item_id="T1:1", arquetipo="A", rasgos={"r": 1}),
        Etiqueta(item_id="T1:2", arquetipo="B", rasgos={"r": 1}),
        Etiqueta(item_id="T1:3", arquetipo="C", rasgos={"r": 1}),
        Etiqueta(item_id="T1:4", arquetipo="D", rasgos={"r": 1}),
        Etiqueta(item_id="P3_2025-11-20:Q1", arquetipo="A", fuente="T1:1", nivel="adaptación"),
        Etiqueta(item_id="P3_2025-11-20:Q2", arquetipo="B", fuente="T1:2", nivel="adaptación"),
        # Examen viejo de otro parcial y semestre anterior (2026-I): NO debe rotar
        Etiqueta(item_id="P1_2026-03-04:Q1", arquetipo="A", fuente="T1:1", nivel="casi copia"),
        # Examen reciente del semestre en curso (2026-II): SÍ debe rotar
        Etiqueta(item_id="P2_2026-10-19:Q1", arquetipo="D", fuente="T1:4", nivel="adaptación"),
    ]
    cfg_calc, deriv = construir_cfg_desde_etiquetas(cfg_mat, base_et)
    assert cfg_calc["rotacion"] == ["D"]
    assert "A" not in cfg_calc["rotacion"]
    assert deriv["examenes_rotacion"] == ["P2_2026-10-19"]

    # Con inicio_semestre explícito en 2026-09-01: 2026-05-04 tampoco rota, 2026-09-10 sí
    cfg_mat_ini = {
        **cfg_mat,
        "semestre": "",
        "objetivo": {**cfg_mat["objetivo"], "inicio_semestre": "2026-09-01"},
    }
    et_ini = base_et[:-2] + [
        Etiqueta(item_id="P1_2026-05-04:Q1", arquetipo="C", fuente="T1:3", nivel="adaptación"),
        Etiqueta(item_id="P2_2026-09-10:Q1", arquetipo="D", fuente="T1:4", nivel="adaptación"),
    ]
    cfg_ini, deriv_ini = construir_cfg_desde_etiquetas(cfg_mat_ini, et_ini)
    assert cfg_ini["rotacion"] == ["D"]
    assert deriv_ini["examenes_rotacion"] == ["P2_2026-09-10"]

    # Verifica que A no queda castigado en el modelo final respecto a no tener P1_2026-03-04
    res_con_viejo = corre(cfg_calc, R=4000, R_rejilla=0, semilla=2026, malla=None)
    cfg_sin_viejo, _ = construir_cfg_desde_etiquetas(
        cfg_mat, [e for e in base_et if not e.item_id.startswith("P1_2026-03-04:")]
    )
    assert cfg_sin_viejo["rotacion"] == cfg_calc["rotacion"]
    res_sin_viejo = corre(cfg_sin_viejo, R=4000, R_rejilla=0, semilla=2026, malla=None)
    assert abs(res_con_viejo["p_base"]["A"] - res_sin_viejo["p_base"]["A"]) <= 0.02
