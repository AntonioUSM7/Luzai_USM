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
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import rag_engine
import router_jeff


class TestRagFaqsJeff(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name)
        ramo_dir = self.data_dir / "TESTRAG"
        ramo_dir.mkdir(parents=True, exist_ok=True)
        with open(ramo_dir / "config.json", "w", encoding="utf-8") as archivo:
            json.dump(
                {
                    "codigo": "TESTRAG",
                    "nombre": "Curso RAG Demo",
                    "faqs_jeff": [
                        {
                            "id": "faq_tunel",
                            "categoria": "Consultas Resueltas",
                            "pregunta": "¿Cuándo se entrega el informe final del proyecto?",
                            "palabras_clave": ["informe final"],
                            "respuesta": "📌 [Jeff - Respuesta Docente TESTRAG]: El documento final se sube hasta el viernes 20 a las 23:59 en AULA.",
                        }
                    ],
                },
                archivo,
                ensure_ascii=False,
                indent=2,
            )
        self.patchers = [
            patch.object(rag_engine, "DATA_DIR", self.data_dir),
            patch.object(rag_engine, "_clientes", {}),
            patch.object(router_jeff, "DATA_DIR", self.data_dir),
        ]
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        self.tmpdir.cleanup()

    @staticmethod
    def _fake_embedding(texto: str):
        t = texto.lower()
        # Vector simple de 4 dimensiones para pruebas deterministas de similitud coseno
        if any(k in t for k in ("informe", "documento", "entrega", "viernes", "subir", "plazo")):
            return [0.95, 0.05, 0.0, 0.0]
        if any(k in t for k in ("sala", "laboratorio", "edificio")):
            return [0.0, 0.95, 0.05, 0.0]
        return [0.0, 0.0, 0.95, 0.05]

    def test_indexar_buscar_formatear_eliminar_y_reindexar_faqs_jeff(self):
        with patch.object(
            rag_engine, "generar_embedding_ollama", side_effect=self._fake_embedding
        ):
            # 1. Reindexar ramo incluye faqs_jeff de config.json
            res_reindex = rag_engine.reindexar_ramo("TESTRAG")
            self.assertEqual(res_reindex["status"], "ok")
            self.assertEqual(res_reindex["faqs_indexadas"], 1)

            # 2. Consulta parafraseada que NO activa las keywords de Jeff ("informe final")
            consulta_parafraseada = "¿Hasta qué día puedo subir el documento del proyecto?"
            self.assertIsNone(router_jeff.resolver_consulta(consulta_parafraseada, "TESTRAG"))

            fragmentos = rag_engine.buscar_fragmentos_relevantes(
                consulta_parafraseada, "TESTRAG", top_k=3, min_score=0.5
            )
            self.assertEqual(len(fragmentos), 1)
            self.assertEqual(fragmentos[0]["carpeta"], rag_engine.CARPETA_FAQS_JEFF)
            self.assertEqual(fragmentos[0]["archivo"], rag_engine.FUENTE_FAQS_JEFF)

            contexto = rag_engine.formatear_contexto(fragmentos)
            self.assertIn("Preguntas Guardadas (Jeff)", contexto)
            self.assertIn("viernes 20", contexto)

            # 3. Agregar una segunda FAQ y luego eliminar solo la primera
            faq2 = {
                "id": "faq_sala",
                "categoria": "Ubicación",
                "pregunta": "¿En qué sala es el laboratorio?",
                "palabras_clave": ["sala"],
                "respuesta": "📌 [Jeff]: Sala C-204.",
            }
            rag_engine.indexar_faq_jeff("TESTRAG", faq2)
            self.assertEqual(rag_engine.obtener_cliente_chroma("TESTRAG").count(), 2)

            rag_engine.eliminar_faq_vectorial("TESTRAG", "faq_tunel")
            self.assertEqual(rag_engine.obtener_cliente_chroma("TESTRAG").count(), 1)


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
