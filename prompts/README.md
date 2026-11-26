# Prompts versionados

Un archivo por prompt (`clasificar_documento.md`, `extraer_examen.md`, `etiquetar_rasgos.md`,
`generar_variante.md`...). El encabezado lleva la versión:

    ---
    nombre: etiquetar_rasgos
    version: 1
    rol: etiquetado
    salida: Etiqueta        # modelo Pydantic de esquemas.py
    ---

`llm.py` carga el archivo, sustituye variables Jinja y guarda `version_prompt` en cada resultado.
Cambiar un prompt = subir la versión (invalida la caché de ese prompt).
