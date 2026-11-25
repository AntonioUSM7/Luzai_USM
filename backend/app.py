import asyncio
import json
import logging
import os
import re
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Dict, Any, List, Literal, Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

import analytics_store
import consultas_store
import rag_engine
import router_jeff
import router_modo

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LuzAI USM - Backend Base",
    description="Servidor base para el Tutor Inteligente USM",
    version="0.1.0",
)

# Permitir conexión desde el frontend en desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DATA_DIR = Path(__file__).resolve().parent / "data" / "ramos"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen3:8b")
OLLAMA_THINK = os.getenv("OLLAMA_THINK", "false").strip().lower() in ("1", "true", "yes")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
AUTO_REINDEX = os.getenv("RAG_AUTO_REINDEX", "1") not in ("0", "false", "False")
RAG_OFFTOPIC_SCORE = float(os.getenv("RAG_OFFTOPIC_SCORE", "0.65"))


class MensajeHistorial(BaseModel):
    rol: Literal["user", "assistant"]
    contenido: str


class ConsultaChat(BaseModel):
    codigo_ramo: str
    mensaje: str
    historial: List[MensajeHistorial] = Field(default_factory=list)


class CrearCarpetaReq(BaseModel):
    nombre: str
    carpeta_padre: Optional[str] = None


class CrearConsultaProfesorReq(BaseModel):
    pregunta: str
    motivo: str = "sin_respaldo_rag"


class ResponderConsultaProfesorReq(BaseModel):
    estado: str = "resuelta"
    respuesta_profesor: Optional[str] = None
    guardar_en_jeff: bool = False
    categoria: str = "Consultas Resueltas"
    palabras_clave: Optional[List[str]] = None


class FaqJeffReq(BaseModel):
    pregunta: Optional[str] = None
    respuesta: str
    palabras_clave: Optional[List[str]] = None
    categoria: str = "Consultas Resueltas"


class TareaJeffReq(BaseModel):
    titulo: str
    fecha_limite: Optional[str] = None
    formato_entrega: Optional[str] = None
    plataforma: Optional[str] = None
    palabras_clave: Optional[List[str]] = None
    respuesta: Optional[str] = None


class ConfigSocraticaReq(BaseModel):
    reglas_socraticas: str = ""
    estilo: Literal["estricto", "equilibrado", "paso_a_paso"] = "equilibrado"
    extension: Literal["corta", "media"] = "media"


class ConfigFallbackReq(BaseModel):
    habilitado: Optional[bool] = None
    permitir_escalar_profesor: Optional[bool] = None
    mensaje_sin_respaldo: Optional[str] = None
    mensaje_fuera_de_foco: Optional[str] = None
    canal_alternativo: Optional[str] = None


def _listar_documentos_ramo(codigo: str) -> List[str]:
    """Lista archivos indexables reales, evitando depender del seed de config.json."""
    dir_documentos = BASE_DATA_DIR / codigo.upper() / "documentos"
    if not dir_documentos.exists():
        return []
    return sorted(
        archivo.relative_to(dir_documentos).as_posix()
        for archivo in dir_documentos.rglob("*")
        if archivo.is_file()
        and archivo.suffix.lower() in rag_engine.EXTENSIONES_INDEXABLES
        and not any(parte.startswith(".") for parte in archivo.relative_to(dir_documentos).parts)
    )


def obtener_lista_ramos():
    """Lee las carpetas de data/ramos/ y devuelve los datos básicos de cada asignatura"""
    ramos = []
    if not BASE_DATA_DIR.exists():
        return ramos

    for carpeta in sorted(BASE_DATA_DIR.iterdir()):
        if carpeta.is_dir():
            archivo_config = carpeta / "config.json"
            if archivo_config.exists():
                with open(archivo_config, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                    codigo = datos.get("codigo") or carpeta.name
                    ramos.append({
                        "codigo": codigo,
                        "nombre": datos.get("nombre"),
                        "departamento": datos.get("departamento"),
                        "profesor": datos.get("profesor"),
                        "descripcion": datos.get("descripcion"),
                        "documentos": _listar_documentos_ramo(codigo),
                        "reglas_socraticas": datos.get("reglas_socraticas", ""),
                    })
    return ramos


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "servicio": "LuzAI USM Backend Base",
        "modelo_llm": OLLAMA_LLM_MODEL,
        "modelo_embeddings": rag_engine.EMBEDDING_MODEL,
        "ollama_host": OLLAMA_HOST,
    }


@app.get("/api/ramos")
def listar_ramos():
    ramos = obtener_lista_ramos()
    return {"total": len(ramos), "ramos": ramos}


def formatear_tamano(tamano_bytes: int) -> str:
    if tamano_bytes < 1024:
        return f"{tamano_bytes} B"
    elif tamano_bytes < 1024 * 1024:
        return f"{tamano_bytes / 1024:.1f} KB"
    else:
        return f"{tamano_bytes / (1024 * 1024):.1f} MB"


CARPETAS_POR_DEFECTO = ["Clases", "Tareas", "Guias", "Certamenes", "Planificacion"]


def normalizar_ruta_carpeta(ruta: str) -> str:
    """
    Normaliza una ruta relativa de carpeta (ej. 'Certamenes/Certamen 1'),
    evitando path traversal y segmentos inválidos.
    """
    if not ruta:
        return ""
    partes_raw = ruta.replace("\\", "/").split("/")
    partes_limpias = []
    for parte in partes_raw:
        seg = parte.strip()
        if not seg or seg in (".", "..") or seg.startswith("."):
            continue
        partes_limpias.append(seg)
    return "/".join(partes_limpias)


def resolver_ruta_segura(dir_base: Path, ruta_relativa: str) -> Path:
    base_resuelta = dir_base.resolve()
    destino = (base_resuelta / ruta_relativa).resolve()
    if destino != base_resuelta and base_resuelta not in destino.parents:
        raise HTTPException(status_code=400, detail="Ruta de carpeta inválida")
    return destino


def obtener_carpetas_ramo(codigo_ramo: str):
    dir_documentos = BASE_DATA_DIR / codigo_ramo.upper() / "documentos"
    dir_documentos.mkdir(parents=True, exist_ok=True)

    # Asegurar carpetas base
    for def_folder in CARPETAS_POR_DEFECTO:
        (dir_documentos / def_folder).mkdir(parents=True, exist_ok=True)

    carpetas = []
    for item in sorted(dir_documentos.rglob("*")):
        if not item.is_dir():
            continue
        rel = item.relative_to(dir_documentos)
        if any(parte.startswith(".") for parte in rel.parts):
            continue
        carpetas.append(rel.as_posix())
    return carpetas


@app.get("/api/ramos/{codigo_ramo}/carpetas")
def listar_carpetas(codigo_ramo: str):
    """Devuelve la lista de carpetas y subcarpetas disponibles para un ramo"""
    carpetas = obtener_carpetas_ramo(codigo_ramo)
    return {"codigo_ramo": codigo_ramo.upper(), "carpetas": carpetas}


@app.post("/api/ramos/{codigo_ramo}/carpetas")
def crear_carpeta_ramo(codigo_ramo: str, datos: CrearCarpetaReq):
    """Crea una nueva carpeta o subcarpeta personalizada para el ramo"""
    codigo = codigo_ramo.upper()
    dir_documentos = BASE_DATA_DIR / codigo / "documentos"
    dir_documentos.mkdir(parents=True, exist_ok=True)

    nombre_seg = normalizar_ruta_carpeta(datos.nombre)
    if not nombre_seg:
        raise HTTPException(status_code=400, detail="El nombre de la carpeta no puede estar vacío")

    padre_limpio = normalizar_ruta_carpeta(datos.carpeta_padre or "")
    ruta_relativa = f"{padre_limpio}/{nombre_seg}" if padre_limpio else nombre_seg

    dir_nueva = resolver_ruta_segura(dir_documentos, ruta_relativa)
    try:
        dir_nueva.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail=f"Sin permisos de escritura en '{padre_limpio or 'documentos'}'. Verifica el propietario de backend/data/ramos/{codigo}/documentos.",
        )
    return {
        "status": "ok",
        "nombre": ruta_relativa,
        "mensaje": f"Carpeta '{ruta_relativa}' creada con éxito.",
    }


