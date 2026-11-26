# Análisis de profesor

Toma todo el material de una materia (exámenes pasados, tareas, láminas, notas) y responde tres
preguntas sobre el próximo examen:

1. **¿Qué temas se repiten y qué tan difícil es cada pregunta?** Ingesta, extracción con
   fórmulas, segmentación en ítems, temas y dificultad cognitiva.
2. **¿Cómo examina este profesor?** Recicla de sus exámenes o de la tarea, el examen es más
   fácil o más difícil que la tarea, saca preguntas de nicho de la clase. Se responde con
   estadística para muestras chicas: bayesiana, no paramétrica y con backtesting.
3. **¿Qué puede salir?** Probabilidad por tipo de pregunta con intervalos, y 5 simulacros
   verificados que reproducen el formato y la dificultad del profe.

Viene de los repos de Programación Lineal, Sistemas Dinámicos II y Simulación (en `legacy/`, solo
como referencia).

## Documentos

| Archivo | Para qué |
|---|---|
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Fases, tareas, criterios de aceptación y quién hace qué |
| [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) | Módulos, contratos de datos y capa LLM |
| [`docs/METODOLOGIA_ESTADISTICA.md`](docs/METODOLOGIA_ESTADISTICA.md) | Qué prueba o intervalo usar en cada paso y por qué |
| [`docs/INVESTIGACION.md`](docs/INVESTIGACION.md) | Literatura y repos revisados, qué se toma de cada uno |
| [`AGENTS.md`](AGENTS.md) | Reglas para cualquier agente de código (Antigravity, Claude Code, Codex...) |

## Instalación

```bash
git clone https://github.com/romoruz/analisis_profesor.git
cd analisis_profesor
bash scripts/setup.sh dev,llm          # Windows: .\scripts\setup.ps1 -Extras "dev,llm"
```

Después llena `.env` con las API keys que uses (nunca se sube a git).

Extras opcionales: `nlp` (embeddings y BERTopic), `ocr` (Marker, pesado), `bayes` (PyMC), `ui`.

## Uso (cuando estén implementadas las fases)

```bash
ap nueva simulacion
ap ingesta simulacion --zip ~/Descargas/simulacion.zip
ap todo simulacion P2
```

El material del profesor (`materias/*/datos`) y las salidas no se suben a git por defecto.
