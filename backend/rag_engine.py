import json
import logging
import os
import re
import threading
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import chromadb
import httpx
import pymupdf4llm

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "ramos"

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

EMBEDDING_BATCH_SIZE = int(os.getenv("RAG_EMBEDDING_BATCH_SIZE", "32"))
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "700"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "100"))
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.25"))
USE_EMBEDDING_PREFIXES = os.getenv("RAG_EMBEDDING_PREFIXES", "1") not in ("0", "false", "False")

logger = logging.getLogger(__name__)

_clientes: Dict[str, Any] = {}
_lock_clientes = threading.Lock()
_lock_escritura = threading.RLock()

_PATRON_ENCABEZADO = re.compile(r"^#{1,6}\s", re.MULTILINE)
_PATRON_IMAGEN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def _cliente_chroma(codigo_ramo: str):
    codigo = codigo_ramo.upper()
    with _lock_clientes:
        if codigo not in _clientes:
            ruta_chroma = DATA_DIR / codigo / "chroma"
            ruta_chroma.mkdir(parents=True, exist_ok=True)
            _clientes[codigo] = chromadb.PersistentClient(path=str(ruta_chroma))
        return _clientes[codigo]


def obtener_cliente_chroma(codigo_ramo: str):
    """Inicializa o carga la base vectorial persistente para el ramo."""
    codigo = codigo_ramo.upper()
    cliente = _cliente_chroma(codigo)
    return cliente.get_or_create_collection(
        name=f"luzai_{codigo.lower()}",
        metadata={"hnsw:space": "cosine"},
    )


def _texto_para_documento(texto: str) -> str:
    return f"search_document: {texto}" if USE_EMBEDDING_PREFIXES else texto


def _texto_para_consulta(texto: str) -> str:
    return f"search_query: {texto}" if USE_EMBEDDING_PREFIXES else texto


def _embedding_individual(client: httpx.Client, texto: str) -> List[float]:
    resp = client.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": EMBEDDING_MODEL, "prompt": texto},
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def generar_embeddings_ollama(textos: List[str]) -> List[List[float]]:
    """Genera embeddings en lote usando Ollama, con fallback al endpoint individual."""
    if not textos:
        return []

    vectores: List[List[float]] = []
    with httpx.Client(timeout=180.0) as client:
        for inicio in range(0, len(textos), EMBEDDING_BATCH_SIZE):
            lote = textos[inicio:inicio + EMBEDDING_BATCH_SIZE]
            try:
                resp = client.post(
                    f"{OLLAMA_HOST}/api/embed",
                    json={"model": EMBEDDING_MODEL, "input": lote},
                )
                resp.raise_for_status()
                embeddings = resp.json().get("embeddings")
                if not embeddings or len(embeddings) != len(lote):
                    raise ValueError("Respuesta de /api/embed inválida")
                vectores.extend(embeddings)
            except Exception as exc:
                logger.warning(
                    "Fallo /api/embed (%s); usando /api/embeddings por fragmento", exc
                )
                for texto in lote:
                    vectores.append(_embedding_individual(client, texto))

    return vectores


def generar_embedding_ollama(texto: str) -> List[float]:
    """Genera un único embedding usando nomic-embed-text en Ollama."""
    return generar_embeddings_ollama([texto])[0]


def _slug_imagenes(texto: str) -> str:
    """Genera un nombre de carpeta seguro para las imágenes extraídas."""
    sin_tildes = "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caracter)
    )
    return re.sub(r"[^A-Za-z0-9._-]+", "_", sin_tildes).strip("_") or "documento"


def _reescribir_imagenes(texto_md: str, codigo_ramo: str, carpeta_imagenes: Path) -> str:
    def _reemplazo(match: re.Match) -> str:
        alt, src = match.group(1), match.group(2).split()[0].strip("<>")
        if src.startswith(("http://", "https://", "/api/")):
            return match.group(0)
        nombre = quote(Path(src).name)
        return f"![{alt}](/api/ramos/{codigo_ramo}/imagenes/{quote(carpeta_imagenes.name)}/{nombre})"

    return _PATRON_IMAGEN.sub(_reemplazo, texto_md)


