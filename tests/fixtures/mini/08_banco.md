# Banco de ejercicios ficticio para pruebas de CI (`mini` — Grafos y Redes Discretas)
# Todos los enunciados y verificaciones son sintéticos; los bloques automáticos usan solo librería estándar.

## B-A-1
arquetipo: A
nivel: casi copia
familia: A-apreton
basado_en: T1:1
rasgos: entregables=2, parametro=0, dimension=1, tecnica=0, demostracion=0, algebra=1, computo=0, casos=2
enunciado: |
  Un grafo simple tiene 8 vértices con grados $[3, 3, 2, 2, 2, 2, 1, 1]$. Determina el número de aristas y verifica cuántos vértices tienen grado impar.
solucion: |
  Por el lema del apretón de manos, la suma de grados es $16 = 2|E|$, luego $|E| = 8$ aristas y hay $4$ vértices de grado impar.
verificacion: |
  grados = [3, 3, 2, 2, 2, 2, 1, 1]
  assert sum(grados) % 2 == 0
  assert sum(grados) // 2 == 8
  assert sum(1 for g in grados if g % 2 == 1) == 4

## B-A-2
arquetipo: A
nivel: adaptación
familia: A-regular
basado_en: T2:3
rasgos: entregables=2, parametro=1, dimension=1, tecnica=0, demostracion=0, algebra=1, computo=0, casos=2
enunciado: |
  ¿Para qué valores enteros de $k$ puede existir un grafo simple $k$-regular con $7$ vértices? Calcula sus aristas para $k=4$.
solucion: |
  La suma $7k$ debe ser par y $0 \le k \le 6$, luego $k \in \{0, 2, 4, 6\}$. Para $k=4$, $|E| = 14$.
verificacion: |
  validos = [k for k in range(7) if (7 * k) % 2 == 0]
  assert validos == [0, 2, 4, 6]
  assert (7 * 4) // 2 == 14

## B-A-3
arquetipo: A
nivel: nueva
familia: A-complemento
basado_en: T1:1
rasgos: entregables=2, parametro=0, dimension=1, tecnica=0, demostracion=0, algebra=1, computo=0, casos=1
enunciado: |
  Sea $G$ un grafo simple con $6$ vértices y $9$ aristas. ¿Cuántas aristas tiene su grafo complemento $\overline{G}$ y cuál es la suma de sus grados?
solucion: |
  El grafo completo $K_6$ tiene $\binom{6}{2} = 15$ aristas, por lo que $\overline{G}$ tiene $15 - 9 = 6$ aristas y suma de grados $12$.
verificacion: |
  n = 6
  e_total = n * (n - 1) // 2
  e_comp = e_total - 9
  assert e_comp == 6
  assert 2 * e_comp == 12

## B-A-4
arquetipo: A
nivel: adaptación
familia: A-bipartito-deg
basado_en: T1:1
rasgos: entregables=2, parametro=0, dimension=1, tecnica=0, demostracion=0, algebra=0, computo=0, casos=2
enunciado: |
  En una reunión con $5$ profesores y $7$ estudiantes cada profesor saluda exactamente a $3$ estudiantes. ¿Cuántos saludos hay en total y cuál es el grado promedio de un estudiante?
solucion: |
  Total de aristas $5 \cdot 3 = 15$; grado promedio en estudiantes $15/7$.
verificacion: |
  aristas = 5 * 3
  assert aristas == 15
  assert abs(aristas / 7 - 15 / 7) < 1e-12

## B-B-1
arquetipo: B
nivel: casi copia
familia: B-euler
basado_en: T2:2
rasgos: entregables=2, parametro=0, dimension=2, tecnica=0, demostracion=0, algebra=0, computo=0, casos=1
enunciado: |
  Determina si el grafo conexo con lista de grados $[4, 4, 2, 2, 2]$ admite un circuito euleriano y un camino euleriano abierto.
solucion: |
  Todos los vértices tienen grado par ($0$ impares), por lo que admite circuito euleriano.
verificacion: |
  grados = [4, 4, 2, 2, 2]
  impares = sum(1 for g in grados if g % 2 == 1)
  assert impares == 0

## B-B-2
arquetipo: B
nivel: casi copia
familia: B-euler-kn
basado_en: T2:2
rasgos: entregables=2, parametro=0, dimension=2, tecnica=0, demostracion=0, algebra=0, computo=0, casos=2
enunciado: |
  Para el grafo completo bipartito $K_{3,4}$, decide si tiene circuito euleriano o camino euleriano abierto.
