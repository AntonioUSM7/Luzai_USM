"""Pruebas unitarias e integración para el fallback estricto (FALLBACK_DOCENTE) y buzón docente."""

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import rag_engine  # noqa: F401
except ModuleNotFoundError:
    _stub = types.ModuleType("rag_engine")
    _stub.buscar_fragmentos_relevantes = lambda *a, **kw: []
    _stub.formatear_contexto = lambda fragmentos: ""
    _stub.estado_ramo = lambda codigo: {"total_chunks": 0, "archivos": []}
    _stub.reindexar_ramo = lambda codigo: {"status": "ok"}
    _stub.indexar_documento = lambda *a, **kw: {"status": "ok"}
    _stub.eliminar_documento_vectorial = lambda *a, **kw: None
    _stub.eliminar_carpeta_vectorial = lambda *a, **kw: None
    sys.modules["rag_engine"] = _stub

from fastapi.testclient import TestClient

import app as backend_app


def _parsear_sse(texto: str):
    eventos = []
    for bloque in texto.split("\n\n"):
        bloque = bloque.strip()
        if bloque.startswith("data: "):
            eventos.append(json.loads(bloque[len("data: "):]))
    return eventos


class TestFallbackEstricto(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(backend_app.app)

    def test_fuera_de_foco_emite_fallback_docente_sin_llamar_ollama(self):
        llamado_ollama = False

        async def _ollama_prohibido(*args, **kwargs):
            nonlocal llamado_ollama
            llamado_ollama = True
            yield {"tipo": "token", "contenido": "no deberia ejecutarse"}

        with (
            patch.object(backend_app.rag_engine, "buscar_fragmentos_relevantes", return_value=[]),
            patch.object(backend_app, "_eventos_ollama", side_effect=_ollama_prohibido),
        ):
            resp = self.client.post(
                "/api/chat",
                json={
                    "codigo_ramo": "MAT024",
                    "mensaje": "¿Cuál es la receta para hacer empanadas de pino?",
                },
            )

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(llamado_ollama, "No debe invocarse a Ollama en fallback estricto")
        eventos = _parsear_sse(resp.text)
        self.assertGreaterEqual(len(eventos), 2)
        self.assertEqual(eventos[0]["canal"], "FALLBACK_DOCENTE")
        self.assertTrue(eventos[0]["puede_escalar"])
        self.assertEqual(eventos[0]["motivo"], "fuera_de_foco")
        self.assertEqual(eventos[-1]["tipo"], "fin")
        self.assertEqual(eventos[-1]["canal"], "FALLBACK_DOCENTE")
        self.assertTrue(eventos[-1]["puede_escalar"])

    def test_sin_respaldo_rag_emite_fallback_docente_sin_llamar_ollama(self):
        llamado_ollama = False

        async def _ollama_prohibido(*args, **kwargs):
            nonlocal llamado_ollama
            llamado_ollama = True
            yield {"tipo": "token", "contenido": "no deberia ejecutarse"}

        with (
            patch.object(backend_app.rag_engine, "buscar_fragmentos_relevantes", return_value=[]),
            patch.object(backend_app.router_modo, "menciona_tema_del_ramo", return_value=True),
            patch.object(backend_app, "_eventos_ollama", side_effect=_ollama_prohibido),
        ):
            resp = self.client.post(
                "/api/chat",
                json={
                    "codigo_ramo": "MAT024",
                    "mensaje": "¿Esta materia se relaciona con el efecto túnel cuántico?",
                },
            )

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(llamado_ollama, "No debe invocarse a Ollama cuando no hay contexto RAG")
        eventos = _parsear_sse(resp.text)
        self.assertEqual(eventos[0]["canal"], "FALLBACK_DOCENTE")
        self.assertTrue(eventos[0]["puede_escalar"])
        self.assertEqual(eventos[0]["motivo"], "sin_respaldo_rag")
        self.assertEqual(eventos[-1]["canal"], "FALLBACK_DOCENTE")


class TestBuzonDocenteYConversionJeff(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name)
        ramo_dir = self.data_dir / "TEST101"
        ramo_dir.mkdir(parents=True, exist_ok=True)
        self.config_inicial = {
            "codigo": "TEST101",
            "nombre": "Curso de Prueba",
            "reglas_socraticas": "Guía con preguntas.",
            "config_fallback": {
                "habilitado": True,
                "permitir_escalar_profesor": True,
                "mensaje_sin_respaldo": "Sin respaldo en TEST101.",
                "mensaje_fuera_de_foco": "Fuera de foco en TEST101.",
            },
            "faqs_jeff": [
                {
                    "id": "faq_base",
                    "categoria": "General",
                    "palabras_clave": ["horario"],
                    "respuesta": "📌 [Jeff]: Lunes 10:00.",
                }
            ],
        }
        with open(ramo_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(self.config_inicial, f, ensure_ascii=False, indent=2)

        self.patchers = [
            patch.object(backend_app, "BASE_DATA_DIR", self.data_dir),
            patch.object(backend_app.router_jeff, "DATA_DIR", self.data_dir),
            patch.object(backend_app.consultas_store, "DATA_DIR", self.data_dir),
        ]
        for p in self.patchers:
            p.start()
        self.client = TestClient(backend_app.app)

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        self.tmpdir.cleanup()

    def test_ciclo_completo_escalamiento_a_faq_jeff(self):
        pregunta = "¿Esta materia se relaciona con el efecto túnel cuántico en física?"

        # 1. Crear consulta confirmada por el alumno
        resp_crear = self.client.post(
            "/api/ramos/TEST101/consultas",
            json={"pregunta": pregunta, "motivo": "sin_respaldo_rag"},
        )
        self.assertEqual(resp_crear.status_code, 200)
        consulta = resp_crear.json()["consulta"]
        self.assertEqual(consulta["estado"], "pendiente")
        self.assertIn("tunel", consulta["palabras_clave_sugeridas"])

        # 2. Listar en vista docente
        resp_listar = self.client.get("/api/ramos/TEST101/consultas")
        self.assertEqual(resp_listar.status_code, 200)
        self.assertEqual(resp_listar.json()["total"], 1)

        # 3. Profesor responde y guarda en faqs_jeff
        resp_responder = self.client.post(
            f"/api/ramos/TEST101/consultas/{consulta['id']}/responder",
            json={
                "estado": "resuelta",
                "respuesta_profesor": "Sí, la ecuación de Schrödinger usa la misma EDP estacionaria que vemos en la Unidad 2.",
                "guardar_en_jeff": True,
                "categoria": "Conexiones Interdisciplinarias",
                "palabras_clave": ["efecto tunel", "cuantico", "schrodinger"],
            },
        )
        self.assertEqual(resp_responder.status_code, 200)
        data_resp = resp_responder.json()
        self.assertEqual(data_resp["consulta"]["estado"], "resuelta")
        self.assertTrue(data_resp["consulta"]["guardada_en_jeff"])
        self.assertIsNotNone(data_resp["faq_creada"])

        # 4. Verificar que config.json conserva metadatos previos + nueva FAQ
        with open(self.data_dir / "TEST101" / "config.json", "r", encoding="utf-8") as f:
            cfg_actual = json.load(f)
        self.assertEqual(cfg_actual["nombre"], "Curso de Prueba")
        self.assertEqual(len(cfg_actual["faqs_jeff"]), 2)

        # 5. Siguiente alumno hace la misma duda -> Jeff responde directo ($0 GPU)
        match_jeff = backend_app.router_jeff.resolver_consulta(pregunta, "TEST101")
        self.assertIsNotNone(match_jeff)
        self.assertEqual(match_jeff["canal"], "JEFF_ADMIN")
        self.assertIn("Schrödinger", match_jeff["respuesta"])

        # Y por /api/chat sale por JEFF_ADMIN sin tocar Ollama
        resp_chat = self.client.post(
            "/api/chat",
            json={"codigo_ramo": "TEST101", "mensaje": pregunta},
        )
        eventos = _parsear_sse(resp_chat.text)
        self.assertEqual(eventos[-1]["canal"], "JEFF_ADMIN")

    def test_descartar_consulta_no_modifica_faqs_jeff(self):
        resp_crear = self.client.post(
            "/api/ramos/TEST101/consultas",
            json={"pregunta": "hola prueba random", "motivo": "fuera_de_foco"},
        )
        consulta_id = resp_crear.json()["consulta"]["id"]

        resp_desc = self.client.post(
            f"/api/ramos/TEST101/consultas/{consulta_id}/responder",
            json={"estado": "descartada", "guardar_en_jeff": False},
        )
        self.assertEqual(resp_desc.status_code, 200)
        self.assertEqual(resp_desc.json()["consulta"]["estado"], "descartada")
        self.assertFalse(resp_desc.json()["consulta"]["guardada_en_jeff"])

        with open(self.data_dir / "TEST101" / "config.json", "r", encoding="utf-8") as f:
            cfg_actual = json.load(f)
        self.assertEqual(len(cfg_actual["faqs_jeff"]), 1)


if __name__ == "__main__":
    unittest.main()
