"""Pruebas unitarias e integración para el fallback estricto (FALLBACK_DOCENTE) y buzón docente."""

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from _test_env import asegurar_backend_en_path, parches_aislamiento_datos

asegurar_backend_en_path()

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
        self.tmpdir = tempfile.TemporaryDirectory()
        self.analytics_dir = Path(self.tmpdir.name) / "analytics"
        self.patchers = [
            patch.object(backend_app.analytics_store, "ANALYTICS_DIR", self.analytics_dir),
        ]
        for p in self.patchers:
            p.start()
        self.client = TestClient(backend_app.app)

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        self.tmpdir.cleanup()

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

        self.analytics_dir = Path(self.tmpdir.name) / "analytics"
        self.patchers = parches_aislamiento_datos(
            self.data_dir,
            self.analytics_dir,
            backend_app=backend_app,
            router_jeff=backend_app.router_jeff,
            consultas_store=backend_app.consultas_store,
            rag_engine=backend_app.rag_engine,
            analytics_store=backend_app.analytics_store,
        )
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
        self.assertEqual(data_resp["faq_creada"]["pregunta"], pregunta)

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

    def test_crud_api_faqs_jeff_y_flujo_dual_chat(self):
        # 1. Listar inicial
        resp_list = self.client.get("/api/ramos/TEST101/faqs_jeff")
        self.assertEqual(resp_list.status_code, 200)
        self.assertEqual(resp_list.json()["total"], 1)

        # 2. Crear FAQ con fallo tolerado en RAG
        with patch.object(
            backend_app.rag_engine,
            "indexar_faq_jeff",
            side_effect=RuntimeError("Ollama offline"),
        ):
            resp_create = self.client.post(
                "/api/ramos/TEST101/faqs_jeff",
                json={
                    "pregunta": "¿Cuándo vence el informe de laboratorio?",
                    "respuesta": "El informe de laboratorio vence el viernes 23:59 en AULA.",
                    "palabras_clave": ["informe laboratorio"],
                    "categoria": "Fechas y Entregas",
                },
            )
        self.assertEqual(resp_create.status_code, 200)
        data_create = resp_create.json()
        self.assertFalse(data_create["rag_sincronizado"])
        faq_id = data_create["faq"]["id"]
        self.assertEqual(
            data_create["faq"]["pregunta"], "¿Cuándo vence el informe de laboratorio?"
        )

        # 3. Editar FAQ con RAG disponible
        with patch.object(
            backend_app.rag_engine,
            "indexar_faq_jeff",
            return_value={"status": "ok", "faq_id": faq_id, "chunks_indexados": 1},
        ) as mock_indexar:
            resp_update = self.client.put(
                f"/api/ramos/TEST101/faqs_jeff/{faq_id}",
                json={
                    "pregunta": "¿Cuál es el plazo del informe de laboratorio?",
                    "respuesta": "El plazo actualizado es el lunes 18:00 en AULA.",
                    "palabras_clave": ["informe laboratorio"],
                    "categoria": "Fechas y Entregas",
                },
            )
        self.assertEqual(resp_update.status_code, 200)
        self.assertTrue(resp_update.json()["rag_sincronizado"])
        mock_indexar.assert_called_once()

        # Editar inexistente -> 404
        resp_404 = self.client.put(
            "/api/ramos/TEST101/faqs_jeff/inexistente",
            json={"respuesta": "x", "palabras_clave": ["clave"]},
        )
        self.assertEqual(resp_404.status_code, 404)

        # 4a. Flujo /api/chat nivel 1: keyword exacta -> Jeff ($0 GPU)
        resp_jeff = self.client.post(
            "/api/chat",
            json={
                "codigo_ramo": "TEST101",
                "mensaje": "¿Fecha del informe laboratorio?",
            },
        )
        self.assertEqual(resp_jeff.status_code, 200)
        eventos_jeff = _parsear_sse(resp_jeff.text)
        self.assertEqual(eventos_jeff[-1]["canal"], "JEFF_ADMIN")

        # 4b. Flujo /api/chat nivel 2: parafraseo sin keyword -> RAG devuelve FAQ -> Tutor Socrático
        prompts_capturados = []

        async def _fake_ollama(system_prompt, mensaje, historial):
            prompts_capturados.append(system_prompt)
            yield {"tipo": "token", "contenido": "Según el docente, el plazo es el lunes 18:00."}

        fragmento_faq = [
            {
                "texto": "Pregunta: ¿Cuál es el plazo del informe de laboratorio?\nRespuesta oficial: El plazo actualizado es el lunes 18:00 en AULA.",
                "archivo": "Preguntas Guardadas (Jeff)",
                "carpeta": "faqs_jeff",
                "pagina": None,
                "distancia": 0.1,
                "score": 0.9,
            }
        ]
        with (
            patch.object(
                backend_app.rag_engine,
                "buscar_fragmentos_relevantes",
                return_value=fragmento_faq,
            ),
            patch.object(backend_app, "_eventos_ollama", side_effect=_fake_ollama),
        ):
            resp_tutor = self.client.post(
                "/api/chat",
                json={
                    "codigo_ramo": "TEST101",
                    "mensaje": "¿Hasta qué día tengo para subir mi reporte práctico?",
                },
            )
        self.assertEqual(resp_tutor.status_code, 200)
        eventos_tutor = _parsear_sse(resp_tutor.text)
        self.assertEqual(eventos_tutor[-1]["canal"], "TUTOR_SOCRATICO")
        self.assertEqual(len(prompts_capturados), 1)
        self.assertIn("Preguntas Guardadas (Jeff)", prompts_capturados[0])
        self.assertIn("lunes 18:00", prompts_capturados[0])

        # 5. Eliminar FAQ y verificar 404 al reintentar
        with patch.object(
            backend_app.rag_engine, "eliminar_faq_vectorial", return_value=None
        ) as mock_del:
            resp_del = self.client.delete(f"/api/ramos/TEST101/faqs_jeff/{faq_id}")
        self.assertEqual(resp_del.status_code, 200)
        self.assertTrue(resp_del.json()["rag_sincronizado"])
        mock_del.assert_called_once_with("TEST101", faq_id)

        resp_del_404 = self.client.delete(f"/api/ramos/TEST101/faqs_jeff/{faq_id}")
        self.assertEqual(resp_del_404.status_code, 404)

    def test_crud_api_tareas_carpeta_planificacion_y_config_fallback(self):
        # 1. Carpeta Planificacion incluida por defecto
        resp_carpetas = self.client.get("/api/ramos/TEST101/carpetas")
        self.assertEqual(resp_carpetas.status_code, 200)
        self.assertIn("Planificacion", resp_carpetas.json()["carpetas"])

        # 2. CRUD HTTP de tareas con sincronización RAG
        with patch.object(
            backend_app.rag_engine,
            "indexar_tarea_jeff",
            return_value={"status": "ok", "chunks_indexados": 1},
        ) as mock_idx_tarea:
            resp_create = self.client.post(
                "/api/ramos/TEST101/tareas",
                json={
                    "titulo": "Tarea 1: Redes",
                    "fecha_limite": "Viernes 23:59",
                    "formato_entrega": "PDF",
                    "plataforma": "AULA",
                    "palabras_clave": ["tarea 1", "entrega tarea 1"],
                },
            )
        self.assertEqual(resp_create.status_code, 200)
        self.assertTrue(resp_create.json()["rag_sincronizado"])
        tarea_id = resp_create.json()["tarea"]["id"]
        mock_idx_tarea.assert_called_once()

        resp_list = self.client.get("/api/ramos/TEST101/tareas")
        self.assertEqual(resp_list.status_code, 200)
        self.assertEqual(resp_list.json()["total"], 1)

        with patch.object(
            backend_app.rag_engine,
            "indexar_tarea_jeff",
            return_value={"status": "ok", "chunks_indexados": 1},
        ):
            resp_put = self.client.put(
                f"/api/ramos/TEST101/tareas/{tarea_id}",
                json={
                    "titulo": "Tarea 1: Redes actualizada",
                    "fecha_limite": "Lunes 18:00",
                    "palabras_clave": ["tarea 1"],
                },
            )
        self.assertEqual(resp_put.status_code, 200)
        self.assertEqual(resp_put.json()["tarea"]["fecha_limite"], "Lunes 18:00")
        self.assertEqual(resp_put.json()["tarea"]["plataforma"], "AULA")
        self.assertEqual(resp_put.json()["tarea"]["formato_entrega"], "PDF")

        with patch.object(
            backend_app.rag_engine, "eliminar_tarea_vectorial", return_value=None
        ) as mock_del_tarea:
            resp_del = self.client.delete(f"/api/ramos/TEST101/tareas/{tarea_id}")
        self.assertEqual(resp_del.status_code, 200)
        self.assertTrue(resp_del.json()["rag_sincronizado"])
        mock_del_tarea.assert_called_once_with("TEST101", tarea_id)

        # 3. GET y PUT config_fallback + efecto en chat FALLBACK_DOCENTE
        resp_cfg_get = self.client.get("/api/ramos/TEST101/config_fallback")
        self.assertEqual(resp_cfg_get.status_code, 200)
        self.assertTrue(resp_cfg_get.json()["habilitado"])

        resp_cfg_put = self.client.put(
            "/api/ramos/TEST101/config_fallback",
            json={
                "habilitado": True,
                "permitir_escalar_profesor": False,
                "mensaje_sin_respaldo": "Mensaje personalizado sin respaldo.",
                "mensaje_fuera_de_foco": "Mensaje personalizado fuera de foco.",
                "canal_alternativo": "Foro AULA",
            },
        )
        self.assertEqual(resp_cfg_put.status_code, 200)
        self.assertFalse(resp_cfg_put.json()["permitir_escalar_profesor"])

        resp_cfg_parcial = self.client.put(
            "/api/ramos/TEST101/config_fallback",
            json={"canal_alternativo": "Foro AULA actualizado"},
        )
        self.assertEqual(resp_cfg_parcial.status_code, 200)
        cfg_parcial = resp_cfg_parcial.json()
        self.assertFalse(cfg_parcial["permitir_escalar_profesor"])
        self.assertEqual(cfg_parcial["mensaje_sin_respaldo"], "Mensaje personalizado sin respaldo.")
        self.assertEqual(cfg_parcial["canal_alternativo"], "Foro AULA actualizado")

        with patch.object(
            backend_app.rag_engine, "buscar_fragmentos_relevantes", return_value=[]
        ):
            resp_chat = self.client.post(
                "/api/chat",
                json={"codigo_ramo": "TEST101", "mensaje": "Receta de cazuela"},
            )
        eventos = _parsear_sse(resp_chat.text)
        self.assertEqual(eventos[-1]["canal"], "FALLBACK_DOCENTE")
        self.assertFalse(eventos[-1]["puede_escalar"])
        texto_total = "".join(e.get("contenido", "") for e in eventos if e.get("tipo") == "token")
        self.assertIn("Mensaje personalizado fuera de foco.", texto_total)
        self.assertIn("Foro AULA actualizado", texto_total)


if __name__ == "__main__":
    unittest.main()
