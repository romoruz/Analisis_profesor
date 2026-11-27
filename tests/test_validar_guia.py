import json
import shutil
from pathlib import Path

import pytest

from analisis_profesor.cli import main
from analisis_profesor.modelo import calcular_modelo
from analisis_profesor.segmentacion import segmentar_carpeta


def _preparar_mini_con_modelo(mini_dir: Path, tmp_path: Path):
    raiz_trabajo = tmp_path / "trabajo"
    carpeta = raiz_trabajo / "mini"
    shutil.copytree(mini_dir, carpeta)
    items = segmentar_carpeta("mini", raiz_trabajo=raiz_trabajo)
    modelo = calcular_modelo(
        "mini",
        raiz_trabajo=raiz_trabajo,
        semilla=2026,
        n_simulaciones=500,
        n_rejilla=100,
        n_sorteos=5,
    )
    return raiz_trabajo, carpeta, items, modelo


def _formatear_guia(
    modelo: dict,
    evidencias: list[str],
    *,
    porcentajes: bool = False,
    cabecera_ic: str = "Intervalo 90 %",
    excluir_k: str | None = None,
    alterar_k: str | None = None,
    ev_sin_id_k: str | None = None,
    cuerpo_extra: str = "",
) -> str:
    orden_k = sorted(modelo["K"], key=lambda k: modelo["p_min"][k], reverse=True)
    filas: list[str] = []
    for idx, k in enumerate(orden_k):
        if k == excluir_k:
            continue
        p = modelo["p_base"][k]
        q05, q95 = modelo["p_q05"][k], modelo["p_q95"][k]
        mn, mx = modelo["p_min"][k], modelo["p_max"][k]
        if k == alterar_k:
            p = 0.01 if p > 0.2 else 0.99
            q05 = 0.01 if q05 > 0.2 else 0.50
            q95 = 0.99 if q95 < 0.8 else 0.10
            mn = 0.01 if mn > 0.2 else 0.60
            mx = 0.99 if mx < 0.8 else 0.65

        if porcentajes:
            p_txt = f"{round(p * 100)} %"
            ic_txt = f"{round(q05 * 100)}–{round(q95 * 100)} %"
            sens_txt = f"[{round(mn * 100)} %, {round(mx * 100)} %]"
        else:
            p_txt = f"{p:.2f}"
            ic_txt = f"[{q05:.2f}, {q95:.2f}]"
            sens_txt = f"[{mn:.2f}, {mx:.2f}]"

        ev = "clase" if k == ev_sin_id_k else evidencias[idx % len(evidencias)]
        nombre = modelo["nombres"][k]
        filas.append(f"| {k} | {nombre} | {p_txt} | {ic_txt} | {sens_txt} | {ev} |")

    ej1 = evidencias[0]
    ej2 = evidencias[min(1, len(evidencias) - 1)]
    return "\n".join(
        [
            "# Guía del P1: Mini curso (Prof. Mini)",
            "",
            "## 0. Ficha de ejecución",
            "- Protocolo v6, modo reducido",
            "- Referencia: https://ejemplo.org:8080/doc generado a las 12:30 (IC:90%).",
            "",
            "## 1. Qué entra y qué supuse",
            "Entran los temas del temario.",
            "",
            "## 2. Cómo examina este profesor",
            f"### Reciclaje\nSimilitud fuerte entre {ej1} y {ej2}.",
            "",
            "## 3. Temas por probabilidad",
            f"| Tipo | Descripción | p | {cabecera_ic} | Mín-máx sensibilidad | Evidencia (ids) |",
            "|---|---|---|---|---|---|",
            *filas,
            "",
            "## 4. Lista de estudio literal",
            f"- Revisar `{ej1}` y `{ej2}`.{cuerpo_extra}",
            "",
            "## 5. Plan de estudio hasta el 2026-05-01",
            "Repasar primero el material literal.",
            "",
            "## 6. Limitaciones",
            "Muestra pequeña.",
            "",
        ]
    )


