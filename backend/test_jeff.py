"""Pruebas unitarias y rápida del enrutador Jeff. No necesita Ollama ni Docker."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
