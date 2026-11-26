"""Paso 4 del protocolo: similitud de textos (TF-IDF + coseno) con respaldo en Python puro."""
from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from analisis_profesor.esquemas import Item, leer_jsonl


def norm(texto: str) -> str:
    """Normaliza a minúsculas, sin acentos y con espacios colapsados."""
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).lower()
    return re.sub(r"\s+", " ", t)


def _percentil_lineal(valores: Sequence[float], p: float) -> float:
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    pos = (p / 100.0) * (len(ordenados) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    return ordenados[lo] + (pos - lo) * (ordenados[hi] - ordenados[lo])


def _tokens_tfidf(doc: str, modo: str) -> Counter[str]:
    if modo == "char_wb":
        toks = [
            f" {w} "[i : i + k]
            for w in doc.split(" ")
            if w
            for k in (3, 4, 5)
            for i in range(len(w) + 2 - k + 1)
        ]
        return Counter(toks)
    palabras = re.findall(r"[a-z0-9]+", doc)
    bigramas = [f"{palabras[i]} {palabras[i + 1]}" for i in range(len(palabras) - 1)]
    return Counter(palabras + bigramas)


def _coseno_tfidf_puro(docs: Sequence[str], modo: str) -> list[list[float]]:
    n_docs = len(docs)
    conteos = [_tokens_tfidf(d, modo) for d in docs]
    df = Counter(tok for c in conteos for tok in c)
    idf = {tok: math.log((1 + n_docs) / (1 + v)) + 1.0 for tok, v in df.items()}
    vectores: list[dict[str, float]] = []
    for c in conteos:
        w = {tok: (1.0 + math.log(cnt)) * idf[tok] for tok, cnt in c.items()}
        norma = math.sqrt(sum(val * val for val in w.values())) or 1.0
        vectores.append({tok: val / norma for tok, val in w.items()})

    mat = [[0.0] * n_docs for _ in range(n_docs)]
    for i in range(n_docs):
        mat[i][i] = 1.0 if vectores[i] else 0.0
        vi = vectores[i]
        for j in range(i + 1, n_docs):
            vj = vectores[j]
            a, b = (vj, vi) if len(vi) > len(vj) else (vi, vj)
            sim = sum(val * b[tok] for tok, val in a.items() if tok in b)
            mat[i][j] = mat[j][i] = sim
    return mat


def _matriz_sklearn(docs: Sequence[str], peso_caracteres: float) -> list[list[float]] | None:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        return None
    try:
        v1 = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
        v2 = TfidfVectorizer(
            analyzer="word", ngram_range=(1, 2), token_pattern=r"[a-z0-9]+", sublinear_tf=True
        )
        a = cosine_similarity(v1.fit_transform(docs))
        b = cosine_similarity(v2.fit_transform(docs))
    except ValueError:
        return None
    s = peso_caracteres * a + (1.0 - peso_caracteres) * b
    return [[float(x) for x in fila] for fila in s]


def matriz(
    docs: Sequence[str], peso_caracteres: float = 0.5, *, usar_sklearn: bool | None = None
) -> list[list[float]]:
    """Matriz de similitud coseno promediando char_wb (3-5) y word (1-2)."""
    if not docs:
        return []
    if usar_sklearn is not False:
        s_sk = _matriz_sklearn(docs, peso_caracteres)
        if s_sk is not None:
            return s_sk
    a = _coseno_tfidf_puro(docs, "char_wb")
    b = _coseno_tfidf_puro(docs, "word")
    n = len(docs)
    return [
        [peso_caracteres * a[i][j] + (1.0 - peso_caracteres) * b[i][j] for j in range(n)]
        for i in range(n)
    ]


def compara(
    consultas: Sequence[tuple[str, str]],
    base: Sequence[tuple[str, str]],
    umbral_copia: float = 0.5,
    top: int = 3,
    *,
    usar_sklearn: bool | None = None,
) -> dict:
    """Compara cada `(id, texto)` de `consultas` contra `base` y clasifica reciclaje."""
    if not consultas or not base:
        return {
            "linea_base_media": 0.0,
            "linea_base_p95": 0.0,
            "n_base": len(base),
            "n_pares_base": 0,
            "umbral_copia": umbral_copia,
            "top": {},
        }
    items = [(i, t, "q") for i, t in consultas] + [(i, t, "b") for i, t in base]
    s = matriz([norm(t) for _, t, _ in items], usar_sklearn=usar_sklearn)
    ib = [k for k, it in enumerate(items) if it[2] == "b"]
    pares = [s[a][b] for idx, a in enumerate(ib) for b in ib[idx + 1 :]]
    p95 = _percentil_lineal(pares, 95.0) if pares else 0.0
    media = sum(pares) / len(pares) if pares else 0.0
    res: dict = {
        "linea_base_media": round(media, 3),
        "linea_base_p95": round(p95, 3),
        "n_base": len(ib),
        "n_pares_base": len(pares),
        "umbral_copia": umbral_copia,
        "top": {},
    }
    for k, (item_id, _, rol) in enumerate(items):
        if rol != "q":
            continue
        orden = sorted(ib, key=lambda j: -s[k][j])
        mejores = [[items[j][0], round(s[k][j], 3)] for j in orden[:top]]
        s1 = mejores[0][1] if mejores else 0.0
        nivel = "casi copia" if s1 > umbral_copia else ("adaptación" if s1 > p95 else "nueva")
        res["top"][item_id] = {"mas_parecidos": mejores, "clasificacion": nivel}
    return res


def calcular_similitud(
    materia: str,
    raiz_trabajo: Path | None = None,
    *,
    umbral_copia: float = 0.5,
    top: int = 3,
    usar_sklearn: bool | None = None,
) -> dict:
    """Ejecuta el paso 4 sobre `trabajo/<materia>/03_items.jsonl` -> `04_similitud.json`."""
    base_dir = (raiz_trabajo or Path("trabajo")) / materia
    items = list(leer_jsonl(base_dir / "03_items.jsonl", Item))
    etiquetables = [it for it in items if not it.padre_id]

    material = [
        (it.id, it.texto) for it in etiquetables if it.tipo_doc in ("tarea", "clase", "notas")
    ]
    if len(material) >= 2:
        s_mat = matriz([norm(t) for _, t in material], usar_sklearn=usar_sklearn)
        pares_mat = [
            s_mat[a][b] for a in range(len(material)) for b in range(a + 1, len(material))
        ]
        linea_base = {
            "n_items": len(material),
            "n_pares": len(pares_mat),
            "media": round(sum(pares_mat) / len(pares_mat), 3),
            "p95": round(_percentil_lineal(pares_mat, 95.0), 3),
        }
    else:
        linea_base = {"n_items": len(material), "n_pares": 0, "media": 0.0, "p95": 0.0}

    grupos_ex: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for it in etiquetables:
        if it.tipo_doc == "examen":
            clave = (it.fecha or "9999-99-99", it.documento_id)
            grupos_ex.setdefault(clave, []).append((it.id, it.texto))

    preguntas_examen: dict[str, dict] = {}
    examenes_previos: list[tuple[str, str]] = []
    for clave in sorted(grupos_ex):
        qs = grupos_ex[clave]
        referencia = material + examenes_previos
        r = compara(qs, referencia, umbral_copia=umbral_copia, top=top, usar_sklearn=usar_sklearn)
        for qid, entrada in r["top"].items():
            preguntas_examen[qid] = {
                "mas_parecidos": entrada["mas_parecidos"],
                "clasificacion": entrada["clasificacion"],
                "linea_base_p95": r["linea_base_p95"],
                "n_referencia": r["n_base"],
                "n_pares_referencia": r["n_pares_base"],
            }
        examenes_previos.extend(qs)

    grupos_t: dict[str, list[tuple[str, str]]] = {}
    for it in etiquetables:
        if it.tipo_doc == "tarea":
            grupos_t.setdefault(it.documento_id, []).append((it.id, it.texto))
    orden_tareas = sorted(
        grupos_t, key=lambda doc_id: ([int(x) for x in re.findall(r"\d+", doc_id)], doc_id)
    )
    tareas_entre_si: dict[str, dict] = {}
    tareas_previas: list[tuple[str, str]] = []
    for doc_id in orden_tareas:
        ejercicios = grupos_t[doc_id]
        if tareas_previas:
            r_t = compara(
                ejercicios,
                tareas_previas,
                umbral_copia=umbral_copia,
                top=top,
                usar_sklearn=usar_sklearn,
            )
            tareas_entre_si[doc_id] = r_t["top"]
        tareas_previas.extend(ejercicios)

    resultado = {
        "umbral_copia": umbral_copia,
        "linea_base": linea_base,
        "preguntas_examen": preguntas_examen,
        "tareas_entre_si": tareas_entre_si,
    }
    (base_dir / "04_similitud.json").write_text(
        json.dumps(resultado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return resultado
