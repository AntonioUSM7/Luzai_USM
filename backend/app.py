import asyncio
import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
