import json
import logging
import os
import re
import threading
import unicodedata
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

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


_KEYWORDS_ADMIN_SEGURAS = {
    "sala", "ubicacion", "edificio", "horario", "certamen", "prueba", "evaluacion",
    "entrega", "plazo", "informe", "rubrica", "bibliografia", "libro", "texto",
    "ayudantia", "ayudante", "profesor", "correo", "recuperativa", "examen",
    "nota", "notas", "ponderacion", "asistencia", "wireshark", "gns3", "packet tracer",
}

_PATRON_EJERCICIO_TECNICO = re.compile(
    r"\b(hosts?|mascara|subred(?:es)?|subnet\w*|calcula\w*|configura\w*|resuelv\w*|resolver|"
    r"comando(?:s)?|implementa\w*|integral\w*|derivada\w*|matriz|matrices|"
    r"deberia\s+usar|como\s+se\s+(?:calcula|configura|hace|implementa))\b|"
    r"\b\d+\s*(?:hosts?|bits?|subredes?|ips?|usuarios?)\b|"
    r"\b\d{1,3}(?:\.\d{1,3}){3}\b"
)


def _coincide(keyword_normalizada: str, mensaje_normalizado: str) -> bool:
    if not keyword_normalizada:
        return False
    if " " in keyword_normalizada:
        patron = rf"(?<!\w){re.escape(keyword_normalizada)}(?!\w)"
        return re.search(patron, mensaje_normalizado) is not None
    if len(keyword_normalizada) <= 4:
        patron = rf"(?<!\w){re.escape(keyword_normalizada)}(?:e?s)?(?!\w)"
        return re.search(patron, mensaje_normalizado) is not None
    patron = rf"(?<!\w){re.escape(keyword_normalizada)}\w*(?!\w)"
    return re.search(patron, mensaje_normalizado) is not None


def _puntuar(palabras_clave: List[str], mensaje_normalizado: str) -> Tuple[int, List[str]]:
    coincidencias: List[str] = []
    tiene_frase = False

    for palabra in palabras_clave or []:
        clave = normalizar(str(palabra))
        if len(clave) < 3:
            continue
        if _coincide(clave, mensaje_normalizado):
            coincidencias.append(clave)
            if " " in clave:
                tiene_frase = True

    if not coincidencias:
        return 0, []

    # Guard anti-secuestro: si no coincidió ninguna frase completa, evitar que una
    # palabra genérica aislada (ej. "red" en un ejercicio de subnetting) intercepte el chat.
    if not tiene_frase:
        raices = {c[:4] for c in coincidencias}
        es_admin_segura = any(c in _KEYWORDS_ADMIN_SEGURAS for c in coincidencias)
        if len(raices) == 1 and not es_admin_segura:
            if _PATRON_EJERCICIO_TECNICO.search(mensaje_normalizado):
                return 0, []
            palabras_utiles = [
                t for t in re.findall(r"[a-z0-9]{3,}", mensaje_normalizado)
                if t not in _STOPWORDS_ES
            ]
            max_len_kw = max(len(c) for c in coincidencias)
            if max_len_kw <= 4 and len(palabras_utiles) >= 4:
                return 0, []

    puntaje = sum(len(clave) * (2 if " " in clave else 1) for clave in coincidencias)
    return puntaje, coincidencias


