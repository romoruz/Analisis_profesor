"""Configuración del modelo para el Parcial 3 de SD-II (temas 4.3 a 4.6).

Supuesto central: este semestre hay un parcial más, así que lo que antes era el Parcial 2
(examenes del 29/04/2020 y del 04/05/2026) es ahora el Parcial 3. Esos dos exámenes son el
'molde'. El Parcial 2 de este semestre (19/10/2026) cubrió el capítulo 3 y ya usó el
ejercicio 3a de la Tarea 4 (polares, ciclo límite): ese tipo se castiga con rho.
"""
ARQUETIPOS = {
    'A': ('Método del potencial: U, equilibrios, estabilidad, retrato fase', 25),
    'B': ('Bifurcación en EDO de 2o orden o escalar: lambda_0, retratos y diagrama', 25),
    'C': ('Bifurcación en sistema plano: ceroclinas, equilibrios según el parámetro', 30),
    'D': ('Sistema polarizable sin parámetro: ciclos límite, omega y alfa límites', 25),
    'E': ('Sistema en polares con parámetro: valores de bifurcación y retratos', 30),
    'F': ('Existencia o no de órbitas periódicas (anillo atrapante, Dulac, energía)', 20),
    'G': ('Demostración sobre conjuntos límite (omega(p))', 15),
    'H': ('Demostración tipo Poincaré-Bendixson / no existencia de órbitas', 15),
    'I': ('Existencia, unicidad e intervalo maximal; simetría de soluciones', 20),
    'J': ('Funciones de Lyapunov: estabilidad y cuenca', 20),
}

# Material: 2 por ejercicio de tarea del alcance, +1 si el profe lo repitió en la Tarea 5
# (que es la tarea de este parcial), 1 para la Tarea 3 (más vieja), 0.5 para lo marginal.
MATERIAL = {
    'A': 2 + 0.5 + 2 + 0.5,      # T4-1, T4-2 (numérico), T4-12 (tres potenciales), T2-8
    'B': 1,                      # T4-13 i (mitad del ejercicio)
    'C': 1 + 3 + 1 + 0.5,        # T4-13 ii, T4-9 = T5-8, T3-5, T3-6
    'D': 3 + 1,                  # T4-3 = T5-1, T3-7
    'E': 3,                      # T4-8 = T5-7
    'F': 3 + 3 + 3,              # T4-4, T4-5, T4-'4' (Dulac/Liénard), todos repetidos en T5
    'G': 0.5,                    # T3-8
    'H': 3 + 3,                  # anillo con secciones, anillo con 7 órbitas
    'I': 3 + 3 + 0.5 + 0.5,      # PVI orden 4, x''=-|x|, Lipschitz, unicidad
    'J': 1 + 1 + 1,              # T3-9, T3-10, T3-11
}
# Molde: tipos que salieron en los Parciales 2 viejos (2020 y mayo 2026)
MOLDE = {'A': 2, 'B': 2, 'D': 1, 'E': 1, 'G': 2}

CFG = {
    'arquetipos': ARQUETIPOS, 'material': MATERIAL, 'molde': MOLDE,
    # 3 de 8 preguntas de los exámenes de 2026 son reciclaje de un examen previo -> Beta(1+3, 1+5)
    'pi_molde': (4, 6),
    'rotacion': ['D'], 'rho': 0.6,
    # demostración: 2 de 2 Parciales 2 viejos la tuvieron (cuentan 1), 0 de 2 exámenes de este
    # semestre (otro temario, cuentan 0.5 cada uno) -> Beta(1+2, 1+1)
    'demostracion': {'arquetipos': ['G', 'H'], 'beta': (3, 2)},
    'N': {4: 1.0},               # los 4 exámenes vistos tienen 4 preguntas de 2.5
    'ventana': (75, 100),        # los Parciales 2 viejos suman 95 y 90 minutos estimados
    'beta': 6, 'suavizado': 0.3,
}
MALLA = {'beta': [3, 6, 12], 'pi': [0.2, 0.4, 0.6], 'rho': [0.3, 0.6, 1.0]}
SEMILLA_SORTEO = 13112026
# nivel de cada pregunta: en las 9 preguntas del alcance hubo 3 casi copias, 4 adaptaciones y
# 2 nuevas -> Laplace (1+3, 1+4, 1+2) / 12
NIVELES = {'casi copia': 4 / 12, 'adaptación': 5 / 12, 'nueva': 3 / 12}
