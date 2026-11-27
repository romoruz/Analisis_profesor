import json
import shutil
import sys
from pathlib import Path

import pytest

from analisis_profesor.cli import main

RAIZ = Path(__file__).resolve().parents[1]


def test_leer_y_escribir_banco_mini_preserva_campos(mini_dir: Path, tmp_path: Path):
    from analisis_profesor.banco import escribir_banco, leer_banco

    ejercicios = leer_banco(mini_dir / "08_banco.md")
    assert len(ejercicios) == 26
    assert ejercicios[0].id == "B-A-1"
    assert ejercicios[0].arquetipo == "A"
    assert ejercicios[0].nivel == "casi copia"
    assert ejercicios[0].familia == "A-apreton"
    assert ejercicios[0].basado_en == "T1:1"
    assert ejercicios[0].rasgos["algebra"] == 1
    assert "assert" in ejercicios[0].verificacion

    manuales = [e for e in ejercicios if e.es_manual]
    assert len(manuales) == 6
    assert all(e.arquetipo == "F" for e in manuales)

    copia = tmp_path / "banco_roundtrip.md"
    escribir_banco(ejercicios, copia)
    releyendo = leer_banco(copia)
    assert releyendo == ejercicios


def test_verificar_banco_mini_reproducible_cli_y_respaldo_puro(
    mini_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    from analisis_profesor.banco import verificar_banco

    raiz_trabajo = tmp_path / "trabajo"
    shutil.copytree(mini_dir, raiz_trabajo / "mini")

    res = verificar_banco("mini", raiz_trabajo=raiz_trabajo, timeout_s=10.0)
    assert res["total"] == 26
    assert res["automaticos_ok"] == 20
    assert res["automaticos_fallidos"] == 0
    assert res["manuales"] == 6
    assert res["verificados"] == 26
    assert res["todos_ok"] is True
    assert res["niveles_faltantes_por_arquetipo"] == {}

    ruta_json = raiz_trabajo / "mini" / "08_verificacion.json"
    assert ruta_json.is_file()
    cargado = json.loads(ruta_json.read_text(encoding="utf-8"))
    assert cargado["verificados"] == 26

    monkeypatch.chdir(tmp_path)
    assert main(["verificar", "mini", "--timeout", "10"]) == 0
    salida = capsys.readouterr().out
    assert "08_verificacion.json" in salida
    assert "26/26" in salida


def test_verificar_banco_detecta_fallo_y_timeout(tmp_path: Path):
    from analisis_profesor.banco import EjercicioBanco, escribir_banco, verificar_banco

    raiz_trabajo = tmp_path / "trabajo"
    carpeta = raiz_trabajo / "fallos"
    carpeta.mkdir(parents=True)
    ejercicios = [
        EjercicioBanco(
            id="OK-1",
            arquetipo="A",
            enunciado="Correcto.",
            solucion="Sol.",
            verificacion="assert 2 + 2 == 4",
        ),
        EjercicioBanco(
            id="FAIL-1",
            arquetipo="A",
            enunciado="Falla.",
            solucion="Sol.",
            verificacion="assert 1 == 2, 'desajuste esperado'",
        ),
        EjercicioBanco(
            id="TO-1",
            arquetipo="B",
            enunciado="Lento.",
            solucion="Sol.",
            verificacion="import time\ntime.sleep(2.0)",
        ),
        EjercicioBanco(
            id="MAN-1",
            arquetipo="C",
            enunciado="Demostración.",
            solucion="Prueba.",
            verificacion="manual",
        ),
    ]
    escribir_banco(ejercicios, carpeta / "08_banco.md")

    res = verificar_banco("fallos", raiz_trabajo=raiz_trabajo, timeout_s=0.25)
    assert res["total"] == 4
    assert res["automaticos_ok"] == 1
    assert res["automaticos_fallidos"] == 2
    assert res["manuales"] == 1
    assert res["verificados"] == 2
    assert res["todos_ok"] is False

    por_id = {r["id"]: r for r in res["resultados"]}
    assert por_id["OK-1"]["estado"] == "ok"
    assert por_id["OK-1"]["verificado"] is True
    assert por_id["FAIL-1"]["estado"] == "fallo"
    assert por_id["FAIL-1"]["verificado"] is False
    assert "desajuste esperado" in por_id["FAIL-1"]["error"]
    assert por_id["TO-1"]["estado"] == "timeout"
    assert por_id["TO-1"]["verificado"] is False
    assert por_id["MAN-1"]["estado"] == "manual"
    assert por_id["MAN-1"]["verificado"] is True

    # También falla con código de salida 1 en la CLI si alguno falla
    import os

    viejo_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        assert main(["verificar", "fallos", "--timeout", "0.25"]) == 1
        assert main(["verificar", "fallos", "--id", "OK-1", "--id", "MAN-1"]) == 0
    finally:
        os.chdir(viejo_cwd)


def test_verificar_banco_legacy_sd2_38_automaticos_y_6_manuales(tmp_path: Path):
    pytest.importorskip("sympy")
    from analisis_profesor.banco import convertir_banco_legacy_sd2, verificar_banco

    ruta_sd2 = (
        RAIZ / "legacy" / "estudio_parciales" / "cursos" / "sistemas_dinamicos_ii"
    )
    raiz_trabajo = tmp_path / "trabajo"
    carpeta = raiz_trabajo / "sd2"
    carpeta.mkdir(parents=True)

    ejercicios = convertir_banco_legacy_sd2(ruta_sd2, carpeta / "08_banco.md")
    assert len(ejercicios) == 44
    assert sum(1 for e in ejercicios if e.es_manual) == 6
    # H-bendix tiene verificación automática por divergencia aunque pertenezca al arquetipo H
    por_id = {e.id: e for e in ejercicios}
    assert not por_id["H-bendix"].es_manual
    assert sys.executable

    res = verificar_banco("sd2", raiz_trabajo=raiz_trabajo, timeout_s=30.0)
    assert res["total"] == 44
    assert res["automaticos_ok"] == 38
    assert res["automaticos_fallidos"] == 0
    assert res["manuales"] == 6
    assert res["verificados"] == 44
    assert res["todos_ok"] is True


def test_niveles_faltantes_por_arquetipo_en_banco_y_aviso_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    from analisis_profesor.banco import (
        EjercicioBanco,
        escribir_banco,
        niveles_faltantes_por_arquetipo,
        verificar_banco,
    )

    raiz_trabajo = tmp_path / "trabajo"
    carpeta = raiz_trabajo / "incompleto"
    carpeta.mkdir(parents=True)
    ejercicios = [
        EjercicioBanco(id="A-1", arquetipo="A", nivel="casi copia", verificacion="assert True"),
        EjercicioBanco(id="A-2", arquetipo="A", nivel="adaptación", verificacion="assert True"),
        EjercicioBanco(id="B-1", arquetipo="B", nivel="adaptación", verificacion="assert True"),
    ]
    assert niveles_faltantes_por_arquetipo(ejercicios) == {
        "A": ["nueva"],
        "B": ["casi copia", "nueva"],
    }
    escribir_banco(ejercicios, carpeta / "08_banco.md")
    res = verificar_banco("incompleto", raiz_trabajo=raiz_trabajo, timeout_s=5.0)
    assert res["todos_ok"] is True
    assert res["niveles_faltantes_por_arquetipo"] == {
        "A": ["nueva"],
        "B": ["casi copia", "nueva"],
    }

    monkeypatch.chdir(tmp_path)
    assert main(["verificar", "incompleto"]) == 0
    salida = capsys.readouterr().out
    assert "niveles faltantes" in salida.lower()
    assert "A" in salida and "nueva" in salida
