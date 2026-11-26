"""Contratos de datos entre pasos del PROTOCOLO. Solo librería estándar (corre en un sandbox).

Regla para agentes: no cambies un campo existente sin actualizar docs/ARQUITECTURA.md y los tests;
agregar campos opcionales (con valor por defecto) sí está permitido.

Archivos en trabajo/<materia>/:
  01_inventario.csv -> Documento     03_items.jsonl -> Item     05_etiquetas.csv -> Etiqueta
  07_modelo.json -> Prediccion       simulacros.json -> Simulacro
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

TIPOS_DOCUMENTO = ("examen", "tarea", "clase", "notas", "temario", "pauta", "otro")
NIVELES_RECICLAJE = ("casi copia", "adaptación", "nueva")
BLOOM = ("recordar", "comprender", "aplicar", "analizar", "evaluar", "crear")


def _en(valor, opciones, campo):
    if valor not in opciones and valor not in ("", None):
        raise ValueError(f"{campo}={valor!r} no está en {opciones}")


@dataclass
class Documento:
    id: str                         # "P2_2026-05-04"
    archivo: str                    # ruta relativa dentro de 00_crudo/
    tipo: str = "otro"
    fecha: str = ""                 # AAAA-MM-DD
    parcial: str = ""               # "P1", "P2", "final"
    metodo_texto: str = ""          # "pymupdf" | "pypdf" | "pdftotext" | "transcrito" | ""
    necesita_transcripcion: bool = False
    sha256: str = ""
    notas: str = ""

    def __post_init__(self):
        _en(self.tipo, TIPOS_DOCUMENTO, "tipo")


@dataclass
class Item:
    """Unidad comparable: pregunta de examen, ejercicio o inciso de tarea, sección de clase."""
    id: str                         # "P2_2026-05-04:Q3", "T4:3a"
    documento_id: str
    tipo_doc: str
    numero: str                     # "3", "3a"
    texto: str
    padre_id: str = ""
    fecha: str = ""
    parcial: str = ""
    puntos_max: float | None = None
    puntos_obtenidos: float | None = None   # dato personal: no sale de trabajo/

    def __post_init__(self):
        _en(self.tipo_doc, TIPOS_DOCUMENTO, "tipo_doc")


@dataclass
class Etiqueta:
    item_id: str
    arquetipo: str = ""
    fuente: str = ""
    nivel: str = ""
    rasgos: dict[str, int] = field(default_factory=dict)
    bloom: str = ""
    dok: int | None = None
    minutos: float | None = None
    pasada: int = 1                 # 1 o 2: doble etiquetado para medir consistencia

    def __post_init__(self):
        _en(self.nivel, NIVELES_RECICLAJE, "nivel")
        _en(self.bloom, BLOOM, "bloom")
        if self.dok is not None and not 1 <= self.dok <= 4:
            raise ValueError(f"dok={self.dok} fuera de 1-4")


@dataclass
class Prediccion:
    arquetipo: str
    p_media: float
    p_q05: float
    p_q95: float
    p_min_sensibilidad: float | None = None
    p_max_sensibilidad: float | None = None


@dataclass
class PreguntaSimulacro:
    arquetipo: str
    banco_id: str
    puntos: float
    dificultad: float
    verificado: bool


@dataclass
class Simulacro:
    numero: int
    semilla: int
    preguntas: list[PreguntaSimulacro]
    dificultad_total: float


def escribir_jsonl(ruta: Path, objetos: Iterable) -> int:
    n = 0
    with open(ruta, "w", encoding="utf-8") as f:
        for o in objetos:
            f.write(json.dumps(asdict(o), ensure_ascii=False) + "\n")
            n += 1
    return n


def leer_jsonl(ruta: Path, clase) -> Iterator:
    nombres = {f.name for f in fields(clase)}
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                d = json.loads(linea)
                yield clase(**{k: v for k, v in d.items() if k in nombres})
