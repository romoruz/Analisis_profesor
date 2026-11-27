"""CLI de `ap.py`. Un subcomando por paso [script] de PROTOCOLO.md. Solo librería estándar aquí.

Los subcomandos PENDIENTE los implementa el agente de código según docs/ROADMAP.md.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import sys
from collections import Counter
from pathlib import Path

from analisis_profesor import __version__

PENDIENTES: dict[str, tuple[str, str]] = {}

LIBRERIAS = {  # nombre de import: para qué sirve
    "numpy": "obligatoria para el modo completo",
    "scipy": "obligatoria para el modo completo (pruebas, bootstrap)",
    "sklearn": "opcional: TF-IDF rápido (si falta, versión en Python puro)",
    "sympy": "opcional: verificación simbólica y similitud de fórmulas",
    "fitz": "opcional: texto de PDF con PyMuPDF",
    "pypdf": "opcional: texto de PDF (alternativa)",
    "pdfplumber": "opcional: texto de PDF (alternativa)",
}


def diagnostico() -> dict:
    libs = {n: importlib.util.find_spec(n) is not None for n in LIBRERIAS}
    pdf = [n for n in ("fitz", "pypdf", "pdfplumber") if libs[n]]
    herramientas = {h: shutil.which(h) is not None for h in ("pdftotext", "pdflatex")}
    modo = "completo" if libs["numpy"] and libs["scipy"] else "reducido"
    return {
        "version_kit": __version__,
        "python": platform.python_version(),
        "python_ok": sys.version_info >= (3, 10),
        "librerias": libs,
        "herramientas": herramientas,
        "lector_pdf": pdf[0] if pdf else ("pdftotext" if herramientas["pdftotext"] else None),
        "modo": modo,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ap.py", description="Kit de análisis de profesor")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version")
    sub.add_parser("diagnostico", help="qué modo del PROTOCOLO se puede usar aquí")
    s_ingesta = sub.add_parser(
        "ingesta", help="zip -> 00_crudo, 01_inventario.csv, 02_texto/, pendientes"
    )
    s_ingesta.add_argument("zip", help="ruta al archivo .zip con el material")
    s_ingesta.add_argument("--materia", "-m", default="", help="id corto para trabajo/<id>/")
    s_items = sub.add_parser("items", help="02_texto/*.md -> 03_items.jsonl")
    s_items.add_argument("materia", help="id de la materia en trabajo/<id>/")
    s_sim = sub.add_parser("similitud", help="03_items.jsonl -> 04_similitud.json")
    s_sim.add_argument("materia", help="id de la materia en trabajo/<id>/")
    s_plant = sub.add_parser(
        "plantilla-etiquetas", help="03_items.jsonl -> 05_etiquetas.csv con una fila por ítem"
    )
    s_plant.add_argument("materia", help="id de la materia en trabajo/<id>/")
    s_plant.add_argument(
        "--sobrescribir", action="store_true", help="regenera todas las filas desde cero"
    )
    s_acu = sub.add_parser("acuerdo", help="consistencia entre pasadas de 05_etiquetas.csv")
    s_acu.add_argument("materia", help="id de la materia en trabajo/<id>/")
    s_acu.add_argument("--contra", default=None, help="CSV externo para comparar contra pasada 1")
    s_acu.add_argument("--semilla", type=int, default=2026, help="semilla bootstrap")
    s_dif = sub.add_parser("dificultad", help="05_etiquetas.csv -> 06_dificultad.json")
    s_dif.add_argument("materia", help="id de la materia en trabajo/<id>/")
    s_dif.add_argument("--semilla", type=int, default=2026, help="semilla bootstrap/permutación")
    s_mod = sub.add_parser("modelo", help="05_etiquetas.csv + materia.toml -> 07_modelo.json")
    s_mod.add_argument("materia", help="id de la materia en trabajo/<id>/")
    s_mod.add_argument("--semilla", type=int, default=None, help="semilla Monte Carlo")
    s_mod.add_argument("--simulaciones", type=int, default=20_000, help="réplicas base (R)")
    s_mod.add_argument("--rejilla", type=int, default=3_000, help="réplicas por punto de malla")
    s_mod.add_argument("--sorteos", type=int, default=5, help="número de simulacros sorteados")
    s_ver = sub.add_parser("verificar", help="ejecuta los bloques `verificacion` de 08_banco.md")
    s_ver.add_argument("materia", help="id de la materia en trabajo/<id>/")
    s_ver.add_argument("--timeout", type=float, default=15.0, help="límite por ejercicio (s)")
    s_ver.add_argument("--id", dest="ids", action="append", help="solo verificar IDs indicados")
    s_arm = sub.add_parser("armar", help="arma simulacros y genera entregables")
    s_arm.add_argument("materia", help="id de la materia en trabajo/<id>/")
    s_arm.add_argument("--n", type=int, default=5, help="número de simulacros a generar")
    s_arm.add_argument("--semilla", type=int, default=2026, help="semilla para desempate")
    s_arm.add_argument("--tolerancia", type=float, default=1.0, help="banda ± de dificultad")
    s_arm.add_argument("--sin-pdf", action="store_true", help="no compilar simulacros.tex a PDF")
    s_val = sub.add_parser("validar-guia", help="verifica citas y cifras de GUIA_PARCIAL.md")
    s_val.add_argument("materia", help="id de la materia en trabajo/<id>/")
    s_val.add_argument("--guia", default=None, help="ruta alternativa a GUIA_PARCIAL.md")
    s_val.add_argument(
        "--tolerancia", type=float, default=0.011, help="tolerancia numérica contra 07_modelo.json"
    )
    for nombre, (_fase, ayuda) in PENDIENTES.items():
        s = sub.add_parser(nombre, help=ayuda)
        s.add_argument("args", nargs="*")
    a = p.parse_args(argv)

    if a.cmd == "version":
        print(__version__)
        return 0
    if a.cmd == "diagnostico":
        d = diagnostico()
        print(json.dumps(d, indent=2, ensure_ascii=False))
        print(f"\nModo del PROTOCOLO: {d['modo'].upper()}")
        if not d["lector_pdf"]:
            print("Sin lector de PDF: transcribe los PDFs mirándolos (paso 2).")
        return 0
    if a.cmd == "ingesta":
        ruta_zip = Path(a.zip)
        if not ruta_zip.is_file():
            print(f"Error: no existe el archivo {ruta_zip}", file=sys.stderr)
            return 1
        materia = a.materia or ruta_zip.stem
        from analisis_profesor.ingesta import ingestar

        docs = ingestar(ruta_zip, materia)
        n_pend = sum(1 for d in docs if d.necesita_transcripcion)
        print(f"Ingesta completa en trabajo/{materia}/: {len(docs)} archivos, {n_pend} pendientes.")
        return 0
    if a.cmd == "items":
        texto_dir = Path("trabajo") / a.materia / "02_texto"
        if not texto_dir.is_dir():
            print(f"Error: no existe {texto_dir}", file=sys.stderr)
            return 1
        from analisis_profesor.segmentacion import segmentar_carpeta

        items = segmentar_carpeta(a.materia)
        etiquetables = [it for it in items if not it.padre_id]
        hijos = [it for it in items if it.padre_id]
        conteo_etiq = Counter(it.documento_id for it in etiquetables)
        conteo_hijos = Counter(it.documento_id for it in hijos)
        for doc_id, n in conteo_etiq.items():
            extra = f" (+{conteo_hijos[doc_id]} incisos)" if conteo_hijos[doc_id] else ""
            print(f"  {doc_id}: {n} ítems{extra}")
        print(
            f"Total: {len(etiquetables)} ítems etiquetables en trabajo/{a.materia}/03_items.jsonl"
        )
        return 0
    if a.cmd == "similitud":
        ruta_items = Path("trabajo") / a.materia / "03_items.jsonl"
        if not ruta_items.is_file():
            print(f"Error: no existe {ruta_items}", file=sys.stderr)
            return 1
        from analisis_profesor.similitud import calcular_similitud

        res = calcular_similitud(a.materia)
        lb = res["linea_base"]
        print(
            f"Línea base material (n_pares={lb['n_pares']}): "
            f"media={lb['media']:.3f}, p95={lb['p95']:.3f}"
        )
        for qid, entrada in res["preguntas_examen"].items():
            cand, sim = entrada["mas_parecidos"][0] if entrada["mas_parecidos"] else ("-", 0.0)
            print(f"  {qid} -> {cand} ({sim:.3f}) [{entrada['clasificacion']}]")
        return 0
    if a.cmd == "plantilla-etiquetas":
        ruta_items = Path("trabajo") / a.materia / "03_items.jsonl"
        if not ruta_items.is_file():
            print(f"Error: no existe {ruta_items}", file=sys.stderr)
            return 1
        from analisis_profesor.config import leer_config_materia
        from analisis_profesor.etiquetas import generar_plantilla_etiquetas, leer_etiquetas

        ruta_csv = generar_plantilla_etiquetas(a.materia, sobrescribir=a.sobrescribir)
        rasgos = leer_config_materia(Path("trabajo") / a.materia)["rasgos"]
        n_filas = len(leer_etiquetas(ruta_csv, rasgos=rasgos))
        print(f"Plantilla escrita en {ruta_csv} ({n_filas} ítems).")
        return 0
    if a.cmd == "acuerdo":
        ruta_etiq = Path("trabajo") / a.materia / "05_etiquetas.csv"
        if not ruta_etiq.is_file():
            print(f"Error: no existe {ruta_etiq}", file=sys.stderr)
            return 1
        ruta_contra = Path(a.contra) if a.contra else None
        if ruta_contra is not None and not ruta_contra.is_file():
            print(f"Error: no existe {ruta_contra}", file=sys.stderr)
            return 1
        from analisis_profesor.acuerdo import calcular_acuerdo

        res = calcular_acuerdo(a.materia, ruta_contra=ruta_contra, semilla=a.semilla)
        if res["n_items"] < 2:
            print(
                f"Error: solo hay {res['n_items']} ítems emparejados; agrega filas con "
                "`pasada=2` en 05_etiquetas.csv o usa `--contra <archivo.csv>`.",
                file=sys.stderr,
            )
            return 1
        print(
            f"Acuerdo calculado en trabajo/{a.materia}/05_acuerdo.json "
            f"(n={res['n_items']}, exploratorio={res['exploratorio']}, "
            f"inestables={res['rasgos_inestables']}):"
        )
        for campo, info in res["por_campo"].items():
            print(
                f"  {campo}: alpha={info['alfa']:.3f} IC={info['ic_bootstrap']} "
                f"[{info['clasificacion']}]"
            )
        return 0
    if a.cmd == "dificultad":
        ruta_etiq = Path("trabajo") / a.materia / "05_etiquetas.csv"
        if not ruta_etiq.is_file():
            print(f"Error: no existe {ruta_etiq}", file=sys.stderr)
            return 1
        from analisis_profesor.dificultad import calcular_dificultad

        res = calcular_dificultad(a.materia, semilla=a.semilla)
        inf = res["alcance_objetivo"]["delta_pares_inferencia"]
        ic = inf["ic_bca"]
        print(
            f"Dificultad calculada en trabajo/{a.materia}/06_dificultad.json "
            f"(pares en alcance n={inf['n']}, omitidos={inf['n_omitidos']}, "
            f"delta={inf['media']}, IC BCa={ic}, p_perm={inf['p_permutacion']}, "
            f"conclusión={inf['conclusion']})."
        )
        return 0
    if a.cmd == "modelo":
        ruta_etiq = Path("trabajo") / a.materia / "05_etiquetas.csv"
        if not ruta_etiq.is_file():
            print(f"Error: no existe {ruta_etiq}", file=sys.stderr)
            return 1
        from analisis_profesor.modelo import calcular_modelo

        res = calcular_modelo(
            a.materia,
            semilla=a.semilla,
            n_simulaciones=a.simulaciones,
            n_rejilla=a.rejilla,
            n_sorteos=a.sorteos,
        )
        print(
            f"Modelo calculado en trabajo/{a.materia}/07_modelo.json "
            f"(R={res['n_simulaciones']}, molde={res['n_examenes_molde']}, "
            f"p_dem={res['probabilidad_demostracion']:.3f}):"
        )
        for aviso in res.get("parametros_derivados", {}).get("avisos_rotacion", []):
            print(f"  Aviso rotación: {aviso}")
        for p_item in sorted(res["predicciones"], key=lambda d: -d["p_media"]):
            print(
                f"  {p_item['arquetipo']}: base={p_item['p_media']:.3f} "
                f"IC 5-95=[{p_item['p_q05']:.3f}, {p_item['p_q95']:.3f}] "
                f"sens=[{p_item['p_min_sensibilidad']:.3f}, {p_item['p_max_sensibilidad']:.3f}]"
            )
        return 0
    if a.cmd == "verificar":
        ruta_banco = Path("trabajo") / a.materia / "08_banco.md"
        if not ruta_banco.is_file():
            print(f"Error: no existe {ruta_banco}", file=sys.stderr)
            return 1
        from analisis_profesor.banco import verificar_banco

        res = verificar_banco(a.materia, timeout_s=a.timeout, ids=a.ids)
        for item in res["resultados"]:
            marca = {"ok": "OK", "manual": "MN", "fallo": "XX", "timeout": "TO"}[item["estado"]]
            print(f"  [{marca}] {item['id']} ({item['arquetipo']}) -> {item['estado']}")
        print(
            f"Verificación completada en trabajo/{a.materia}/08_verificacion.json: "
            f"{res['verificados']}/{res['total']} verificados "
            f"({res['automaticos_ok']} automáticos OK, {res['manuales']} manuales, "
            f"{res['automaticos_fallidos']} fallidos)."
        )
        faltantes_niv = res.get("niveles_faltantes_por_arquetipo") or {}
        if faltantes_niv:
            resumen_niv = "; ".join(
                f"{arq}: {', '.join(nivs)}" for arq, nivs in faltantes_niv.items()
            )
            print(f"Aviso: niveles faltantes en 08_banco.md -> {resumen_niv}")
        return 0 if res["todos_ok"] else 1
    if a.cmd == "armar":
        ruta_banco = Path("trabajo") / a.materia / "08_banco.md"
        if not ruta_banco.is_file():
            print(f"Error: no existe {ruta_banco}", file=sys.stderr)
            return 1
        from analisis_profesor.armado import armar_simulacros

        res = armar_simulacros(
            a.materia,
            n_simulacros=a.n,
            semilla=a.semilla,
            tolerancia=a.tolerancia,
            compilar_pdf=not a.sin_pdf,
        )
        print(
            f"Simulacros armados en trabajo/{a.materia}/simulacros.json "
            f"(meta={res['meta_dificultad_total']:.2f}, n={len(res['examenes'])}):"
        )
        for ex in res["examenes"]:
            ids_str = " ".join(f"{q['arq']}:{q['id']}" for q in ex["preguntas"])
            print(
                f"  Simulacro {ex['numero']} ({ex['minutos']} min, "
                f"dificultad={ex['dificultad_total']:.2f}): {ids_str}"
            )
        print(
            f"Huecos relajados: {res['n_huecos_relajados']}/{res['n_huecos_totales']} "
            f"(nivel={res['n_huecos_nivel_relajado']})"
        )
        for aviso in res.get("avisos_relajacion", []):
            print(f"  Aviso: {aviso}")
        ent = res["entregables"]
        print(
            f"Entregables: SIMULACROS.md, SOLUCIONES.md, simulacros.tex"
            f"{', simulacros.pdf' if ent.get('pdf_generado') else ''}"
        )
        motivo = str(ent.get("motivo", ""))
        if not a.sin_pdf and not ent.get("pdf_generado") and motivo:
            print(f"Aviso: no se generó el PDF ({motivo}). Usa SIMULACROS.md o el .tex.")
        return 0
    if a.cmd == "validar-guia":
        base = Path("trabajo") / a.materia
        ruta_items = base / "03_items.jsonl"
        ruta_modelo = base / "07_modelo.json"
        guia_path = Path(a.guia) if a.guia else (base / "entregables" / "GUIA_PARCIAL.md")
        for req in (ruta_items, ruta_modelo, guia_path):
            if not req.is_file():
                print(f"Error: no existe {req}", file=sys.stderr)
                return 1
        from analisis_profesor.validacion_guia import validar_guia

        res = validar_guia(a.materia, ruta_guia=guia_path, tolerancia=a.tolerancia)
        estado = "VÁLIDA" if res["valida"] else "INVÁLIDA"
        n_k = len(res["arquetipos_en_tabla"]) + len(res["arquetipos_faltantes"])
        desf = res.get("salidas_desfasadas", [])
        desf_txt = f"; salidas desfasadas: {len(desf)}" if desf else ""
        print(f"Validación de guía ({a.materia}): {estado} -> {base / '09_validacion_guia.json'}")
        print(
            f"  IDs citados: {res['n_ids_citados']} "
            f"(inexistentes: {len(res['ids_inexistentes'])}); "
            f"temas validados: {res['temas_validados']}/{n_k}{desf_txt}"
        )
        for aviso in res["avisos"]:
            print(f"  Aviso: {aviso}")
        for err in res["errores"]:
            print(f"  Error: {err}")
        return 0 if res["valida"] else 1
    fase, _ = PENDIENTES[a.cmd]
    print(f"PENDIENTE: `{a.cmd}` se implementa en la {fase} (docs/ROADMAP.md). "
          "Mientras tanto, haz este paso a mano según el Anexo C de PROTOCOLO.md.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
