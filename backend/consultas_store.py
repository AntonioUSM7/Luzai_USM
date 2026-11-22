"""Persistencia thread-safe de consultas escaladas al profesor por ramo."""

import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import router_jeff

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "ramos"

_STORE_LOCK = threading.Lock()
ESTADOS_VALIDOS = {"pendiente", "resuelta", "descartada"}


def _ruta_consultas(codigo_ramo: str) -> Path:
    return DATA_DIR / codigo_ramo.upper() / "consultas_profesor.json"


def _leer_lista(ruta: Path) -> List[Dict[str, Any]]:
    if not ruta.exists():
        return []
    with open(ruta, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)
    return datos if isinstance(datos, list) else []


def _escribir_lista(ruta: Path, consultas: List[Dict[str, Any]]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta_tmp = ruta.with_suffix(".json.tmp")
    with open(ruta_tmp, "w", encoding="utf-8") as archivo:
        json.dump(consultas, archivo, ensure_ascii=False, indent=2)
    os.replace(ruta_tmp, ruta)


def listar_consultas(
    codigo_ramo: str, estado: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Devuelve las consultas registradas para un ramo (más recientes primero)."""
    ruta = _ruta_consultas(codigo_ramo)
    with _STORE_LOCK:
        consultas = _leer_lista(ruta)
    if estado:
        consultas = [c for c in consultas if c.get("estado") == estado]
    return list(reversed(consultas))


def crear_consulta(
    codigo_ramo: str,
    pregunta: str,
    motivo: str = "sin_respaldo_rag",
) -> Dict[str, Any]:
    """Registra una consulta escalada por el alumno en estado pendiente."""
    codigo = codigo_ramo.upper()
    ruta_config = DATA_DIR / codigo / "config.json"
    if not ruta_config.exists():
        raise FileNotFoundError(f"Ramo {codigo} no encontrado")

    pregunta_limpia = (pregunta or "").strip()
    if not pregunta_limpia:
        raise ValueError("La pregunta no puede estar vacía")

    registro = {
        "id": f"cons_{uuid.uuid4().hex[:10]}",
        "codigo_ramo": codigo,
        "pregunta": pregunta_limpia,
        "motivo": (motivo or "sin_respaldo_rag").strip(),
        "estado": "pendiente",
        "fecha_creacion": datetime.now().isoformat(timespec="seconds"),
        "fecha_respuesta": None,
        "respuesta_profesor": None,
        "guardada_en_jeff": False,
        "faq_jeff_id": None,
        "palabras_clave_sugeridas": router_jeff.sugerir_palabras_clave(pregunta_limpia),
    }

    ruta = _ruta_consultas(codigo)
    with _STORE_LOCK:
        consultas = _leer_lista(ruta)
        consultas.append(registro)
        _escribir_lista(ruta, consultas)

    return registro


def responder_consulta(
    codigo_ramo: str,
    consulta_id: str,
    estado: str = "resuelta",
    respuesta_profesor: Optional[str] = None,
    guardar_en_jeff: bool = False,
    categoria: str = "Consultas Resueltas",
    palabras_clave: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Actualiza una consulta pendiente (resuelta o descartada) y opcionalmente
    persiste la respuesta como nueva FAQ de Jeff en config.json.
    """
    if estado not in ("resuelta", "descartada"):
        raise ValueError("El estado debe ser 'resuelta' o 'descartada'")

    codigo = codigo_ramo.upper()
    ruta = _ruta_consultas(codigo)
    faq_creada: Optional[Dict[str, Any]] = None

    with _STORE_LOCK:
        consultas = _leer_lista(ruta)
        objetivo = next((c for c in consultas if c.get("id") == consulta_id), None)
        if objetivo is None:
            raise KeyError(f"Consulta '{consulta_id}' no encontrada en {codigo}")

        respuesta_limpia = (respuesta_profesor or "").strip() or None
        if estado == "resuelta" and guardar_en_jeff:
            if not respuesta_limpia:
                raise ValueError("Para guardar en Jeff debes escribir una respuesta")
            claves = palabras_clave or objetivo.get("palabras_clave_sugeridas") or []
            faq_creada = router_jeff.agregar_faq_jeff(
                codigo_ramo=codigo,
                respuesta=respuesta_limpia,
                palabras_clave=claves,
                categoria=categoria,
                pregunta=objetivo.get("pregunta"),
            )
            objetivo["guardada_en_jeff"] = True
            objetivo["faq_jeff_id"] = faq_creada["id"]

        objetivo["estado"] = estado
        objetivo["respuesta_profesor"] = respuesta_limpia
        objetivo["fecha_respuesta"] = datetime.now().isoformat(timespec="seconds")
        _escribir_lista(ruta, consultas)

    return {"consulta": objetivo, "faq_creada": faq_creada}