def test_validar_guia_valida_decimales_y_porcentajes(
    mini_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    from analisis_profesor.validacion_guia import validar_guia

    raiz_trabajo, carpeta, items, modelo = _preparar_mini_con_modelo(mini_dir, tmp_path)
    evidencias = [it.id for it in items if not it.padre_id]
    assert evidencias

    entregables = carpeta / "entregables"
    entregables.mkdir(parents=True, exist_ok=True)
    ruta_guia = entregables / "GUIA_PARCIAL.md"
    ruta_guia.write_text(_formatear_guia(modelo, evidencias), encoding="utf-8")

    res = validar_guia("mini", raiz_trabajo=raiz_trabajo)
    assert res["valida"] is True
    assert res["ids_inexistentes"] == []
    assert res["discrepancias_modelo"] == []
    assert res["arquetipos_faltantes"] == []
    assert res["filas_sin_evidencia"] == []
    assert res["temas_validados"] == len(modelo["K"])

    ruta_json = carpeta / "09_validacion_guia.json"
    assert ruta_json.is_file()
    assert json.loads(ruta_json.read_text(encoding="utf-8")) == res

    monkeypatch.chdir(tmp_path)
    assert main(["validar-guia", "mini"]) == 0
    salida = capsys.readouterr().out
    assert "VÁLIDA" in salida

    ruta_pct = tmp_path / "guia_porcentajes.md"
    ruta_pct.write_text(_formatear_guia(modelo, evidencias, porcentajes=True), encoding="utf-8")
    res_pct = validar_guia("mini", raiz_trabajo=raiz_trabajo, ruta_guia=ruta_pct)
    assert res_pct["valida"] is True
    assert main(["validar-guia", "mini", "--guia", str(ruta_pct)]) == 0


def test_validar_guia_detecta_errores_y_cli_devuelve_1(
    mini_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from analisis_profesor.validacion_guia import validar_guia

    raiz_trabajo, carpeta, items, modelo = _preparar_mini_con_modelo(mini_dir, tmp_path)
    evidencias = [it.id for it in items if not it.padre_id]
    k0 = modelo["K"][0]
    k_ultimo = modelo["K"][-1]

    # (a) IDs inventados sin falsos positivos en URL ni hora
    guia_ids = tmp_path / "guia_ids.md"
    guia_ids.write_text(
        _formatear_guia(
            modelo,
            ["P1_2024-01-01:Q4", *evidencias[1:]],
            cuerpo_extra=" También ver T9:99.",
        ),
        encoding="utf-8",
    )
    res_ids = validar_guia("mini", raiz_trabajo=raiz_trabajo, ruta_guia=guia_ids)
    assert res_ids["valida"] is False
    assert res_ids["ids_inexistentes"] == ["P1_2024-01-01:Q4", "T9:99"]

    # (b) Cifras alteradas respecto a 07_modelo.json
    guia_cifras = tmp_path / "guia_cifras.md"
    guia_cifras.write_text(_formatear_guia(modelo, evidencias, alterar_k=k0), encoding="utf-8")
    res_cifras = validar_guia("mini", raiz_trabajo=raiz_trabajo, ruta_guia=guia_cifras)
    assert res_cifras["valida"] is False
    campos_malos = {d["campo"] for d in res_cifras["discrepancias_modelo"]}
    assert {"p", "intervalo_90", "sensibilidad"}.issubset(campos_malos)

    # (c) Cabecera de intervalo incorrecta (95 % cuando el modelo es 5-95 %)
    guia_cab = tmp_path / "guia_cab.md"
    guia_cab.write_text(
        _formatear_guia(modelo, evidencias, cabecera_ic="Intervalo 95 %"), encoding="utf-8"
    )
    res_cab = validar_guia("mini", raiz_trabajo=raiz_trabajo, ruta_guia=guia_cab)
    assert res_cab["valida"] is False
    assert any("95" in err and "90" in err for err in res_cab["errores"])

    # (d) Fila sin id existente en Evidencia
    guia_sin_ev = tmp_path / "guia_sin_ev.md"
    guia_sin_ev.write_text(
        _formatear_guia(modelo, evidencias, ev_sin_id_k=k0), encoding="utf-8"
    )
    res_sin_ev = validar_guia("mini", raiz_trabajo=raiz_trabajo, ruta_guia=guia_sin_ev)
    assert res_sin_ev["valida"] is False
    assert res_sin_ev["filas_sin_evidencia"] == [k0]

    # (e) Arquetipo faltante en la tabla
    guia_falta = tmp_path / "guia_falta.md"
    guia_falta.write_text(_formatear_guia(modelo, evidencias, excluir_k=k_ultimo), encoding="utf-8")
    res_falta = validar_guia("mini", raiz_trabajo=raiz_trabajo, ruta_guia=guia_falta)
    assert res_falta["valida"] is False
    assert res_falta["arquetipos_faltantes"] == [k_ultimo]

    # (f) CLI devuelve 1 ante guía inválida o inexistente
    monkeypatch.chdir(tmp_path)
    assert main(["validar-guia", "mini", "--guia", str(guia_cifras)]) == 1
    assert main(["validar-guia", "mini", "--guia", str(tmp_path / "no_existe.md")]) == 1
