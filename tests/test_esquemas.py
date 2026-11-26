import pytest

from analisis_profesor.esquemas import Etiqueta, Item, escribir_jsonl, leer_jsonl


def test_roundtrip_item(tmp_path):
    it = Item(id="T4:3a", documento_id="T4", tipo_doc="tarea", numero="3a", texto="Retrato fase")
    ruta = tmp_path / "items.jsonl"
    assert escribir_jsonl(ruta, [it]) == 1
    assert list(leer_jsonl(ruta, Item)) == [it]


def test_tipo_invalido():
    with pytest.raises(ValueError):
        Item(id="x", documento_id="x", tipo_doc="examenn", numero="1", texto="")


def test_etiqueta_dok_rango():
    with pytest.raises(ValueError):
        Etiqueta(item_id="a", dok=7)
