# Investigación: literatura y repos

Revisado en noviembre de 2026. Para cada fuente se dice qué se toma y en qué fase. Las cifras
son las que reportan los propios autores.

## 1. Repos que encontraste

| Repo | Qué es | Qué tomamos | Fase |
|---|---|---|---|
| [CodeMesh39/Past-Paper-Analysis](https://github.com/CodeMesh39/Past-Paper-Analysis) | App TS + GPT-4o-mini: temas, cobertura del temario, plan de estudio, preguntas de práctica. MIT | Score de importancia de tema = frecuencia × recencia × peso en puntos, y cobertura contra temario. Solo LLM, sin estadística ni verificación | 5, 7 |
| [CodebyKumar/QPAT](https://github.com/CodebyKumar/QPAT-QuestionPaperAnalysingTool) | Streamlit + Gemini: PDF → JSON → categorías → "más probables". MIT | Estructura lineal del pipeline y banco por materia, unidad y año. No copiar el manejo de la API key | 1 |
| [Priyanka-SA04/BLOOMS-TAXONOMY-PREDICTION](https://github.com/Priyanka-SA04/BLOOMS-TAXONOMY-PREDICTION) | Flask + DistilBERT, Bloom de 6 niveles. Sin licencia | Tabla de verbos por nivel como línea base de reglas. No reutilizar pesos (sin licencia) | 4 |
| [VMD7/blooms-taxonomy-classifier](https://github.com/VMD7/blooms-taxonomy-classifier) | Clasificador Bloom con app web y Android. MIT | Referencia de despliegue; el modelo no está documentado | — |
| [RyanLauQF/BloomBERT](https://github.com/RyanLauQF/BloomBERT) | DistilBERT, 6175 ítems; 0.90 de exactitud en validación contra 0.87 de SVC + TF-IDF. MIT | Comparación de líneas base, la idea de **pérdida ordinal** (confundir Crear con Recordar cuesta más) y que un SVC con TF-IDF casi empata | 4 |
| [TaroAndMulan/QuestionExtractorAI](https://github.com/TaroAndMulan/QuestionExtractorAI) | OpenCV para recortar preguntas en escaneos. En desarrollo | Solo si hay escaneos de muchas páginas; para fotos sueltas basta el VLM | 1 (opcional) |
| [yerdaulet-damir/openquiz](https://github.com/yerdaulet-damir/openquiz) | App de tarjetas y quiz (Next.js) | Patrón "el LLM devuelve JSON y se importa", y un score de fuerza para repaso espaciado | 7 (opcional) |

**Conclusión:** ninguno combina reciclaje, dificultad, estadística con incertidumbre, simulacros
verificados y validación por predicción. Tu `legacy` ya está por encima en metodología. Lo que
estos repos aportan es producto (interfaz, plan de estudio, importación) y líneas base para
Bloom.

## 2. Repos adicionales (búsqueda por exam-paper-analyzer, pyq-analysis, question-clustering)

- [github.com/topics/study-prioritizer](https://github.com/topics/study-prioritizer): aquí aparece
  un *exam-question-paper-analyzer* con agrupación semántica, distribución de pesos y Pareto
  80/20. Lo de Pareto (qué 20 % de temas da el 80 % de puntos) sirve para el reporte.
- [dev-saxena-tech PYQ-Analyzer](https://github.com/dev-saxena-tech/Dev_saxena-PYQ-Analyzer-):
  Streamlit, TF-IDF y agrupación de preguntas repetidas.
- [yashvi-chulawala/GTU-PYQ-Analyzer](https://github.com/yashvi-chulawala/GTU-PYQ-Analyzer): agrupa
  por tema y ordena por frecuencia, unidad por unidad.
- [Jaheed1901/DAV-Project](https://github.com/Jaheed1901/DAV-Project): normalización de cadenas,
  n-gramas y umbral de coseno. Es lo mismo que tu fase 2 léxica.
- [kaushiki-guha/PYQ-Chatbot-Analyzer](https://github.com/kaushiki-guha/PYQ-Chatbot-Analyzer):
  K-Means más Gemini.
- [dooms90/PYQ_HeatMap](https://github.com/dooms90/PYQ_HeatMap): mapa de calor de preguntas
  contra temario. Buena idea de visualización para el reporte.
- [HUSAM-07/UniDash-PYQ-Analyzer](https://github.com/HUSAM-07/UniDash-PYQ-Analyzer),
  [Max9561/AI-PYQ-Analyzer](https://github.com/Max9561/AI-PYQ-Analyzer),
  [R024k/Exam-Query](https://github.com/R024k/Exam-Query) (búsqueda de preguntas, no predicción) y
  [thatiswat/QPP-Pro](https://github.com/thatiswat/QPP-Pro) (generación de exámenes con embeddings).

Todos siguen el mismo patrón: extraer, agrupar, contar frecuencia y pedirle al LLM que ordene.
Ninguno valida sus predicciones ni cuantifica incertidumbre. Ese es el diferenciador de este
proyecto.

**Herramientas de extracción:**

- [Marker](https://github.com/VikParuchuri/marker) ([PyPI](https://pypi.org/project/marker-pdf/)):
  PDF a Markdown con ecuaciones; 76.0 % en olmOCR-bench según su propio benchmark.
- [MinerU](https://pypi.org/project/mineru/3.0.9/): fórmulas a LaTeX, tablas a HTML.
- [Nougat](https://arxiv.org/abs/2308.13418) (Meta, ICLR 2024): OCR académico a markup con
  LaTeX. Pesos CC-BY-NC y funciona mejor en inglés.

  Recomendación: la propia IA del chat transcribe las fotos y los escaneos (es multimodal), y
  Marker queda como opción local.

**Otras librerías:**

- [BERTopic](https://arxiv.org/abs/2203.05794): embeddings + UMAP + HDBSCAN + c-TF-IDF. Es
  modular, así que se puede usar con embeddings multilingües (fase 3).
- LiteLLM se evaluó para llamar APIs desde el código, pero se descartó: el juicio lo pone la IA
  del chat que sigue `PROTOCOLO.md`, sin API keys.

## 3. Literatura

**Dificultad de preguntas desde el texto (fase 4)**

- Benedetto et al. (2023), *A Survey on Recent Approaches to Question Difficulty Estimation from
  Text*, ACM Computing Surveys ([DOI](https://doi.org/10.1145/3556538)). Es la referencia base:
  rasgos lingüísticos, de legibilidad y modelos neuronales.
- Benedetto (2023), *A quantitative study of NLP approaches to question difficulty estimation*
  ([arXiv:2305.10236](https://arxiv.org/abs/2305.10236v1)). Comparación empírica: los
  transformers ganan si hay datos; si no, los rasgos explícitos compiten. Justifica que tu rúbrica
  de rasgos sea el score principal.
- Alkhuzaey et al. (2023), revisión sistemática en IJAIED
  ([Springer](https://link.springer.com/article/10.1007/s40593-023-00362-1)). Catálogo de rasgos
  de dificultad.

**Bloom, DOK y Stein (fase 4.2)**

- BloomNet ([arXiv:2108.07249](https://arxiv.org/pdf/2108.07249)): transformer con información
  lingüística y semántica.
- Clasificación Bloom entre bases de datos con modelos supervisados y LLMs con prompt
  ([arXiv:2606.13684](https://arxiv.org/pdf/2606.13684)): cuánto cae el desempeño fuera del
  dominio de entrenamiento. Justifica no reutilizar clasificadores de GitHub.
- Con pocos datos, un SVM con aumento de datos compite con BERT
  ([arXiv:2511.10903](https://arxiv.org/pdf/2511.10903v1)).
- GenAI en lógica matemática ([arXiv:2505.11899](https://arxiv.org/html/2505.11899v1)): Webb DOK
  se ajusta mejor que Bloom para matemáticas. Por eso se guardan los dos.
- Guía de análisis de tareas de Stein y Smith (cuatro niveles de demanda en matemáticas, hasta
  "hacer matemáticas") y matriz de rigor cognitivo de Hess (Bloom × DOK)
  ([Springer 2023](https://link.springer.com/article/10.1007/s10649-023-10254-9),
  [matriz de Hess](https://www.scusd.edu/sites/main/files/file-attachments/hess_cognitive_rigor_matrix.pdf)).

**Generación con dificultad controlada (fase 6)**

- Elkins et al. (2024), preguntas por nivel Bloom con *few-shot*
  ([arXiv:2401.05914](https://arxiv.org/pdf/2401.05914v2)).
- DiffiQG, generación condicionada a dificultad ([CEUR](https://ceur-ws.org/Vol-4296/paper4.pdf)).
- DeepQuestion ([arXiv:2505.24532](https://arxiv.org/html/2505.24532)): subir el nivel cognitivo
  baja hasta 70 % el desempeño de los LLM. Por eso todo ejercicio generado pasa por un
  verificador.
- Advertencia ([arXiv:2609.27063](https://arxiv.org/pdf/2609.27063)): cuando el LLM pone él mismo
  la etiqueta de dificultad, esta refleja su prompt, no la dificultad empírica. Por eso la
  dificultad del banco se calcula con la misma rúbrica que los exámenes reales, no la declara el
  generador.

**LLM como etiquetador y acuerdo (fase 4.3)**

- Equivalencia del LLM con anotadores humanos y prueba de equivalencia sobre α de Krippendorff
  ([arXiv:2510.06658](https://arxiv.org/pdf/2510.06658)).
- El LLM pierde acuerdo en categorías ambiguas y oraciones complejas
  ([arXiv:2411.19638](https://arxiv.org/pdf/2411.19638),
  [arXiv:2512.00046](https://arxiv.org/pdf/2512.00046)). El α se infla o desinfla con clases
  raras: hay que estratificar la muestra.

**Similitud de fórmulas (fase 2.3)**

- Tangent-CFT: embeddings de árboles de símbolos (SLT) y de operadores (OPT)
  ([ICTIR 2019](https://www.cs.rit.edu/~rlaz/files/Mansouri_ICTIR2019.pdf)). Aprendizaje de
  ranking combinando subárbol, árbol completo y embedding
  ([SIGIR 2021](https://www.cs.rit.edu/~rlaz/files/LTR_Formulas_SIGIR2021.pdf)). SSEmb
  ([arXiv:2508.04162](https://arxiv.org/html/2508.04162v2)), evaluado en ARQMath.
- Para exámenes basta algo simple: árbol de operadores con sympy y símbolos canónicos. La
  literatura confirma que la estructura (OPT) le gana a la apariencia para detectar "la misma
  ecuación con otros números".

**Detección de casi duplicados (fase 2.1)**

- [MinHash](https://www.wikipedia.org/wiki/MinHash) y LSH para copias literales. Los métodos de
  n-gramas fallan con paráfrasis y los neuronales los superan
  ([arXiv:2210.04261](https://arxiv.org/pdf/2210.04261)). Por eso se fusionan léxica, semántica y
  fórmulas.

**Estadística con muestras chicas (fases 4 y 5)**

- Bootstrap BCa con prueba de permutación por cambio de signo para deltas pareados
  ([arXiv:2511.19794](https://arxiv.org/pdf/2511.19794)).
- Inferencia con muestras chicas ([arXiv:2609.35815](https://arxiv.org/pdf/2609.35815)): Wilcoxon
  y la prueba de permutación conservan bien el error tipo I; la mayoría de los bootstraps no.
- Dirichlet-multinomial conjugado y el problema de las celdas en cero
  ([apuntes Berkeley STAT 238](https://stat238.berkeley.edu/spring-2026/lecturethirteen238spring2026),
  [Dirichlet-multinomial](https://www.wikipedia.org/wiki/Dirichlet-multinomial_distribution)).
  Prior simétrico de suavizado a ≈ 0.8/m según Berger, Bernardo y Sun
  ([arXiv:1504.02689](https://arxiv.org/pdf/1504.02689)).
- TRI con muestras chicas: incluso los métodos jerárquicos bayesianos piden N ≈ 100 examinados
  ([König, Spoden y Frey](https://publikationen.ub.uni-frankfurt.de/files/54836/0146621619893786.pdf),
  [PMC7221499](https://pmc.ncbi.nlm.nih.gov/articles/PMC7221499)). Por eso aquí no se usa TRI.
- Puntuaciones propias (Brier y log score) para evaluar predicciones probabilísticas
  ([arXiv:2205.10586](https://arxiv.org/pdf/2205.10586)). La predicción conforme con calibración
  chica pierde garantías ([arXiv:2512.04566](https://arxiv.org/abs/2512.04566v1)), así que no se
  adopta.

**Sistemas de análisis de exámenes pasados**

- Proceso OCR + NLP + modelado de tópicos + agrupación semántica + frecuencia
  ([Atlantis Press](https://www.atlantis-press.com/article/126025320.pdf)). Es el estado del arte
  "producto" y no valida sus predicciones.

## 4. Lo que la evidencia no respalda (para no prometerlo)

- "Predecir las preguntas exactas": con 2 a 4 exámenes solo se puede dar la distribución sobre
  tipos con intervalos anchos. El backtesting dirá cuánto vale.
- Clasificar Bloom con un modelo de GitHub en matemáticas en español: fuera de dominio.
- TRI, conformal o ji-cuadrada con estos tamaños de muestra.
