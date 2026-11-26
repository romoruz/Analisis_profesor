import hashlib
import zipfile
from pathlib import Path

import pytest

from analisis_profesor.cli import diagnostico, main


def test_respaldos_pdf_orden(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import analisis_profesor.pdf as pdf_mod

    ruta = tmp_path / "doc.pdf"
    ruta.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(pdf_mod, "_con_fitz", lambda _r: ["página 1"])
    monkeypatch.setattr(pdf_mod, "_con_pypdf", lambda _r: ["página pypdf"])
    monkeypatch.setattr(pdf_mod, "_con_pdfplumber", lambda _r: ["página plumber"])
    monkeypatch.setattr(pdf_mod, "_con_pdftotext", lambda _r: ["página poppler"])

    r1 = pdf_mod.extraer_pdf(ruta)
    assert r1.metodo == "pymupdf" and r1.paginas == ["página 1"]

    monkeypatch.setattr(pdf_mod, "_con_fitz", lambda _r: None)
    assert pdf_mod.extraer_pdf(ruta).metodo == "pypdf"

    monkeypatch.setattr(pdf_mod, "_con_pypdf", lambda _r: None)
    assert pdf_mod.extraer_pdf(ruta).metodo == "pdfplumber"

    monkeypatch.setattr(pdf_mod, "_con_pdfplumber", lambda _r: None)
    assert pdf_mod.extraer_pdf(ruta).metodo == "pdftotext"

    monkeypatch.setattr(pdf_mod, "_con_pdftotext", lambda _r: None)
    r5 = pdf_mod.extraer_pdf(ruta)
    assert r5.metodo == "" and r5.paginas == []


def test_extraccion_pdf_real_pymupdf(tmp_path: Path):
    pymupdf = pytest.importorskip("pymupdf")
    from analisis_profesor.pdf import extraer_pdf

    ruta = tmp_path / "prueba.pdf"
    doc = pymupdf.open()
    for idx in (1, 2):
        pagina = doc.new_page()
        lineas = [
            f"Página {idx} línea {k}: contenido de prueba suficientemente largo."
            for k in range(8)
        ]
        pagina.insert_text((72, 72), "\n".join(lineas))
    doc.save(ruta)
    doc.close()

    res = extraer_pdf(ruta)
    assert res.metodo == "pymupdf"
    assert len(res.paginas) == 2
    assert res.chars_por_pagina >= 200


def test_ingesta_zip_sintetico_reglas_y_pendientes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import analisis_profesor.ingesta as ing_mod
    from analisis_profesor.pdf import TextoPDF

    ruta_zip = tmp_path / "curso.zip"
    with zipfile.ZipFile(ruta_zip, "w") as zf:
        zf.writestr("examenes/Parcial_1_2026-04-10.pdf", b"%PDF-ex")
        zf.writestr("examenes/P2_2026-05-20.jpg", b"\xff\xd8\xff\xe0img")
        zf.writestr("tareas/Tarea_1.pdf", b"%PDF-t1")
        zf.writestr("clases/Escaneo_Clase1.pdf", b"%PDF-scan")
        zf.writestr("suelto.pdf", b"%PDF-suelto")
        zf.writestr("__MACOSX/._Tarea_1.pdf", b"basura")
        zf.writestr(".DS_Store", b"basura")

    falsos = {
        "Parcial_1_2026-04-10.pdf": TextoPDF(["Pregunta 1 de examen. " * 15], "pymupdf"),
        "Tarea_1.pdf": TextoPDF(["Ejercicio 1 de la tarea uno. " * 12], "pymupdf"),
        "Escaneo_Clase1.pdf": TextoPDF(["Escaneo corto"], "pymupdf"),
        "suelto.pdf": TextoPDF(
            ["Temario del curso y bibliografía, 15 de agosto de 2026. " * 6], "pymupdf"
        ),
    }
    monkeypatch.setattr(ing_mod, "extraer_pdf", lambda r: falsos[r.name])

    raiz_trabajo = tmp_path / "trabajo"
    docs = ing_mod.ingestar(ruta_zip, "sintetico", raiz_trabajo=raiz_trabajo)
    base = raiz_trabajo / "sintetico"

    assert len(docs) == 5
    por_id = {d.id: d for d in docs}
    assert set(por_id) == {
        "Parcial_1_2026-04-10",
        "P2_2026-05-20",
        "Tarea_1",
        "Escaneo_Clase1",
        "suelto",
    }

    for d in docs:
        crudo = base / "00_crudo" / d.archivo
        assert crudo.is_file()
        assert d.sha256 == hashlib.sha256(crudo.read_bytes()).hexdigest()

    assert ing_mod.leer_inventario(base / "01_inventario.csv") == docs

    ex1 = por_id["Parcial_1_2026-04-10"]
    assert (ex1.tipo, ex1.fecha, ex1.parcial, ex1.necesita_transcripcion) == (
        "examen",
        "2026-04-10",
        "P1",
        True,
    )
    ex2 = por_id["P2_2026-05-20"]
    assert (ex2.tipo, ex2.fecha, ex2.parcial, ex2.necesita_transcripcion) == (
        "examen",
        "2026-05-20",
        "P2",
        True,
    )
    t1 = por_id["Tarea_1"]
    assert t1.tipo == "tarea" and not t1.necesita_transcripcion
    assert (base / "02_texto" / "Tarea_1.md").is_file()

    c1 = por_id["Escaneo_Clase1"]
    assert c1.tipo == "clase" and c1.necesita_transcripcion
    assert not (base / "02_texto" / "Escaneo_Clase1.md").exists()

    suelto = por_id["suelto"]
    assert (suelto.tipo, suelto.fecha, suelto.necesita_transcripcion) == (
        "temario",
        "2026-08-15",
        False,
    )
    assert (base / "02_texto" / "suelto.md").is_file()

    pendientes = (base / "pendientes_transcripcion.txt").read_text(encoding="utf-8").splitlines()
    assert pendientes == [
        "clases/Escaneo_Clase1.pdf",
        "examenes/P2_2026-05-20.jpg",
        "examenes/Parcial_1_2026-04-10.pdf",
    ]


def test_ingesta_rechaza_zip_slip(tmp_path: Path):
    from analisis_profesor.ingesta import ingestar

    ruta_zip = tmp_path / "malo.zip"
    with zipfile.ZipFile(ruta_zip, "w") as zf:
        zf.writestr("../escape.txt", "contenido malicioso")

    with pytest.raises(ValueError):
        ingestar(ruta_zip, "malo", raiz_trabajo=tmp_path / "trabajo")


def test_cli_ingesta_subcomando(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ruta_zip = tmp_path / "mini.zip"
    with zipfile.ZipFile(ruta_zip, "w") as zf:
        zf.writestr("notas/apuntes.txt", "Resumen de ecuaciones lineales.\n")

    monkeypatch.chdir(tmp_path)
    assert main(["ingesta", str(ruta_zip), "--materia", "cli_test"]) == 0
    assert (tmp_path / "trabajo" / "cli_test" / "01_inventario.csv").is_file()
    assert (tmp_path / "trabajo" / "cli_test" / "02_texto" / "apuntes.md").is_file()


@pytest.mark.real
def test_ingesta_sd2_real(sd2_dir: Path, tmp_path: Path):
    from analisis_profesor.ingesta import ingestar

    datos_dir = sd2_dir / "datos"
    zip_sd2 = tmp_path / "sd2_material.zip"
    with zipfile.ZipFile(zip_sd2, "w") as zf:
        for ruta in sorted(datos_dir.rglob("*")):
            if ruta.is_file():
                zf.write(ruta, ruta.relative_to(datos_dir).as_posix())

    raiz_trabajo = tmp_path / "trabajo"
    docs = ingestar(zip_sd2, "sd2", raiz_trabajo=raiz_trabajo)
    base = raiz_trabajo / "sd2"
    assert len(docs) == 9

    por_id = {d.id: d for d in docs}
    esperados_ex = {
        "P1_2026-03-04": ("2026-03-04", "P1"),
        "P2_2020-04-29": ("2020-04-29", "P2"),
        "P2_2026-05-04": ("2026-05-04", "P2"),
        "P2_2026-10-19": ("2026-10-19", "P2"),
    }
    for doc_id, (fecha, parcial) in esperados_ex.items():
        d = por_id[doc_id]
        assert (d.tipo, d.fecha, d.parcial, d.necesita_transcripcion) == (
            "examen",
            fecha,
            parcial,
            True,
        )

    for i in range(1, 6):
        d = por_id[f"Tarea_{i}"]
        assert d.tipo == "tarea"
        assert len(d.sha256) == 64

    if diagnostico()["lector_pdf"] is not None:
        for i in range(1, 6):
            assert not por_id[f"Tarea_{i}"].necesita_transcripcion
            assert (base / "02_texto" / f"Tarea_{i}.md").read_text(encoding="utf-8").strip()
        pendientes = (
            (base / "pendientes_transcripcion.txt").read_text(encoding="utf-8").splitlines()
        )
        assert pendientes == [
            "examenes/P1_2026-03-04.jpg",
            "examenes/P2_2020-04-29.jpg",
            "examenes/P2_2026-05-04.jpg",
            "examenes/P2_2026-10-19.jpg",
        ]
