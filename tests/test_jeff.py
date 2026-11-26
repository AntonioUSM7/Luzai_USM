"""Pruebas unitarias y rápida del enrutador Jeff. No necesita Ollama ni Docker."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from _test_env import asegurar_backend_en_path

asegurar_backend_en_path()

import rag_engine
import router_jeff

CASOS = [
    ("¿Cuándo es el certamen de MAT024?", "MAT024"),
    ("¿Qué libro recomienda el ramo?", "MAT024"),
    ("¿Cómo se entrega la tarea 1?", "MAT024"),
    ("¿Dónde es el laboratorio de TEL20425?", "TEL20425"),
    ("¿Cómo parametrizo la frontera de la semiesfera?", "MAT024"),
    ("ensalada de frutas", "TEL20425"),
]


class TestRouterJeffCrud(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name)
        ramo_dir = self.data_dir / "TEST101"
        ramo_dir.mkdir(parents=True, exist_ok=True)
        with open(ramo_dir / "config.json", "w", encoding="utf-8") as archivo:
            json.dump(
                {
                    "codigo": "TEST101",
                    "nombre": "Curso Demo",
                    "faqs_jeff": [
                        {
                            "id": "faq_inicial",
                            "categoria": "General",
                            "palabras_clave": ["horario"],
                            "respuesta": "📌 [Jeff]: Lunes 10:00.",
                        }
                    ],
                },
                archivo,
                ensure_ascii=False,
                indent=2,
            )
        self.patcher = patch.object(router_jeff, "DATA_DIR", self.data_dir)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmpdir.cleanup()

    def test_crud_faqs_jeff_con_pregunta_y_autosugerencia(self):
        # Listar inicial
        faqs = router_jeff.listar_faqs_jeff("TEST101")
        self.assertEqual(len(faqs), 1)

        # Agregar con pregunta y sin palabras_clave -> auto-sugiere desde pregunta
        creada = router_jeff.agregar_faq_jeff(
            codigo_ramo="TEST101",
            respuesta="La evaluación recuperativa es el martes 15 en sala C-201.",
            palabras_clave=[],
            categoria="Evaluaciones",
            pregunta="¿Cuándo es la prueba recuperativa del curso?",
        )
        self.assertEqual(creada["pregunta"], "¿Cuándo es la prueba recuperativa del curso?")
        self.assertIn("recuperativa", creada["palabras_clave"])
        self.assertTrue(creada["respuesta"].startswith("[Jeff"))

        # Jeff responde por keyword auto-sugerida
        match = router_jeff.resolver_consulta("consulta sobre recuperativa", "TEST101")
        self.assertIsNotNone(match)
        self.assertEqual(match["topico"], creada["id"])

        # Actualizar FAQ
        actualizada = router_jeff.actualizar_faq_jeff(
            codigo_ramo="TEST101",
            faq_id=creada["id"],
            respuesta="La recuperativa cambió al miércoles 16 en sala B-102.",
            palabras_clave=["recuperativa", "examen sustitutivo"],
            categoria="Fechas y Entregas",
            pregunta="¿Fecha actualizada de la evaluación recuperativa?",
        )
        self.assertEqual(actualizada["categoria"], "Fechas y Entregas")
        self.assertEqual(
            actualizada["pregunta"], "¿Fecha actualizada de la evaluación recuperativa?"
        )
        self.assertIn("examen sustitutivo", actualizada["palabras_clave"])
        self.assertIn("miércoles 16", actualizada["respuesta"])

        # Eliminar FAQ
        eliminada = router_jeff.eliminar_faq_jeff("TEST101", creada["id"])
        self.assertEqual(eliminada["id"], creada["id"])
        self.assertEqual(len(router_jeff.listar_faqs_jeff("TEST101")), 1)

        # Eliminar inexistente -> KeyError
        with self.assertRaises(KeyError):
            router_jeff.eliminar_faq_jeff("TEST101", "no_existe")

    def test_crud_tareas_jeff(self):
        tareas_iniciales = router_jeff.listar_tareas("TEST101")
        self.assertEqual(tareas_iniciales, [])

        creada = router_jeff.agregar_tarea(
            codigo_ramo="TEST101",
            titulo="Informe 2",
            fecha_limite="Viernes 23:59 hrs",
            formato_entrega="PDF vía AULA USM",
            plataforma="Buzón de Tareas",
            palabras_clave=["informe 2", "entrega informe 2"],
        )
        self.assertEqual(creada["titulo"], "Informe 2")
        self.assertEqual(len(router_jeff.listar_tareas("TEST101")), 1)

        match = router_jeff.resolver_consulta("cuando se entrega el informe 2", "TEST101")
        self.assertIsNotNone(match)
        self.assertEqual(match["tipo"], "tarea")
        self.assertEqual(match["topico"], creada["id"])

        actualizada = router_jeff.actualizar_tarea(
            codigo_ramo="TEST101",
            tarea_id=creada["id"],
            titulo="Informe 2 actualizado",
            fecha_limite="Lunes 12:00 hrs",
            formato_entrega="PDF y DOCX",
            plataforma="AULA USM",
            palabras_clave=["informe 2"],
        )
        self.assertEqual(actualizada["fecha_limite"], "Lunes 12:00 hrs")
        self.assertEqual(actualizada["formato_entrega"], "PDF y DOCX")

        eliminada = router_jeff.eliminar_tarea("TEST101", creada["id"])
        self.assertEqual(eliminada["id"], creada["id"])
        self.assertEqual(router_jeff.listar_tareas("TEST101"), [])

        with self.assertRaises(KeyError):
            router_jeff.eliminar_tarea("TEST101", "no_existe")

    def test_consulta_parafraseada_de_tarea_no_activa_keyword_y_recupera_rag(self):
        tarea = router_jeff.agregar_tarea(
            codigo_ramo="TEST101",
            titulo="Informe de laboratorio 2",
            fecha_limite="Viernes 23:59",
            palabras_clave=["informe laboratorio 2"],
        )
        consulta = "¿Hasta cuándo tengo que subir el reporte práctico?"

        def _embedding(texto: str):
            normalizado = texto.lower()
            if any(
                clave in normalizado
                for clave in ("entrega", "reporte", "plazo", "informe", "tarea")
            ):
                return [0.95, 0.05, 0.0, 0.0]
            return [0.0, 0.0, 0.95, 0.05]

        with (
            patch.object(rag_engine, "DATA_DIR", self.data_dir),
            patch.object(rag_engine, "_clientes", {}),
            patch.object(rag_engine, "generar_embedding_ollama", side_effect=_embedding),
        ):
            rag_engine.indexar_tarea_jeff("TEST101", tarea)
            self.assertIsNone(router_jeff.resolver_consulta(consulta, "TEST101"))
            fragmentos = rag_engine.buscar_fragmentos_relevantes(
                consulta, "TEST101", top_k=3, min_score=0.5
            )

        self.assertTrue(
            any(f["carpeta"] == rag_engine.CARPETA_TAREAS_JEFF for f in fragmentos)
        )

    def test_planificacion_documentos_y_desambiguacion(self):
        dir_plan = self.data_dir / "TEST101" / "documentos" / "Planificacion"
        dir_plan.mkdir(parents=True, exist_ok=True)
        (dir_plan / "Planificacion_Materia.pdf").write_bytes(b"%PDF-1.4")

        # 1 documento: entrega enlace directo
        r1 = router_jeff.resolver_consulta("cual es la planificacion del curso?", "TEST101")
        self.assertIsNotNone(r1)
        self.assertEqual(r1["canal"], "JEFF_ADMIN")
        self.assertIn("/api/ramos/TEST101/documentos/Planificacion/Planificacion_Materia.pdf", r1["respuesta"])

        # 2 documentos: pregunta general ofrece botones clicables de desambiguación
        (dir_plan / "Planificacion_Proyecto.pdf").write_bytes(b"%PDF-1.4")
        r2 = router_jeff.resolver_consulta("cual es la planificacion del curso?", "TEST101")
        self.assertIsNotNone(r2)
        self.assertEqual(r2["tipo"], "planificacion_desambiguacion")
        self.assertEqual(len(r2.get("sugerencias") or []), 2)

        # Al elegir una opción específica (ej. clic en botón), devuelve el enlace exacto
        r3 = router_jeff.resolver_consulta("Ver Planificacion Proyecto", "TEST101")
        self.assertIsNotNone(r3)
        self.assertEqual(r3["tipo"], "planificacion_doc")
        self.assertIn("Planificacion_Proyecto.pdf", r3["respuesta"])

        # Consulta puntual sobre experiencia 3 pasa al canal RAG informativo (retorna None en Jeff)
        r4 = router_jeff.resolver_consulta("que se ve en la experiencia 3?", "TEST101")
        self.assertIsNone(r4)

    def test_guard_anti_secuestro_keyword_generica_en_ejercicio_tecnico(self):
        router_jeff.agregar_faq_jeff(
            codigo_ramo="TEST101",
            respuesta="Una red es un conjunto de dispositivos conectados.",
            palabras_clave=["red", "redes", "que es una red"],
            categoria="Consultas Resueltas",
            pregunta="¿Qué es una red?",
        )

        # Ejercicio técnico de subnetting que menciona "red" NO debe ser secuestrado por Jeff
        r_ej = router_jeff.resolver_consulta(
            "si tengo quiero una red 10 host, que mascara deberia usar",
            "TEST101",
        )
        self.assertIsNone(r_ej)

        # Pregunta directa por frase exacta SÍ debe responder desde Jeff
        r_def = router_jeff.resolver_consulta("que es una red?", "TEST101")
        self.assertIsNotNone(r_def)
        self.assertEqual(r_def["canal"], "JEFF_ADMIN")


def main() -> None:
    for mensaje, ramo in CASOS:
        resultado = router_jeff.resolver_consulta(mensaje, ramo)
        canal = resultado["canal"] if resultado else "TUTOR_SOCRATICO (deriva a RAG)"
        print(f"\n> {mensaje}  [{ramo}]")
        print(f"  canal: {canal}")
        if resultado:
            print(f"  topico: {resultado['topico']}")
            print(f"  respuesta: {resultado['respuesta']}")
        else:
            print(json.dumps(resultado, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
