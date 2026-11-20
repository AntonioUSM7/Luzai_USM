"""
Prueba aislada del motor RAG.

Uso:
    python test_rag.py --query "¿Cómo se calcula una integral de superficie?"
    python test_rag.py --ramo TEL20425 --archivo data/ramos/TEL20425/documentos/Guias/guia.pdf
    python test_rag.py --solo-buscar --query "teorema de Stokes"

Nota: requiere que Ollama esté corriendo y `ollama pull nomic-embed-text`.
"""

import argparse
import json
from pathlib import Path

import rag_engine


def buscar_pdf_por_defecto(ramo: str) -> Path:
    base = Path(__file__).resolve().parent / "data" / "ramos" / ramo / "documentos"
    pdfs = sorted(base.rglob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No encontré PDFs en {base}")
    return pdfs[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Prueba del pipeline RAG de LuzAI")
    parser.add_argument("--ramo", default="MAT024", help="Código del ramo (ej. MAT024)")
    parser.add_argument("--archivo", default=None, help="Ruta del PDF a indexar")
    parser.add_argument("--carpeta", default=None, help="Carpeta lógica del documento")
    parser.add_argument("--query", default="¿Cómo se calcula una integral de superficie?")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--solo-buscar", action="store_true", help="No indexar, solo consultar")
    args = parser.parse_args()

    ramo = args.ramo.upper()

    if args.archivo:
        ruta = Path(args.archivo)
        if not ruta.is_absolute():
            ruta = Path(__file__).resolve().parent / ruta
    else:
        ruta = buscar_pdf_por_defecto(ramo)

    carpeta = args.carpeta or ruta.parent.name

    if not args.solo_buscar:
        print(f"\n[1/3] Indexando {ruta.name} (carpeta={carpeta}) ...")
        resultado = rag_engine.indexar_documento(ruta, ramo, carpeta)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))

    coleccion = rag_engine.obtener_cliente_chroma(ramo)
    print(f"\n[2/3] Fragmentos almacenados en {ramo}: {coleccion.count()}")

    print(f"\n[3/3] Consulta: {args.query}")
    fragmentos = rag_engine.buscar_fragmentos(args.query, ramo, top_k=args.top_k)
    if not fragmentos:
        print("Sin resultados. Revisa que el PDF tenga texto y que Ollama esté disponible.")
        return

    for indice, fragmento in enumerate(fragmentos, start=1):
        print(
            f"\n[{indice}] {fragmento['archivo']} | pág. {fragmento['pagina']} "
            f"| carpeta {fragmento['carpeta']} | score {fragmento['score']}"
        )
        print(fragmento["texto"][:500])


if __name__ == "__main__":
    main()