solucion: |
  Los vértices de $K_{3,4}$ tienen grados tres veces $4$ y cuatro veces $3$; al haber $4 > 2$ vértices impares, no tiene ni circuito ni camino euleriano.
verificacion: |
  grados = [4, 4, 4, 3, 3, 3, 3]
  impares = sum(1 for g in grados if g % 2 == 1)
  assert impares == 4 and impares > 2

## B-B-3
arquetipo: B
nivel: adaptación
familia: B-dirac
basado_en: T2:2
rasgos: entregables=2, parametro=0, dimension=2, tecnica=0, demostracion=0, algebra=1, computo=0, casos=1
enunciado: |
  Un grafo simple con $n=6$ vértices tiene grado mínimo $\delta(G) = 3$. ¿Satisface la condición de Dirac para garantizar un ciclo hamiltoniano?
solucion: |
  Como $n = 6 \ge 3$ y $\delta(G) = 3 \ge 6/2$, cumple el teorema de Dirac y es hamiltoniano.
verificacion: |
  n, delta = 6, 3
  assert n >= 3 and delta >= n / 2

## B-B-4
arquetipo: B
nivel: nueva
familia: B-rueda
basado_en: T2:2
rasgos: entregables=2, parametro=0, dimension=2, tecnica=0, demostracion=0, algebra=0, computo=0, casos=1
enunciado: |
  Considera el grafo completo $K_5$ sin una arista. ¿Cuántos vértices de grado impar quedan y es euleriano tras quitar otra arista disjunta?
solucion: |
  En $K_5$ todos tienen grado $4$. Al quitar $(1,2)$ quedan $2$ vértices de grado $3$ (camino euleriano). Al quitar $(3,4)$ quedan $4$ impares (no euleriano).
verificacion: |
  g1 = [3, 3, 4, 4, 4]
  g2 = [3, 3, 3, 3, 4]
  assert sum(1 for x in g1 if x % 2 == 1) == 2
  assert sum(1 for x in g2 if x % 2 == 1) == 4

## B-C-1
arquetipo: C
nivel: casi copia
familia: C-kruskal-a
basado_en: T1:4
rasgos: entregables=2, parametro=0, dimension=2, tecnica=0, demostracion=0, algebra=1, computo=0, casos=1
enunciado: |
  Aplica el algoritmo de Kruskal sobre un grafo de $4$ vértices con aristas ponderadas $(0,1,1)$, $(1,2,3)$, $(2,3,2)$, $(0,3,4)$, $(0,2,5)$ y calcula el peso total del árbol generador mínimo.
solucion: |
  Se eligen $(0,1,1)$, $(2,3,2)$ y $(1,2,3)$, con peso total $6$.
verificacion: |
  aristas = sorted([(1, 0, 1), (3, 1, 2), (2, 2, 3), (4, 0, 3), (5, 0, 2)])
  padre = list(range(4))
  def raiz(u):
      while padre[u] != u:
          u = padre[u]
      return u
  peso, usadas = 0, 0
  for w, u, v in aristas:
      ru, rv = raiz(u), raiz(v)
      if ru != rv:
          padre[ru] = rv
          peso += w
          usadas += 1
  assert usadas == 3 and peso == 6

## B-C-2
arquetipo: C
nivel: casi copia
familia: C-kruskal-b
basado_en: T1:4
rasgos: entregables=2, parametro=0, dimension=2, tecnica=0, demostracion=0, algebra=1, computo=0, casos=2
enunciado: |
  Determina el peso mínimo de un árbol generador para un grafo conexo de $5$ vértices con aristas $(0,1,2)$, $(0,2,3)$, $(1,2,1)$, $(1,3,4)$, $(2,4,5)$, $(3,4,2)$.
solucion: |
  Aristas seleccionadas: $(1,2,1)$, $(0,1,2)$, $(3,4,2)$ y $(1,3,4)$, sumando peso $9$.
verificacion: |
  aristas = sorted([(2, 0, 1), (3, 0, 2), (1, 1, 2), (4, 1, 3), (5, 2, 4), (2, 3, 4)])
  comp = list(range(5))
  total = 0
  for w, u, v in aristas:
      cu, cv = comp[u], comp[v]
      if cu != cv:
          comp = [cu if c == cv else c for c in comp]
          total += w
  assert len(set(comp)) == 1 and total == 9