@app.get("/api/ramos/{codigo_ramo}/archivos")
def listar_archivos_ramo(codigo_ramo: str):
    """Lista todos los archivos organizados por carpeta/subcarpeta para un ramo específico"""
    codigo = codigo_ramo.upper()
    dir_documentos = BASE_DATA_DIR / codigo / "documentos"
    if not dir_documentos.exists():
        raise HTTPException(status_code=404, detail="Carpeta del ramo no encontrada")

    carpetas_existentes = obtener_carpetas_ramo(codigo)
    archivos = []

    # Recorrer subcarpetas y archivos
    for item in dir_documentos.rglob("*"):
        if item.is_file() and not item.name.startswith("."):
            rel_parent = item.parent.relative_to(dir_documentos)
            if any(parte.startswith(".") for parte in rel_parent.parts):
                continue
            carpeta_padre = "General" if rel_parent == Path(".") else rel_parent.as_posix()

            stats = item.stat()
            fecha_iso = datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M")
            archivos.append({
                "nombre": item.name,
                "carpeta": carpeta_padre,
                "tamano_bytes": stats.st_size,
                "tamano_legible": formatear_tamano(stats.st_size),
                "fecha_modificacion": fecha_iso,
                "indexado_rag": rag_engine.esta_indexado(item.name, codigo, carpeta_padre),
            })

    return {
        "codigo_ramo": codigo,
        "carpetas": carpetas_existentes,
        "total": len(archivos),
        "archivos": archivos,
    }


@app.post("/api/ramos/{codigo_ramo}/archivos")
async def subir_archivos_ramo(
    codigo_ramo: str,
    background_tasks: BackgroundTasks,
    archivos: Optional[List[UploadFile]] = File(None),
    archivo: Optional[UploadFile] = File(None),
    carpeta: str = Form("Clases"),
):
    """Sube uno o varios archivos a la carpeta seleccionada y los indexa en background."""
    codigo = codigo_ramo.upper()
    dir_documentos = BASE_DATA_DIR / codigo / "documentos"
    carpeta_limpia = normalizar_ruta_carpeta(carpeta) or "General"

    entradas = [entrada for entrada in (archivos or []) if entrada is not None]
    if archivo is not None:
        entradas.append(archivo)
    if not entradas:
        raise HTTPException(status_code=400, detail="Debe seleccionar al menos un archivo")

    dir_destino = resolver_ruta_segura(dir_documentos, carpeta_limpia)
    dir_destino.mkdir(parents=True, exist_ok=True)

    subidos = []
    nombres_usados = set()
    for entrada in entradas:
        nombre = Path(entrada.filename or "").name.replace(" ", "_")
        if not nombre:
            await entrada.close()
            raise HTTPException(status_code=400, detail="Hay archivos sin nombre válido")

        if nombre in nombres_usados:
            stem, extension = os.path.splitext(nombre)
            indice = 2
            while f"{stem}_{indice}{extension}" in nombres_usados:
                indice += 1
            nombre = f"{stem}_{indice}{extension}"
        nombres_usados.add(nombre)

        ruta_archivo = dir_destino / nombre
        with open(ruta_archivo, "wb") as destino:
            shutil.copyfileobj(entrada.file, destino)
        await entrada.close()

        background_tasks.add_task(rag_engine.indexar_documento, ruta_archivo, codigo, carpeta_limpia)

        stats = ruta_archivo.stat()
        fecha_iso = datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M")
        subidos.append({
            "nombre": nombre,
            "carpeta": carpeta_limpia,
            "tamano_bytes": stats.st_size,
            "tamano_legible": formatear_tamano(stats.st_size),
            "fecha_modificacion": fecha_iso,
            "indexado_rag": False,
            "estado_indexacion": "pendiente",
        })

    cantidad = len(subidos)
    return {
        "status": "ok",
        "mensaje": f"{cantidad} archivo(s) subido(s) exitosamente. Indexación RAG en curso.",
        "total": cantidad,
        "archivos": subidos,
        "archivo": subidos[0] if subidos else None,
    }


@app.delete("/api/ramos/{codigo_ramo}/archivos")
def eliminar_archivo_ramo(codigo_ramo: str, carpeta: str, nombre_archivo: str):
    """Elimina un archivo de la carpeta/subcarpeta de un ramo y sus vectores asociados"""
    codigo = codigo_ramo.upper()
    dir_documentos = BASE_DATA_DIR / codigo / "documentos"
    carpeta_limpia = normalizar_ruta_carpeta(carpeta)
    nombre_seguro = Path(nombre_archivo).name
    if not carpeta_limpia or not nombre_seguro:
        raise HTTPException(status_code=400, detail="Ruta de archivo inválida")

    dir_carpeta = resolver_ruta_segura(dir_documentos, carpeta_limpia)
    ruta_archivo = dir_carpeta / nombre_seguro
    if not ruta_archivo.exists():
        raise HTTPException(status_code=404, detail="El archivo no existe")

    ruta_archivo.unlink()
    rag_engine.eliminar_documento_vectorial(nombre_seguro, codigo, carpeta_limpia)
    return {"status": "ok", "mensaje": f"Archivo '{nombre_seguro}' eliminado correctamente."}


@app.delete("/api/ramos/{codigo_ramo}/carpetas")
def eliminar_carpeta_ramo(codigo_ramo: str, nombre_carpeta: str):
    """Elimina una carpeta (y sus subcarpetas), sus archivos y sus vectores asociados del ramo"""
    codigo = codigo_ramo.upper()
    dir_documentos = BASE_DATA_DIR / codigo / "documentos"
    nombre_limpio = normalizar_ruta_carpeta(nombre_carpeta)
    if not nombre_limpio:
        raise HTTPException(status_code=400, detail="Nombre de carpeta inválido")

    ruta_carpeta = resolver_ruta_segura(dir_documentos, nombre_limpio)

    if not ruta_carpeta.exists() or not ruta_carpeta.is_dir():
        raise HTTPException(status_code=404, detail="La carpeta no existe")

    # Recolectar la carpeta y todas sus subcarpetas para limpiar vectores en RAG
    carpetas_a_limpiar = [nombre_limpio]
    for sub in ruta_carpeta.rglob("*"):
        if sub.is_dir():
            rel = sub.relative_to(dir_documentos).as_posix()
            carpetas_a_limpiar.append(rel)

    shutil.rmtree(ruta_carpeta)
    for carpeta_vec in carpetas_a_limpiar:
        rag_engine.eliminar_carpeta_vectorial(codigo, carpeta_vec)

    return {
        "status": "ok",
        "mensaje": f"Carpeta '{nombre_limpio}' y sus archivos fueron eliminados correctamente.",
    }


@app.get("/api/ramos/{codigo_ramo}/documentos/{ruta:path}")
def ver_documento_ramo(codigo_ramo: str, ruta: str):
    """Sirve un documento del ramo inline para que el alumno pueda abrirlo en el navegador."""
    codigo = codigo_ramo.upper()
    dir_documentos = BASE_DATA_DIR / codigo / "documentos"
    ruta_limpia = normalizar_ruta_carpeta(ruta)
    if not ruta_limpia:
        raise HTTPException(status_code=400, detail="Ruta de documento inválida")

    destino = resolver_ruta_segura(dir_documentos, ruta_limpia)
    if not destino.exists() or not destino.is_file():
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    return FileResponse(destino, content_disposition_type="inline")


@app.post("/api/ramos/{codigo_ramo}/reindexar")
def reindexar_ramo(codigo_ramo: str, background_tasks: BackgroundTasks):
    """Reconstruye la base vectorial del ramo en segundo plano."""
    codigo = codigo_ramo.upper()
    if not (BASE_DATA_DIR / codigo).exists():
        raise HTTPException(status_code=404, detail="Ramo no encontrado")

    background_tasks.add_task(rag_engine.reindexar_ramo, codigo)
    return {
        "status": "aceptado",
        "codigo_ramo": codigo,
        "mensaje": "Reindexación iniciada en segundo plano.",
    }


@app.get("/api/ramos/{codigo_ramo}/estado_rag")
def estado_rag(codigo_ramo: str):
    """Devuelve cuántos fragmentos vectorizados tiene el ramo (útil para testear)."""
    try:
        coleccion = rag_engine.obtener_cliente_chroma(codigo_ramo)
        total = coleccion.count()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo consultar la base vectorial: {exc}")

    return {"codigo_ramo": codigo_ramo.upper(), "fragmentos_indexados": total}


