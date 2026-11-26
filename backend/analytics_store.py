"""Analítica anónima por ramo: registro JSONL, agrupación de dudas y resumen agregado."""

import hashlib
import json
import re
import threading
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

BASE_DIR = Path(__file__).resolve().parent
ANALYTICS_DIR = BASE_DIR / "data" / "analytics"
RAMOS_DIR = BASE_DIR / "data" / "ramos"

DIAS_DEFAULT = 30
DIAS_MAX = 365
TOP_DUDAS_DEFAULT = 10
TOP_DUDAS_MAX = 30
MAX_PREGUNTA = 500
CANALES = ("JEFF_ADMIN", "TUTOR_SOCRATICO", "FALLBACK_DOCENTE")
UMBRAL_SIMILITUD_DUDAS = 0.5

_STORE_LOCK = threading.Lock()

_PATRON_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.IGNORECASE)
_PATRON_RUT = re.compile(
    r"\b\d{1,2}\s*\.?\s*\d{3}\s*\.?\s*\d{3}\s*-?\s*[\dkK]\b"
)
_PATRON_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_PATRON_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_PATRON_IPV6 = re.compile(r"\b(?:[0-9a-f]{1,4}:){2,7}[0-9a-f]{0,4}\b", re.IGNORECASE)
_PATRON_TELEFONO = re.compile(
    r"(?<!\d)(?:\+?56[\s-]*)?9[\s-]?\d{4}[\s-]?\d{4}(?!\d)|"
    r"(?<!\d)\+\d{1,3}[\s-]?\d{4}[\s-]?\d{4,6}(?!\d)|"
    r"(?<!\d)\d{8,12}(?!\d)"
)
_PATRON_ESPACIOS = re.compile(r"\s+")

_STOPWORDS_ANALITICA = {
    "a", "al", "algo", "algun", "alguna", "algunas", "alguno", "algunos", "ante",
    "aqui", "asi", "buenas", "buenos", "como", "con", "cual", "cuales", "cuando",
    "de", "del", "desde", "dias", "dime", "donde", "dos", "el", "ella", "ellas",
    "ellos", "en", "entre", "es", "esa", "esas", "ese", "eso", "esos", "esta",
    "estan", "estas", "este", "esto", "estos", "explica", "explicame", "explicar",
    "favor", "funciona", "gracias", "hace", "hacer", "hacia", "hasta", "hay",
    "hola", "la", "las", "le", "les", "lo", "los", "mas", "me", "mi", "mis",
    "muchas", "muy", "no", "nos", "o", "para", "pero", "por", "porque", "profe",
    "profesor", "puede", "pueden", "puedo", "que", "queria", "quien", "quienes",
    "quisiera", "saber", "se", "ser", "si", "significa", "sin", "sirve", "sobre",
    "son", "su", "sus", "tal", "tambien", "tengo", "tiene", "tienen", "todo",
    "todos", "tu", "tutor", "un", "una", "unas", "uno", "unos", "usa", "usar",
    "uso", "y", "ya",
}


def _codigo_limpio(codigo_ramo: str) -> str:
    limpio = re.sub(r"[^A-Z0-9_-]+", "_", (codigo_ramo or "").upper()).strip("_")
    return limpio or "SIN_RAMO"


def _ruta_eventos(codigo_ramo: str) -> Path:
    return ANALYTICS_DIR / f"{_codigo_limpio(codigo_ramo)}_log.jsonl"


def _ahora_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def anonimizar_pregunta(texto: str, limite: int = MAX_PREGUNTA) -> str:
    """Elimina identificadores directos (correo, RUT, URL, IP, teléfono) y normaliza."""
    limpio = str(texto or "").strip()
    if not limpio:
        return ""

    limpio = _PATRON_URL.sub(" ", limpio)
    limpio = _PATRON_EMAIL.sub(" ", limpio)
    limpio = _PATRON_RUT.sub(" ", limpio)
    limpio = _PATRON_IPV4.sub(" ", limpio)
    limpio = _PATRON_IPV6.sub(" ", limpio)
    limpio = _PATRON_TELEFONO.sub(" ", limpio)
    limpio = _PATRON_ESPACIOS.sub(" ", limpio).strip()
    return limpio[:limite].strip()


def _normalizar_texto(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto or "")
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    limpio = re.sub(r"[^a-z0-9\s]", " ", sin_tildes.lower())
    return _PATRON_ESPACIOS.sub(" ", limpio).strip()