def extraer_documento_markdown(ruta_pdf: Path, codigo_ramo: str) -> List[Dict[str, Any]]:
    """
    Convierte un PDF a Markdown con soporte de LaTeX/tablas y extrae sus imágenes.
    Devuelve una lista de páginas con su número y texto descriptivo.
    """
    codigo = codigo_ramo.upper()
    ruta_imagenes = DATA_DIR / codigo / "imagenes" / _slug_imagenes(ruta_pdf.stem)
    ruta_imagenes.mkdir(parents=True, exist_ok=True)

    try:
        paginas_md = pymupdf4llm.to_markdown(
            doc=str(ruta_pdf),
            page_chunks=True,
            write_images=True,
            image_path=str(ruta_imagenes),
            image_format="png",
        )
    except Exception as exc:
        logger.error("No se pudo convertir %s a Markdown: %s", ruta_pdf.name, exc)
        return []

    if isinstance(paginas_md, str):
        paginas_md = [{"text": paginas_md, "metadata": {}}]

    paginas: List[Dict[str, Any]] = []
    for indice, pagina in enumerate(paginas_md):
        if isinstance(pagina, dict):
            texto = pagina.get("text", "") or ""
            numero = pagina.get("metadata", {}).get("page", indice + 1)
        else:
            texto = str(pagina)
            numero = indice + 1

        texto = _reescribir_imagenes(texto, codigo, ruta_imagenes)
        if texto.strip():
            paginas.append({"pagina": int(numero), "texto": texto.strip()})

    return paginas


EXTENSIONES_INDEXABLES = {".pdf", ".docx", ".txt", ".md"}


def extraer_documento_docx(ruta_docx: Path) -> List[Dict[str, Any]]:
    """Extrae párrafos de un DOCX usando solo la librería estándar."""
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    try:
        with zipfile.ZipFile(ruta_docx) as archivo:
            xml = archivo.read("word/document.xml")
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        logger.error("No se pudo leer %s como DOCX: %s", ruta_docx.name, exc)
        return []

    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError as exc:
        logger.error("XML inválido en %s: %s", ruta_docx.name, exc)
        return []

    parrafos: List[str] = []
    for parrafo in raiz.iter(f"{ns}p"):
        textos = [nodo.text for nodo in parrafo.iter(f"{ns}t") if nodo.text]
        if textos:
            parrafos.append("".join(textos).strip())

    texto = "\n\n".join(p for p in parrafos if p)
    return [{"pagina": 1, "texto": texto}] if texto else []


def extraer_documento_texto(ruta_texto: Path) -> List[Dict[str, Any]]:
    """Extrae el contenido de un archivo de texto plano o Markdown."""
    try:
        texto = ruta_texto.read_text(encoding="utf-8", errors="replace").strip()
    except OSError as exc:
        logger.error("No se pudo leer %s: %s", ruta_texto.name, exc)
        return []
    return [{"pagina": 1, "texto": texto}] if texto else []


def _dividir_unidades(texto: str) -> List[str]:
    """Separa el Markdown en bloques semánticos (encabezados, párrafos, código)."""
    unidades: List[str] = []
    buffer: List[str] = []
    en_codigo = False

    for linea in texto.splitlines():
        limpia = linea.strip()
        if limpia.startswith(("```", "~~~")):
            en_codigo = not en_codigo
            buffer.append(linea)
            continue
        if en_codigo:
            buffer.append(linea)
            continue
        if _PATRON_ENCABEZADO.match(linea) or not limpia:
            if buffer:
                unidades.append("\n".join(buffer).strip())
                buffer = []
            if limpia:
                unidades.append(limpia)
        else:
            buffer.append(linea)

    if buffer:
        unidades.append("\n".join(buffer).strip())

    return [unidad for unidad in unidades if unidad]


def _partir_texto_largo(texto: str, max_caracteres: int, overlap: int) -> List[str]:
    partes: List[str] = []
    inicio = 0
    paso = max(1, max_caracteres - overlap)
    while inicio < len(texto):
        parte = texto[inicio:inicio + max_caracteres].strip()
        if parte:
            partes.append(parte)
        inicio += paso
    return partes


