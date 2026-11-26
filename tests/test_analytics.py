"""Pruebas de analítica anónima: sanitización, agrupación de dudas e integración API."""

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
    _stub.EXTENSIONES_INDEXABLES = {".pdf", ".docx", ".txt", ".md"}
    _stub.buscar_fragmentos_relevantes = lambda *a, **kw: []
    _stub.buscar_fragmentos_planificacion = lambda *a, **kw: []
    _stub.formatear_contexto = lambda fragmentos: ""
    _stub.reindexar_ramo = lambda codigo: {"status": "ok"}
    _stub.indexar_documento = lambda *a, **kw: {"status": "ok"}
    _stub.indexar_faq_jeff = lambda *a, **kw: {"status": "ok"}
    _stub.indexar_tarea_jeff = lambda *a, **kw: {"status": "ok"}
    _stub.eliminar_documento_vectorial = lambda *a, **kw: None
    _stub.eliminar_carpeta_vectorial = lambda *a, **kw: None
    _stub.eliminar_faq_vectorial = lambda *a, **kw: None
    _stub.eliminar_tarea_vectorial = lambda *a, **kw: None
    _stub.esta_indexado = lambda *a, **kw: False
    sys.modules["rag_engine"] = _stub

from fastapi.testclient import TestClient

import analytics_store
import app as backend_app


