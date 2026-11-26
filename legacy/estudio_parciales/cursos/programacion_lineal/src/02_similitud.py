"""Paso 2. Similitud de textos (TF-IDF + coseno) para medir cuánto recicla el profesor.

Modos:
  examenes : cada pregunta de examen contra cada ejercicio de tarea y bloque de clase (Parcial 1 y 2).
  tarea4   : cada ejercicio de la Tarea 4 contra los bloques de las Clases 12 a 16 (Parcial 3).

Uso:  python src/02_similitud.py examenes   |   python src/02_similitud.py tarea4
Salida: salidas/similitud_<modo>.json
"""
import json, os, re, sys, unicodedata
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(RAIZ, 'corpus')
OUT = os.path.join(RAIZ, 'salidas')

def norm(t):
    """Minúsculas, sin acentos y con espacios colapsados."""
    t = unicodedata.normalize('NFKD', t)
    t = ''.join(ch for ch in t if not unicodedata.combining(ch)).lower()
    return re.sub(r'\s+', ' ', t)

def leer(sub, f):
    return open(os.path.join(C, sub, f), encoding='utf-8', errors='ignore').read()

def ejercicios_tarea(archivo, etiqueta):
    """Parte una tarea en ejercicios usando los encabezados 'Ejercicio N'."""
    t = leer('tareas', archivo)
    partes = re.split(r'(Ejercicio\s+\d+)', t)
    return [(f'{etiqueta}-Ej{re.findall(r"[0-9]+", partes[i])[0]}', 'tarea', partes[i + 1][:2500])
            for i in range(1, len(partes), 2)]

def bloques_clase(clases):
    """Bloques de 30 líneas que empiezan en 'Ejercicio' o 'Ejemplo', sin duplicados."""
    items = []
    for f in sorted(os.listdir(os.path.join(C, 'clases'))):
        num = re.findall(r'\d+', f)
        if not num or int(num[0]) not in clases:
            continue
        if f.startswith('Clase_8'):        # la Clase 8 repite la Clase 7
            continue
        lineas = leer('clases', f).splitlines()
        idx = [k for k, l in enumerate(lineas) if re.match(r'\s*(Ejercicio|Ejemplo)', l)]
        vistos = set()
        for n, k in enumerate(idx):
            bloque = '\n'.join(lineas[k:k + 30])
            clave = norm(bloque)[:110]
            if clave in vistos:
                continue
            vistos.add(clave)
            items.append((f'Clase{num[0]}-b{n + 1}', 'clase', bloque))
    return items

def preguntas_examen():
    """Enunciados de las Pruebas 1 y 2 (se corta en la palabra SOLUCIÓN de la pauta)."""
    items = []
    t = leer('examenes', 'Pauta_Prueba1.txt')
    qs = re.split(r'\n\s*(\d)\.\s*\((\d) puntos\)', t)
    for i in range(1, len(qs), 3):
        items.append((f'P1-Q{qs[i]}', 'examen', re.split(r'SOLUCI', qs[i + 2])[0]))
    t = leer('examenes', 'Pauta_Prueba2.txt')
    qs = re.split(r'Pregunta\s+(\d)', t)
    for i in range(1, len(qs), 2):
        items.append((f'P2-Q{qs[i]}', 'examen', re.split(r'SOLUCI', qs[i + 1])[0]))
    return items

def matriz_similitud(docs):
    """Promedio de dos TF-IDF: n-gramas de 3 a 5 caracteres (capta fórmulas) y palabras de 1 a 2 (capta redacción)."""
    v1 = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), sublinear_tf=True)
    v2 = TfidfVectorizer(analyzer='word', ngram_range=(1, 2), token_pattern=r'[a-z0-9]+', sublinear_tf=True)
    return 0.5 * cosine_similarity(v1.fit_transform(docs)) + 0.5 * cosine_similarity(v2.fit_transform(docs))

def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else 'examenes'
    if modo == 'examenes':
        items = (ejercicios_tarea('Tarea_1.txt', 'T1') + ejercicios_tarea('Tarea_2.txt', 'T2') +
                 ejercicios_tarea('Tarea_3.txt', 'T3') + preguntas_examen() + bloques_clase(range(7, 12)))
        consulta, base_src = 'examen', 'tarea'
    else:
        items = ejercicios_tarea('Tarea_4.txt', 'T4') + bloques_clase(range(12, 17))
        consulta, base_src = 'tarea', 'clase'
    ids = [i[0] for i in items]; src = [i[1] for i in items]
    S = matriz_similitud([norm(i[2]) for i in items])

    # línea base: similitud entre pares distintos de la colección de referencia
    ref = [k for k, s in enumerate(src) if s == base_src]
    base = [S[a, b] for a in ref for b in ref if a < b]
    p95 = float(np.percentile(base, 95))
    res = {'modo': modo, 'n_items': {s: src.count(s) for s in set(src)},
           'linea_base_media': round(float(np.mean(base)), 3), 'linea_base_p95': round(p95, 3), 'top': {}}
    for i, d in enumerate(ids):
        if src[i] != consulta:
            continue
        orden = [j for j in np.argsort(-S[i]) if src[j] != consulta]
        top = [(ids[j], round(float(S[i, j]), 3)) for j in orden[:3]]
        s1 = top[0][1]
        nivel = 'casi copia' if s1 > 0.5 else ('adaptación' if s1 > p95 else 'nueva')
        res['top'][d] = {'mas_parecidos': top, 'clasificacion': nivel}
        print(f'{d:12s} -> {top[0][0]:14s} {s1:.3f}  [{nivel}]')
    print(f'Línea base: media {res["linea_base_media"]}, percentil 95 {res["linea_base_p95"]}')
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, f'similitud_{modo}.json'), 'w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