@app.get("/api/ramos/{codigo_ramo}/imagenes/{ruta:path}")
def obtener_imagen(codigo_ramo: str, ruta: str):
    """Sirve las imágenes extraídas de los PDFs, evitando path traversal."""
    base = (BASE_DATA_DIR / codigo_ramo.upper() / "imagenes").resolve()
    destino = (base / ruta).resolve()
    try:
        destino.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=403, detail="Ruta no permitida")

    if not destino.is_file():
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    return FileResponse(destino)


@app.get("/api/ramos/{codigo_ramo}/consultas")
def listar_consultas_profesor(codigo_ramo: str, estado: Optional[str] = None):
    """Lista las consultas escaladas al profesor para un ramo."""
    codigo = codigo_ramo.upper()
    if not (BASE_DATA_DIR / codigo / "config.json").exists():
        raise HTTPException(status_code=404, detail="Ramo no encontrado")
    consultas = consultas_store.listar_consultas(codigo, estado=estado)
    return {
        "codigo_ramo": codigo,
        "total": len(consultas),
        "consultas": consultas,
    }


@app.post("/api/ramos/{codigo_ramo}/consultas")
def crear_consulta_profesor(codigo_ramo: str, req: CrearConsultaProfesorReq):
    """Registra una consulta escalada por el estudiante tras confirmación explícita."""
    try:
        consulta = consultas_store.crear_consulta(
            codigo_ramo=codigo_ramo,
            pregunta=req.pregunta,
            motivo=req.motivo,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ramo no encontrado")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"status": "ok", "consulta": consulta}


def _sincronizar_faq_rag(codigo_ramo: str, faq: Dict[str, Any]) -> bool:
    """Indexa una FAQ de Jeff en ChromaDB sin bloquear la operación ante fallos de Ollama."""
    try:
        rag_engine.indexar_faq_jeff(codigo_ramo, faq)
        return True
    except Exception as exc:
        logger.warning(
            "No se pudo indexar FAQ '%s' de %s en RAG: %s",
            faq.get("id"),
            codigo_ramo,
            exc,
        )
        return False


def _eliminar_faq_rag(codigo_ramo: str, faq_id: str) -> bool:
    """Elimina una FAQ de Jeff en ChromaDB de forma tolerante a fallos."""
    try:
        rag_engine.eliminar_faq_vectorial(codigo_ramo, faq_id)
        return True
    except Exception as exc:
        logger.warning(
            "No se pudo eliminar FAQ '%s' de %s en RAG: %s",
            faq_id,
            codigo_ramo,
            exc,
        )
        return False


@app.post("/api/ramos/{codigo_ramo}/consultas/{consulta_id}/responder")
def responder_consulta_profesor(
    codigo_ramo: str, consulta_id: str, req: ResponderConsultaProfesorReq
):
    """Permite al profesor responder o descartar una consulta y opcionalmente guardarla en Jeff."""
    try:
        resultado = consultas_store.responder_consulta(
            codigo_ramo=codigo_ramo,
            consulta_id=consulta_id,
            estado=req.estado,
            respuesta_profesor=req.respuesta_profesor,
            guardar_en_jeff=req.guardar_en_jeff,
            categoria=req.categoria,
            palabras_clave=req.palabras_clave,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ramo no encontrado")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    rag_sincronizado = False
    if resultado.get("faq_creada"):
        rag_sincronizado = _sincronizar_faq_rag(codigo_ramo, resultado["faq_creada"])

    return {"status": "ok", "rag_sincronizado": rag_sincronizado, **resultado}


@app.get("/api/ramos/{codigo_ramo}/faqs_jeff")
def listar_faqs_jeff_ramo(codigo_ramo: str):
    """Lista las preguntas guardadas de Jeff para un ramo."""
    codigo = codigo_ramo.upper()
    try:
        faqs = router_jeff.listar_faqs_jeff(codigo)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ramo no encontrado")
    return {"codigo_ramo": codigo, "total": len(faqs), "faqs": faqs}


@app.post("/api/ramos/{codigo_ramo}/faqs_jeff")
def crear_faq_jeff_ramo(codigo_ramo: str, req: FaqJeffReq):
    """Crea una nueva pregunta guardada de Jeff y la sincroniza con RAG."""
    codigo = codigo_ramo.upper()
    try:
        faq = router_jeff.agregar_faq_jeff(
            codigo_ramo=codigo,
            respuesta=req.respuesta,
            palabras_clave=req.palabras_clave,
            categoria=req.categoria,
            pregunta=req.pregunta,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ramo no encontrado")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    rag_sincronizado = _sincronizar_faq_rag(codigo, faq)
    return {"status": "ok", "faq": faq, "rag_sincronizado": rag_sincronizado}


@app.put("/api/ramos/{codigo_ramo}/faqs_jeff/{faq_id}")
def actualizar_faq_jeff_ramo(codigo_ramo: str, faq_id: str, req: FaqJeffReq):
    """Actualiza una pregunta guardada de Jeff y la re-indexa en RAG."""
    codigo = codigo_ramo.upper()
    try:
        faq = router_jeff.actualizar_faq_jeff(
            codigo_ramo=codigo,
            faq_id=faq_id,
            respuesta=req.respuesta,
            palabras_clave=req.palabras_clave,
            categoria=req.categoria,
            pregunta=req.pregunta,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ramo no encontrado")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    rag_sincronizado = _sincronizar_faq_rag(codigo, faq)
    return {"status": "ok", "faq": faq, "rag_sincronizado": rag_sincronizado}


@app.delete("/api/ramos/{codigo_ramo}/faqs_jeff/{faq_id}")
def eliminar_faq_jeff_ramo(codigo_ramo: str, faq_id: str):
    """Elimina una pregunta guardada de Jeff y remueve su vector en RAG."""
    codigo = codigo_ramo.upper()
    try:
        eliminada = router_jeff.eliminar_faq_jeff(codigo, faq_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ramo no encontrado")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    rag_sincronizado = _eliminar_faq_rag(codigo, faq_id)
    return {"status": "ok", "faq": eliminada, "rag_sincronizado": rag_sincronizado}


def _sincronizar_tarea_rag(codigo_ramo: str, tarea: Dict[str, Any]) -> bool:
    """Indexa una tarea de Jeff en ChromaDB sin bloquear la operación ante fallos de Ollama."""
    try:
        rag_engine.indexar_tarea_jeff(codigo_ramo, tarea)
        return True
    except Exception as exc:
        logger.warning(
            "No se pudo indexar tarea '%s' de %s en RAG: %s",
            tarea.get("id"),
            codigo_ramo,
            exc,
        )
        return False


def _eliminar_tarea_rag(codigo_ramo: str, tarea_id: str) -> bool:
    """Elimina una tarea de Jeff en ChromaDB de forma tolerante a fallos."""
    try:
        rag_engine.eliminar_tarea_vectorial(codigo_ramo, tarea_id)
        return True
    except Exception as exc:
        logger.warning(
            "No se pudo eliminar tarea '%s' de %s en RAG: %s",
            tarea_id,
            codigo_ramo,
            exc,
        )
        return False


@app.get("/api/ramos/{codigo_ramo}/tareas")
def listar_tareas_ramo(codigo_ramo: str):
    """Lista las tareas y entregas configuradas para un ramo."""
    codigo = codigo_ramo.upper()
    try:
        tareas = router_jeff.listar_tareas(codigo)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ramo no encontrado")
    return {"codigo_ramo": codigo, "total": len(tareas), "tareas": tareas}


@app.post("/api/ramos/{codigo_ramo}/tareas")
def crear_tarea_ramo(codigo_ramo: str, req: TareaJeffReq):
    """Crea una tarea administrativa para Jeff y la sincroniza con RAG."""
    codigo = codigo_ramo.upper()
    try:
        tarea = router_jeff.agregar_tarea(
            codigo_ramo=codigo,
            titulo=req.titulo,
            fecha_limite=req.fecha_limite,
            formato_entrega=req.formato_entrega,
            plataforma=req.plataforma,
            palabras_clave=req.palabras_clave,
            respuesta=req.respuesta,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ramo no encontrado")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    rag_sincronizado = _sincronizar_tarea_rag(codigo, tarea)
    return {"status": "ok", "tarea": tarea, "rag_sincronizado": rag_sincronizado}


@app.put("/api/ramos/{codigo_ramo}/tareas/{tarea_id}")
def actualizar_tarea_ramo(codigo_ramo: str, tarea_id: str, req: TareaJeffReq):
    """Actualiza una tarea administrativa existente y la re-indexa en RAG."""
    codigo = codigo_ramo.upper()
    try:
        tarea = router_jeff.actualizar_tarea(
            codigo_ramo=codigo,
            tarea_id=tarea_id,
            titulo=req.titulo,
            fecha_limite=req.fecha_limite,
            formato_entrega=req.formato_entrega,
            plataforma=req.plataforma,
            palabras_clave=req.palabras_clave,
            respuesta=req.respuesta,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ramo no encontrado")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    rag_sincronizado = _sincronizar_tarea_rag(codigo, tarea)
    return {"status": "ok", "tarea": tarea, "rag_sincronizado": rag_sincronizado}


@app.delete("/api/ramos/{codigo_ramo}/tareas/{tarea_id}")
def eliminar_tarea_ramo(codigo_ramo: str, tarea_id: str):
    """Elimina una tarea administrativa del ramo y remueve su vector en RAG."""
    codigo = codigo_ramo.upper()
    try:
        tarea = router_jeff.eliminar_tarea(codigo, tarea_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ramo no encontrado")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    rag_sincronizado = _eliminar_tarea_rag(codigo, tarea_id)
    return {"status": "ok", "tarea": tarea, "rag_sincronizado": rag_sincronizado}


@app.get("/api/ramos/{codigo_ramo}/analytics/resumen")
def obtener_analitica_ramo(
    codigo_ramo: str,
    dias: int = analytics_store.DIAS_DEFAULT,
    canal: Optional[str] = None,
    limite: int = analytics_store.TOP_DUDAS_DEFAULT,
):
    """Devuelve métricas agregadas y anónimas de uso del tutor para el ramo."""
    codigo = codigo_ramo.upper()
    if not (BASE_DATA_DIR / codigo / "config.json").exists():
        raise HTTPException(status_code=404, detail="Ramo no encontrado")
    if dias < 1 or dias > analytics_store.DIAS_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"dias debe estar entre 1 y {analytics_store.DIAS_MAX}",
        )
    if canal and canal not in analytics_store.CANALES:
        raise HTTPException(
            status_code=400,
            detail=f"canal debe ser uno de: {', '.join(analytics_store.CANALES)}",
        )
    if limite < 1 or limite > analytics_store.TOP_DUDAS_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"limite debe estar entre 1 y {analytics_store.TOP_DUDAS_MAX}",
        )
    return analytics_store.resumen(codigo, dias=dias, canal=canal, limite=limite)


_ESTILOS_SOCRATICOS = {
    "estricto": (
        "ESTILO DEL DOCENTE (ESTRICTO): responde únicamente con preguntas guía breves y "
        "pistas mínimas para que el estudiante deduzca el razonamiento por sí mismo. "
        "No entregues explicaciones largas ni pasos resueltos."
    ),
    "equilibrado": (
        "ESTILO DEL DOCENTE (EQUILIBRADO): entrega una síntesis conceptual breve cuando "
        "corresponda y acompáñala siempre con 1-2 preguntas guía para verificar comprensión."
    ),
    "paso_a_paso": (
        "ESTILO DEL DOCENTE (PASO A PASO): divide la orientación en pasos progresivos pequeños; "
        "guía solo el paso actual con una pista clara y pregunta al estudiante antes de avanzar."
    ),
}

_EXTENSIONES_SOCRATICAS = {
    "corta": "EXTENSIÓN DE RESPUESTA (CORTA): sé conciso (máximo 1 párrafo breve o 3 viñetas y 1 pregunta).",
    "media": "EXTENSIÓN DE RESPUESTA (MEDIA): desarrolla una guía clara y estructurada de 1 a 2 párrafos breves con 1-2 preguntas.",
}


def _obtener_config_socratica(datos_ramo: Dict[str, Any]) -> Dict[str, str]:
    cfg = datos_ramo.get("config_socratica") or {}
    estilo = cfg.get("estilo", "equilibrado")
    if estilo not in _ESTILOS_SOCRATICOS:
        estilo = "equilibrado"
    extension = cfg.get("extension", "media")
    if extension not in _EXTENSIONES_SOCRATICAS:
        extension = "media"
    return {
        "reglas_socraticas": str(datos_ramo.get("reglas_socraticas", "") or ""),
        "estilo": estilo,
        "extension": extension,
    }


@app.get("/api/ramos/{codigo_ramo}/config_socratica")
def obtener_config_socratica_ramo(codigo_ramo: str):
    """Devuelve la configuración socrática editable del ramo."""
    codigo = codigo_ramo.upper()
    ruta_config = BASE_DATA_DIR / codigo / "config.json"
    if not ruta_config.exists():
        raise HTTPException(status_code=404, detail="Ramo no encontrado")
    with open(ruta_config, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)
    return {"codigo_ramo": codigo, **_obtener_config_socratica(datos)}


@app.put("/api/ramos/{codigo_ramo}/config_socratica")
def actualizar_config_socratica_ramo(codigo_ramo: str, req: ConfigSocraticaReq):
    """Actualiza de forma atómica reglas_socraticas y config_socratica en config.json."""
    codigo = codigo_ramo.upper()
    ruta_config = BASE_DATA_DIR / codigo / "config.json"

    with router_jeff._CONFIG_LOCK:
        if not ruta_config.exists():
            raise HTTPException(status_code=404, detail="Ramo no encontrado")
        with open(ruta_config, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)

        datos["reglas_socraticas"] = req.reglas_socraticas.strip()
        datos["config_socratica"] = {
            "estilo": req.estilo,
            "extension": req.extension,
        }

        ruta_tmp = ruta_config.with_suffix(".json.tmp")
        with open(ruta_tmp, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=2)
        os.replace(ruta_tmp, ruta_config)

    return {
        "status": "ok",
        "codigo_ramo": codigo,
        "reglas_socraticas": datos["reglas_socraticas"],
        "estilo": req.estilo,
        "extension": req.extension,
    }


@app.get("/api/ramos/{codigo_ramo}/config_fallback")
def obtener_config_fallback_ramo(codigo_ramo: str):
    """Devuelve la configuración editable de fallback estricto del ramo."""
    codigo = codigo_ramo.upper()
    ruta_config = BASE_DATA_DIR / codigo / "config.json"
    if not ruta_config.exists():
        raise HTTPException(status_code=404, detail="Ramo no encontrado")
    with open(ruta_config, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)
    return {"codigo_ramo": codigo, **_obtener_config_fallback(datos, codigo)}


@app.put("/api/ramos/{codigo_ramo}/config_fallback")
def actualizar_config_fallback_ramo(codigo_ramo: str, req: ConfigFallbackReq):
    """Actualiza de forma atómica config_fallback en config.json."""
    codigo = codigo_ramo.upper()
    ruta_config = BASE_DATA_DIR / codigo / "config.json"

    with router_jeff._CONFIG_LOCK:
        if not ruta_config.exists():
            raise HTTPException(status_code=404, detail="Ramo no encontrado")
        with open(ruta_config, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)

        actual = _obtener_config_fallback(datos, codigo)

        def texto(nuevo: Optional[str], clave: str) -> str:
            if nuevo is None:
                return actual[clave]
            return nuevo.strip() or _obtener_config_fallback({}, codigo)[clave]

        datos["config_fallback"] = {
            "habilitado": bool(req.habilitado) if req.habilitado is not None else actual["habilitado"],
            "permitir_escalar_profesor": bool(req.permitir_escalar_profesor)
            if req.permitir_escalar_profesor is not None
            else actual["permitir_escalar_profesor"],
            "mensaje_sin_respaldo": texto(req.mensaje_sin_respaldo, "mensaje_sin_respaldo"),
            "mensaje_fuera_de_foco": texto(req.mensaje_fuera_de_foco, "mensaje_fuera_de_foco"),
            "canal_alternativo": (req.canal_alternativo or "").strip()
            if req.canal_alternativo is not None
            else actual["canal_alternativo"],
        }
        router_jeff._guardar_config_atomico(ruta_config, datos)

    return {"status": "ok", "codigo_ramo": codigo, **datos["config_fallback"]}


def _sse(evento: Dict[str, Any]) -> str:
    return f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"


def _fragmentos_token(texto: str):
    palabras = texto.split(" ")
    for indice, palabra in enumerate(palabras):
        yield palabra if indice == 0 else f" {palabra}"


async def _respuesta_fija(
    texto: str,
    modo: str,
    con_contexto: bool,
    canal: str = "TUTOR_SOCRATICO",
    **extra: Any,
) -> AsyncIterator[str]:
    """Emite una respuesta determinista por SSE, sin llamar al LLM."""
    yield _sse({
        "tipo": "inicio",
        "canal": canal,
        "modo": modo,
        "con_contexto": con_contexto,
        **extra,
    })
    for fragmento in _fragmentos_token(texto):
        yield _sse({"tipo": "token", "contenido": fragmento})
        await asyncio.sleep(0.02)
    yield _sse({"tipo": "fin", "canal": canal, **extra})


def _obtener_config_fallback(datos_ramo: Dict[str, Any], codigo: str) -> Dict[str, Any]:
    """Obtiene la configuración de fallback estricto del ramo con valores por defecto seguros."""
    cfg = datos_ramo.get("config_fallback") or {}
    return {
        "habilitado": bool(cfg.get("habilitado", True)),
        "permitir_escalar_profesor": bool(cfg.get("permitir_escalar_profesor", True)),
        "mensaje_sin_respaldo": cfg.get("mensaje_sin_respaldo")
        or (
            f"No encontré respaldo suficiente en los apuntes oficiales ni en la información "
            f"administrativa de {codigo} para responder con certeza. Si quieres, puedes enviar "
            f"esta pregunta al profesor para que la revise."
        ),
        "mensaje_fuera_de_foco": cfg.get("mensaje_fuera_de_foco")
        or (
            f"Esa consulta parece estar fuera del foco del ramo {codigo}. "
            "Este tutor responde únicamente con base en los contenidos oficiales del curso. "
            "Si crees que sí está relacionada con la asignatura, puedes enviarla al profesor."
        ),
        "canal_alternativo": cfg.get("canal_alternativo", ""),
    }


def _texto_con_canal_alternativo(texto: str, cfg: Dict[str, Any]) -> str:
    """Anexa el canal alternativo configurable a las respuestas FALLBACK_DOCENTE."""
    canal = str(cfg.get("canal_alternativo") or "").strip()
    if not canal:
        return texto
    return f"{texto}\n\nPuedes consultar también por {canal}."


def _pista_calculo(mensaje: str) -> str:
    """Primera pista socrática para un cálculo directo, sin entregar el resultado."""
    texto = router_jeff.normalizar(mensaje)
    if "mascara" in texto or "subred" in texto:
        return (
            "Para la máscara de subred, el primer paso es identificar cuántos bits de red y "
            "de host tiene el prefijo. ¿Cuántos bits de host quedan en un /24?"
        )
    if "integral" in texto:
        return (
            "Para la integral, el primer paso es identificar el método o la parametrización. "
            "¿Qué método crees que conviene y por qué?"
        )
    if "derivada" in texto:
        return (
            "Para la derivada, el primer paso es identificar la regla de derivación. "
            "¿Qué regla aplicarías primero?"
        )
    if "area" in texto or "perimetro" in texto or "volumen" in texto:
        return (
            "Para el cálculo geométrico, el primer paso es identificar la fórmula y los datos "
            "que tienes. ¿Qué fórmula crees que corresponde y por qué?"
        )
    return (
        "Vamos paso a paso. No te daré el resultado directo: quiero que lo construyas tú. "
        "¿Cuál crees que es el primer paso y qué datos tienes? Si escribes tu intento, te doy una pista."
    )


def _obtener_temario(codigo_ramo: str, limite: int = 12) -> List[str]:
    """Lista los temas del ramo a partir de los títulos de sus documentos."""
    dir_documentos = BASE_DATA_DIR / codigo_ramo.upper() / "documentos"
    if not dir_documentos.exists():
        return []

    temas: List[str] = []
    archivos = sorted(
        archivo
        for archivo in dir_documentos.rglob("*")
        if archivo.is_file()
        and archivo.suffix.lower() in rag_engine.EXTENSIONES_INDEXABLES
        and not any(parte.startswith(".") for parte in archivo.relative_to(dir_documentos).parts)
    )
    for archivo in archivos:
        nombre = re.sub(
            r"^[A-Z]{2,}\d+\s*N\d+\s*-\s*",
            "",
            archivo.stem,
            flags=re.IGNORECASE,
        )
        temas.append(nombre.replace("_", " ").strip())
    return temas[:limite]


def _construir_system_prompt(
    datos_ramo: Dict[str, Any],
    codigo_ramo: str,
    contexto: str,
    modo: str = "general",
    es_resumen: bool = False,
) -> str:
    nombre = datos_ramo.get("nombre", codigo_ramo)
    cfg_socratica = _obtener_config_socratica(datos_ramo)
    reglas = cfg_socratica["reglas_socraticas"]
    estilo_docente = _ESTILOS_SOCRATICOS[cfg_socratica["estilo"]]
    extension_docente = _EXTENSIONES_SOCRATICAS[cfg_socratica["extension"]]
    temario = _obtener_temario(codigo_ramo)

    prompt = (
        f"Eres LuzAI, tutor socrático institucional de la Universidad Técnica Federico Santa María "
        f"para la asignatura {codigo_ramo} ({nombre}).\n\n"
        "PRINCIPIO GENERAL: ayuda a aprender, no a copiar. En ejercicios, laboratorios, cálculos "
        "y configuraciones, guía con preguntas y pistas progresivas sin entregar la solución "
        "completa. En consultas conceptuales, sí puedes explicar y resumir: una explicación breve "
        "no es una solución.\n"
        f"{estilo_docente}\n"
        f"{extension_docente}\n"
    )
    if reglas:
        prompt += f"REGLAS DEL RAMO: {reglas}\n"

    prompt += (
        "\nALCANCE: responde solo consultas relacionadas con los contenidos del ramo. Si la "
        "consulta es de cultura general o de otra asignatura, no la respondas: indica en una "
        "frase que está fuera de foco y ofrece volver al temario del ramo.\n"
    )

    if contexto:
        prompt += (
            "\nCONTEXTO OFICIAL recuperado de los apuntes del profesor. Úsalo como fuente técnica "
            "principal. Si el contexto no alcanza para un detalle específico, dilo; no inventes "
            "datos del curso:\n"
            f"{contexto}\n"
        )
    else:
        prompt += (
            "\nNo se recuperó contexto de apuntes para esta consulta. No inventes datos "
            "específicos del ramo (fechas, normas, configuraciones exactas). Si la consulta es "
            "conceptual, puedes dar una orientación general breve y aclarar que no proviene de "
            "los apuntes; si es procedimental, pide los antecedentes necesarios.\n"
        )

    if temario:
        prompt += (
            "\nTEMARIO DEL RAMO (según los apuntes disponibles):\n"
            + "\n".join(f"- {tema}" for tema in temario)
            + "\nUsa este temario para orientar resúmenes amplios y para decir qué temas cubre "
              "el ramo. No inventes temas que no aparezcan aquí.\n"
        )

    if modo == "conceptual":
        prompt += (
            "\nMODO CONCEPTUAL/DESCRIPTIVO:\n"
            "- El alumno pide una definición, explicación, resumen o comparación. Entrega primero "
            "una síntesis breve y clara (3-6 frases o 3-5 viñetas) usando el contexto y el temario.\n"
            "- Sí puedes definir, explicar y dar intuición; eso no es resolver una tarea. No "
            "entregues desarrollos completos de ejercicios, resultados finales ni configuraciones "
            "listas para copiar.\n"
            "- Después de la síntesis, formula 1-2 preguntas para verificar comprensión o conectar "
            "con un ejemplo del ramo. Termina siempre con esas preguntas.\n"
            "- Si el alumno pide un resumen amplio, recorre el TEMARIO y menciona cada tema en una "
            "viñeta breve. No agregues protocolos o temas que no estén en el temario; no respondas "
            "solo con preguntas.\n"
        )
        if es_resumen and temario:
            prompt += (
                "- El alumno pidió un resumen. Recorre EXACTAMENTE estos temas, uno por viñeta, "
                "en este orden: " + "; ".join(temario) + ". No agregues protocolos ni temas "
                "fuera de esa lista. Termina con 1-2 preguntas.\n"
            )
    elif modo == "procedimental":
        prompt += (
            "\nMODO PROCEDIMENTAL/EJERCICIO:\n"
            "- El alumno pide calcular, resolver, configurar o implementar. No entregues la "
            "solución completa, el resultado final, el comando completo ni la configuración lista.\n"
            "- El contexto puede contener soluciones, comandos o configuraciones completas. NO los "
            "copies ni los transcribas; úsalos solo para identificar qué pasos existen.\n"
            "- PROHIBIDO escribir comandos de configuración completos, bloques de configuración o "
            "resultados finales, incluso si aparecen en el contexto. Si el alumno pide un comando, "
            "responde con una pregunta que lo ayude a deducirlo o con el nombre del paso.\n"
            "- Ejemplo PROHIBIDO: entregar una secuencia de comandos o el resultado numérico final. "
            "En su lugar, pregunta por el primer paso o por el concepto que falta.\n"
            "- Guía con preguntas, pistas progresivas y pasos de razonamiento. Puedes explicar el "
            "concepto necesario para el paso actual.\n"
        )
    else:
        prompt += (
            "\nMODO GENERAL:\n"
            "- Si la consulta es conceptual, explica de forma breve y luego pregunta. Si es "
            "procedimental, guía sin resolver. Si no está clara, pide una aclaración.\n"
        )

    prompt += (
        "\nFUERA DE FOCO:\n"
        "- Si la consulta no tiene relación con el ramo o con el temario, dilo brevemente y "
        "redirige a los temas del curso. No respondas en profundidad temas ajenos.\n"
    )

    prompt += (
        "\nFORMATO OBLIGATORIO DE SALIDA (Markdown + LaTeX):\n"
        "- Responde SIEMPRE en Markdown: usa '##' para secciones, listas con '-', negritas con "
        "**texto** y tablas cuando aporten.\n"
        "- TODA variable, expresión o ecuación matemática debe ir en LaTeX: inline entre $...$ y "
        "desplegada entre $$...$$. Esto incluye pistas y preguntas socráticas.\n"
        "- Usa únicamente $...$ y $$...$$; no uses \\(...\\) ni \\[...\\].\n"
        "- No uses HTML crudo ni etiquetas como <sup>; usa LaTeX para matemáticas. No uses "
        "Markdown de énfasis (_..._) para fórmulas.\n"
        "- Para una ecuación en bloque usa exactamente $$...$$ en líneas separadas; nunca la "
        "envuelvas en _..._. Ejemplo: $$a = b + c$$\n"
        "- Los comandos de consola, si aparecen en una pista, van en bloques de código con triple "
        "backtick; nunca en LaTeX.\n"
        "- No copies enlaces de imágenes ni artefactos de conversión del contexto.\n"
        "- Ejemplo solo de formato (no de contenido): '## Tema. La relación $a = b + c$ indica "
        "que $a$ depende de $b$ y $c$. ¿Qué ocurre con $a$ si $b$ aumenta?'\n"
        "- REGLA FINAL: revisa que toda fórmula esté entre $...$ o $$...$$; no uses _..._ ni "
        "<sup>. Mantén el enfoque pedagógico y no entregues la solución completa.\n"
    )

    if modo == "procedimental":
        prompt += (
            "\nRECORDATORIO FINAL PARA MODO PROCEDIMENTAL:\n"
            "- No entregues el resultado final, la máscara, la integral resuelta, la tabla, "
            "la configuración ni el comando final.\n"
            "- Da como máximo el primer paso y termina con una pregunta.\n"
            "- INCORRECTO: 'El resultado final es X.'\n"
            "- CORRECTO: 'El primer paso es identificar los datos. ¿Qué dato tienes y cuál falta?'\n"
        )

    return prompt


def _reindexar_ramos_pendientes() -> None:
    """Indexa automáticamente ramos con PDFs que aún no tienen vectores."""
    if not AUTO_REINDEX:
        logger.info("Reindexación automática deshabilitada (RAG_AUTO_REINDEX=0).")
        return

    if not BASE_DATA_DIR.exists():
        return

    logger.info("Revisando ramos para reindexación automática...")
    for dir_ramo in sorted(BASE_DATA_DIR.iterdir()):
        if not dir_ramo.is_dir():
            continue
        if not (dir_ramo / "config.json").exists():
            continue

        codigo = dir_ramo.name.upper()
        dir_documentos = dir_ramo / "documentos"
        if not dir_documentos.exists():
            continue

        archivos = sorted(
            archivo
            for archivo in dir_documentos.rglob("*")
            if archivo.is_file()
            and archivo.suffix.lower() in rag_engine.EXTENSIONES_INDEXABLES
            and not any(parte.startswith(".") for parte in archivo.relative_to(dir_documentos).parts)
        )
        if not archivos:
            continue

        try:
            pendientes = []
            for archivo in archivos:
                carpeta = (
                    archivo.parent.relative_to(dir_documentos).as_posix()
                    if archivo.parent != dir_documentos
                    else "General"
                )
                if not rag_engine.esta_indexado(archivo.name, codigo, carpeta):
                    pendientes.append(archivo.name)

            if not pendientes:
                logger.info("RAG %s al día (%d archivos).", codigo, len(archivos))
                continue

            logger.info(
                "Reindexando %s automáticamente: %d PDF(s) pendientes.",
                codigo,
                len(pendientes),
            )
            resultado = rag_engine.reindexar_ramo(codigo)
            logger.info("Reindexación automática de %s: %s", codigo, resultado)
        except Exception as exc:
            logger.error("Falló la reindexación automática de %s: %s", codigo, exc)

    logger.info("Revisión de reindexación automática finalizada.")


@app.on_event("startup")
def iniciar_reindexacion_automatica() -> None:
    if not AUTO_REINDEX:
        return
    hilo = threading.Thread(target=_reindexar_ramos_pendientes, daemon=True)
    hilo.start()


MAX_HISTORIAL_MENSAJES = 6
MAX_HISTORIAL_CHARS = 800


def _limpiar_historial(historial: List[MensajeHistorial]) -> List[Dict[str, str]]:
    """Conserva una ventana deslizante corta (últimos 6 mensajes) para cuidar VRAM y latencia."""
    limpios: List[Dict[str, str]] = []
    for item in (historial or [])[-MAX_HISTORIAL_MENSAJES:]:
        contenido = (item.contenido or "").strip()
        if not contenido:
            continue
        if len(contenido) > MAX_HISTORIAL_CHARS:
            contenido = contenido[:MAX_HISTORIAL_CHARS] + "..."
        limpios.append({"role": item.rol, "content": contenido})
    return limpios


_PATRON_ADMIN_O_EVALUACION = re.compile(
    r"\b(presentacion|diapositiva|diapositivas|certamen|prueba|examen|control|tarea|"
    r"informe|laboratorio|rubrica|nota|notas|calificacion|plazo|fecha|hora|horario|"
    r"sala|ayudantia|profesor|docente|recuperativa|evaluacion|asistencia|ponderacion|porcentaje)\b"
)


def _es_consulta_admin_o_evaluacion(mensaje: str) -> bool:
    return bool(_PATRON_ADMIN_O_EVALUACION.search(router_jeff.normalizar(mensaje)))


def _detectar_fuera_de_foco_en_respuesta(texto_inicio: str) -> bool:
    """Detecta si el LLM inició su respuesta declarando que la consulta está fuera de foco."""
    norm = router_jeff.normalizar(texto_inicio).lstrip("#*-:>• ").strip()
    return (
        norm.startswith("fuera de foco")
        or norm.startswith("esta consulta parece estar fuera del foco")
        or norm.startswith("esta consulta esta fuera de foco")
        or norm.startswith("la consulta no esta relacionada con el temario")
    )


def _construir_consulta_contextual(
    mensaje: str,
    historial_limpio: List[Dict[str, str]],
    temario: List[str],
) -> str:
    """
    Si el mensaje es un seguimiento corto sin tema explícito (ej. '¿qué ventajas ofrece?'),
    lo combina con la última pregunta del alumno del historial para RAG y alcance ($0 GPU).
    No combina consultas administrativas/evaluativas para no contaminarlas con el tema previo.
    """
    if (
        router_modo.es_saludo(mensaje)
        or router_modo.menciona_tema_del_ramo(mensaje, temario)
        or _es_consulta_admin_o_evaluacion(mensaje)
    ):
        return mensaje

    if len(mensaje.split()) > 6:
        return mensaje

    ultimo_user: Optional[str] = None
    for item in reversed(historial_limpio):
        if item["role"] != "user":
            continue
        if ultimo_user is None:
            ultimo_user = item["content"]
        if router_modo.menciona_tema_del_ramo(item["content"], temario):
            return f"{item['content']} {mensaje}"

    if ultimo_user:
        return f"{ultimo_user} {mensaje}"

    return mensaje


async def _eventos_ollama(
    system_prompt: str,
    mensaje: str,
    historial_limpio: Optional[List[Dict[str, str]]] = None,
) -> AsyncIterator[Dict[str, Any]]:
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if historial_limpio:
        messages.extend(historial_limpio)
    messages.append({"role": "user", "content": mensaje})

    payload = {
        "model": OLLAMA_LLM_MODEL,
        "messages": messages,
        "stream": True,
        "think": OLLAMA_THINK,
        "options": {"temperature": 0.2, "num_ctx": OLLAMA_NUM_CTX},
    }

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{OLLAMA_HOST}/api/chat", json=payload) as respuesta:
                if respuesta.status_code != 200:
                    detalle = (await respuesta.aread()).decode("utf-8", errors="replace")
                    logger.error("Ollama respondió %s: %s", respuesta.status_code, detalle[:300])
                    yield {
                        "tipo": "token",
                        "contenido": (
                            "⚠️ El modelo de lenguaje no está disponible en Ollama. "
                            f"Verifica `ollama pull {OLLAMA_LLM_MODEL}` y que el servicio esté activo."
                        ),
                    }
                    return

                async for linea in respuesta.aiter_lines():
                    if not linea.strip():
                        continue
                    try:
                        evento = json.loads(linea)
                    except json.JSONDecodeError:
                        continue

                    contenido = (evento.get("message") or {}).get("content")
                    if contenido:
                        yield {"tipo": "token", "contenido": contenido}
                    if evento.get("done"):
                        break
    except httpx.HTTPError as exc:
        logger.error("Error conectando con Ollama: %s", exc)
        yield {
            "tipo": "token",
            "contenido": (
                "⚠️ No pude conectar con Ollama. Revisa que esté corriendo en "
                f"{OLLAMA_HOST} (o la variable OLLAMA_HOST en Docker)."
            ),
        }


def _construir_prompt_informativo_planificacion(
    datos_ramo: Dict[str, Any],
    codigo: str,
    contexto: str,
) -> str:
    nombre = datos_ramo.get("nombre", codigo)
    return (
        f"Eres el asistente administrativo oficial de {codigo} ({nombre}) en la Universidad Técnica Federico Santa María.\n"
        "Responde en español de forma DIRECTA, CLARA y CONCISA a la consulta administrativa o de planificación del estudiante.\n"
        "REGLAS ESTRICTAS:\n"
        "- Entrega los datos exactos (fechas por paralelo 200/201, clase, tema, laboratorio y evaluación) usando ÚNICAMENTE la información del contexto.\n"
        "- NO apliques estilo socrático ni hagas preguntas de vuelta para retener información administrativa.\n"
        "- No inventes fechas ni contenidos que no aparezcan en el contexto. Si el dato no figura, indícalo brevemente.\n\n"
        f"CONTEXTO DE PLANIFICACIÓN Y FAQS:\n{contexto}"
    )


def _registrar_analitica_evento(
    codigo: str,
    mensaje: str,
    canal: str,
    modo: Optional[str] = None,
    topico: Optional[str] = None,
    categoria: Optional[str] = None,
    motivo: Optional[str] = None,
    con_contexto: Optional[bool] = None,
    score: Optional[float] = None,
    inicio: Optional[float] = None,
    error: bool = False,
) -> None:
    """Registra un evento sin romper el chat si falla la escritura de analítica."""
    duracion_ms = (
        int((time.perf_counter() - inicio) * 1000) if inicio is not None else None
    )
    try:
        analytics_store.registrar_evento(
            codigo_ramo=codigo,
            pregunta=mensaje,
            canal=canal,
            modo=modo,
            topico=topico,
            categoria=categoria,
            motivo=motivo,
            con_contexto=con_contexto,
            score=score,
            duracion_ms=duracion_ms,
            error=error,
        )
    except Exception as exc:
        logger.warning("No se pudo registrar analítica de %s: %s", codigo, exc)


@app.post("/api/chat")
async def chat(consulta: ConsultaChat):
    """
    Flujo: Jeff (administrativo, $0 GPU) -> RAG (contexto de apuntes) -> Ollama (tutor socrático).
    """
    codigo = consulta.codigo_ramo.upper()
    ruta_config = BASE_DATA_DIR / codigo / "config.json"
    if not ruta_config.exists():
        raise HTTPException(status_code=404, detail="Ramo no encontrado")

    with open(ruta_config, "r", encoding="utf-8") as f:
        datos_ramo = json.load(f)

    inicio_chat = time.perf_counter()
    historial_limpio = _limpiar_historial(consulta.historial)

    # 1. Jeff responde dudas administrativas sin tocar la GPU.
    jeff = router_jeff.resolver_consulta(consulta.mensaje, codigo, historial=historial_limpio)
    if jeff:
        _registrar_analitica_evento(
            codigo,
            consulta.mensaje,
            canal="JEFF_ADMIN",
            modo="administrativo",
            topico=jeff.get("topico"),
            categoria=jeff.get("categoria"),
            con_contexto=False,
            score=jeff.get("puntaje"),
            inicio=inicio_chat,
        )

        async def generador_jeff():
            for fragmento in _fragmentos_token(jeff["respuesta"]):
                yield _sse({"tipo": "token", "contenido": fragmento})
                await asyncio.sleep(0.02)
            evento_fin: Dict[str, Any] = {
                "tipo": "fin",
                "canal": "JEFF_ADMIN",
                "topico": jeff.get("topico"),
                "categoria": jeff.get("categoria"),
            }
            if jeff.get("sugerencias"):
                evento_fin["sugerencias"] = jeff["sugerencias"]
            yield _sse(evento_fin)

        return StreamingResponse(generador_jeff(), media_type="text/event-stream")

    modo = router_modo.detectar_modo(consulta.mensaje)
    es_resumen = router_modo.es_solicitud_resumen(consulta.mensaje)
    es_seguimiento_plan = (
        bool(historial_limpio)
        and len(consulta.mensaje.split()) <= 8
        and (
            "[Jeff - Planificación" in (
                historial_limpio[-1].get("content") or historial_limpio[-1].get("contenido") or ""
            )
            or "Documento de planificación:" in (
                historial_limpio[-1].get("content") or historial_limpio[-1].get("contenido") or ""
            )
        )
        and not router_modo.es_saludo(consulta.mensaje)
    )
    es_admin_plan = router_modo.es_consulta_administrativa_o_planificacion(consulta.mensaje) or es_seguimiento_plan
    temario = _obtener_temario(codigo)
    consulta_contextual = _construir_consulta_contextual(
        consulta.mensaje, historial_limpio, temario
    )

    # 2. RAG informativo para consultas administrativas / de planificación:
    # busca en Planificacion/ + faqs_jeff y adjunta el enlace directo al documento original.
    if es_admin_plan:
        try:
            fragmentos_plan = await asyncio.to_thread(
                rag_engine.buscar_fragmentos_planificacion, consulta_contextual, codigo
            )
        except Exception as exc:
            logger.error("Falló la recuperación RAG de planificación para %s: %s", codigo, exc)
            fragmentos_plan = []

        docs_plan = router_jeff.listar_documentos_planificacion(codigo)
        contexto_plan = rag_engine.formatear_contexto(fragmentos_plan)
        score_plan = max(
            (f.get("score") or 0.0 for f in fragmentos_plan), default=None
        )

        # Identificar enlaces relevantes (los documentos citados por RAG o todos los de Planificacion/)
        archivos_citados = {f.get("archivo") for f in fragmentos_plan if f.get("archivo")}
        docs_relevantes = [d for d in docs_plan if d["nombre"] in archivos_citados] or docs_plan

        if contexto_plan:
            logger.info("Chat %s canal RAG informativo de planificación (frags=%d)", codigo, len(fragmentos_plan))
            system_prompt_plan = _construir_prompt_informativo_planificacion(
                datos_ramo, codigo, contexto_plan
            )
            bloque_enlaces = ""
            if docs_relevantes:
                enlaces_md = " · ".join(
                    f"[{d['etiqueta']} ({d['nombre']})]({d['url']})" for d in docs_relevantes
                )
                bloque_enlaces = f"\n\n---\nDocumento de planificación: {enlaces_md}"

            async def generador_plan_rag():
                try:
                    yield _sse({
                        "tipo": "inicio",
                        "canal": "JEFF_ADMIN",
                        "modo": "informativo",
                        "con_contexto": True,
                    })
                    async for evento in _eventos_ollama(
                        system_prompt_plan, consulta.mensaje, historial_limpio
                    ):
                        yield _sse(evento)
                    if bloque_enlaces:
                        yield _sse({"tipo": "token", "contenido": bloque_enlaces})
                    yield _sse({"tipo": "fin", "canal": "JEFF_ADMIN", "categoria": "Planificación del Curso"})
                finally:
                    _registrar_analitica_evento(
                        codigo,
                        consulta.mensaje,
                        canal="JEFF_ADMIN",
                        modo="informativo",
                        topico="planificacion",
                        categoria="Planificación del Curso",
                        con_contexto=True,
                        score=score_plan,
                        inicio=inicio_chat,
                    )

            return StreamingResponse(generador_plan_rag(), media_type="text/event-stream")

        if docs_plan:
            enlaces_md = "\n".join(
                f"- [{d['etiqueta']} ({d['nombre']})]({d['url']})" for d in docs_plan
            )
            texto_docs = (
                f"[Jeff - Planificación {codigo}]: Puedes revisar la planificación oficial "
                f"directamente en:\n\n{enlaces_md}"
            )
            _registrar_analitica_evento(
                codigo,
                consulta.mensaje,
                canal="JEFF_ADMIN",
                modo="informativo",
                topico="planificacion",
                categoria="Planificación del Curso",
                con_contexto=False,
                motivo="enlaces_planificacion",
                inicio=inicio_chat,
            )
            return StreamingResponse(
                _respuesta_fija(
                    texto_docs,
                    "informativo",
                    False,
                    canal="JEFF_ADMIN",
                ),
                media_type="text/event-stream",
            )

    # 2b. RAG general: recupera contexto de los apuntes (en hilo aparte para no bloquear el event loop).
    try:
        fragmentos = await asyncio.to_thread(
            rag_engine.buscar_fragmentos_relevantes, consulta_contextual, codigo
        )
    except Exception as exc:
        logger.error("Falló la recuperación RAG para %s: %s", codigo, exc)
        fragmentos = []

    contexto = rag_engine.formatear_contexto(fragmentos)
    max_score = max(
        (fragmento.get("score") or 0.0 for fragmento in fragmentos), default=0.0
    )

    # 2b. Guard de cálculo directo: entrega una pista inicial, nunca el resultado.
    if modo == "procedimental" and router_modo.es_calculo_directo(consulta.mensaje):
        pista = _pista_calculo(consulta.mensaje)
        logger.info("Chat %s cálculo directo: pista forzada", codigo)
        _registrar_analitica_evento(
            codigo,
            consulta.mensaje,
            canal="TUTOR_SOCRATICO",
            modo=modo,
            motivo="calculo_directo",
            con_contexto=bool(contexto),
            score=max_score,
            inicio=inicio_chat,
        )
        return StreamingResponse(
            _respuesta_fija(pista, modo, bool(contexto), pista_forzada=True),
            media_type="text/event-stream",
        )

    # 2c. Guard de fallback estricto ($0 GPU): evita llamar al LLM fuera de foco o sin respaldo RAG.
    cfg_fallback = _obtener_config_fallback(datos_ramo, codigo)
    es_saludo = router_modo.es_saludo(consulta.mensaje)
    fuera_de_foco = (
        not es_saludo
        and not router_modo.menciona_tema_del_ramo(consulta_contextual, temario)
        and max_score < RAG_OFFTOPIC_SCORE
    )
    if fuera_de_foco:
        if cfg_fallback["habilitado"]:
            texto_fuera = _texto_con_canal_alternativo(
                cfg_fallback["mensaje_fuera_de_foco"], cfg_fallback
            )
            logger.info(
                "Chat %s FALLBACK_DOCENTE fuera de foco (modo=%s score=%.3f)",
                codigo,
                modo,
                max_score,
            )
            _registrar_analitica_evento(
                codigo,
                consulta.mensaje,
                canal="FALLBACK_DOCENTE",
                modo=modo,
                motivo="fuera_de_foco",
                con_contexto=bool(contexto),
                score=max_score,
                inicio=inicio_chat,
            )
            return StreamingResponse(
                _respuesta_fija(
                    texto_fuera,
                    modo,
                    bool(contexto),
                    canal="FALLBACK_DOCENTE",
                    puede_escalar=cfg_fallback["permitir_escalar_profesor"],
                    motivo="fuera_de_foco",
                    fuera_de_foco=True,
                ),
                media_type="text/event-stream",
            )
        texto_fuera = (
            f"Esa consulta parece estar fuera del foco del ramo {codigo}. "
            "Este tutor está para ayudarte con los contenidos del curso. "
            "¿Quieres que repasemos algún tema del temario?"
        )
        logger.info(
            "Chat %s fuera de foco (modo=%s score=%.3f)", codigo, modo, max_score
        )
        _registrar_analitica_evento(
            codigo,
            consulta.mensaje,
            canal="TUTOR_SOCRATICO",
            modo=modo,
            motivo="fuera_de_foco_sin_config",
            con_contexto=bool(contexto),
            score=max_score,
            inicio=inicio_chat,
        )
        return StreamingResponse(
            _respuesta_fija(texto_fuera, modo, bool(contexto), fuera_de_foco=True),
            media_type="text/event-stream",
        )

    sin_respaldo_rag = (
        cfg_fallback["habilitado"]
        and not es_saludo
        and not es_resumen
        and not bool(contexto)
    )
    if sin_respaldo_rag:
        texto_sin_respaldo = _texto_con_canal_alternativo(
            cfg_fallback["mensaje_sin_respaldo"], cfg_fallback
        )
        logger.info(
            "Chat %s FALLBACK_DOCENTE sin respaldo RAG (modo=%s score=%.3f)",
            codigo,
            modo,
            max_score,
        )
        _registrar_analitica_evento(
            codigo,
            consulta.mensaje,
            canal="FALLBACK_DOCENTE",
            modo=modo,
            motivo="sin_respaldo_rag",
            con_contexto=False,
            score=max_score,
            inicio=inicio_chat,
        )
        return StreamingResponse(
            _respuesta_fija(
                texto_sin_respaldo,
                modo,
                False,
                canal="FALLBACK_DOCENTE",
                puede_escalar=cfg_fallback["permitir_escalar_profesor"],
                motivo="sin_respaldo_rag",
            ),
            media_type="text/event-stream",
        )

    logger.info(
        "Chat %s modo=%s resumen=%s con_contexto=%s score=%.3f",
        codigo,
        modo,
        es_resumen,
        bool(contexto),
        max_score,
    )
    system_prompt = _construir_system_prompt(
        datos_ramo, codigo, contexto, modo, es_resumen
    )

    # 3. Tutor socrático con streaming.
    async def generador_ollama():
        canal_final = "TUTOR_SOCRATICO"
        motivo_final: Optional[str] = None
        error_final = False
        try:
            yield _sse({
                "tipo": "inicio",
                "canal": "TUTOR_SOCRATICO",
                "modo": modo,
                "con_contexto": bool(contexto),
            })
            prefijo_respuesta = ""
            async for evento in _eventos_ollama(
                system_prompt, consulta.mensaje, historial_limpio
            ):
                if evento.get("tipo") == "token" and len(prefijo_respuesta) < 120:
                    prefijo_respuesta += str(evento.get("contenido") or "")
                yield _sse(evento)

            if cfg_fallback["habilitado"] and _detectar_fuera_de_foco_en_respuesta(prefijo_respuesta):
                canal_final = "FALLBACK_DOCENTE"
                motivo_final = "fuera_de_foco"
                yield _sse({
                    "tipo": "fin",
                    "canal": "FALLBACK_DOCENTE",
                    "puede_escalar": cfg_fallback["permitir_escalar_profesor"],
                    "motivo": "fuera_de_foco",
                })
            else:
                yield _sse({"tipo": "fin", "canal": "TUTOR_SOCRATICO"})
        except Exception as exc:
            error_final = True
            logger.error("Error en streaming del tutor %s: %s", codigo, exc)
            raise
        finally:
            _registrar_analitica_evento(
                codigo,
                consulta.mensaje,
                canal=canal_final,
                modo=modo,
                motivo=motivo_final,
                con_contexto=bool(contexto),
                score=max_score,
                inicio=inicio_chat,
                error=error_final,
            )

    return StreamingResponse(generador_ollama(), media_type="text/event-stream")