def _singular_simple(token: str) -> str:
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def _tokens_clave(texto: str) -> Set[str]:
    norm = _normalizar_texto(texto)
    tokens: Set[str] = set()
    for palabra in norm.split():
        if palabra in _STOPWORDS_ANALITICA:
            continue
        base = _singular_simple(palabra)
        if base in _STOPWORDS_ANALITICA or len(base) < 2:
            continue
        tokens.add(base)
    return tokens


def _similitud_tokens(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    comunes = a & b
    if len(comunes) < 2:
        return 0.0
    return len(comunes) / len(a | b)


def _etiquetas_topicos_ramo(codigo_ramo: str) -> Dict[str, str]:
    """Obtiene etiquetas legibles para tópicos de Jeff desde config.json si existe."""
    ruta_config = RAMOS_DIR / _codigo_limpio(codigo_ramo) / "config.json"
    if not ruta_config.exists():
        return {}
    try:
        with open(ruta_config, "r", encoding="utf-8") as archivo:
            cfg = json.load(archivo)
    except (OSError, json.JSONDecodeError):
        return {}

    etiquetas: Dict[str, str] = {"planificacion_documento": "Planificación del curso"}
    for tarea in cfg.get("tareas") or []:
        tid = str(tarea.get("id") or "").strip()
        titulo = str(tarea.get("titulo") or "").strip()
        if tid and titulo:
            etiquetas[tid] = titulo
    for faq in cfg.get("faqs_jeff") or []:
        fid = str(faq.get("id") or "").strip()
        pregunta = str(faq.get("pregunta") or "").strip()
        categoria = str(faq.get("categoria") or "").strip()
        if fid:
            etiquetas[fid] = pregunta or categoria or fid
    return etiquetas


def registrar_evento(
    codigo_ramo: str,
    pregunta: str,
    canal: str,
    modo: Optional[str] = None,
    topico: Optional[str] = None,
    categoria: Optional[str] = None,
    motivo: Optional[str] = None,
    con_contexto: Optional[bool] = None,
    score: Optional[float] = None,
    duracion_ms: Optional[int] = None,
    error: bool = False,
) -> Dict[str, Any]:
    """Agrega un evento anónimo al archivo JSONL del ramo."""
    pregunta_limpia = anonimizar_pregunta(pregunta)
    if not pregunta_limpia:
        return {}

    evento: Dict[str, Any] = {
        "timestamp": _ahora_utc(),
        "codigo_ramo": _codigo_limpio(codigo_ramo),
        "canal": canal if canal in CANALES else "TUTOR_SOCRATICO",
        "modo": modo,
        "topico": topico,
        "categoria": categoria,
        "motivo": motivo,
        "con_contexto": con_contexto,
        "score": round(float(score), 4) if score is not None else None,
        "duracion_ms": int(duracion_ms) if duracion_ms is not None else None,
        "error": bool(error),
        "pregunta_anonimizada": pregunta_limpia,
    }

    ruta = _ruta_eventos(codigo_ramo)
    with _STORE_LOCK:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(evento, ensure_ascii=False) + "\n")

    return evento


def _parsear_fecha(valor: Any) -> Optional[datetime]:
    if not isinstance(valor, str):
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None


def leer_eventos(codigo_ramo: str, dias: int = DIAS_DEFAULT) -> List[Dict[str, Any]]:
    """Lee los eventos del rango solicitado, ignorando líneas inválidas."""
    dias = max(1, min(int(dias or DIAS_DEFAULT), DIAS_MAX))
    desde = datetime.now(timezone.utc) - timedelta(days=dias)
    ruta = _ruta_eventos(codigo_ramo)
    if not ruta.exists():
        return []

    eventos: List[Dict[str, Any]] = []
    with _STORE_LOCK:
        with open(ruta, "r", encoding="utf-8") as archivo:
            for linea in archivo:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    evento = json.loads(linea)
                except json.JSONDecodeError:
                    continue
                fecha = _parsear_fecha(evento.get("timestamp"))
                if fecha is None or fecha < desde:
                    continue
                eventos.append(evento)
    return eventos


def _id_grupo_lexico(canal: str, tokens: Set[str], clave_norm: str) -> str:
    base = "|".join(sorted(tokens)) if tokens else f"raw:{clave_norm}"
    digest = hashlib.sha1(f"{canal}:{base}".encode("utf-8")).hexdigest()[:12]
    return f"lexico:{canal}:{digest}"