## B-C-3
arquetipo: C
nivel: adaptación
familia: C-kruskal-c
basado_en: T2:4
rasgos: entregables=2, parametro=1, dimension=2, tecnica=0, demostracion=0, algebra=1, computo=0, casos=2
enunciado: |
  Si un árbol generador mínimo de $n=6$ vértices tiene aristas de pesos $1, 2, 4, 5$ y una arista adicional de peso $k$ positiva, ¿cuál es el menor entero $k$ para que el peso total supere $15$?
solucion: |
  Un árbol de $6$ vértices tiene $5$ aristas; suma $12 + k > 15 \implies k \ge 4$.
verificacion: |
  base = [1, 2, 4, 5]
  assert len(base) + 1 == 5
  k_min = next(k for k in range(1, 20) if sum(base) + k > 15)
  assert k_min == 4

## B-C-4
arquetipo: C
nivel: nueva
familia: C-segundo-mst
basado_en: T2:4
rasgos: entregables=3, parametro=0, dimension=2, tecnica=1, demostracion=0, algebra=1, computo=0, casos=1
enunciado: |
  En un triángulo de pesos $(0,1,2)$, $(1,2,3)$ y $(0,2,6)$, encuentra tanto el árbol generador mínimo como el segundo árbol generador de menor peso.
solucion: |
  El MST tiene peso $2 + 3 = 5$ y el segundo menor peso es $2 + 6 = 8$.
verificacion: |
  pesos_ciclo = [2, 3, 6]
  totales = sorted(sum(pesos_ciclo) - p for p in pesos_ciclo)
  assert totales[0] == 5 and totales[1] == 8

## B-D-1
arquetipo: D
nivel: casi copia
familia: D-cromatico-ciclo
basado_en: T2:1
rasgos: entregables=2, parametro=0, dimension=2, tecnica=0, demostracion=0, algebra=0, computo=0, casos=2
enunciado: |
  Calcula el número cromático $\chi(C_7)$ y $\chi(C_8)$ para los ciclos de $7$ y $8$ vértices.
solucion: |
  Todo ciclo impar requiere $3$ colores y todo ciclo par $2$ colores: $\chi(C_7)=3$, $\chi(C_8)=2$.
verificacion: |
  def chi_ciclo(n):
      return 2 if n % 2 == 0 else 3
  assert chi_ciclo(7) == 3
  assert chi_ciclo(8) == 2

## B-D-2
arquetipo: D
nivel: adaptación
familia: D-bipartito-color
basado_en: T2:1
rasgos: entregables=2, parametro=0, dimension=2, tecnica=0, demostracion=0, algebra=1, computo=0, casos=2
enunciado: |
  Un grafo plano tiene grado máximo $\Delta(G) = 3$ y contiene un subgrafo isomorfo a $K_4$ menos una arista ($K_4 - e$). ¿Cuál es $\chi(G)$ si el resto del grafo es un árbol adherido a un vértice?
solucion: |
  $K_4 - e$ contiene un triángulo, luego $\chi \ge 3$, y por Brooks (no es $K_4$ ni ciclo impar) $\chi(G) = 3$.
