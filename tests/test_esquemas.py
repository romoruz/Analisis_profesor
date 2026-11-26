from analisis_profesor.esquemas import Documento, Etiqueta, Item, TipoDocumento


def test_roundtrip_item():
    it = Item(id="T4:3a", documento_id="T4", numero="3a", texto="Dibujar el retrato fase")
    assert Item.model_validate_json(it.model_dump_json()) == it


def test_documento_tipo():
    d = Documento(id="P2_2026-05-04", materia="sd2", tipo=TipoDocumento.examen, archivo="x.jpg")
    assert d.tipo == "examen"


def test_etiqueta_dok_rango():
    import pytest
    with pytest.raises(ValueError):
        Etiqueta(item_id="a", etiquetador="humano:x", dok=7)
