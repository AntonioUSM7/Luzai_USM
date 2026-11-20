import json
import logging
import os
import re
import threading
import unicodedata
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "ramos"

logger = logging.getLogger(__name__)
_CONFIG_LOCK = threading.Lock()

_STOPWORDS_ES = {
    "algo", "algun", "alguna", "algunas", "alguno", "algunos", "aqui", "como",
    "cual", "cuales", "cuando", "donde", "desde", "ellas", "ellos", "entre",
    "esas", "esos", "esta", "estan", "estas", "este", "esto", "estos", "hace",
    "hacia", "hasta", "para", "pero", "porque", "puede", "pueden", "puedo",
    "queria", "quien", "quienes", "quisiera", "saber", "sobre", "tambien",
    "tengo", "tiene", "tienen", "todo", "todos", "unas", "unos", "usar",
}


def normalizar(texto: str) -> str:
    """Pasa a minúsculas, quita tildes y colapsa espacios para comparar keywords."""
    if not texto:
        return ""
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return " ".join(sin_tildes.lower().split())


def cargar_config(codigo_ramo: str) -> Optional[Dict[str, Any]]:
    ruta = DATA_DIR / codigo_ramo.upper() / "config.json"
    if not ruta.exists():
        return None
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("No se pudo leer %s: %s", ruta, exc)
        return None


def _coincide(keyword_normalizada: str, mensaje_normalizado: str) -> bool:
    if not keyword_normalizada:
        return False
    if " " in keyword_normalizada:
        return keyword_normalizada in mensaje_normalizado
    patron = rf"(?<!\w){re.escape(keyword_normalizada)}\w*(?!\w)"
    return re.search(patron, mensaje_normalizado) is not None


def _puntuar(palabras_clave: List[str], mensaje_normalizado: str) -> Tuple[int, List[str]]:
    coincidencias = []
    for palabra in palabras_clave or []:
        clave = normalizar(str(palabra))
        if len(clave) < 3:
            continue
        if _coincide(clave, mensaje_normalizado):
            coincidencias.append(clave)

    puntaje = sum(len(clave) for clave in coincidencias)
    return puntaje, coincidencias


def _formatear_tarea(tarea: Dict[str, Any], codigo_ramo: str) -> str:
    if tarea.get("respuesta"):
        return tarea["respuesta"]

    lineas = [
        f"📌 [Jeff - Info Administrativa {codigo_ramo}]: {tarea.get('titulo', 'Tarea')}"
    ]
    if tarea.get("fecha_limite"):
        lineas.append(f"• Fecha límite: {tarea['fecha_limite']}")
    if tarea.get("formato_entrega"):
        lineas.append(f"• Formato de entrega: {tarea['formato_entrega']}")
    if tarea.get("plataforma"):
        lineas.append(f"• Plataforma: {tarea['plataforma']}")
    return "\n".join(lineas)


def _mejor_coincidencia(
    entradas: List[Dict[str, Any]],
    mensaje_normalizado: str,
) -> Optional[Tuple[Dict[str, Any], int, List[str]]]:
    mejor: Optional[Tuple[Dict[str, Any], int, List[str]]] = None
    for entrada in entradas or []:
        puntaje, coincidencias = _puntuar(entrada.get("palabras_clave", []), mensaje_normalizado)
        if puntaje == 0:
            continue
        if mejor is None or puntaje > mejor[1]:
            mejor = (entrada, puntaje, coincidencias)
    return mejor


def resolver_consulta(mensaje: str, codigo_ramo: str) -> Optional[Dict[str, Any]]:
    """
    Intenta resolver una consulta administrativa sin usar GPU.
    Devuelve un dict con la respuesta si hay coincidencia, o None si es pedagógica.
    """
    config = cargar_config(codigo_ramo)
    if not config:
        return None

    mensaje_normalizado = normalizar(mensaje)
    codigo = codigo_ramo.upper()

    tarea = _mejor_coincidencia(config.get("tareas", []), mensaje_normalizado)
    if tarea:
        entrada, puntaje, coincidencias = tarea
        return {
            "canal": "JEFF_ADMIN",
            "tipo": "tarea",
            "topico": entrada.get("id", "tarea"),
            "categoria": "Tareas y Entregas",
            "respuesta": _formatear_tarea(entrada, codigo),
            "coincidencias": coincidencias,
            "puntaje": puntaje,
        }

    faq = _mejor_coincidencia(config.get("faqs_jeff", []), mensaje_normalizado)
    if faq:
        entrada, puntaje, coincidencias = faq
        return {
            "canal": "JEFF_ADMIN",
            "tipo": "faq",
            "topico": entrada.get("id", "faq"),
            "categoria": entrada.get("categoria", "Administrativa"),
            "respuesta": entrada.get("respuesta", ""),
            "coincidencias": coincidencias,
            "puntaje": puntaje,
        }

    return None


def sugerir_palabras_clave(pregunta: str, max_palabras: int = 6) -> List[str]:
    """Extrae palabras clave candidatas desde una pregunta para pre-llenar una FAQ de Jeff."""
    texto = normalizar(pregunta)
    tokens = re.findall(r"[a-z0-9]{4,}", texto)
    sugeridas: List[str] = []
    vistas = set()
    for token in tokens:
        if token in _STOPWORDS_ES or token in vistas:
            continue
        vistas.add(token)
        sugeridas.append(token)
        if len(sugeridas) >= max_palabras:
            break
    return sugeridas


def agregar_faq_jeff(
    codigo_ramo: str,
    respuesta: str,
    palabras_clave: List[str],
    categoria: str = "Consultas Resueltas",
    faq_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Agrega una nueva entrada en faqs_jeff dentro de config.json de forma thread-safe y atómica.
    """
    codigo = codigo_ramo.upper()
    ruta = DATA_DIR / codigo / "config.json"
    claves_limpias: List[str] = []
    vistas = set()
    for palabra in palabras_clave or []:
        clave = normalizar(str(palabra))
        if len(clave) < 3 or clave in vistas:
            continue
        vistas.add(clave)
        claves_limpias.append(clave)

    if not claves_limpias:
        raise ValueError("Se requiere al menos una palabra clave de 3 o más caracteres")

    respuesta_limpia = (respuesta or "").strip()
    if not respuesta_limpia:
        raise ValueError("La respuesta de la FAQ no puede estar vacía")

    if not respuesta_limpia.startswith("📌"):
        respuesta_limpia = f"📌 [Jeff - Respuesta Docente {codigo}]: {respuesta_limpia}"

    nueva_faq = {
        "id": faq_id or f"docente_{uuid.uuid4().hex[:8]}",
        "categoria": (categoria or "Consultas Resueltas").strip() or "Consultas Resueltas",
        "palabras_clave": claves_limpias,
        "respuesta": respuesta_limpia,
    }

    with _CONFIG_LOCK:
        if not ruta.exists():
            raise FileNotFoundError(f"No existe config.json para el ramo {codigo}")
        with open(ruta, "r", encoding="utf-8") as archivo:
            config = json.load(archivo)

        faqs = config.setdefault("faqs_jeff", [])
        if not isinstance(faqs, list):
            faqs = []
            config["faqs_jeff"] = faqs
        faqs.append(nueva_faq)

        ruta_tmp = ruta.with_suffix(".json.tmp")
        with open(ruta_tmp, "w", encoding="utf-8") as archivo:
            json.dump(config, archivo, ensure_ascii=False, indent=2)
        os.replace(ruta_tmp, ruta)

    return nueva_faq
