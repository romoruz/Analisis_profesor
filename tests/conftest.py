import os
import zipfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
RUTA_ZIP_SD2_DEFECTO = RAIZ / "entrada" / "estudio_parciales.zip"


def extraer_sd2(ruta_zip: Path, destino: Path) -> Path:
    """Descomprime el zip de estudio_parciales y devuelve la ruta a SD-II."""
    if not ruta_zip.is_file():
        pytest.skip(f"No existe el material real de SD-II en {ruta_zip}")

    with zipfile.ZipFile(ruta_zip) as archivo_zip:
        archivo_zip.extractall(destino)

    candidatos = (
        destino / "estudio_parciales" / "cursos" / "sistemas_dinamicos_ii",
        destino / "cursos" / "sistemas_dinamicos_ii",
    )
    for ruta in candidatos:
        if ruta.is_dir():
            return ruta
    raise FileNotFoundError(
        f"No se encontró cursos/sistemas_dinamicos_ii al extraer {ruta_zip}"
    )


@pytest.fixture(scope="session")
def mini_dir() -> Path:
    """Ruta al curso inventado tests/fixtures/mini."""
    return RAIZ / "tests" / "fixtures" / "mini"


@pytest.fixture(scope="session")
def ruta_zip_sd2() -> Path:
    """Ruta al zip real de SD-II o salta la prueba si no existe."""
    env_zip = os.environ.get("AP_SD2_ZIP")
    ruta = Path(env_zip) if env_zip else RUTA_ZIP_SD2_DEFECTO
    if not ruta.is_file():
        pytest.skip(f"No existe el material real de SD-II en {ruta}")
    return ruta


@pytest.fixture(scope="session")
def sd2_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Descomprime SD-II real en un directorio temporal o salta si no existe."""
    env_zip = os.environ.get("AP_SD2_ZIP")
    ruta_zip = Path(env_zip) if env_zip else RUTA_ZIP_SD2_DEFECTO
    if not ruta_zip.is_file() and not env_zip:
        respaldos = (
            RAIZ / "entrada" / "sd2" / "cursos" / "sistemas_dinamicos_ii",
            RAIZ / "entrada" / "sd2",
        )
        for respaldo in respaldos:
            if (respaldo / "datos").is_dir():
                return respaldo
    return extraer_sd2(ruta_zip, tmp_path_factory.mktemp("sd2"))
