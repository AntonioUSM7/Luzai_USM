import asyncio
import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import shutil
from datetime import datetime
from pydantic import BaseModel

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
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")


class ConsultaChat(BaseModel):
    codigo_ramo: str
    mensaje: str


class CrearCarpetaReq(BaseModel):
    nombre: str


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
                    ramos.append({
                        "codigo": datos.get("codigo"),
                        "nombre": datos.get("nombre"),
                        "departamento": datos.get("departamento"),
                        "profesor": datos.get("profesor"),
                        "descripcion": datos.get("descripcion"),
                        "documentos": datos.get("documentos", []),
                        "reglas_socraticas": datos.get("reglas_socraticas", ""),
                    })
    return ramos


@app.get("/api/health")
def health():
    return {"status": "ok", "servicio": "LuzAI USM Backend Base"}


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


CARPETAS_POR_DEFECTO = ["Clases", "Tareas", "Guias", "Certamenes"]


def obtener_carpetas_ramo(codigo_ramo: str):
    dir_documentos = BASE_DATA_DIR / codigo_ramo.upper() / "documentos"
    dir_documentos.mkdir(parents=True, exist_ok=True)

    # Asegurar carpetas base
    for def_folder in CARPETAS_POR_DEFECTO:
        (dir_documentos / def_folder).mkdir(parents=True, exist_ok=True)

    carpetas = []
    for item in sorted(dir_documentos.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            carpetas.append(item.name)
    return carpetas


@app.get("/api/ramos/{codigo_ramo}/carpetas")
def listar_carpetas(codigo_ramo: str):
    """Devuelve la lista de carpetas disponibles para un ramo"""
    carpetas = obtener_carpetas_ramo(codigo_ramo)
    return {"codigo_ramo": codigo_ramo.upper(), "carpetas": carpetas}


@app.post("/api/ramos/{codigo_ramo}/carpetas")
def crear_carpeta_ramo(codigo_ramo: str, datos: CrearCarpetaReq):
    """Crea una nueva carpeta personalizada para el ramo"""
    codigo = codigo_ramo.upper()
    nombre_limpio = datos.nombre.strip().replace("/", "_").replace("\\", "_")
    if not nombre_limpio:
        raise HTTPException(status_code=400, detail="El nombre de la carpeta no puede estar vacío")

    dir_nueva = BASE_DATA_DIR / codigo / "documentos" / nombre_limpio
    dir_nueva.mkdir(parents=True, exist_ok=True)
    return {"status": "ok", "nombre": nombre_limpio, "mensaje": f"Carpeta '{nombre_limpio}' creada con éxito."}


@app.get("/api/ramos/{codigo_ramo}/archivos")
def listar_archivos_ramo(codigo_ramo: str):
    """Lista todos los archivos organizados por carpeta para un ramo específico"""
    dir_documentos = BASE_DATA_DIR / codigo_ramo.upper() / "documentos"
    if not dir_documentos.exists():
        raise HTTPException(status_code=404, detail="Carpeta del ramo no encontrada")

    carpetas_existentes = obtener_carpetas_ramo(codigo_ramo)
    archivos = []

    # Recorrer subcarpetas y archivos
    for item in dir_documentos.rglob("*"):
        if item.is_file() and not item.name.startswith("."):
            carpeta_padre = item.parent.name
            if carpeta_padre == "documentos":
                carpeta_padre = "General"

            stats = item.stat()
            fecha_iso = datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M")
            archivos.append({
                "nombre": item.name,
                "carpeta": carpeta_padre,
                "tamano_bytes": stats.st_size,
                "tamano_legible": formatear_tamano(stats.st_size),
                "fecha_modificacion": fecha_iso,
                "indexado_rag": True,
            })

    return {
        "codigo_ramo": codigo_ramo.upper(),
        "carpetas": carpetas_existentes,
        "total": len(archivos),
        "archivos": archivos,
    }


@app.post("/api/ramos/{codigo_ramo}/archivos")
async def subir_archivo_ramo(
    codigo_ramo: str,
    archivo: UploadFile = File(...),
    carpeta: str = Form("Clases"),
):
    """Sube un archivo a la carpeta seleccionada del ramo"""
    codigo = codigo_ramo.upper()
    carpeta_limpia = carpeta.strip().replace("/", "_").replace("\\", "_") or "General"

    dir_destino = BASE_DATA_DIR / codigo / "documentos" / carpeta_limpia
    dir_destino.mkdir(parents=True, exist_ok=True)

    # Limpiar nombre del archivo
    nombre_limpio = Path(archivo.filename).name.replace(" ", "_")
    ruta_archivo = dir_destino / nombre_limpio

    try:
        with open(ruta_archivo, "wb") as f:
            shutil.copyfileobj(archivo.file, f)
    finally:
        await archivo.close()

    stats = ruta_archivo.stat()
    fecha_iso = datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M")

    return {
        "status": "ok",
        "mensaje": f"Archivo '{nombre_limpio}' subido exitosamente a la carpeta '{carpeta_limpia}'.",
        "archivo": {
            "nombre": nombre_limpio,
            "carpeta": carpeta_limpia,
            "tamano_bytes": stats.st_size,
            "tamano_legible": formatear_tamano(stats.st_size),
            "fecha_modificacion": fecha_iso,
            "indexado_rag": True,
        },
    }


@app.delete("/api/ramos/{codigo_ramo}/archivos")
def eliminar_archivo_ramo(codigo_ramo: str, carpeta: str, nombre_archivo: str):
    """Elimina un archivo de la carpeta de un ramo"""
    codigo = codigo_ramo.upper()
    ruta_archivo = BASE_DATA_DIR / codigo / "documentos" / carpeta / nombre_archivo
    if not ruta_archivo.exists():
        raise HTTPException(status_code=404, detail="El archivo no existe")

    ruta_archivo.unlink()
    return {"status": "ok", "mensaje": f"Archivo '{nombre_archivo}' eliminado correctamente."}


@app.delete("/api/ramos/{codigo_ramo}/carpetas")
def eliminar_carpeta_ramo(codigo_ramo: str, nombre_carpeta: str):
    """Elimina una carpeta y todos sus archivos asociados del ramo"""
    codigo = codigo_ramo.upper()
    nombre_limpio = nombre_carpeta.strip().replace("/", "_").replace("\\", "_")
    ruta_carpeta = BASE_DATA_DIR / codigo / "documentos" / nombre_limpio

    if not ruta_carpeta.exists() or not ruta_carpeta.is_dir():
        raise HTTPException(status_code=404, detail="La carpeta no existe")

    shutil.rmtree(ruta_carpeta)
    return {
        "status": "ok",
        "mensaje": f"Carpeta '{nombre_limpio}' y sus archivos fueron eliminados correctamente.",
    }


@app.post("/api/chat")
async def chat(consulta: ConsultaChat):
    """
    Endpoint base de chat. 
    Por ahora devuelve una respuesta básica en streaming para que el frontend funcione.
    (La lógica de Jeff y Ollama la construiremos paso a paso).
    """
    ruta_config = BASE_DATA_DIR / consulta.codigo_ramo.upper() / "config.json"
    if not ruta_config.exists():
        raise HTTPException(status_code=404, detail="Ramo no encontrado")

    with open(ruta_config, "r", encoding="utf-8") as f:
        datos_ramo = json.load(f)

    texto_respuesta = (
        f"Hola, recibí tu consulta para {datos_ramo.get('nombre')}: '{consulta.mensaje}'. "
        f"Este es el endpoint base de respuesta listo para conectar."
    )

    async def generador_stream():
        palabras = texto_respuesta.split(" ")
        for i, palabra in enumerate(palabras):
            chunk = palabra if i == 0 else f" {palabra}"
            yield f"data: {json.dumps({'tipo': 'token', 'contenido': chunk})}\n\n"
            await asyncio.sleep(0.04)
        yield f"data: {json.dumps({'tipo': 'fin'})}\n\n"

    return StreamingResponse(generador_stream(), media_type="text/event-stream")