class TestAnaliticaAnonima(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.analytics_dir = Path(self.tmpdir.name) / "analytics"
        self.ramos_dir = Path(self.tmpdir.name) / "ramos"
        (self.ramos_dir / "TEL20425").mkdir(parents=True, exist_ok=True)
        with open(self.ramos_dir / "TEL20425" / "config.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "codigo": "TEL20425",
                    "nombre": "Laboratorio de Redes",
                    "reglas_socraticas": "Guía con preguntas.",
                    "faqs_jeff": [
                        {
                            "id": "tel_entrega",
                            "categoria": "Fechas y Entregas",
                            "pregunta": "¿Cuándo se entrega el informe del laboratorio 1?",
                            "palabras_clave": ["informe", "entrega"],
                            "respuesta": "[Jeff]: Viernes 23:59 hrs.",
                        }
                    ],
                    "tareas": [],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        self.patchers = [
            patch.object(analytics_store, "ANALYTICS_DIR", self.analytics_dir),
            patch.object(analytics_store, "RAMOS_DIR", self.ramos_dir),
        ]
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        self.tmpdir.cleanup()

    def test_sanitiza_datos_personales_telefonos_y_urls(self):
        texto = (
            "Mi correo es alumno@usm.cl, RUT 12 345 678-9, fono +56 9 8765 4321, "
            "IP 192.168.1.20, IPv6 2001:db8:85a3::8a2e y revisa "
            "https://ejemplo.cl/privado sobre la tarea"
        )
        limpio = analytics_store.anonimizar_pregunta(texto)
        self.assertNotIn("alumno@usm.cl", limpio)
        self.assertNotIn("12.345.678-9", limpio)
        self.assertNotIn("12 345 678-9", limpio)
        self.assertNotIn("8765", limpio)
        self.assertNotIn("192.168.1.20", limpio)
        self.assertNotIn("2001:db8", limpio)
        self.assertNotIn("https://ejemplo.cl", limpio)
        self.assertIn("tarea", limpio)

    def test_agrupa_preguntas_equivalentes_y_topicos_jeff(self):
        # Variantes equivalentes de una misma duda conceptual en el tutor
        for variante in (
            "¿Qué es una VLAN?",
            "que es vlan",
            "explicame para que sirve una vlan",
        ):
            analytics_store.registrar_evento(
                "TEL20425",
                variante,
                canal="TUTOR_SOCRATICO",
                modo="conceptual",
                con_contexto=True,
                duracion_ms=900,
            )

        # Variantes multi-palabra sobre máscara de subred
        analytics_store.registrar_evento(
            "TEL20425",
            "¿Cómo se calcula la máscara de subred?",
            canal="TUTOR_SOCRATICO",
            modo="procedimental",
            duracion_ms=1100,
        )
        analytics_store.registrar_evento(
            "TEL20425",
            "calcular mascara subred",
            canal="TUTOR_SOCRATICO",
            modo="procedimental",
            duracion_ms=1300,
        )

        # Dos consultas administrativas distintas que activan el mismo tópico de Jeff
        analytics_store.registrar_evento(
            "TEL20425",
            "¿Cuándo se entrega el informe?",
            canal="JEFF_ADMIN",
            modo="administrativo",
            topico="tel_entrega",
            categoria="Fechas y Entregas",
            duracion_ms=40,
        )
        analytics_store.registrar_evento(
            "TEL20425",
            "plazo del informe laboratorio",
            canal="JEFF_ADMIN",
            modo="administrativo",
            topico="tel_entrega",
            categoria="Fechas y Entregas",
            duracion_ms=50,
        )

        resumen = analytics_store.resumen("TEL20425", dias=30)
        self.assertEqual(resumen["total_eventos"], 7)
        top_vlan = next(d for d in resumen["top_dudas"] if "vlan" in d["texto"].lower())
        self.assertEqual(top_vlan["total"], 3)
        self.assertEqual(top_vlan["variantes"], 3)

        top_subred = next(d for d in resumen["top_dudas"] if "subred" in d["texto"].lower())
        self.assertEqual(top_subred["total"], 2)

        top_jeff = next(d for d in resumen["top_dudas"] if d.get("topico") == "tel_entrega")
        self.assertEqual(top_jeff["total"], 2)
        self.assertEqual(
            top_jeff["etiqueta"], "¿Cuándo se entrega el informe del laboratorio 1?"
        )

        # Filtro por canal específico
        resumen_jeff = analytics_store.resumen("TEL20425", dias=30, canal="JEFF_ADMIN", limite=1)
        self.assertEqual(len(resumen_jeff["top_dudas"]), 1)
        self.assertEqual(resumen_jeff["top_dudas"][0]["canal"], "JEFF_ADMIN")
        self.assertEqual(resumen_jeff["total_eventos"], 2)
        totales_jeff = {item["canal"]: item["total"] for item in resumen_jeff["por_canal"]}
        self.assertEqual(totales_jeff["JEFF_ADMIN"], 2)
        self.assertEqual(totales_jeff["TUTOR_SOCRATICO"], 0)

    def test_evento_vacio_no_se_registra(self):
        evento = analytics_store.registrar_evento(
            "TEL20425", "   ", canal="TUTOR_SOCRATICO"
        )
        self.assertEqual(evento, {})
        self.assertFalse((self.analytics_dir / "TEL20425_log.jsonl").exists())

    def test_resumen_sin_datos(self):
        resumen = analytics_store.resumen("MAT024", dias=30)
        self.assertEqual(resumen["total_eventos"], 0)
        self.assertEqual(resumen["top_dudas"], [])
        self.assertEqual(resumen["por_motivo_fallback"], [])
        self.assertEqual(resumen["latencia_promedio_ms"], 0)


class TestIntegracionChatAnalitica(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name) / "ramos"
        self.analytics_dir = Path(self.tmpdir.name) / "analytics"
        ramo_dir = self.data_dir / "TESTANA"
        ramo_dir.mkdir(parents=True, exist_ok=True)
        with open(ramo_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "codigo": "TESTANA",
                    "nombre": "Curso Analitica",
                    "reglas_socraticas": "Guía con preguntas.",
                    "config_fallback": {
                        "habilitado": True,
                        "permitir_escalar_profesor": True,
                        "mensaje_sin_respaldo": "Sin respaldo.",
                        "mensaje_fuera_de_foco": "Fuera de foco.",
                    },
                    "faqs_jeff": [
                        {
                            "id": "faq_horario",
                            "categoria": "Horarios",
                            "pregunta": "¿Cuál es el horario de clases?",
                            "palabras_clave": ["horario"],
                            "respuesta": "[Jeff]: Martes 10:00.",
                        }
                    ],
                    "tareas": [],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        self.patchers = parches_aislamiento_datos(
            self.data_dir,
            self.analytics_dir,
            backend_app=backend_app,
            router_jeff=backend_app.router_jeff,
            consultas_store=backend_app.consultas_store,
            rag_engine=backend_app.rag_engine,
            analytics_store=backend_app.analytics_store,
        ) + [patch.object(analytics_store, "RAMOS_DIR", self.data_dir)]
        for p in self.patchers:
            p.start()
        self.client = TestClient(backend_app.app)

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        self.tmpdir.cleanup()

    def test_chat_registra_tres_canales_y_endpoint_resumen(self):
        ruta_analytics_real = Path(__file__).resolve().parents[1] / "backend" / "data" / "analytics"
        antes_real = (
            {ruta.name for ruta in ruta_analytics_real.glob("*")}
            if ruta_analytics_real.exists()
            else set()
        )

        # 1. JEFF_ADMIN (con identificadores que deben sanitizarse)
        r_jeff = self.client.post(
            "/api/chat",
            json={
                "codigo_ramo": "TESTANA",
                "mensaje": "¿Cuál es el horario? alumno@usm.cl RUT 12.345.678-9",
            },
        )
        self.assertEqual(r_jeff.status_code, 200)

        # 2. FALLBACK_DOCENTE
        with patch.object(
            backend_app.rag_engine, "buscar_fragmentos_relevantes", return_value=[]
        ):
            r_fb = self.client.post(
                "/api/chat",
                json={"codigo_ramo": "TESTANA", "mensaje": "Receta de pan amasado"},
            )
        self.assertEqual(r_fb.status_code, 200)

        # 3. TUTOR_SOCRATICO (dos variantes equivalentes)
        async def _fake_ollama(*args, **kwargs):
            yield {"tipo": "token", "contenido": "¿Qué entiendes por VLAN?"}

        frags = [{"texto": "Una VLAN segmenta redes.", "archivo": "Clase.pdf", "pagina": 1, "score": 0.85}]
        for pregunta in ("¿Qué es una VLAN?", "para que sirve una vlan"):
            with (
                patch.object(
                    backend_app.rag_engine, "buscar_fragmentos_relevantes", return_value=frags
                ),
                patch.object(
                    backend_app.rag_engine, "formatear_contexto", return_value="Una VLAN segmenta redes."
                ),
                patch.object(backend_app, "_obtener_temario", return_value=["VLAN"]),
                patch.object(backend_app, "_eventos_ollama", side_effect=_fake_ollama),
            ):
                r_tut = self.client.post(
                    "/api/chat",
                    json={"codigo_ramo": "TESTANA", "mensaje": pregunta},
                )
            self.assertEqual(r_tut.status_code, 200)

        resp_resumen = self.client.get("/api/ramos/TESTANA/analytics/resumen?dias=30")
        self.assertEqual(resp_resumen.status_code, 200)
        data = resp_resumen.json()
        self.assertEqual(data["total_eventos"], 4)
        por_canal = {c["canal"]: c["total"] for c in data["por_canal"]}
        self.assertEqual(por_canal["JEFF_ADMIN"], 1)
        self.assertEqual(por_canal["FALLBACK_DOCENTE"], 1)
        self.assertEqual(por_canal["TUTOR_SOCRATICO"], 2)
        self.assertEqual(data["top_dudas"][0]["total"], 2)
        self.assertIn("vlan", data["top_dudas"][0]["texto"].lower())

        ruta_eventos = self.analytics_dir / "TESTANA_log.jsonl"
        with open(ruta_eventos, "r", encoding="utf-8") as archivo:
            eventos = [json.loads(linea) for linea in archivo if linea.strip()]
        self.assertEqual(len(eventos), 4)
        for evento in eventos:
            pregunta = evento["pregunta_anonimizada"]
            self.assertNotIn("alumno@usm.cl", pregunta)
            self.assertNotIn("12.345.678-9", pregunta)

        despues_real = (
            {ruta.name for ruta in ruta_analytics_real.glob("*")}
            if ruta_analytics_real.exists()
            else set()
        )
        self.assertEqual(despues_real, antes_real)

        # Validaciones de parámetros
        self.assertEqual(
            self.client.get("/api/ramos/TESTANA/analytics/resumen?dias=0").status_code, 400
        )
        self.assertEqual(
            self.client.get("/api/ramos/TESTANA/analytics/resumen?canal=OTRO").status_code, 400
        )
        self.assertEqual(
            self.client.get("/api/ramos/NOEXISTE/analytics/resumen").status_code, 404
        )

        # Eliminación selectiva de preguntas poco frecuentes vía API
        dudas = data["top_dudas"]
        ids_poco_frecuentes = [d["id"] for d in dudas if d["total"] == 1]
        self.assertEqual(len(ids_poco_frecuentes), 2)

        resp_del = self.client.post(
            "/api/ramos/TESTANA/analytics/eliminar-dudas",
            json={"ids": ids_poco_frecuentes, "dias": 30},
        )
        self.assertEqual(resp_del.status_code, 200)
        del_data = resp_del.json()
        self.assertEqual(del_data["status"], "ok")
        self.assertEqual(del_data["eliminados"], 2)
        self.assertEqual(del_data["grupos_eliminados"], 2)

        resp_resumen_post = self.client.get("/api/ramos/TESTANA/analytics/resumen?dias=30")
        self.assertEqual(resp_resumen_post.status_code, 200)
        data_post = resp_resumen_post.json()
        self.assertEqual(data_post["total_eventos"], 2)
        self.assertEqual(len(data_post["top_dudas"]), 1)
        self.assertIn("vlan", data_post["top_dudas"][0]["texto"].lower())

        # Validaciones de endpoint de eliminación
        self.assertEqual(
            self.client.post(
                "/api/ramos/TESTANA/analytics/eliminar-dudas",
                json={"ids": [], "dias": 30},
            ).status_code,
            422,
        )
        self.assertEqual(
            self.client.post(
                "/api/ramos/NOEXISTE/analytics/eliminar-dudas",
                json={"ids": ["abc"], "dias": 30},
            ).status_code,
            404,
        )


if __name__ == "__main__":
    unittest.main()