def _formatear_tarea(tarea: Dict[str, Any], codigo_ramo: str) -> str:
    if tarea.get("respuesta"):
        return tarea["respuesta"]

    lineas = [
        f"[Jeff - Info Administrativa {codigo_ramo}]: {tarea.get('titulo', 'Tarea')}"
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


def _etiqueta_documento_planificacion(ruta_en_plan: Path) -> str:
    """Genera una etiqueta legible a partir de la subcarpeta y/o nombre del archivo."""
    partes_dir = list(ruta_en_plan.parent.parts)
    stem_limpio = re.sub(r"[_-]+", " ", ruta_en_plan.stem).strip()
    if partes_dir:
        sub = " / ".join(re.sub(r"[_-]+", " ", p).strip() for p in partes_dir)
        if stem_limpio.lower() in ("planificacion", "cronograma", "calendario", sub.lower()):
            return f"Planificación de {sub}"
        return f"{sub} ({stem_limpio})"
    return stem_limpio or ruta_en_plan.name


def listar_documentos_planificacion(codigo_ramo: str) -> List[Dict[str, str]]:
    """Lista todos los documentos disponibles dentro de documentos/Planificacion/ (y subcarpetas)."""
    codigo = codigo_ramo.upper()
    dir_documentos = DATA_DIR / codigo / "documentos"
    dir_plan = dir_documentos / "Planificacion"
    if not dir_plan.exists() or not dir_plan.is_dir():
        return []

    docs: List[Dict[str, str]] = []
    for item in sorted(dir_plan.rglob("*")):
        if not item.is_file() or item.name.startswith("."):
            continue
        rel_en_plan = item.relative_to(dir_plan)
        if any(p.startswith(".") for p in rel_en_plan.parts):
            continue
        ruta_relativa = item.relative_to(dir_documentos).as_posix()
        docs.append({
            "nombre": item.name,
            "ruta_relativa": ruta_relativa,
            "carpeta": item.parent.relative_to(dir_documentos).as_posix(),
            "etiqueta": _etiqueta_documento_planificacion(rel_en_plan),
            "url": f"/api/ramos/{codigo}/documentos/{quote(ruta_relativa, safe='/')}",
        })
    return docs


_PATRON_PREGUNTA_ESPECIFICA_PLAN = re.compile(
    r"\b(experiencia|exp|laboratorio|lab|clase|sesion|semana)\s*0*\d+\b|"
    r"\b(ot\s*\d+|pres(?:entacion)?\s*\d+|certamen|fiestas\s+patrias|vacaciones|notas\s+finales)\b|"
    r"\b(que\s+se\s+ve\s+en|que\s+entra\s+en|que\s+toca\s+en|cuando\s+es|que\s+fecha\s+es|que\s+pasa\s+en)\b"
)

_PATRON_CONSULTA_PLANIFICACION_GENERAL = re.compile(
    r"\b(planificacion|planificaciones|cronograma|calendario|programa\s+del\s+curso|fechas\s+del\s+curso)\b"
)


def _resolver_planificacion_documentos(
    mensaje_normalizado: str,
    codigo: str,
) -> Optional[Dict[str, Any]]:
    docs = listar_documentos_planificacion(codigo)
    if not docs:
        return None

    # Si pregunta algo puntual de contenido/fecha (ej. "que se ve en la experiencia 3?"),
    # dejar que pase al canal RAG informativo (que responderá y adjuntará el link al PDF).
    if _PATRON_PREGUNTA_ESPECIFICA_PLAN.search(mensaje_normalizado):
        return None

    # Verificar si coincide directamente con alguna etiqueta/archivo de planificación
    # (ej. al hacer clic en un botón de desambiguación o pedir "planificacion del proyecto").
    tokens_msg = {
        t
        for t in re.findall(r"[a-z0-9]{3,}", mensaje_normalizado)
        if t not in _STOPWORDS_ES and t not in ("planificacion", "planificaciones", "ver", "curso", "del", "las", "los")
    }

    coincidencias_doc: List[Tuple[int, Dict[str, str]]] = []
    for doc in docs:
        etiqueta_norm = normalizar(doc["etiqueta"])
        if etiqueta_norm and etiqueta_norm in mensaje_normalizado:
            coincidencias_doc.append((100, doc))
            continue
        bolsa_doc = normalizar(f"{doc['etiqueta']} {doc['nombre']}")
        tokens_doc = {
            t
            for t in re.findall(r"[a-z0-9]{3,}", bolsa_doc)
            if t not in _STOPWORDS_ES and t not in ("planificacion", "pdf", "docx", "txt")
        }
        comunes = tokens_msg.intersection(tokens_doc)
        if comunes:
            coincidencias_doc.append((sum(len(t) for t in comunes), doc))

    es_consulta_general = bool(_PATRON_CONSULTA_PLANIFICACION_GENERAL.search(mensaje_normalizado))

    if not es_consulta_general and not coincidencias_doc:
        return None

    # Caso 1: Solo hay 1 documento de planificación -> entregar enlace directo
    if len(docs) == 1:
        doc = docs[0]
        return {
            "canal": "JEFF_ADMIN",
            "tipo": "planificacion_doc",
            "topico": "planificacion_documento",
            "categoria": "Planificación del Curso",
            "respuesta": (
                f"[Jeff - Planificación {codigo}]: Puedes revisar la planificación oficial "
                f"en el siguiente documento:\n\n"
                f"- [{doc['etiqueta']} ({doc['nombre']})]({doc['url']})"
            ),
            "coincidencias": ["planificacion"],
            "puntaje": 100,
        }

    # Caso 2: Hay múltiples documentos y el alumno indicó uno específico
    if coincidencias_doc:
        coincidencias_doc.sort(key=lambda x: x[0], reverse=True)
        mejor_score = coincidencias_doc[0][0]
        ganadores = [d for s, d in coincidencias_doc if s == mejor_score]
        if len(ganadores) == 1:
            doc = ganadores[0]
            return {
                "canal": "JEFF_ADMIN",
                "tipo": "planificacion_doc",
                "topico": "planificacion_documento",
                "categoria": "Planificación del Curso",
                "respuesta": (
                    f"[Jeff - Planificación {codigo}]: Aquí tienes el documento correspondiente:\n\n"
                    f"- [{doc['etiqueta']} ({doc['nombre']})]({doc['url']})"
                ),
                "coincidencias": [doc["etiqueta"]],
                "puntaje": 100,
            }

    # Caso 3: Hay múltiples documentos y la consulta es general -> desambiguación con botones clicables
    opciones = [f"Ver {d['etiqueta']}" for d in docs]
    return {
        "canal": "JEFF_ADMIN",
        "tipo": "planificacion_desambiguacion",
        "topico": "planificacion_opciones",
        "categoria": "Planificación del Curso",
        "respuesta": (
            f"[Jeff - Planificación {codigo}]: Hay más de un documento de planificación "
            "disponible para este curso. ¿Cuál necesitas revisar?"
        ),
        "sugerencias": opciones,
        "coincidencias": ["planificacion"],
        "puntaje": 100,
    }


def resolver_consulta(
    mensaje: str,
    codigo_ramo: str,
    historial: Optional[List[Dict[str, str]]] = None,
) -> Optional[Dict[str, Any]]:
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

    plan_doc = _resolver_planificacion_documentos(mensaje_normalizado, codigo)
    if plan_doc:
        return plan_doc

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


def _limpiar_palabras_clave(
    palabras_clave: Optional[List[str]],
    pregunta: Optional[str] = None,
) -> List[str]:
    claves_limpias: List[str] = []
    vistas = set()
    for palabra in palabras_clave or []:
        clave = normalizar(str(palabra))
        if len(clave) < 3 or clave in vistas:
            continue
        vistas.add(clave)
        claves_limpias.append(clave)

    if not claves_limpias and pregunta:
        for palabra in sugerir_palabras_clave(pregunta):
            clave = normalizar(str(palabra))
            if len(clave) < 3 or clave in vistas:
                continue
            vistas.add(clave)
            claves_limpias.append(clave)

    if not claves_limpias:
        raise ValueError("Se requiere al menos una palabra clave de 3 o más caracteres")

    return claves_limpias


def _formatear_respuesta_docente(respuesta: str, codigo: str) -> str:
    respuesta_limpia = (respuesta or "").strip()
    if respuesta_limpia.startswith("📌"):
        respuesta_limpia = respuesta_limpia.lstrip("📌").strip()
    if not respuesta_limpia:
        raise ValueError("La respuesta de la FAQ no puede estar vacía")
    if not respuesta_limpia.startswith("[Jeff"):
        respuesta_limpia = f"[Jeff - Respuesta Docente {codigo}]: {respuesta_limpia}"
    return respuesta_limpia


def _guardar_config_atomico(ruta: Path, config: Dict[str, Any]) -> None:
    ruta_tmp = ruta.with_suffix(".json.tmp")
    with open(ruta_tmp, "w", encoding="utf-8") as archivo:
        json.dump(config, archivo, ensure_ascii=False, indent=2)
    os.replace(ruta_tmp, ruta)


def listar_faqs_jeff(codigo_ramo: str) -> List[Dict[str, Any]]:
    """Lista las FAQs guardadas de Jeff para un ramo."""
    codigo = codigo_ramo.upper()
    ruta = DATA_DIR / codigo / "config.json"
    with _CONFIG_LOCK:
        if not ruta.exists():
            raise FileNotFoundError(f"No existe config.json para el ramo {codigo}")
        with open(ruta, "r", encoding="utf-8") as archivo:
            config = json.load(archivo)
    faqs = config.get("faqs_jeff", [])
    return list(faqs) if isinstance(faqs, list) else []


def agregar_faq_jeff(
    codigo_ramo: str,
    respuesta: str,
    palabras_clave: Optional[List[str]] = None,
    categoria: str = "Consultas Resueltas",
    faq_id: Optional[str] = None,
    pregunta: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Agrega una nueva entrada en faqs_jeff dentro de config.json de forma thread-safe y atómica.
    """
    codigo = codigo_ramo.upper()
    ruta = DATA_DIR / codigo / "config.json"
    pregunta_limpia = (pregunta or "").strip()
    claves_limpias = _limpiar_palabras_clave(palabras_clave, pregunta=pregunta_limpia)
    respuesta_limpia = _formatear_respuesta_docente(respuesta, codigo)

    nueva_faq: Dict[str, Any] = {
        "id": faq_id or f"docente_{uuid.uuid4().hex[:8]}",
        "categoria": (categoria or "Consultas Resueltas").strip() or "Consultas Resueltas",
        "palabras_clave": claves_limpias,
        "respuesta": respuesta_limpia,
    }
    if pregunta_limpia:
        nueva_faq["pregunta"] = pregunta_limpia

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
        _guardar_config_atomico(ruta, config)

    return nueva_faq


def actualizar_faq_jeff(
    codigo_ramo: str,
    faq_id: str,
    respuesta: str,
    palabras_clave: Optional[List[str]] = None,
    categoria: str = "Consultas Resueltas",
    pregunta: Optional[str] = None,
) -> Dict[str, Any]:
    """Actualiza una entrada existente en faqs_jeff dentro de config.json de forma atómica."""
    codigo = codigo_ramo.upper()
    ruta = DATA_DIR / codigo / "config.json"
    pregunta_limpia = (pregunta or "").strip()
    claves_limpias = _limpiar_palabras_clave(palabras_clave, pregunta=pregunta_limpia)
    respuesta_limpia = _formatear_respuesta_docente(respuesta, codigo)
    categoria_limpia = (categoria or "Consultas Resueltas").strip() or "Consultas Resueltas"

    with _CONFIG_LOCK:
        if not ruta.exists():
            raise FileNotFoundError(f"No existe config.json para el ramo {codigo}")
        with open(ruta, "r", encoding="utf-8") as archivo:
            config = json.load(archivo)

        faqs = config.get("faqs_jeff", [])
        if not isinstance(faqs, list):
            faqs = []

        objetivo = next((f for f in faqs if f.get("id") == faq_id), None)
        if objetivo is None:
            raise KeyError(f"FAQ '{faq_id}' no encontrada en {codigo}")

        objetivo["categoria"] = categoria_limpia
        objetivo["palabras_clave"] = claves_limpias
        objetivo["respuesta"] = respuesta_limpia
        if pregunta_limpia:
            objetivo["pregunta"] = pregunta_limpia
        else:
            objetivo.pop("pregunta", None)

        _guardar_config_atomico(ruta, config)
        return dict(objetivo)


def eliminar_faq_jeff(codigo_ramo: str, faq_id: str) -> Dict[str, Any]:
    """Elimina una entrada de faqs_jeff dentro de config.json de forma atómica."""
    codigo = codigo_ramo.upper()
    ruta = DATA_DIR / codigo / "config.json"

    with _CONFIG_LOCK:
        if not ruta.exists():
            raise FileNotFoundError(f"No existe config.json para el ramo {codigo}")
        with open(ruta, "r", encoding="utf-8") as archivo:
            config = json.load(archivo)

        faqs = config.get("faqs_jeff", [])
        if not isinstance(faqs, list):
            faqs = []

        indice = next((i for i, f in enumerate(faqs) if f.get("id") == faq_id), None)
        if indice is None:
            raise KeyError(f"FAQ '{faq_id}' no encontrada en {codigo}")

        eliminada = faqs.pop(indice)
        config["faqs_jeff"] = faqs
        _guardar_config_atomico(ruta, config)
        return dict(eliminada)
