# Roadmap

## Idea central

El producto son dos piezas:

1. **`PROTOCOLO.md`**: instrucciones que cualquier IA de chat sigue.
2. **`ap.py`**: scripts deterministas que esa IA ejecuta en su sandbox.

La IA pone el juicio: transcribir fotos, decidir de dónde sale una pregunta, etiquetar
dificultad, escribir ejercicios. Los scripts ponen las cuentas: similitud, intervalos, modelo y
sorteo. **No hay API keys ni llamadas a LLM dentro del código.**

Esto obliga a dos restricciones de diseño:

- **El núcleo solo usa la librería estándar, numpy y scipy.** Todo lo demás es opcional y tiene
  respaldo, porque los sandboxes de ChatGPT, Claude y Gemini no permiten instalar libremente.
- **Todo intercambio es por archivos simples** (Markdown, CSV, JSONL, TOML) que una IA sabe
  escribir y un humano sabe revisar.

## Estrategia: rebanada vertical primero, después calidad

Ni "toda la arquitectura y luego calibrar", ni "meter material nuevo ya". Primero se hace un
camino **de punta a punta, mínimo**, y se calibra con **Sistemas Dinámicos II**, porque ahí ya
conoces las respuestas: reciclaje 0.98, 0.88 y 0.86, dificultad 13.4 y 12.3, probabilidades por
tipo y 44/44 verificados.

Cuando el camino reproduzca SD-II, se prueba en los chats reales (fase 2). Después se mejora la
calidad (fases 3 y 4) y luego se distribuye (fase 5). El material de una materia nueva entra en
la fase 2, no antes.

```
F0 base ─> F1 rebanada SD-II ─> F2 prueba en chats ─> F3 extracción/etiquetado ─> F4 estadística
                                       │                                               │
                                       └──────────── F5 distribución (skill, GPT, Gem) <┘
                                                     F6 migrar PL y Simulación, priors entre profes
```

---

## Fase 0: Base  ✅ (orquestador)

- [x] 0.1 Estructura, `pyproject` con núcleo mínimo (numpy y scipy), `scripts/setup.sh` y
      `.gitignore` que protege `entrada/`, `trabajo/` y datos.
- [x] 0.2 `PROTOCOLO.md` v1, `esquemas.py` (dataclasses, solo librería estándar), `ap.py` sin
      instalación, `ap.py diagnostico` funcionando.
- [x] 0.3 `AGENTS.md`, workflows de Antigravity y documentación.

## Fase 1: Rebanada vertical con SD-II (implementador)

Meta: cada paso [script] del protocolo existe en versión mínima y, alimentado con los datos de
SD-II, reproduce los resultados de `legacy/`.

- [x] 1.1 **CI** (GitHub Actions) con tres trabajos: (a) Python 3.11 y 3.12 con `dev,completo`;
      (b) "sandbox mínimo", solo numpy y scipy; (c) "Python puro", sin nada, que corre
      `ap.py diagnostico` y `ap.py items` con `python -I`.
      *Acepta:* los tres en verde en el PR.
- [x] 1.2 **Fixtures**:
      - `tests/fixtures/mini/`: un curso **inventado** con 2 exámenes, 2 tareas y 1 lámina, ya en
        el formato del paso 2, más su `05_etiquetas.csv`. Se versiona y lo usa la CI.
      - SD-II real: pruebas marcadas `@pytest.mark.real` que leen `entrada/sd2/` (ignorado por
        git) y se saltan si no existe.

      *Acepta:* `pytest` pasa con y sin `entrada/sd2/`.
- [x] 1.3 `ingesta`:
      - descomprime en `trabajo/<id>/00_crudo` y calcula el sha256;
      - `01_inventario.csv` con tipo, fecha y parcial por reglas de nombre y contenido;
      - texto de PDF con respaldos fitz → pypdf → pdfplumber → `pdftotext` → nada;
      - `pendientes_transcripcion.txt` con imágenes, PDFs con menos de 200 caracteres por página
        y exámenes.

      *Acepta:* con el zip original de SD-II, inventario correcto y las 4 fotos en pendientes.
- [x] 1.4 `items`: lee `02_texto/*.md` en el formato del paso 2 (incluye `calificacion_alumno`) y
      escribe `03_items.jsonl`. Regla de segmentación (dejar también en `PROTOCOLO.md` §3 al
      hacer la 1.4): "En exámenes el ítem etiquetable es la pregunta (Q3) y sus incisos son
      ítems hijos con padre_id. En tareas, si los incisos son ejercicios independientes (otros
      datos u otro objeto), cada inciso es el ítem etiquetable (T1:2a); si no, lo es el
      ejercicio."
      *Acepta:* con las transcripciones de `legacy/.../corpus` convertidas al formato, saca 4
      preguntas por examen y el conteo correcto por tarea.
