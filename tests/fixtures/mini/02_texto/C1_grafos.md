# Grafos y Redes Discretas - Lámina 1 - 2026-08-20
tipo: clase

## Tema 1: Grados, apretón de manos y recorridos eulerianos
Teorema del apretón de manos: $\sum_{v \in V(G)} \deg(v) = 2|E(G)|$, por lo que el número de vértices de grado impar es siempre par.
Teorema de Euler: un grafo conexo admite un circuito euleriano si y solo si todos sus vértices tienen grado par.

## Tema 2: Árboles generadores mínimos y coloración
El algoritmo de Kruskal ordena las aristas por peso creciente y agrega cada arista que no forme ciclo con las ya elegidas.
Un grafo es $2$-coloreable (bipartito) si y solo si no contiene ciclos de longitud impar.

## Tema 3: Caracterización de árboles y puentes
Una arista $e$ en un grafo conexo $G$ es un puente si al eliminarla $G - e$ deja de ser conexo. En particular, $e$ es puente si y solo si $e$ no yace en ningún ciclo de $G$.
