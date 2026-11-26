"""Contratos de datos entre fases. TODA fase lee y escribe estos modelos (JSONL en salidas/).

Regla para agentes: no cambies un campo existente sin actualizar docs/ARQUITECTURA.md y los tests;
agregar campos opcionales sí está permitido.

Flujo:  Documento -> Item (pregunta/ejercicio/inciso) -> Etiqueta (arquetipo, rasgos, Bloom/DOK)
        -> Relacion (reciclaje) -> Prediccion (prob. por arquetipo) -> Simulacro.
"""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class TipoDocumento(str, Enum):
    examen = "examen"
    tarea = "tarea"
    clase = "clase"          # láminas / presentaciones del profe
    notas = "notas"          # apuntes (del profe o del alumno)
    temario = "temario"
    pauta = "pauta"          # solución oficial


class Documento(BaseModel):
    id: str                                  # p. ej. "P2_2026-05-04"
    materia: str
    tipo: TipoDocumento
    archivo: str                             # ruta relativa dentro de materias/<m>/datos
    fecha: date | None = None
    parcial: str | None = None               # "P1", "P2", "final"...
    semestre: str | None = None              # "2026-II"
    profesor: str | None = None
    metodo_extraccion: str = ""              # "pymupdf" | "vlm:<modelo>" | "marker" | "manual"
    revisado_por_humano: bool = False
    hash_sha256: str = ""                    # para detectar duplicados y cambios


class Item(BaseModel):
    """Unidad mínima comparable: una pregunta de examen, un ejercicio o un inciso de tarea."""
    id: str                                  # "P2_2026-05-04:Q3" o "T4:3a"
    documento_id: str
    numero: str                              # "3", "3a"
    padre_id: str | None = None              # el ejercicio al que pertenece un inciso
    texto: str                               # texto plano normalizado
    latex: str = ""                          # fórmulas en LaTeX, si se extrajeron
    puntos_max: float | None = None
    puntos_obtenidos: float | None = None    # calificación del alumno, si la hay (dato personal)
    examinable: bool = True


class NivelReciclaje(str, Enum):
    copia = "casi copia"
    adaptacion = "adaptación"
    nueva = "nueva"


class Relacion(BaseModel):
    """Resultado de fase 2: qué tanto se parece un ítem a otro anterior."""
    item_id: str
    candidato_id: str
    sim_lexica: float | None = None          # TF-IDF char/word, MinHash
    sim_semantica: float | None = None       # embeddings
    sim_formulas: float | None = None        # LaTeX/sympy normalizado
    sim_fusion: float
    p_valor_nulo: float | None = None        # contra distribución de pares no relacionados
    nivel: NivelReciclaje
    confirmado_por_humano: bool | None = None


class Bloom(str, Enum):
    recordar = "recordar"
    comprender = "comprender"
    aplicar = "aplicar"
    analizar = "analizar"
    evaluar = "evaluar"
    crear = "crear"


class Etiqueta(BaseModel):
    """Resultado de fases 3-4. Una por (item, etiquetador, corrida) para poder medir acuerdo."""
    item_id: str
    etiquetador: str                         # "humano:<iniciales>" | "llm:<modelo>"
    corrida: int = 0
    arquetipo: str | None = None
    rasgos: dict[str, int] = Field(default_factory=dict)   # rasgos de dificultad de la materia
    bloom: Bloom | None = None
    dok: int | None = Field(default=None, ge=1, le=4)      # Webb Depth of Knowledge
    stein: int | None = Field(default=None, ge=1, le=4)    # demanda cognitiva (matemáticas)
    minutos_estimados: float | None = None
    fuente_id: str | None = None             # ítem de tarea/clase/examen del que sale
    justificacion: str = ""
    version_prompt: str = ""


class Prediccion(BaseModel):
    """Resultado de fase 5 para un parcial objetivo."""
    materia: str
    parcial: str
    arquetipo: str
    p_media: float
    p_q05: float                              # intervalo creíble 90 %
    p_q95: float
    p_min_sensibilidad: float | None = None   # mín/máx sobre la rejilla de hiperparámetros
    p_max_sensibilidad: float | None = None
    modelo: str = ""                          # nombre + versión del modelo
    fecha_emision: date | None = None         # se congela ANTES del examen (diario de predicciones)


class PreguntaSimulacro(BaseModel):
    arquetipo: str
    item_banco_id: str
    enunciado_latex: str
    puntos: float
    dificultad_objetivo: float
    dificultad: float
    verificado: bool
    metodo_verificacion: str = ""             # "sympy", "numérico", "revisión humana"


class Simulacro(BaseModel):
    materia: str
    parcial: str
    numero: int
    semilla: int
    preguntas: list[PreguntaSimulacro]
    dificultad_total: float
