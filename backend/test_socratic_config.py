"""Pruebas unitarias para configuración socrática por ramo y payload de Qwen3 en Ollama."""

import asyncio
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


class _FakeStreamResponse:
    def __init__(self, lines):
        self.status_code = 200
        self._lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _FakeAsyncClient:
    captured_payload = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def stream(self, method, url, json=None):
        _FakeAsyncClient.captured_payload = json
        return _FakeStreamResponse(
            [
                '{"message": {"content": "Pista socrática"}, "done": false}',
                '{"message": {"content": ""}, "done": true}',
            ]
        )


class TestQwenYConfigSocratica(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name)
        ramo_dir = self.data_dir / "MAT999"
        ramo_dir.mkdir(parents=True, exist_ok=True)
        with open(ramo_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "codigo": "MAT999",
                    "nombre": "Matemática de Prueba",
                    "reglas_socraticas": "Regla base inicial.",
                    "config_socratica": {
                        "estilo": "equilibrado",
                        "extension": "media",
                    },
                    "faqs_jeff": [],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        self.patchers = [
            patch.object(backend_app, "BASE_DATA_DIR", self.data_dir),
            patch.object(backend_app.router_jeff, "DATA_DIR", self.data_dir),
        ]
        for p in self.patchers:
            p.start()
        self.client = TestClient(backend_app.app)

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        self.tmpdir.cleanup()

    def test_eventos_ollama_envia_think_false_y_modelo_configurado(self):
        _FakeAsyncClient.captured_payload = None

        async def _recoger():
            eventos = []
            async for ev in backend_app._eventos_ollama("Sistema", "¿Qué es Fourier?"):
                eventos.append(ev)
            return eventos

        with (
            patch.object(backend_app, "OLLAMA_LLM_MODEL", "qwen3:8b"),
            patch.object(backend_app, "OLLAMA_THINK", False),
            patch.object(backend_app.httpx, "AsyncClient", _FakeAsyncClient),
        ):
            eventos = asyncio.run(_recoger())

        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["contenido"], "Pista socrática")
        self.assertIsNotNone(_FakeAsyncClient.captured_payload)
        self.assertEqual(_FakeAsyncClient.captured_payload["model"], "qwen3:8b")
        self.assertIs(_FakeAsyncClient.captured_payload["think"], False)

    def test_construir_system_prompt_incluye_estilo_extension_y_reglas(self):
        datos = {
            "nombre": "Matemática de Prueba",
            "reglas_socraticas": "No resuelvas integrales triples.",
            "config_socratica": {"estilo": "estricto", "extension": "corta"},
        }
        prompt = backend_app._construir_system_prompt(datos, "MAT999", "Apunte 1", modo="conceptual")
        self.assertIn("ESTILO DEL DOCENTE (ESTRICTO)", prompt)
        self.assertIn("EXTENSIÓN DE RESPUESTA (CORTA)", prompt)
        self.assertIn("No resuelvas integrales triples.", prompt)

    def test_get_y_put_config_socratica_persiste_y_valida(self):
        resp_get = self.client.get("/api/ramos/MAT999/config_socratica")
        self.assertEqual(resp_get.status_code, 200)
        self.assertEqual(resp_get.json()["estilo"], "equilibrado")
        self.assertEqual(resp_get.json()["extension"], "media")

        resp_put = self.client.put(
            "/api/ramos/MAT999/config_socratica",
            json={
                "reglas_socraticas": "Usa solo analogías geométricas.",
                "estilo": "paso_a_paso",
                "extension": "corta",
            },
        )
        self.assertEqual(resp_put.status_code, 200)
        self.assertEqual(resp_put.json()["estilo"], "paso_a_paso")
        self.assertEqual(resp_put.json()["extension"], "corta")

        # Verifica persistencia en config.json sin borrar otros campos
        with open(self.data_dir / "MAT999" / "config.json", "r", encoding="utf-8") as f:
            guardado = json.load(f)
        self.assertEqual(guardado["nombre"], "Matemática de Prueba")
        self.assertEqual(guardado["reglas_socraticas"], "Usa solo analogías geométricas.")
        self.assertEqual(guardado["config_socratica"]["estilo"], "paso_a_paso")
        self.assertEqual(guardado["config_socratica"]["extension"], "corta")

        # Valores inválidos son rechazados con 422
        resp_invalido = self.client.put(
            "/api/ramos/MAT999/config_socratica",
            json={
                "reglas_socraticas": "X",
                "estilo": "modo_inexistente",
                "extension": "gigante",
            },
        )
        self.assertEqual(resp_invalido.status_code, 422)

    def test_chat_mantiene_hilo_con_ventana_deslizante(self):
        _FakeAsyncClient.captured_payload = None

        historial = [
            {"rol": "user", "contenido": f"msg {i}"} if i % 2 == 0 else {"rol": "assistant", "contenido": f"resp {i}"}
            for i in range(8)
        ]
        # El último turno del usuario menciona VLAN
        historial[-2] = {"rol": "user", "contenido": "Qué es una VLAN?"}
        historial[-1] = {"rol": "assistant", "contenido": "Es una red lógica. ¿Qué ventajas ofrece?"}

        fragmentos_mock = [{"texto": "Las VLAN separan dominios de broadcast.", "archivo": "Clase5.pdf", "pagina": 3, "score": 0.72}]

        with (
            patch.object(backend_app.rag_engine, "buscar_fragmentos_relevantes", return_value=fragmentos_mock) as mock_rag,
            patch.object(backend_app.rag_engine, "formatear_contexto", return_value="Las VLAN separan dominios de broadcast."),
            patch.object(backend_app, "_obtener_temario", return_value=["VLAN", "STP"]),
            patch.object(backend_app.httpx, "AsyncClient", _FakeAsyncClient),
        ):
            resp = self.client.post(
                "/api/chat",
                json={
                    "codigo_ramo": "MAT999",
                    "mensaje": "Que ventajas ofrece?",
                    "historial": historial,
                },
            )

        self.assertEqual(resp.status_code, 200)
        # RAG recibió consulta combinada con el turno anterior ("Qué es una VLAN? Que ventajas ofrece?")
        consulta_rag = mock_rag.call_args[0][0]
        self.assertIn("VLAN", consulta_rag)
        self.assertIn("Que ventajas ofrece?", consulta_rag)

        # Ollama recibió system + máx 6 mensajes de historial + mensaje actual = 8 mensajes
        mensajes_enviados = _FakeAsyncClient.captured_payload["messages"]
        self.assertEqual(len(mensajes_enviados), 8)
        self.assertEqual(mensajes_enviados[0]["role"], "system")
        self.assertEqual(mensajes_enviados[-2]["content"], "Es una red lógica. ¿Qué ventajas ofrece?")
        self.assertEqual(mensajes_enviados[-1]["content"], "Que ventajas ofrece?")

        # Tercer turno de seguimiento ("Como se aplica?") debe anclarse a "Qué es una VLAN?"
        historial_3 = historial + [
            {"rol": "user", "contenido": "Que ventajas ofrece?"},
            {"rol": "assistant", "contenido": "Segmentación y reducción de broadcast."},
        ]
        with (
            patch.object(backend_app.rag_engine, "buscar_fragmentos_relevantes", return_value=fragmentos_mock) as mock_rag_3,
            patch.object(backend_app.rag_engine, "formatear_contexto", return_value="Las VLAN separan dominios de broadcast."),
            patch.object(backend_app, "_obtener_temario", return_value=["VLAN", "STP"]),
            patch.object(backend_app.httpx, "AsyncClient", _FakeAsyncClient),
        ):
            resp_3 = self.client.post(
                "/api/chat",
                json={
                    "codigo_ramo": "MAT999",
                    "mensaje": "Como se aplica?",
                    "historial": historial_3,
                },
            )
        self.assertEqual(resp_3.status_code, 200)
        self.assertIn("VLAN", mock_rag_3.call_args[0][0])
        self.assertIn("Como se aplica?", mock_rag_3.call_args[0][0])

    def test_pregunta_admin_no_se_pega_a_tema_previo_y_cae_en_fallback_docente(self):
        historial = [
            {"rol": "user", "contenido": "Que es una ip?"},
            {"rol": "assistant", "contenido": "Es un identificador de red."},
        ]
        llamado_ollama = False

        async def _ollama_prohibido(*args, **kwargs):
            nonlocal llamado_ollama
            llamado_ollama = True
            yield {"tipo": "token", "contenido": "no deberia"}

        with (
            patch.object(backend_app.rag_engine, "buscar_fragmentos_relevantes", return_value=[]),
            patch.object(backend_app, "_obtener_temario", return_value=["IP", "VLAN"]),
            patch.object(backend_app, "_eventos_ollama", side_effect=_ollama_prohibido),
        ):
            resp = self.client.post(
                "/api/chat",
                json={
                    "codigo_ramo": "MAT999",
                    "mensaje": "Para la presentacion 1 cuanto diapositivas debe llevar?",
                    "historial": historial,
                },
            )

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(llamado_ollama, "No debe llamar a Ollama en pregunta admin desconocida")
        eventos = [
            json.loads(b[len("data: "):])
            for b in resp.text.split("\n\n")
            if b.strip().startswith("data: ")
        ]
        self.assertEqual(eventos[-1]["canal"], "FALLBACK_DOCENTE")
        self.assertTrue(eventos[-1]["puede_escalar"])

    def test_si_qwen_responde_fuera_de_foco_habilita_escalamiento(self):
        async def _ollama_fuera_de_foco(*args, **kwargs):
            yield {"tipo": "token", "contenido": "Fuera de foco. "}
            yield {"tipo": "token", "contenido": "La consulta no está relacionada con el temario."}

        fragmentos_mock = [{"texto": "Apunte IP", "archivo": "Clase6.pdf", "pagina": 1, "score": 0.7}]

        with (
            patch.object(backend_app.rag_engine, "buscar_fragmentos_relevantes", return_value=fragmentos_mock),
            patch.object(backend_app.rag_engine, "formatear_contexto", return_value="Apunte IP"),
            patch.object(backend_app, "_obtener_temario", return_value=["IP", "VLAN"]),
            patch.object(backend_app, "_eventos_ollama", side_effect=_ollama_fuera_de_foco),
        ):
            resp = self.client.post(
                "/api/chat",
                json={
                    "codigo_ramo": "MAT999",
                    "mensaje": "Pregunta ambigua sobre IP",
                },
            )

        self.assertEqual(resp.status_code, 200)
        eventos = [
            json.loads(b[len("data: "):])
            for b in resp.text.split("\n\n")
            if b.strip().startswith("data: ")
        ]
        self.assertEqual(eventos[-1]["tipo"], "fin")
        self.assertEqual(eventos[-1]["canal"], "FALLBACK_DOCENTE")
        self.assertTrue(eventos[-1]["puede_escalar"])
        self.assertEqual(eventos[-1]["motivo"], "fuera_de_foco")


if __name__ == "__main__":
    unittest.main()
