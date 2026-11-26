"""Pruebas de subida múltiple de archivos al repositorio docente."""

import sys
import tempfile
import types
import unittest
from io import BytesIO
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
    _stub.buscar_fragmentos_planificacion = lambda *a, **kw: []
    _stub.formatear_contexto = lambda fragmentos: ""
    _stub.estado_ramo = lambda codigo: {"total_chunks": 0, "archivos": []}
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

import app as backend_app


class TestSubidaMultiplesArchivos(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name) / "ramos"
        self.analytics_dir = Path(self.tmpdir.name) / "analytics"
        ramo_dir = self.data_dir / "TESTUP"
        ramo_dir.mkdir(parents=True, exist_ok=True)
        with open(ramo_dir / "config.json", "w", encoding="utf-8") as archivo:
            archivo.write('{"codigo": "TESTUP", "nombre": "Ramo de prueba"}')

        self.patchers = parches_aislamiento_datos(
            self.data_dir,
            self.analytics_dir,
            backend_app=backend_app,
            router_jeff=backend_app.router_jeff,
            consultas_store=backend_app.consultas_store,
            rag_engine=backend_app.rag_engine,
            analytics_store=backend_app.analytics_store,
        )
        for parche in self.patchers:
            parche.start()
        self.client = TestClient(backend_app.app)

    def tearDown(self):
        for parche in self.patchers:
            parche.stop()
        self.tmpdir.cleanup()

    def test_sube_varios_archivos_a_la_carpeta_seleccionada(self):
        with patch.object(backend_app.rag_engine, "indexar_documento") as indexar:
            respuesta = self.client.post(
                "/api/ramos/TESTUP/archivos",
                data={"carpeta": "Clases/Lab 1"},
                files=[
                    ("archivos", ("Apunte uno.pdf", BytesIO(b"uno"), "application/pdf")),
                    ("archivos", ("Guia dos.txt", BytesIO(b"dos"), "text/plain")),
                    ("archivos", ("Formulario tres.docx", BytesIO(b"tres"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
                ],
            )

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos["total"], 3)
        self.assertEqual(len(datos["archivos"]), 3)
        self.assertEqual(
            [item["nombre"] for item in datos["archivos"]],
            ["Apunte_uno.pdf", "Guia_dos.txt", "Formulario_tres.docx"],
        )
        self.assertTrue(
            all(item["carpeta"] == "Clases/Lab 1" for item in datos["archivos"])
        )
        self.assertEqual(indexar.call_count, 3)

        destino = self.data_dir / "TESTUP" / "documentos" / "Clases" / "Lab 1"
        self.assertEqual(len(list(destino.iterdir())), 3)
        self.assertEqual(
            (destino / "Apunte_uno.pdf").read_bytes(), b"uno"
        )

    def test_renombra_nombres_duplicados_del_mismo_lote(self):
        with patch.object(backend_app.rag_engine, "indexar_documento"):
            respuesta = self.client.post(
                "/api/ramos/TESTUP/archivos",
                data={"carpeta": "Guias"},
                files=[
                    ("archivos", ("Apunte.pdf", BytesIO(b"primero"), "application/pdf")),
                    ("archivos", ("Apunte.pdf", BytesIO(b"segundo"), "application/pdf")),
                ],
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            [item["nombre"] for item in respuesta.json()["archivos"]],
            ["Apunte.pdf", "Apunte_2.pdf"],
        )

    def test_mantiene_compatibilidad_con_campo_archivo_individual(self):
        with patch.object(backend_app.rag_engine, "indexar_documento"):
            respuesta = self.client.post(
                "/api/ramos/TESTUP/archivos",
                data={"carpeta": "Clases"},
                files=[("archivo", ("Unico.pdf", BytesIO(b"unico"), "application/pdf"))],
            )

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos["total"], 1)
        self.assertEqual(datos["archivo"]["nombre"], "Unico.pdf")
        self.assertEqual(datos["archivos"][0]["nombre"], "Unico.pdf")

    def test_rechaza_peticion_sin_archivos(self):
        respuesta = self.client.post(
            "/api/ramos/TESTUP/archivos",
            data={"carpeta": "Clases"},
        )
        self.assertEqual(respuesta.status_code, 400)


if __name__ == "__main__":
    unittest.main()