def crear_chunks(
    texto: str,
    max_caracteres: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """Divide texto en fragmentos respetando encabezados y párrafos del Markdown."""
    max_caracteres = max(200, max_caracteres)
    overlap = max(0, min(overlap, max_caracteres // 2))

    chunks: List[str] = []
    actual = ""

    for unidad in _dividir_unidades(texto):
        if len(unidad) > max_caracteres:
            if actual:
                chunks.append(actual.strip())
                actual = ""
            chunks.extend(_partir_texto_largo(unidad, max_caracteres, overlap))
            continue

        candidato = f"{actual}\n\n{unidad}" if actual else unidad
        if len(candidato) <= max_caracteres:
            actual = candidato
            continue

        if actual:
            chunks.append(actual.strip())
            cola = actual[-overlap:] if overlap else ""
            actual = f"{cola}\n\n{unidad}".strip() if cola else unidad
        else:
            actual = unidad

        if len(actual) > max_caracteres:
            chunks.extend(_partir_texto_largo(actual, max_caracteres, overlap))
            actual = ""

    if actual.strip():
        chunks.append(actual.strip())

    return chunks


def _upsert_en_lotes(
    coleccion,
    ids: List[str],
    embeddings: List[List[float]],
    documents: List[str],
    metadatas: List[Dict[str, Any]],
    tam_lote: int = 256,
) -> None:
    for inicio in range(0, len(ids), tam_lote):
        fin = inicio + tam_lote
        coleccion.upsert(
            ids=ids[inicio:fin],
            embeddings=embeddings[inicio:fin],
            documents=documents[inicio:fin],
            metadatas=metadatas[inicio:fin],
        )


def indexar_documento(ruta_archivo: Path, codigo_ramo: str, carpeta: str) -> Dict[str, Any]:
    with _lock_escritura:
        return _indexar_documento(ruta_archivo, codigo_ramo, carpeta)


def _indexar_documento(ruta_archivo: Path, codigo_ramo: str, carpeta: str) -> Dict[str, Any]:
    """
    Lee un documento soportado, lo fragmenta, calcula embeddings y lo almacena
    en la colección vectorial del ramo. Es idempotente por archivo.
    """
    codigo = codigo_ramo.upper()
    sufijo = ruta_archivo.suffix.lower()
    if sufijo not in EXTENSIONES_INDEXABLES:
        return {
            "status": "omitido",
            "archivo": ruta_archivo.name,
            "chunks_indexados": 0,
            "motivo": "Solo se indexan PDF, DOCX, TXT y Markdown",
        }

    coleccion = obtener_cliente_chroma(codigo)
    eliminar_documento_vectorial(ruta_archivo.name, codigo, carpeta, coleccion=coleccion)

    if sufijo == ".pdf":
        paginas = extraer_documento_markdown(ruta_archivo, codigo)
    elif sufijo == ".docx":
        paginas = extraer_documento_docx(ruta_archivo)
    else:
        paginas = extraer_documento_texto(ruta_archivo)

    if not paginas:
        return {
            "status": "sin_texto",
            "archivo": ruta_archivo.name,
            "chunks_indexados": 0,
            "motivo": "No se extrajo texto del documento",
        }

    ids: List[str] = []
    textos: List[str] = []
    metadatos: List[Dict[str, Any]] = []

    for pagina in paginas:
        for indice, fragmento in enumerate(crear_chunks(pagina["texto"])):
            ids.append(f"{carpeta}__{ruta_archivo.name}__p{pagina['pagina']}__c{indice}")
            textos.append(fragmento)
            metadatos.append({
                "archivo": ruta_archivo.name,
                "carpeta": carpeta,
                "pagina": pagina["pagina"],
                "codigo_ramo": codigo,
            })

    if not textos:
        return {
            "status": "sin_texto",
            "archivo": ruta_archivo.name,
            "chunks_indexados": 0,
            "motivo": "El documento no generó fragmentos",
        }

    embeddings = generar_embeddings_ollama([_texto_para_documento(t) for t in textos])
    _upsert_en_lotes(coleccion, ids, embeddings, textos, metadatos)

    return {
        "status": "ok",
        "archivo": ruta_archivo.name,
        "chunks_indexados": len(textos),
    }


def eliminar_documento_vectorial(
    nombre_archivo: str,
    codigo_ramo: str,
    carpeta: str = "",
    coleccion=None,
) -> None:
    """Elimina de ChromaDB los fragmentos de un archivo (opcionalmente por carpeta)."""
    coleccion = coleccion or obtener_cliente_chroma(codigo_ramo)
    where: Dict[str, Any] = {"archivo": nombre_archivo}
    if carpeta:
        where = {"$and": [{"archivo": nombre_archivo}, {"carpeta": carpeta}]}
    with _lock_escritura:
        try:
            coleccion.delete(where=where)
        except Exception as exc:
            logger.warning("No se pudieron borrar vectores de %s: %s", nombre_archivo, exc)


def eliminar_carpeta_vectorial(codigo_ramo: str, carpeta: str) -> None:
    """Elimina de ChromaDB todos los fragmentos asociados a una carpeta."""
    coleccion = obtener_cliente_chroma(codigo_ramo)
    with _lock_escritura:
        try:
            coleccion.delete(where={"carpeta": carpeta})
        except Exception as exc:
            logger.warning("No se pudieron borrar vectores de la carpeta %s: %s", carpeta, exc)


def eliminar_ramo_vectorial(codigo_ramo: str) -> None:
    """Elimina por completo la colección vectorial de un ramo."""
    codigo = codigo_ramo.upper()
    cliente = _cliente_chroma(codigo)
    with _lock_escritura:
        try:
            cliente.delete_collection(name=f"luzai_{codigo.lower()}")
        except Exception as exc:
            logger.warning("No se pudo eliminar la colección de %s: %s", codigo, exc)


def esta_indexado(nombre_archivo: str, codigo_ramo: str, carpeta: Optional[str] = None) -> bool:
    """Indica si un archivo ya tiene fragmentos en la base vectorial."""
    try:
        coleccion = obtener_cliente_chroma(codigo_ramo)
        where: Dict[str, Any] = {"archivo": nombre_archivo}
        if carpeta:
            where = {"$and": [{"archivo": nombre_archivo}, {"carpeta": carpeta}]}
        resultado = coleccion.get(where=where, limit=1)
        return bool(resultado.get("ids"))
    except Exception as exc:
        logger.warning("No se pudo consultar estado de %s: %s", nombre_archivo, exc)
        return False


_PATRON_IDENTIFICADOR_DOC = re.compile(
    r"\b(?:(ot|exp|experiencia|lab|laboratorio|guia|clase|n)[\s_-]*(?:n[°º]?\s*)?0*(\d+))\b",
    re.IGNORECASE,
)


def _extraer_identificadores_documento(query: str) -> List[str]:
    """Extrae identificadores explícitos de documentos (ej. OT3, Exp 2, N04) desde la consulta."""
    identificadores: List[str] = []
    for prefijo, numero in _PATRON_IDENTIFICADOR_DOC.findall(query or ""):
        pref = prefijo.lower()
        num = str(int(numero))
        num_pad = numero.zfill(2)
        if pref in ("ot", "exp", "experiencia", "lab", "laboratorio"):
            identificadores.extend([f"ot{num}", f"ot{num_pad}", f"exp{num}", f"experiencia{num}", f"lab{num}"])
        elif pref == "n":
            identificadores.extend([f"n{num_pad}", f"n{num}"])
        else:
            identificadores.extend([f"{pref}{num}", f"{pref}{num_pad}"])
    return list(dict.fromkeys(identificadores))


def _buscar_fragmentos_por_nombre_archivo(
    query: str,
    coleccion: Any,
    vector_query: List[float],
    carpeta: Optional[str],
    limite: int,
) -> List[Dict[str, Any]]:
    """Prioriza fragmentos de archivos cuyo nombre coincide con un identificador explícito (ej. OT3)."""
    identificadores = _extraer_identificadores_documento(query)
    if not identificadores or limite <= 0:
        return []

    try:
        kwargs_get: Dict[str, Any] = {"include": ["metadatas"]}
        if carpeta:
            kwargs_get["where"] = {"carpeta": carpeta}
        meta_res = coleccion.get(**kwargs_get)
    except Exception:
        return []

    archivos_unicos = sorted({
        meta.get("archivo", "")
        for meta in (meta_res.get("metadatas") or [])
        if isinstance(meta, dict) and meta.get("archivo")
    })

    archivos_coincidentes: List[str] = []
    for archivo in archivos_unicos:
        tokens_archivo = {t.lower() for t in re.findall(r"[a-zA-Z0-9]+", archivo)}
        norm_compacto = re.sub(r"[^a-z0-9]+", "", archivo.lower())
        if any(ident in tokens_archivo or ident in norm_compacto for ident in identificadores):
            archivos_coincidentes.append(archivo)

    if not archivos_coincidentes:
        return []

    priorizados: List[Dict[str, Any]] = []
    por_archivo = max(1, min(3, limite))
    for archivo in archivos_coincidentes[:2]:
        where_filtro: Dict[str, Any] = (
            {"$and": [{"archivo": archivo}, {"carpeta": carpeta}]}
            if carpeta
            else {"archivo": archivo}
        )
        try:
            res = coleccion.query(
                query_embeddings=[vector_query],
                n_results=por_archivo,
                where=where_filtro,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            continue

        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        for idx, texto in enumerate(docs):
            meta = metas[idx] if idx < len(metas) else {}
            distancia = dists[idx] if idx < len(dists) else None
            priorizados.append({
                "texto": texto,
                "archivo": meta.get("archivo", ""),
                "carpeta": meta.get("carpeta", ""),
                "pagina": meta.get("pagina"),
                "distancia": distancia,
                "score": (1 - distancia) if isinstance(distancia, (int, float)) else None,
            })

    return priorizados[:limite]


def buscar_fragmentos(
    query: str,
    codigo_ramo: str,
    top_k: int = DEFAULT_TOP_K,
    carpeta: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Recupera los fragmentos más similares a la consulta del alumno."""
    coleccion = obtener_cliente_chroma(codigo_ramo)
    total = coleccion.count()
    if total == 0 or not query.strip():
        return []

    vector_query = generar_embedding_ollama(_texto_para_consulta(query))
    priorizados = _buscar_fragmentos_por_nombre_archivo(
        query, coleccion, vector_query, carpeta, min(3, top_k)
    )
    argumentos: Dict[str, Any] = {
        "query_embeddings": [vector_query],
        "n_results": min(top_k, total),
        "include": ["documents", "metadatas", "distances"],
    }
    if carpeta:
        argumentos["where"] = {"carpeta": carpeta}

    resultados = coleccion.query(**argumentos)

    documentos = (resultados.get("documents") or [[]])[0]
    metadatos = (resultados.get("metadatas") or [[]])[0]
    distancias = (resultados.get("distances") or [[]])[0]

    fragmentos: List[Dict[str, Any]] = []
    vistos = set()
    for frag in priorizados:
        clave = (frag.get("archivo"), frag.get("pagina"), frag.get("texto", "")[:120])
        if clave not in vistos:
            vistos.add(clave)
            fragmentos.append(frag)

    for indice, texto in enumerate(documentos):
        meta = metadatos[indice] if indice < len(metadatos) else {}
        distancia = distancias[indice] if indice < len(distancias) else None
        clave = (meta.get("archivo", ""), meta.get("pagina"), texto[:120])
        if clave in vistos:
            continue
        vistos.add(clave)
        fragmentos.append({
            "texto": texto,
            "archivo": meta.get("archivo", ""),
            "carpeta": meta.get("carpeta", ""),
            "pagina": meta.get("pagina"),
            "distancia": distancia,
            "score": (1 - distancia) if isinstance(distancia, (int, float)) else None,
        })
        if len(fragmentos) >= top_k:
            break

    return fragmentos


_PATRON_IMAGEN_MD = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_PATRON_COMENTARIO_HTML = re.compile(r"<!--.*?-->", re.DOTALL)
_PATRON_ETIQUETA_HTML = re.compile(
    r"</?(?:sup|sub|br|p|div|span|img|a|table|thead|tbody|tr|td|th|ul|ol|li|h[1-6]|"
    r"strong|em|code|pre|blockquote)\b[^>]*>",
    re.IGNORECASE,
)
_PATRON_ENFASIS_MD = re.compile(r"(?<!\w)_([^_\n]{1,160})_(?!\w)")
_PATRON_SALTOS = re.compile(r"\n{3,}")


def _limpiar_fragmento(texto: str) -> str:
    """Quita artefactos de conversión que el LLM podría copiar en su respuesta."""
    texto = _PATRON_IMAGEN_MD.sub("", texto)
    texto = _PATRON_COMENTARIO_HTML.sub("", texto)
    texto = _PATRON_ETIQUETA_HTML.sub("", texto)
    texto = _PATRON_ENFASIS_MD.sub(r"\1", texto)
    texto = texto.replace("\ufffd", "")
    texto = _PATRON_SALTOS.sub("\n\n", texto)
    return texto.strip()


def formatear_contexto(fragmentos: List[Dict[str, Any]]) -> str:
    """Convierte los fragmentos recuperados en un bloque de contexto citable."""
    if not fragmentos:
        return ""

    bloques: List[str] = []
    for indice, fragmento in enumerate(fragmentos, start=1):
        ubicacion = fragmento.get("archivo", "documento")
        if fragmento.get("pagina") is not None:
            ubicacion += f" | pág. {fragmento['pagina']}"
        if fragmento.get("carpeta"):
            ubicacion += f" | {fragmento['carpeta']}"
        bloques.append(
            f"[Fuente {indice}: {ubicacion}]\n{_limpiar_fragmento(fragmento['texto'])}"
        )

    return "\n\n---\n\n".join(bloques)


def buscar_fragmentos_relevantes(
    query: str,
    codigo_ramo: str,
    top_k: int = DEFAULT_TOP_K,
    carpeta: Optional[str] = None,
    min_score: float = MIN_SCORE,
) -> List[Dict[str, Any]]:
    """Busca fragmentos y descarta los que quedan bajo el umbral de relevancia."""
    fragmentos = buscar_fragmentos(query, codigo_ramo, top_k, carpeta)
    return [
        fragmento
        for fragmento in fragmentos
        if fragmento.get("score") is None or fragmento["score"] >= min_score
    ]


def buscar_contexto_relevante(
    query: str,
    codigo_ramo: str,
    top_k: int = DEFAULT_TOP_K,
    carpeta: Optional[str] = None,
    min_score: float = MIN_SCORE,
) -> str:
    """Busca fragmentos, descarta los poco relevantes y los formatea para el LLM."""
    fragmentos = buscar_fragmentos_relevantes(
        query, codigo_ramo, top_k, carpeta, min_score
    )
    return formatear_contexto(fragmentos)


def buscar_fragmentos_planificacion(
    query: str,
    codigo_ramo: str,
    top_k: int = 6,
    min_score: float = 0.28,
) -> List[Dict[str, Any]]:
    """
    Recupera fragmentos priorizando documentos en Planificacion (incluyendo subcarpetas)
    y faqs_jeff para responder consultas administrativas o de cronograma en modo informativo.
    """
    coleccion = obtener_cliente_chroma(codigo_ramo)
    total = coleccion.count()
    if total == 0 or not query.strip():
        return []

    candidatos = buscar_fragmentos(query, codigo_ramo, top_k=total)
    resultados: List[Dict[str, Any]] = []
    vistos = set()

    for frag in candidatos:
        carpeta = (frag.get("carpeta") or "").strip()
        es_plan = (
            carpeta.lower() == "planificacion"
            or carpeta.lower().startswith("planificacion/")
            or carpeta == CARPETA_FAQS_JEFF
            or carpeta == CARPETA_TAREAS_JEFF
        )
        score = frag.get("score")
        if not es_plan:
            continue
        if score is not None and score < min_score:
            continue
        clave = (frag.get("archivo"), frag.get("pagina"), (frag.get("texto") or "")[:80])
        if clave not in vistos:
            vistos.add(clave)
            resultados.append(frag)

    resultados.sort(key=lambda f: f.get("score") or 0.0, reverse=True)
    return resultados[:top_k]


CARPETA_FAQS_JEFF = "faqs_jeff"
FUENTE_FAQS_JEFF = "Preguntas Guardadas (Jeff)"
CARPETA_TAREAS_JEFF = "tareas_jeff"
FUENTE_TAREAS_JEFF = "Tareas y Entregas (Jeff)"


def _construir_texto_faq(faq: Dict[str, Any]) -> str:
    """Construye el texto indexable de una pregunta guardada de Jeff."""
    lineas: List[str] = []
    pregunta = str(faq.get("pregunta") or "").strip()
    categoria = str(faq.get("categoria") or "").strip()
    palabras_clave = [
        str(p).strip() for p in (faq.get("palabras_clave") or []) if str(p).strip()
    ]
    respuesta = str(faq.get("respuesta") or "").strip()

    if pregunta:
        lineas.append(f"Pregunta: {pregunta}")
    elif palabras_clave:
        lineas.append(f"Palabras clave: {', '.join(palabras_clave)}")

    if categoria:
        lineas.append(f"Categoría: {categoria}")

    if respuesta:
        lineas.append(f"Respuesta oficial: {respuesta}")

    return "\n".join(lineas).strip()


def indexar_faq_jeff(codigo_ramo: str, faq: Dict[str, Any]) -> Dict[str, Any]:
    """Indexa o actualiza una pregunta guardada de Jeff en ChromaDB."""
    codigo = codigo_ramo.upper()
    faq_id = str(faq.get("id") or "").strip()
    if not faq_id:
        raise ValueError("La FAQ debe tener un identificador 'id'")

    texto = _construir_texto_faq(faq)
    if not texto:
        raise ValueError("La FAQ no tiene contenido indexable")

    vector = generar_embedding_ollama(_texto_para_documento(texto))
    metadata = {
        "ramo": codigo,
        "carpeta": CARPETA_FAQS_JEFF,
        "archivo": FUENTE_FAQS_JEFF,
        "faq_id": faq_id,
        "categoria": str(faq.get("categoria") or "General"),
    }

    with _lock_escritura:
        coleccion = obtener_cliente_chroma(codigo)
        coleccion.upsert(
            ids=[f"faq_{faq_id}"],
            embeddings=[vector],
            documents=[texto],
            metadatas=[metadata],
        )

    return {"status": "ok", "faq_id": faq_id, "chunks_indexados": 1}


def eliminar_faq_vectorial(codigo_ramo: str, faq_id: str) -> None:
    """Elimina el vector asociado a una pregunta guardada de Jeff en ChromaDB."""
    codigo = codigo_ramo.upper()
    limpio = str(faq_id or "").strip()
    if not limpio:
        return

    with _lock_escritura:
        coleccion = obtener_cliente_chroma(codigo)
        try:
            coleccion.delete(ids=[f"faq_{limpio}"])
        except Exception as exc:
            logger.warning("No se pudo eliminar FAQ vectorial %s en %s: %s", limpio, codigo, exc)


def sincronizar_faqs_jeff(codigo_ramo: str) -> Dict[str, Any]:
    """Indexa todas las faqs_jeff declaradas en config.json del ramo."""
    codigo = codigo_ramo.upper()
    ruta_config = DATA_DIR / codigo / "config.json"
    if not ruta_config.exists():
        return {"faqs_indexadas": 0, "errores": []}

    with open(ruta_config, "r", encoding="utf-8") as archivo:
        config = json.load(archivo)

    faqs = config.get("faqs_jeff", [])
    if not isinstance(faqs, list):
        return {"faqs_indexadas": 0, "errores": []}

    indexadas = 0
    errores: List[str] = []
    for faq in faqs:
        if not isinstance(faq, dict):
            continue
        try:
            indexar_faq_jeff(codigo, faq)
            indexadas += 1
        except Exception as exc:
            logger.warning("Error indexando FAQ %s en %s: %s", faq.get("id"), codigo, exc)
            errores.append(f"faq:{faq.get('id')}: {exc}")

    return {"faqs_indexadas": indexadas, "errores": errores}


def _construir_texto_tarea(tarea: Dict[str, Any]) -> str:
    """Construye el texto indexable de una tarea o entrega administrativa."""
    lineas: List[str] = []
    titulo = str(tarea.get("titulo") or "").strip()
    fecha = str(tarea.get("fecha_limite") or "").strip()
    formato = str(tarea.get("formato_entrega") or "").strip()
    plataforma = str(tarea.get("plataforma") or "").strip()
    palabras = [str(p).strip() for p in (tarea.get("palabras_clave") or []) if str(p).strip()]
    respuesta = str(tarea.get("respuesta") or "").strip()

    if titulo:
        lineas.append(f"Tarea o entrega: {titulo}")
    if fecha:
        lineas.append(f"Fecha límite: {fecha}")
    if formato:
        lineas.append(f"Formato de entrega: {formato}")
    if plataforma:
        lineas.append(f"Plataforma: {plataforma}")
    if palabras:
        lineas.append(f"Palabras clave: {', '.join(palabras)}")
    if respuesta:
        lineas.append(f"Detalle oficial: {respuesta}")

    return "\n".join(lineas).strip()


def indexar_tarea_jeff(codigo_ramo: str, tarea: Dict[str, Any]) -> Dict[str, Any]:
    """Indexa o actualiza una tarea de Jeff en ChromaDB."""
    codigo = codigo_ramo.upper()
    tarea_id = str(tarea.get("id") or "").strip()
    if not tarea_id:
        raise ValueError("La tarea debe tener un identificador 'id'")

    texto = _construir_texto_tarea(tarea)
    if not texto:
        raise ValueError("La tarea no tiene contenido indexable")

    vector = generar_embedding_ollama(_texto_para_documento(texto))
    metadata = {
        "ramo": codigo,
        "carpeta": CARPETA_TAREAS_JEFF,
        "archivo": FUENTE_TAREAS_JEFF,
        "tarea_id": tarea_id,
    }

    with _lock_escritura:
        coleccion = obtener_cliente_chroma(codigo)
        coleccion.upsert(
            ids=[f"tarea_{tarea_id}"],
            embeddings=[vector],
            documents=[texto],
            metadatas=[metadata],
        )

    return {"status": "ok", "tarea_id": tarea_id, "chunks_indexados": 1}


def eliminar_tarea_vectorial(codigo_ramo: str, tarea_id: str) -> None:
    """Elimina el vector asociado a una tarea de Jeff en ChromaDB."""
    codigo = codigo_ramo.upper()
    limpio = str(tarea_id or "").strip()
    if not limpio:
        return

    with _lock_escritura:
        coleccion = obtener_cliente_chroma(codigo)
        coleccion.delete(ids=[f"tarea_{limpio}"])


def sincronizar_tareas_jeff(codigo_ramo: str) -> Dict[str, Any]:
    """Indexa todas las tareas declaradas en config.json del ramo."""
    codigo = codigo_ramo.upper()
    ruta_config = DATA_DIR / codigo / "config.json"
    if not ruta_config.exists():
        return {"tareas_indexadas": 0, "errores": []}

    with open(ruta_config, "r", encoding="utf-8") as archivo:
        config = json.load(archivo)

    tareas = config.get("tareas", [])
    if not isinstance(tareas, list):
        return {"tareas_indexadas": 0, "errores": []}

    indexadas = 0
    errores: List[str] = []
    for tarea in tareas:
        if not isinstance(tarea, dict):
            continue
        try:
            indexar_tarea_jeff(codigo, tarea)
            indexadas += 1
        except Exception as exc:
            logger.warning("Error indexando tarea %s en %s: %s", tarea.get("id"), codigo, exc)
            errores.append(f"tarea:{tarea.get('id')}: {exc}")

    return {"tareas_indexadas": indexadas, "errores": errores}


def reindexar_ramo(codigo_ramo: str) -> Dict[str, Any]:
    with _lock_escritura:
        return _reindexar_ramo(codigo_ramo)


def _reindexar_ramo(codigo_ramo: str) -> Dict[str, Any]:
    """Reconstruye por completo la base vectorial de un ramo desde sus PDFs y FAQs de Jeff."""
    codigo = codigo_ramo.upper()
    dir_documentos = DATA_DIR / codigo / "documentos"
    ruta_config = DATA_DIR / codigo / "config.json"
    if not dir_documentos.exists() and not ruta_config.exists():
        return {"status": "error", "motivo": f"No existe {dir_documentos}", "chunks_indexados": 0}

    eliminar_ramo_vectorial(codigo)

    total_chunks = 0
    procesados = 0
    errores: List[str] = []

    if dir_documentos.exists():
        archivos = sorted(
            archivo
            for archivo in dir_documentos.rglob("*")
            if archivo.is_file()
            and archivo.suffix.lower() in EXTENSIONES_INDEXABLES
            and not any(parte.startswith(".") for parte in archivo.relative_to(dir_documentos).parts)
        )
        for archivo in archivos:
            carpeta = (
                archivo.parent.relative_to(dir_documentos).as_posix()
                if archivo.parent != dir_documentos
                else "General"
            )
            try:
                resultado = indexar_documento(archivo, codigo, carpeta)
                total_chunks += resultado.get("chunks_indexados", 0)
                procesados += 1
            except Exception as exc:
                logger.error("Error indexando %s: %s", archivo.name, exc)
                errores.append(f"{archivo.name}: {exc}")

    res_faqs = sincronizar_faqs_jeff(codigo)
    faqs_indexadas = res_faqs.get("faqs_indexadas", 0)
    total_chunks += faqs_indexadas
    errores.extend(res_faqs.get("errores", []))

    res_tareas = sincronizar_tareas_jeff(codigo)
    tareas_indexadas = res_tareas.get("tareas_indexadas", 0)
    total_chunks += tareas_indexadas
    errores.extend(res_tareas.get("errores", []))

    return {
        "status": "ok",
        "codigo_ramo": codigo,
        "documentos_procesados": procesados,
        "faqs_indexadas": faqs_indexadas,
        "tareas_indexadas": tareas_indexadas,
        "chunks_indexados": total_chunks,
        "errores": errores,
    }
