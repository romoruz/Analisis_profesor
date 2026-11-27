import importlib.util
from pathlib import Path

from analisis_profesor.config import _parsear_toml_basico, cargar_toml, leer_config_materia
from analisis_profesor.esquemas import Etiqueta
from analisis_profesor.modelo import calcular_modelo

RAIZ = Path(__file__).resolve().parents[1]


def test_materia_sd2_arquetipos_coinciden_con_legacy():
    ruta_toml = RAIZ / "materias" / "sd2" / "materia.toml"
    assert ruta_toml.is_file(), f"Falta {ruta_toml}"

    texto = ruta_toml.read_text(encoding="utf-8")
    assert _parsear_toml_basico(texto) == cargar_toml(texto)

    cfg = leer_config_materia(ruta_toml)
    assert cfg["id"] == "sd2"
    assert cfg["objetivo"]["molde"] == []
    assert cfg["objetivo"]["ya_examinado_este_semestre"] == []

    ruta_legacy = (
        RAIZ
        / "legacy"
        / "estudio_parciales"
        / "cursos"
        / "sistemas_dinamicos_ii"
        / "src"
        / "config_parcial3.py"
    )
    spec = importlib.util.spec_from_file_location("legacy_cfg_sd2", ruta_legacy)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    esperados = {k: (desc, float(mins)) for k, (desc, mins) in mod.ARQUETIPOS.items()}
    assert list(cfg["arquetipos"]) == list("ABCDEFGHIJ")
    assert cfg["arquetipos"] == esperados


def test_dos_corridas_mismo_materia_toml_mismas_claves_k(tmp_path: Path):
    from analisis_profesor.etiquetas import escribir_etiquetas

    ruta_sd2 = RAIZ / "materias" / "sd2" / "materia.toml"
    texto_base = ruta_sd2.read_text(encoding="utf-8")
    texto_corrida = texto_base.replace('molde = []', 'molde = ["P3_2025-11-15"]', 1)

    base_et = [
        Etiqueta(item_id="T1:1", arquetipo="A"),
        Etiqueta(item_id="T1:2", arquetipo="B"),
        Etiqueta(item_id="T1:3", arquetipo="C"),
        Etiqueta(item_id="T1:4", arquetipo="D"),
        Etiqueta(item_id="T1:5", arquetipo="E"),
        Etiqueta(item_id="T1:6", arquetipo="F"),
        Etiqueta(item_id="T1:7", arquetipo="G"),
        Etiqueta(item_id="T1:8", arquetipo="H"),
        Etiqueta(item_id="T1:9", arquetipo="I"),
        Etiqueta(item_id="P3_2025-11-15:Q1", arquetipo="A", fuente="T1:1", nivel="casi copia"),
        Etiqueta(item_id="P3_2025-11-15:Q2", arquetipo="B", fuente="T1:2", nivel="adaptación"),
        Etiqueta(item_id="P3_2025-11-15:Q3", arquetipo="D", fuente="T1:4", nivel="nueva"),
        Etiqueta(item_id="P3_2025-11-15:Q4", arquetipo="G", fuente="T1:7", nivel="casi copia"),
    ]
    et_corrida_1 = base_et
    et_corrida_2 = [*base_et, Etiqueta(item_id="T1:10", arquetipo="J")]

    claves_corridas: list[list[str]] = []
    for nombre, etiquetas in (("corrida1", et_corrida_1), ("corrida2", et_corrida_2)):
        raiz_t = tmp_path / nombre
        carpeta = raiz_t / "sd2"
        carpeta.mkdir(parents=True)
        (carpeta / "materia.toml").write_text(texto_corrida, encoding="utf-8")
        rasgos = leer_config_materia(carpeta)["rasgos"]
        escribir_etiquetas(carpeta / "05_etiquetas.csv", etiquetas, rasgos)
        res = calcular_modelo(
            "sd2",
            raiz_trabajo=raiz_t,
            semilla=2026,
            n_simulaciones=200,
            n_rejilla=20,
            n_sorteos=3,
        )
        claves_corridas.append(res["K"])

    assert claves_corridas[0] == claves_corridas[1] == list("ABCDEFGHIJ")


def test_protocolo_v8_y_empaquetar_kit_incluye_materias():
    proto = (RAIZ / "PROTOCOLO.md").read_text(encoding="utf-8")
    assert "Versión del protocolo: 8" in proto
    assert "materias/<id>/materia.toml" in proto
    assert "úsalo tal cual y no inventes arquetipos" in proto

    script = (RAIZ / "scripts" / "empaquetar_kit.sh").read_text(encoding="utf-8")
    assert "materias/_plantilla" not in script
    assert " materias" in script
