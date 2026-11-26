"""Plantilla: copia este archivo y llénalo para tu materia y parcial.
Los nombres de tipo (A, B, ...) deben coincidir con la columna `arq` de rasgos_dificultad.csv."""
ARQUETIPOS = {          # tipo: (descripción, minutos estimados para resolverlo)
    'A': ('Tipo de pregunta A', 25),
    'B': ('Tipo de pregunta B', 25),
    'C': ('Demostración', 15),
    'D': ('Tipo de pregunta D', 20),
    'E': ('Tipo de pregunta E', 30),
    'F': ('Tipo de pregunta F', 20),
}
MATERIAL = {'A': 4, 'B': 2, 'C': 1, 'D': 2, 'E': 1, 'F': 1}     # 2 por ejercicio de tarea, 1 por ejemplo de clase, 0.5 por teorema
MOLDE = {'A': 1}                         # tipos que salieron en exámenes previos del mismo parcial (vacío si no hay)
CFG = {
    'arquetipos': ARQUETIPOS, 'material': MATERIAL, 'molde': MOLDE,
    'pi_molde': (1, 1),                  # Beta(1+copiadas de examen previo, 1+no copiadas)
    'rotacion': [], 'rho': 0.6,          # tipos ya preguntados este semestre y su castigo
    'demostracion': {'arquetipos': ['C'], 'beta': (2, 2)},
    'N': {3: 0.6, 4: 0.4},               # número de preguntas
    'ventana': (60, 95),                 # minutos aceptables
    # 'cobertura': {'bloques': [['A'], ['B']], 'kappa': 0.8},   # si el profe anunció bloques
    'beta': 6, 'suavizado': 0.3,
}
MALLA = {'beta': [3, 6, 12], 'pi': [0.2, 0.4, 0.6], 'rho': [0.3, 0.6, 1.0]}
SEMILLA_SORTEO = 1
NIVELES = {'casi copia': 1 / 3, 'adaptación': 1 / 3, 'nueva': 1 / 3}
