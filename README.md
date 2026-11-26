# Análisis de profesor

Subes un **.zip** con el material de una materia (exámenes pasados, tareas, láminas, notas) a un
chat de IA, y te devuelve **5 simulacros del próximo parcial y una guía de estudio**. La guía dice
qué temas es más probable que salgan, cuánto recicla el profe y qué tan difícil examina
comparado con la tarea.

No hacen falta API keys. La IA del chat (Claude, ChatGPT, Gemini o Antigravity) sigue
[`PROTOCOLO.md`](PROTOCOLO.md):

- **ella** lee, transcribe, etiqueta y redacta;
- **los scripts de `ap.py`** hacen las cuentas, para que las probabilidades, intervalos y sorteos
  sean reproducibles y no inventados.

## Cómo usarlo

### En un chat con ejecución de código (Claude, ChatGPT, Gemini)

1. Descarga este repo como zip:
   [main.zip](https://github.com/romoruz/Analisis_profesor/archive/refs/heads/main.zip).
2. Abre un chat nuevo y sube **dos archivos**: ese zip y el zip de tu material.
3. Pega este mensaje:

> Descomprime `Analisis_profesor-main.zip` y sigue su `PROTOCOLO.md` paso a paso con mi
> material (`<mi_material>.zip`). Materia: ___. Viene el parcial ___ el ___, temas: ___.
> Al final dame `GUIA_PARCIAL.md`, `SIMULACROS.md` y `SOLUCIONES.md`.

Si el chat puede navegar pero no recibe archivos de código, basta con el enlace al protocolo:
`https://raw.githubusercontent.com/romoruz/Analisis_profesor/main/PROTOCOLO.md`. El chat
trabaja en "modo sin código" (Anexo C del protocolo): menos preciso, pero funciona.

### En Antigravity o Claude Code (en tu computadora)

```bash
git clone https://github.com/romoruz/Analisis_profesor.git && cd Analisis_profesor
bash scripts/setup.sh
```

Copia tu zip a `entrada/` y en el chat del agente escribe: `/analizar entrada/<material>.zip`.

## Qué hay aquí

| Ruta | Para qué |
|---|---|
| `PROTOCOLO.md` | El manual que sigue la IA. **Es el producto** |
| `ap.py` + `src/analisis_profesor/` | Los scripts de cálculo. Solo usan numpy y scipy (con respaldo en Python puro) para correr en cualquier sandbox |
| `materias/_plantilla/`, `plantillas/` | Configuración de materia y plantilla de la guía |
| `docs/ROADMAP.md` | Fases de desarrollo y qué falta |
| `docs/METODOLOGIA_ESTADISTICA.md` | Qué estadística se usa y por qué |
| `docs/INVESTIGACION.md` | Papers y repos en los que se apoya |
| `AGENTS.md` | Reglas para los agentes que **desarrollan** este repo |
| `legacy/` | Código de los análisis anteriores (PL, SD-II), como referencia |

Estado: protocolo v1 escrito; los scripts están en construcción (ver roadmap). Mientras tanto, el
protocolo funciona en modo sin código.
