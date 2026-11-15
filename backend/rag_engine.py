import logging
import os
import re
import threading
import unicodedata
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
    Lee un PDF, lo fragmenta, calcula embeddings y lo almacena en la colección
    vectorial del ramo. Es idempotente: reemplaza los vectores previos del archivo.
    """
    codigo = codigo_ramo.upper()
    if ruta_archivo.suffix.lower() != ".pdf":
        return {
            "status": "omitido",
            "archivo": ruta_archivo.name,
            "chunks_indexados": 0,
            "motivo": "Solo se indexan archivos PDF",
        }

    coleccion = obtener_cliente_chroma(codigo)
    eliminar_documento_vectorial(ruta_archivo.name, codigo, carpeta, coleccion=coleccion)

    paginas = extraer_documento_markdown(ruta_archivo, codigo)
    if not paginas:
        return {
            "status": "sin_texto",
            "archivo": ruta_archivo.name,
            "chunks_indexados": 0,
            "motivo": "No se extrajo texto (posible PDF escaneado)",
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
    for indice, texto in enumerate(documentos):
        meta = metadatos[indice] if indice < len(metadatos) else {}
        distancia = distancias[indice] if indice < len(distancias) else None
        fragmentos.append({
            "texto": texto,
            "archivo": meta.get("archivo", ""),
            "carpeta": meta.get("carpeta", ""),
            "pagina": meta.get("pagina"),
            "distancia": distancia,
            "score": (1 - distancia) if isinstance(distancia, (int, float)) else None,
        })

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


def reindexar_ramo(codigo_ramo: str) -> Dict[str, Any]:
    with _lock_escritura:
        return _reindexar_ramo(codigo_ramo)


def _reindexar_ramo(codigo_ramo: str) -> Dict[str, Any]:
    """Reconstruye por completo la base vectorial de un ramo desde sus PDFs."""
    codigo = codigo_ramo.upper()
    dir_documentos = DATA_DIR / codigo / "documentos"
    if not dir_documentos.exists():
        return {"status": "error", "motivo": f"No existe {dir_documentos}", "chunks_indexados": 0}

    eliminar_ramo_vectorial(codigo)

    total_chunks = 0
    procesados = 0
    errores: List[str] = []

    for archivo in sorted(dir_documentos.rglob("*.pdf")):
        carpeta = archivo.parent.name if archivo.parent != dir_documentos else "General"
        try:
            resultado = indexar_documento(archivo, codigo, carpeta)
            total_chunks += resultado.get("chunks_indexados", 0)
            procesados += 1
        except Exception as exc:
            logger.error("Error indexando %s: %s", archivo.name, exc)
            errores.append(f"{archivo.name}: {exc}")

    return {
        "status": "ok",
        "codigo_ramo": codigo,
        "documentos_procesados": procesados,
        "chunks_indexados": total_chunks,
        "errores": errores,
    }