- [x] 1.5 `similitud`: portar `legacy/.../nucleo/similitud.py`, con un TF-IDF en Python puro si
      no hay sklearn.
      *Acepta:* reproduce `legacy/.../salidas/similitud.json` (±0.01) con sklearn, y la misma
      clasificación sin sklearn.
- [x] 1.6 `plantilla-etiquetas` y su lector: `05_etiquetas.csv` ↔ `Etiqueta`, más un convertidor
      `legacy rasgos_dificultad.csv → 05_etiquetas.csv`.
- [x] 1.7 `dificultad`: portar `legacy/.../nucleo/dificultad.py` (rasgos desde `materia.toml`) y
      agregar IC BCa y permutación por cambio de signo para el delta por pares.
      *Acepta:* reproduce `legacy/.../salidas/dificultad.json` (deltas 0.27 y 0.40, totales 13.4,
      12.3, 8.0 y 8.4).
- [x] 1.8 `modelo`: portar `legacy/.../nucleo/modelo.py`. **Nuevo:** `MATERIAL`, `MOLDE` y la
      rotación se calculan desde `05_etiquetas.csv` y `materia.toml`. La regla es la de legacy:
      2 por ejercicio de tarea, +1 si se repite, 1 por clase, 0.5 marginal.
      *Acepta:* con `MATERIAL` y `MOLDE` legacy inyectados, reproduce `modelo_parcial3.json`
      exacto con la semilla. Con los calculados, las probabilidades difieren ≤ 0.08 y las
      diferencias se documentan.
- [ ] 1.9 `verificar`: lee `08_banco.md`, ejecuta cada bloque `verificacion` en un subproceso con
      timeout y escribe el estado.
      *Acepta:* el banco de SD-II convertido da 44/44 más 7 manuales.
- [ ] 1.10 `armar`: portar `05_armar_simulacros.py` (banda de dificultad, sorteo balanceado) y
      escribir `SIMULACROS.md`, `SOLUCIONES.md` y `simulacros.tex` (más PDF si hay `pdflatex`).
      *Acepta:* mismos 5 simulacros que `legacy/.../salidas/simulacros.json` con la misma
      semilla.
- [ ] 1.11 **E2E**: `scripts/e2e.sh <id>` corre todos los pasos [script] sobre `trabajo/<id>/`.
      *Acepta:* corre con `mini` en CI y con SD-II en local.

## Lotes y carriles (para ir más rápido sin perder rigor)

Antigravity trabaja por **lotes** con `/lote <tareas>`: hace merge solo si pasan la CI y la
auditoría (`/auditar`), y se detiene ante cualquier discrepancia. El orquestador revisa cada lote
completo.

| Lote | Tareas | Depende de | Carril |
|---|---|---|---|
| A | 1.6 etiquetas, 1.7 dificultad (+ `estadistica.py`) | 1.5 | 1 |
| B | 1.8 modelo | A | 1 |
| C | 1.9 verificar | 1.4 | 2 (en paralelo con A y B) |
| D | 1.10 armar, 1.11 E2E | B, C | 1 |
| E | 3.4 chequeos de transcripción, 5.1 empaquetar kit | 1.4 | 2 |

Dos agentes pueden trabajar en paralelo solo en **carriles distintos**, cada uno en su propio
`git worktree` (p. ej. `../Analisis_profesor-carril2`), y nunca tocan los mismos archivos.

**Precisiones de rigor para el lote A:**

- 1.7 usa `estadistica.py` con:
  - BCa contrastado con `scipy.stats.bootstrap(method="BCa")` (diferencia ≤ 0.02 con 10 000
    remuestras y la misma semilla);
  - permutación por cambio de signo exacta si n ≤ 20 (enumerar las 2ⁿ asignaciones);
    Monte Carlo con semilla si n > 20;
  - Wilcoxon contra `scipy.stats.wilcoxon`;
  - Spearman contra `scipy.stats.spearmanr`, con IC bootstrap;
  - intervalo de Jeffreys contra `scipy.stats.beta.ppf`.
- La salida de 1.7 reproduce `legacy/.../salidas/dificultad.json`: deltas por pares de 0.27 y
  0.40, totales por examen de 13.4, 12.3, 8.0 y 8.4, y fracción ≥ 0.99 de perturbaciones de
  pesos con el mismo signo. Agrega intervalos y p-valores sin alterar esos números.

