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


@pytest.mark.parametrize("raiz_zip", ["estudio_parciales", "Parciales"])
def test_clasificacion_prioridad_ignora_carpetas_superiores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raiz_zip: str
):
    import analisis_profesor.ingesta as ing_mod
    from analisis_profesor.pdf import TextoPDF

    ruta_zip = tmp_path / f"{raiz_zip}.zip"
    with zipfile.ZipFile(ruta_zip, "w") as zf:
        zf.writestr(f"{raiz_zip}/tareas/Tarea_1.pdf", b"%PDF-t1")
        zf.writestr(f"{raiz_zip}/clases/Clase7.pdf", b"%PDF-c7")
        zf.writestr(f"{raiz_zip}/tareas/documento.pdf", b"%PDF-doc")
        zf.writestr(f"{raiz_zip}/examenes/Pauta_Prueba1.pdf", b"%PDF-p1")

    monkeypatch.setattr(
        ing_mod,
        "extraer_pdf",
        lambda _r: TextoPDF(["Contenido neutro del documento. " * 12], "pymupdf"),
    )

    docs = ing_mod.ingestar(ruta_zip, f"raiz_{raiz_zip}", raiz_trabajo=tmp_path / "trabajo")
    por_nombre = {Path(d.archivo).name: d for d in docs}

    assert por_nombre["Tarea_1.pdf"].tipo == "tarea"
    assert por_nombre["Clase7.pdf"].tipo == "clase"
    assert por_nombre["documento.pdf"].tipo == "tarea"
    assert por_nombre["Pauta_Prueba1.pdf"].tipo == "pauta"


def test_extensiones_no_material_formato_no_soportado(tmp_path: Path):
    from analisis_profesor.ingesta import ingestar

    ruta_zip = tmp_path / "mixto.zip"
    with zipfile.ZipFile(ruta_zip, "w") as zf:
        zf.writestr("src/04_modelo_parcial3.py", "print(1)\n")
        zf.writestr("salidas/modelo.json", "{}\n")
        zf.writestr("rasgos.csv", "a,b\n1,2\n")
        zf.writestr("simulacros.tex", "\\documentclass{article}\n")
        zf.writestr("correr.sh", "#!/bin/sh\n")
        zf.writestr("guia.docx", b"PK\x03\x04docx")
        zf.writestr("clase1.pptx", b"PK\x03\x04pptx")
        zf.writestr("examenes/P1_2026-03-04.jpg", b"\xff\xd8\xff\xe0img")

    raiz_trabajo = tmp_path / "trabajo"
    docs = ingestar(ruta_zip, "mixto", raiz_trabajo=raiz_trabajo)
    base = raiz_trabajo / "mixto"
    por_archivo = {d.archivo: d for d in docs}

    no_material = (
        "src/04_modelo_parcial3.py",
        "salidas/modelo.json",
        "rasgos.csv",
        "simulacros.tex",
        "correr.sh",
        "guia.docx",
        "clase1.pptx",
    )
    for arch in no_material:
        d = por_archivo[arch]
        assert d.tipo == "otro"
        assert d.necesita_transcripcion is False
        assert "formato no soportado" in d.notas
        assert not (base / "02_texto" / f"{d.id}.md").exists()

    pendientes = (base / "pendientes_transcripcion.txt").read_text(encoding="utf-8").splitlines()
    assert pendientes == ["examenes/P1_2026-03-04.jpg"]


@pytest.mark.real
def test_ingesta_sd2_real(ruta_zip_sd2: Path, tmp_path: Path):
    from analisis_profesor.ingesta import EXTENSIONES_IMAGEN, ingestar

    raiz_trabajo = tmp_path / "trabajo"
    docs = ingestar(ruta_zip_sd2, "sd2", raiz_trabajo=raiz_trabajo)
    base = raiz_trabajo / "sd2"
    por_archivo = {d.archivo: d for d in docs}

    sd2_datos = [d for d in docs if "sistemas_dinamicos_ii/datos/" in d.archivo]
    assert len(sd2_datos) == 9
    assert sum(1 for d in sd2_datos if d.tipo == "examen") == 4
    assert sum(1 for d in sd2_datos if d.tipo == "tarea") == 5

    clases_lp = [
        d
        for d in docs
        if Path(d.archivo).name.startswith("Clase") and d.archivo.endswith("_LP.pdf")
    ]
    assert len(clases_lp) == 10
    assert all(d.tipo == "clase" for d in clases_lp)

    pautas = [
        d
        for d in docs
        if Path(d.archivo).name.startswith("Pauta_Prueba") and d.archivo.endswith(".pdf")
    ]
    assert len(pautas) == 2
    assert all(d.tipo == "pauta" for d in pautas)

    for d in docs:
        if Path(d.archivo).suffix.lower() in {".py", ".json", ".csv", ".tex", ".sh"}:
            assert d.tipo == "otro"
            assert not d.necesita_transcripcion
            assert "formato no soportado" in d.notas

    if diagnostico()["lector_pdf"] is not None:
        pendientes = (
            (base / "pendientes_transcripcion.txt").read_text(encoding="utf-8").splitlines()
        )
        for foto in (
            "estudio_parciales/cursos/sistemas_dinamicos_ii/datos/examenes/P1_2026-03-04.jpg",
            "estudio_parciales/cursos/sistemas_dinamicos_ii/datos/examenes/P2_2020-04-29.jpg",
            "estudio_parciales/cursos/sistemas_dinamicos_ii/datos/examenes/P2_2026-05-04.jpg",
            "estudio_parciales/cursos/sistemas_dinamicos_ii/datos/examenes/P2_2026-10-19.jpg",
        ):
            assert foto in pendientes
        for arch in pendientes:
            assert (
                Path(arch).suffix.lower() in EXTENSIONES_IMAGEN
                or por_archivo[arch].tipo == "examen"
            )
