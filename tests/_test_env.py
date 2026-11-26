"""Utilidades comunes para ejecutar las pruebas aisladas fuera de backend/."""

import sys
from pathlib import Path
from typing import List
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"


def asegurar_backend_en_path() -> None:
    """Agrega backend/ al sys.path cuando las pruebas corren desde la raíz."""
    backend_str = str(BACKEND_DIR)
    if BACKEND_DIR.exists() and backend_str not in sys.path:
        sys.path.insert(0, backend_str)


def parches_aislamiento_datos(
    data_dir: Path,
    analytics_dir: Path,
    *,
    backend_app=None,
    router_jeff=None,
    consultas_store=None,
    rag_engine=None,
    analytics_store=None,
) -> List:
    """Construye patchers para redirigir todas las escrituras a directorios temporales."""
    patchers: List = []
    if backend_app is not None:
        patchers.append(patch.object(backend_app, "BASE_DATA_DIR", data_dir))
    if router_jeff is not None:
        patchers.append(patch.object(router_jeff, "DATA_DIR", data_dir))
    if consultas_store is not None:
        patchers.append(patch.object(consultas_store, "DATA_DIR", data_dir))
    if rag_engine is not None:
        patchers.append(patch.object(rag_engine, "DATA_DIR", data_dir))
        patchers.append(patch.object(rag_engine, "_clientes", {}))
    if analytics_store is not None:
        patchers.append(patch.object(analytics_store, "ANALYTICS_DIR", analytics_dir))
    return patchers
