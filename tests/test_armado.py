import json
import shutil
from pathlib import Path

import pytest
from conftest import pdflatex_funcional

from analisis_profesor.cli import main
from analisis_profesor.config import RASGOS_LEGACY_SD2

RAIZ = Path(__file__).resolve().parents[1]


def _escribir_toml_sd2_para_armar(destino: Path) -> None:
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
        'A = ["Método del potencial", 25]',
        'B = ["Bifurcación en EDO escalar", 25]',
        'C = ["Bifurcación en sistema plano", 30]',
        'D = ["Sistema polarizable sin parámetro", 25]',
        'E = ["Sistema en polares con parámetro", 30]',
        'F = ["Existencia o no de órbitas periódicas", 20]',
        'G = ["Demostración sobre conjuntos límite", 15]',
        'H = ["Demostración tipo Poincaré-Bendixson", 15]',
        'I = ["Existencia, unicidad e intervalo maximal", 20]',
        'J = ["Funciones de Lyapunov", 20]',
        "",
        "[rasgos]",
    ]
    for nombre, (peso, base, maximo) in RASGOS_LEGACY_SD2.items():
        lineas.append(f"{nombre} = [{peso}, {base}, {maximo}]")
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def test_regresion_exacta_legacy_simulacros_sd2(tmp_path: Path):
    from analisis_profesor.armado import armar_simulacros
    from analisis_profesor.banco import convertir_banco_legacy_sd2

    ruta_sd2 = (
        RAIZ / "legacy" / "estudio_parciales" / "cursos" / "sistemas_dinamicos_ii"
    )
    ref = json.loads((ruta_sd2 / "salidas" / "simulacros.json").read_text(encoding="utf-8"))

    raiz_trabajo = tmp_path / "trabajo"
    carpeta = raiz_trabajo / "sd2"
    carpeta.mkdir(parents=True)
    _escribir_toml_sd2_para_armar(carpeta / "materia.toml")
    shutil.copy2(ruta_sd2 / "salidas" / "dificultad.json", carpeta / "06_dificultad.json")
    shutil.copy2(ruta_sd2 / "salidas" / "modelo_parcial3.json", carpeta / "07_modelo.json")

    ejercicios = convertir_banco_legacy_sd2(ruta_sd2, carpeta / "08_banco.md")
    # Prepara 08_verificacion.json (equivalente a 44/44 verificados en banco legacy)
    # para que la regresión de armado corra también en el sandbox mínimo sin sympy.
    verif = {
        "materia": "sd2",
        "timeout_s": 15.0,
        "total": len(ejercicios),
        "automaticos_ok": sum(1 for e in ejercicios if not e.es_manual),
        "automaticos_fallidos": 0,
        "manuales": sum(1 for e in ejercicios if e.es_manual),
        "verificados": len(ejercicios),
        "todos_ok": True,
        "resultados": [
            {
                "id": e.id,
                "arquetipo": e.arquetipo,
                "nivel": e.nivel,
                "tipo_verificacion": "manual" if e.es_manual else "automatico",
                "estado": "manual" if e.es_manual else "ok",
                "verificado": True,
            }
            for e in ejercicios
        ],
    }
    (carpeta / "08_verificacion.json").write_text(
        json.dumps(verif, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    out = armar_simulacros(
        "sd2",
        raiz_trabajo=raiz_trabajo,
        semilla=13112026,
        tolerancia=1.0,
        usar_numpy=True,
        compilar_pdf=pdflatex_funcional(),
    )

    assert out["meta_dificultad_total"] == ref["meta_dificultad_total"] == 12.82
    assert out["tolerancia"] == ref["tolerancia"] == 1.0
    assert len(out["examenes"]) == len(ref["examenes"]) == 5

    claves_legacy = ("id", "arq", "nivel", "score", "objetivo", "tex")
    for ex_out, ex_ref in zip(out["examenes"], ref["examenes"], strict=True):
        assert ex_out["numero"] == ex_ref["numero"]
        assert ex_out["minutos"] == ex_ref["minutos"]
        assert ex_out["dificultad_total"] == ex_ref["dificultad_total"]
        assert len(ex_out["preguntas"]) == len(ex_ref["preguntas"])
        for q_out, q_ref in zip(ex_out["preguntas"], ex_ref["preguntas"], strict=True):
            assert {k: q_out[k] for k in claves_legacy} == q_ref

    ent = carpeta / "entregables"
    assert (ent / "SIMULACROS.md").is_file()
    assert (ent / "SOLUCIONES.md").is_file()
    assert (ent / "simulacros.tex").is_file()
    if pdflatex_funcional():
        ruta_pdf = ent / "simulacros.pdf"
        assert ruta_pdf.is_file()
        assert ruta_pdf.stat().st_size > 1000


def test_armar_mini_reproducible_sin_fuga_soluciones_cli_y_respaldo_puro(
    mini_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    from analisis_profesor.armado import armar_simulacros
    from analisis_profesor.banco import EjercicioBanco, escribir_banco, leer_banco, verificar_banco
    from analisis_profesor.dificultad import calcular_dificultad
    from analisis_profesor.modelo import calcular_modelo

    raiz_trabajo = tmp_path / "trabajo"
    carpeta = raiz_trabajo / "mini"
    shutil.copytree(mini_dir, carpeta)

    # Agregamos un ejercicio no verificado y con solución trampa para comprobar su exclusión
    ejercicios_base = leer_banco(carpeta / "08_banco.md")
    solucion_prohibida = "MARCADOR_PROHIBIDO_NO_VERIFICADO"
    trampa = EjercicioBanco(
        id="B-A-FAIL",
        arquetipo="A",
        nivel="casi copia",
        familia="A-trampa",
        rasgos=ejercicios_base[0].rasgos,
        enunciado="Ejercicio fallido que nunca debe elegirse.",
        solucion=solucion_prohibida,
        verificacion="assert False",
    )
    escribir_banco(ejercicios_base + [trampa], carpeta / "08_banco.md")

    calcular_dificultad("mini", raiz_trabajo=raiz_trabajo, semilla=2026)
    calcular_modelo(
        "mini", raiz_trabajo=raiz_trabajo, semilla=2026, n_simulaciones=4000, n_rejilla=500
    )
    verif = verificar_banco("mini", raiz_trabajo=raiz_trabajo, timeout_s=10.0)
    assert verif["automaticos_fallidos"] == 1

    res1 = armar_simulacros(
        "mini", raiz_trabajo=raiz_trabajo, semilla=2026, n_simulacros=5, compilar_pdf=False
    )
    ent = carpeta / "entregables"
    bytes_json1 = (carpeta / "simulacros.json").read_text(encoding="utf-8")
    bytes_sim1 = (ent / "SIMULACROS.md").read_text(encoding="utf-8")
    bytes_sol1 = (ent / "SOLUCIONES.md").read_text(encoding="utf-8")
    bytes_tex1 = (ent / "simulacros.tex").read_text(encoding="utf-8")

    res2 = armar_simulacros(
        "mini", raiz_trabajo=raiz_trabajo, semilla=2026, n_simulacros=5, compilar_pdf=False
    )
    assert res1 == res2
    assert (carpeta / "simulacros.json").read_text(encoding="utf-8") == bytes_json1
    assert (ent / "SIMULACROS.md").read_text(encoding="utf-8") == bytes_sim1
    assert (ent / "SOLUCIONES.md").read_text(encoding="utf-8") == bytes_sol1
    assert (ent / "simulacros.tex").read_text(encoding="utf-8") == bytes_tex1

    # Exclusión del ejercicio fallido y no fuga de soluciones
    elegidos = [q for ex in res1["examenes"] for q in ex["preguntas"]]
    assert len(elegidos) == 20
    assert all(q["id"] != "B-A-FAIL" for q in elegidos)
    assert all(q["verificado"] is True for q in elegidos)
    assert solucion_prohibida not in bytes_sim1
    assert solucion_prohibida not in bytes_sol1

    por_id = {e.id: e for e in ejercicios_base}
    for q in elegidos:
        sol_txt = por_id[q["id"]].solucion.strip()
        assert sol_txt
        assert sol_txt not in bytes_json1
        assert sol_txt not in bytes_sim1
        assert sol_txt not in bytes_tex1
        assert sol_txt in bytes_sol1

    # Respaldo en Python puro (sin numpy)
    res_puro = armar_simulacros(
        "mini",
        raiz_trabajo=raiz_trabajo,
        semilla=2026,
        n_simulacros=5,
        usar_numpy=False,
        compilar_pdf=False,
    )
    assert res_puro["meta_dificultad_total"] == res1["meta_dificultad_total"]
    assert len(res_puro["examenes"]) == 5

    # CLI end-to-end (con PDF si pdflatex está instalado)
    monkeypatch.chdir(tmp_path)
    assert main(["armar", "mini", "--n", "5", "--semilla", "2026"]) == 0
    salida = capsys.readouterr().out
    assert "simulacros.json" in salida
    assert "SIMULACROS.md" in salida
    assert "SOLUCIONES.md" in salida
    if pdflatex_funcional():
        assert (ent / "simulacros.pdf").is_file()