verificacion: |
  aristas = {(0, 1), (1, 2), (0, 2), (0, 3), (2, 3), (3, 4)}
  for a in range(3**5):
      col = [(a // (3**i)) % 3 for i in range(5)]
      if all(col[u] != col[v] for u, v in aristas):
          ok = True
          break
  else:
      ok = False
  assert ok

## B-D-3
arquetipo: D
nivel: adaptación
familia: D-rueda-color
basado_en: T2:1
rasgos: entregables=2, parametro=0, dimension=2, tecnica=0, demostracion=0, algebra=0, computo=0, casos=2
enunciado: |
  Encuentra el número cromático del grafo rueda $W_5$ (un centro conectado a un ciclo $C_5$).
solucion: |
  El centro requiere su propio color y $C_5$ necesita $3$ colores más, por lo que $\chi(W_5) = 4$.
verificacion: |
  aristas = [(i, (i + 1) % 5) for i in range(5)] + [(5, i) for i in range(5)]
  def es_coloreable(k):
      for c in range(k**6):
          cols = [(c // (k**i)) % k for i in range(6)]
          if all(cols[u] != cols[v] for u, v in aristas):
              return True
      return False
  assert not es_coloreable(3) and es_coloreable(4)

## B-D-4
arquetipo: D
nivel: nueva
familia: D-greedy
basado_en: T2:1
rasgos: entregables=2, parametro=0, dimension=2, tecnica=1, demostracion=0, algebra=0, computo=0, casos=1
enunciado: |
  Para el grafo completo $K_5$ y la trayectoria $P_6$, verifica las cotas de coloración $\omega(G) \le \chi(G) \le \Delta(G) + 1$.
solucion: |
  Para $K_5$: $5 \le 5 \le 5$; para $P_6$: $2 \le 2 \le 3$.
verificacion: |
  omega_k5, chi_k5, delta_k5 = 5, 5, 4
  omega_p6, chi_p6, delta_p6 = 2, 2, 2
  assert omega_k5 <= chi_k5 <= delta_k5 + 1
  assert omega_p6 <= chi_p6 <= delta_p6 + 1

## B-E-1
arquetipo: E
nivel: casi copia
familia: E-hall-a
basado_en: T1:2a
rasgos: entregables=2, parametro=0, dimension=2, tecnica=1, demostracion=0, algebra=0, computo=0, casos=2
enunciado: |
  En un grafo bipartito $(X, Y)$ con $|X|=3$ y vecindades $N(x_1)=\{y_1, y_2\}$, $N(x_2)=\{y_1\}$, $N(x_3)=\{y_2, y_3\}$, comprueba la condición de Hall y exhibe un emparejamiento perfecto de $X$.
solucion: |
  Todos los subconjuntos $S \subseteq X$ cumplen $|N(S)| \ge |S|$; sirve $\{(x_1,y_2),(x_2,y_1),(x_3,y_3)\}$.
verificacion: |
  ady = {0: {0, 1}, 1: {0}, 2: {1, 2}}
  for mask in range(1, 8):
      s = [i for i in range(3) if mask & (1 << i)]
      ns = set().union(*(ady[i] for i in s))
      assert len(ns) >= len(s)
  emparejamiento = {0: 1, 1: 0, 2: 2}
  assert len(set(emparejamiento.values())) == 3
  assert all(v in ady[k] for k, v in emparejamiento.items())

## B-E-2
arquetipo: E
nivel: casi copia
familia: E-hall-b
basado_en: T1:2b
rasgos: entregables=2, parametro=0, dimension=2, tecnica=1, demostracion=0, algebra=0, computo=0, casos=2
enunciado: |
  Considera $X=\{x_1, x_2, x_3, x_4\}$ con $N(x_1)=N(x_2)=\{y_1\}$, $N(x_3)=\{y_2,y_3\}$, $N(x_4)=\{y_3,y_4\}$. Determina si existe emparejamiento que sature $X$ o exhibe un subconjunto que viole Hall.
solucion: |
  Para $S=\{x_1, x_2\}$ se tiene $|N(S)| = 1 < 2 = |S|$, luego viola Hall.
verificacion: |
  ady = {0: {0}, 1: {0}, 2: {1, 2}, 3: {2, 3}}
  s = [0, 1]
  ns = set().union(*(ady[i] for i in s))
  assert len(ns) < len(s)

## B-E-3
arquetipo: E
nivel: adaptación
familia: E-regular-bip
basado_en: T1:2b
rasgos: entregables=2, parametro=0, dimension=2, tecnica=1, demostracion=0, algebra=1, computo=0, casos=1
enunciado: |
  Sea $G$ un grafo bipartito $2$-regular con $6$ vértices ($3$ en cada parte), por ejemplo el ciclo $C_6$. Verifica el teorema de Hall y exhibe dos emparejamientos perfectos disjuntos.
solucion: |
  Todo bipartito $k$-regular ($k \ge 1$) admite $k$ emparejamientos perfectos disjuntos; en $C_6$ son las aristas pares y las impares.
verificacion: |
  aristas = {(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)}
  m1 = {(0, 1), (2, 3), (4, 5)}
  m2 = {(1, 2), (3, 4), (5, 0)}
  assert m1.issubset(aristas) and m2.issubset(aristas) and m1.isdisjoint(m2)
  assert len(set().union(*m1)) == 6 and len(set().union(*m2)) == 6

## B-E-4
arquetipo: E
nivel: nueva
familia: E-estable
basado_en: T1:2a
rasgos: entregables=2, parametro=0, dimension=2, tecnica=1, demostracion=0, algebra=1, computo=0, casos=2
enunciado: |
  En una escuela hay $2$ vacantes $P_1, P_2$ y $2$ aspirantes $A_1, A_2$ donde $|N(S)| \ge |S|$ y se asigna $(A_1, P_1), (A_2, P_2)$. Verifica si hay pareja bloqueante cuando $A_1$ prefiere $P_2$ sobre $P_1$ y $P_2$ prefiere $A_1$ sobre $A_2$.
solucion: |
  $(A_1, P_2)$ bloquea el emparejamiento; al intercambiar a $(A_1, P_2), (A_2, P_1)$ ya es estable.
verificacion: |
  pref_a = {0: [1, 0], 1: [0, 1]}
  pref_p = {0: [0, 1], 1: [0, 1]}
  def estable(asig):
      inv = {p: a for a, p in asig.items()}
      for a, p in asig.items():
          for p2 in pref_a[a]:
              if p2 == p:
                  break
              if pref_p[p2].index(a) < pref_p[p2].index(inv[p2]):
                  return False
      return True
  assert not estable({0: 0, 1: 1})
  assert estable({0: 1, 1: 0})

## B-F-1
arquetipo: F
nivel: casi copia
familia: F-arbol-aristas
basado_en: T1:3
rasgos: entregables=1, parametro=0, dimension=2, tecnica=1, demostracion=2, algebra=0, computo=0, casos=1
enunciado: |
  Demuestra por inducción sobre $n$ que todo árbol finito con $n \ge 1$ vértices tiene exactamente $n - 1$ aristas.
solucion: |
  Para $n=1$ tiene $0$ aristas. Todo árbol con $n \ge 2$ posee al menos una hoja; al retirarla queda un árbol de $n-1$ vértices con $(n-2)$ aristas, luego el original tiene $n-1$.
verificacion: manual

## B-F-2
arquetipo: F
nivel: casi copia
familia: F-hojas
basado_en: T2:5
rasgos: entregables=1, parametro=0, dimension=2, tecnica=1, demostracion=2, algebra=0, computo=0, casos=1
enunciado: |
  Demuestra que todo árbol con al menos $n \ge 2$ vértices tiene por lo menos dos vértices de grado $1$ (hojas).
solucion: |
  Considera una trayectoria simple de longitud máxima; sus dos extremos solo pueden tener un vecino dentro de la trayectoria y ninguno fuera por maximilidad ni por aciclicidad.
verificacion: manual

## B-F-3
arquetipo: F
nivel: adaptación
familia: F-bipartito-ciclo
basado_en: T1:3
rasgos: entregables=2, parametro=0, dimension=2, tecnica=1, demostracion=2, algebra=0, computo=0, casos=1
enunciado: |
  Demuestra que un grafo es bipartito si y solo si no contiene ciclos de longitud impar.
solucion: |
  La ida sigue de que los vértices en un ciclo alternan de parte. Para el regreso, en cada componente conexa elige una raíz y particiona según la paridad de la distancia más corta; cualquier arista del mismo nivel formaría un ciclo impar.
verificacion: manual

## B-F-4
arquetipo: F
nivel: adaptación
familia: F-puentes
basado_en: T2:5
rasgos: entregables=2, parametro=0, dimension=2, tecnica=1, demostracion=2, algebra=0, computo=0, casos=1
enunciado: |
  Demuestra que en todo grafo conexo una arista $e$ es un puente (su eliminación desconecta el grafo) si y solo si $e$ no pertenece a ningún ciclo.
solucion: |
  Si $e=(u,v)$ pertenece a un ciclo, el resto del ciclo conecta $u$ con $v$ en $G-e$. Si $G-e$ es conexo, existe una trayectoria $u-v$ que junto con $e$ forma un ciclo.
verificacion: manual

## B-F-5
arquetipo: F
nivel: adaptación
familia: F-componentes-euler
basado_en: T1:3
rasgos: entregables=2, parametro=0, dimension=2, tecnica=1, demostracion=2, algebra=0, computo=0, casos=1
enunciado: |
  Sea $G$ un grafo con al menos una arista cuyos vértices tienen todos grado par. Demuestra que todas las aristas de $G$ pueden descomponerse en ciclos disjuntos por aristas.
solucion: |
  Por el lema del grado par la parte mínima en cualquier caminata maximal se cierra en un ciclo; al retirarlo todos los grados siguen siendo pares e induce por el número de aristas.
verificacion: manual

## B-F-6
arquetipo: F
nivel: nueva
familia: F-bosque
basado_en: T2:5
rasgos: entregables=1, parametro=0, dimension=2, tecnica=1, demostracion=2, algebra=0, computo=0, casos=1
enunciado: |
  Demuestra que un bosque con $n$ vértices y $k$ componentes conexas tiene exactamente $n - k$ aristas.
solucion: |
  Cada componente $i$ es un árbol con $n_i$ vértices y $n_i - 1$ aristas; sumando sobre las $k$ componentes se obtiene $\sum (n_i - 1) = n - k$.
verificacion: manual
