"""Similitud de textos (TF-IDF + coseno) para medir cuánto recicla un profesor.

Generalización del paso 2 del repo de Programación Lineal: recibe listas de (id, texto)
y no sabe nada de la materia. La clasificación usa una línea base: el percentil 95 de la
similitud entre pares DISTINTOS de la colección de referencia.
"""
import re, unicodedata
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def norm(t):
    t = unicodedata.normalize('NFKD', t)
    t = ''.join(ch for ch in t if not unicodedata.combining(ch)).lower()
    return re.sub(r'\s+', ' ', t)

def matriz(docs, peso_caracteres=0.5):
    """Promedio de TF-IDF de n-gramas de caracteres (3-5, captan fórmulas) y de palabras (1-2)."""
    v1 = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), sublinear_tf=True)
    v2 = TfidfVectorizer(analyzer='word', ngram_range=(1, 2), token_pattern=r'[a-z0-9]+', sublinear_tf=True)
    a = cosine_similarity(v1.fit_transform(docs))
    b = cosine_similarity(v2.fit_transform(docs))
    return peso_caracteres * a + (1 - peso_caracteres) * b

def compara(consultas, base, umbral_copia=0.5, top=3):
    """consultas, base: listas de (id, texto). Devuelve dict con la línea base y, para cada
    consulta, sus `top` más parecidos de la base y una clasificación."""
    items = [(i, t, 'q') for i, t in consultas] + [(i, t, 'b') for i, t in base]
    S = matriz([norm(t) for _, t, _ in items])
    ib = [k for k, it in enumerate(items) if it[2] == 'b']
    pares = [S[a, b] for a in ib for b in ib if a < b]
    p95 = float(np.percentile(pares, 95))
    res = {'linea_base_media': round(float(np.mean(pares)), 3), 'linea_base_p95': round(p95, 3),
           'umbral_copia': umbral_copia, 'top': {}}
    for k, (i, _, s) in enumerate(items):
        if s != 'q':
            continue
        orden = [j for j in np.argsort(-S[k]) if items[j][2] == 'b']
        mejores = [(items[j][0], round(float(S[k, j]), 3)) for j in orden[:top]]
        s1 = mejores[0][1]
        nivel = 'casi copia' if s1 > umbral_copia else ('adaptación' if s1 > p95 else 'nueva')
        res['top'][i] = {'mas_parecidos': mejores, 'clasificacion': nivel}
    return res