def _agrupar_dudas(
    eventos: List[Dict[str, Any]],
    codigo_ramo: str = "",
    canal: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Agrupa preguntas frecuentes y conserva los índices de eventos de cada grupo:
    - En eventos con tópico (JEFF_ADMIN): consolida por tópico con etiqueta legible.
    - En Tutor Socrático / Fallback: agrupa variantes equivalentes por similitud léxica sin stopwords.
    """
    etiquetas_topicos = _etiquetas_topicos_ramo(codigo_ramo) if codigo_ramo else {}
    grupos_topico: Dict[str, Dict[str, Any]] = {}
    grupos_lexicos: List[Dict[str, Any]] = []

    for idx, evento in enumerate(eventos):
        canal_ev = evento.get("canal") or "TUTOR_SOCRATICO"
        if canal and canal_ev != canal:
            continue

        topico = str(evento.get("topico") or "").strip()
        categoria = str(evento.get("categoria") or "").strip()
        pregunta = str(evento.get("pregunta_anonimizada") or "").strip()
        if not pregunta and not topico:
            continue

        if topico:
            clave = f"{canal_ev}:{topico}"
            actual = grupos_topico.get(clave)
            etiqueta = etiquetas_topicos.get(topico) or categoria or topico
            if actual is None:
                grupos_topico[clave] = {
                    "id": f"topico:{clave}",
                    "texto": pregunta or etiqueta,
                    "total": 1,
                    "canal": canal_ev,
                    "topico": topico,
                    "etiqueta": etiqueta,
                    "_textos": Counter([pregunta]) if pregunta else Counter(),
                    "_indices": {idx},
                }
            else:
                actual["total"] += 1
                actual["_indices"].add(idx)
                if pregunta:
                    actual["_textos"][pregunta] += 1
            continue

        tokens = _tokens_clave(pregunta)
        mejor_grupo = None
        mejor_sim = 0.0
        for grupo in grupos_lexicos:
            if grupo["canal"] != canal_ev:
                continue
            sim = _similitud_tokens(tokens, grupo["_tokens"])
            if sim >= UMBRAL_SIMILITUD_DUDAS and sim > mejor_sim:
                mejor_sim = sim
                mejor_grupo = grupo

        if mejor_grupo is None and not tokens:
            clave_norm = _normalizar_texto(pregunta)
            for grupo in grupos_lexicos:
                if grupo["canal"] == canal_ev and grupo["_clave_norm"] == clave_norm:
                    mejor_grupo = grupo
                    break

        if mejor_grupo is None:
            clave_norm = _normalizar_texto(pregunta)
            grupos_lexicos.append({
                "id": _id_grupo_lexico(canal_ev, tokens, clave_norm),
                "texto": pregunta or "(sin texto)",
                "total": 1,
                "canal": canal_ev,
                "topico": None,
                "etiqueta": ", ".join(sorted(tokens)[:4]) if tokens else None,
                "_tokens": set(tokens),
                "_clave_norm": clave_norm,
                "_textos": Counter([pregunta]) if pregunta else Counter(),
                "_indices": {idx},
            })
        else:
            mejor_grupo["total"] += 1
            mejor_grupo["_indices"].add(idx)
            if pregunta:
                mejor_grupo["_textos"][pregunta] += 1

    return list(grupos_topico.values()) + grupos_lexicos


def _top_dudas(
    eventos: List[Dict[str, Any]],
    codigo_ramo: str = "",
    canal: Optional[str] = None,
    limite: int = TOP_DUDAS_DEFAULT,
) -> List[Dict[str, Any]]:
    """Devuelve las dudas agrupadas ordenadas por frecuencia."""
    todos = _agrupar_dudas(eventos, codigo_ramo=codigo_ramo, canal=canal)
    resultado: List[Dict[str, Any]] = []
    for grupo in todos:
        textos_counter: Counter = grupo["_textos"]
        texto_rep = textos_counter.most_common(1)[0][0] if textos_counter else grupo["texto"]
        item: Dict[str, Any] = {
            "id": grupo["id"],
            "texto": texto_rep,
            "total": grupo["total"],
            "canal": grupo["canal"],
            "variantes": len(textos_counter) if textos_counter else 1,
        }
        if grupo.get("topico"):
            item["topico"] = grupo["topico"]
        if grupo.get("etiqueta"):
            item["etiqueta"] = grupo["etiqueta"]
        resultado.append(item)

    resultado.sort(key=lambda item: (item["total"], item["variantes"]), reverse=True)
    return resultado[: max(1, min(int(limite or TOP_DUDAS_DEFAULT), TOP_DUDAS_MAX))]


def eliminar_dudas(
    codigo_ramo: str,
    ids_grupos: List[str],
    dias: int = DIAS_DEFAULT,
    canal: Optional[str] = None,
) -> Dict[str, int]:
    """Elimina del registro JSONL los eventos pertenecientes a los grupos seleccionados."""
    ids_objetivo = {str(gid).strip() for gid in (ids_grupos or []) if str(gid).strip()}
    if not ids_objetivo:
        return {"eliminados": 0, "grupos_eliminados": 0}

    dias = max(1, min(int(dias or DIAS_DEFAULT), DIAS_MAX))
    desde = datetime.now(timezone.utc) - timedelta(days=dias)
    canal_filtro = canal if canal in CANALES else None
    ruta = _ruta_eventos(codigo_ramo)
    if not ruta.exists():
        return {"eliminados": 0, "grupos_eliminados": 0}

    with _STORE_LOCK:
        with open(ruta, "r", encoding="utf-8") as archivo:
            lineas = archivo.readlines()

        eventos_rango: List[Dict[str, Any]] = []
        mapa_linea_por_evento: List[int] = []
        for idx_linea, linea in enumerate(lineas):
            contenido = linea.strip()
            if not contenido:
                continue
            try:
                evento = json.loads(contenido)
            except json.JSONDecodeError:
                continue
            fecha = _parsear_fecha(evento.get("timestamp"))
            if fecha is None or fecha < desde:
                continue
            if canal_filtro and (evento.get("canal") or "TUTOR_SOCRATICO") != canal_filtro:
                continue
            eventos_rango.append(evento)
            mapa_linea_por_evento.append(idx_linea)

        grupos = _agrupar_dudas(eventos_rango, codigo_ramo=codigo_ramo, canal=canal_filtro)
        lineas_a_borrar: Set[int] = set()
        grupos_eliminados = 0
        for grupo in grupos:
            if grupo["id"] in ids_objetivo:
                grupos_eliminados += 1
                for idx_ev in grupo["_indices"]:
                    lineas_a_borrar.add(mapa_linea_por_evento[idx_ev])

        if not lineas_a_borrar:
            return {"eliminados": 0, "grupos_eliminados": 0}

        nuevas_lineas = [
            linea for idx_linea, linea in enumerate(lineas) if idx_linea not in lineas_a_borrar
        ]
        with open(ruta, "w", encoding="utf-8") as archivo:
            archivo.writelines(nuevas_lineas)

    return {
        "eliminados": len(lineas_a_borrar),
        "grupos_eliminados": grupos_eliminados,
    }


def resumen(
    codigo_ramo: str,
    dias: int = DIAS_DEFAULT,
    canal: Optional[str] = None,
    limite: int = TOP_DUDAS_DEFAULT,
) -> Dict[str, Any]:
    """Construye métricas agregadas sin exponer eventos individuales."""
    dias = max(1, min(int(dias or DIAS_DEFAULT), DIAS_MAX))
    eventos = leer_eventos(codigo_ramo, dias=dias)
    canal_filtro = canal if canal in CANALES else None
    if canal_filtro:
        eventos = [
            evento for evento in eventos
            if (evento.get("canal") or "TUTOR_SOCRATICO") == canal_filtro
        ]

    por_canal = Counter(str(e.get("canal") or "") for e in eventos)
    motivos = Counter(
        str(e.get("motivo")) for e in eventos if str(e.get("motivo") or "").strip()
    )
    por_dia = Counter(
        str(e.get("timestamp") or "")[:10]
        for e in eventos
        if str(e.get("timestamp") or "").strip()
    )
    latencias = [
        int(e["duracion_ms"])
        for e in eventos
        if isinstance(e.get("duracion_ms"), (int, float))
    ]

    hoy = date.today()
    desde = hoy - timedelta(days=dias - 1)

    return {
        "codigo_ramo": _codigo_limpio(codigo_ramo),
        "desde": desde.isoformat(),
        "hasta": hoy.isoformat(),
        "dias": dias,
        "canal_filtro": canal_filtro,
        "total_eventos": len(eventos),
        "por_canal": [
            {"canal": c, "total": por_canal.get(c, 0)} for c in CANALES
        ],
        "por_motivo_fallback": [
            {"motivo": motivo, "total": total}
            for motivo, total in sorted(motivos.items(), key=lambda item: item[1], reverse=True)
        ],
        "top_dudas": _top_dudas(eventos, codigo_ramo=codigo_ramo, canal=canal, limite=limite),
        "por_dia": [
            {"fecha": fecha, "total": total}
            for fecha, total in sorted(por_dia.items(), reverse=True)
        ],
        "latencia_promedio_ms": round(sum(latencias) / len(latencias)) if latencias else 0,
        "eventos_con_error": sum(1 for e in eventos if e.get("error")),
    }