## Fase 2: Prueba en chats reales (dueño + orquestador)

Aquí entra el contexto real. Se hace en cuanto cierre la 1.11, o antes en modo sin código para
probar el protocolo.

- [ ] 2.1 SD-II en **Antigravity** (`/analizar`), en **Claude.ai**, en **ChatGPT** y en
      **Gemini**, cada uno con el zip original y el prompt del README.
- [ ] 2.2 Bitácora por plataforma en `docs/pruebas_chat/<plataforma>.md`:
      - dónde se atoró;
      - qué no pudo ejecutar o instalar;
      - qué inventó;
      - comparación de su guía contra `legacy/MEJORAS_Y_USO.md`.
- [ ] 2.3 Protocolo v2 con las correcciones. Cada fricción se vuelve una regla o un script.
- [ ] 2.4 **Primera materia nueva real** con la plataforma que mejor funcionó.

## Fase 3: Extracción y etiquetado de calidad

- [ ] 3.1 `acuerdo`: α de Krippendorff ordinal entre las dos pasadas del paso 5.2 (y contra
      etiquetas humanas, si las hay) y reporte de rasgos inestables.
- [ ] 3.2 Similitud de fórmulas: LaTeX → sympy con símbolos canónicos y comparación de árbol de
      operadores; Jaccard de tokens LaTeX si no hay sympy.
      *Acepta:* detecta P2_2026-10-19:Q1 ≈ T4:3a.
- [ ] 3.3 MinHash en Python puro (o datasketch) para copias literales, y fusión de las
      similitudes con control de falsos positivos (Benjamini-Hochberg).
- [ ] 3.4 Chequeos automáticos de transcripción: LaTeX balanceado, puntos que suman, numeración
      continua y `[ilegible]` contados.
- [ ] 3.5 Arquetipos asistidos: `ap.py sugerir-arquetipos` agrupa ítems (TF-IDF con
      aglomerativo) como punto de partida para el paso 5.1.

## Fase 4: Estadística sólida

- [ ] 4.1 Intervalos creíbles 5-95 % por arquetipo, además del rango de sensibilidad.
- [ ] 4.2 Recencia: peso por antigüedad del examen.
- [ ] 4.3 Backtesting: predecir cada examen viejo con lo anterior; Brier y log score contra
      uniforme, solo tareas y último examen.
- [ ] 4.4 Diario de predicciones: `07_modelo.json` con fecha, y `ap.py evaluar` cuando llega el
      examen real.
- [ ] 4.5 Chequeos predictivos posteriores (número de preguntas, minutos, mezcla de fuentes).
- [ ] 4.6 Robustez del etiquetado: usar las dos pasadas como perturbación.

## Fase 5: Distribución

- [ ] 5.1 `scripts/empaquetar_kit.sh` → `dist/kit_analisis_profesor.zip` (protocolo, `ap.py`,
      `src`, plantillas; sin legacy ni tests), y un GitHub Action que lo publica como release en
      cada tag `v*`.
- [ ] 5.2 **Claude Skill**: `distribucion/claude-skill/SKILL.md`, que apunta al protocolo, más
      los scripts. Se sube a Claude.ai como skill personalizada.
- [ ] 5.3 **Custom GPT** y **Gem**: `distribucion/chatgpt.md` y `distribucion/gemini.md` con las
      instrucciones del sistema y qué archivos cargar como conocimiento.
- [ ] 5.4 Workflow `/analizar` de Antigravity y comando de Claude Code (`.claude/commands`).

## Fase 6: Más materias y aprendizaje entre profesores

- [ ] 6.1 Migrar PL, y Simulación cuando se recupere su código (`armado.py`, recorte por incisos;
      no venía en el zip).
- [ ] 6.2 Priors jerárquicos entre profesores (fracción que sale de la tarea, reciclaje,
      demostración) a partir de las materias acumuladas.

## Fase 7: Opcional (solo local)

Embeddings y BERTopic (extra `nlp`), servidor MCP con `ap.py` como herramientas, interfaz web.

---

## Cómo se trabaja

```
Dueño elige tarea ─> Antigravity: /tarea 1.3  ─> rama fase1/ingesta ─> pruebas ─> push ─> PR
                                                                                      │
Claude Code (orquestador) revisa el PR contra el "Acepta:" de la tarea <───────────────┘
Dueño hace merge a main
```
