import asyncio
import json
import logging
import os
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Dict, Any, List

import httpx
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

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
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:3b")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
AUTO_REINDEX = os.getenv("RAG_AUTO_REINDEX", "1") not in ("0", "false", "False")
RAG_OFFTOPIC_SCORE = float(os.getenv("RAG_OFFTOPIC_SCORE", "0.65"))


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
    codigo = codigo_ramo.upper()
    dir_documentos = BASE_DATA_DIR / codigo / "documentos"
    if not dir_documentos.exists():
        raise HTTPException(status_code=404, detail="Carpeta del ramo no encontrada")

    carpetas_existentes = obtener_carpetas_ramo(codigo)
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
                "indexado_rag": rag_engine.esta_indexado(item.name, codigo, carpeta_padre),
            })

    return {
        "codigo_ramo": codigo,
        "carpetas": carpetas_existentes,
        "total": len(archivos),
        "archivos": archivos,
    }


@app.post("/api/ramos/{codigo_ramo}/archivos")
async def subir_archivo_ramo(
    codigo_ramo: str,
    background_tasks: BackgroundTasks,
    archivo: UploadFile = File(...),
    carpeta: str = Form("Clases"),
):
    """Sube un archivo a la carpeta seleccionada del ramo y lo indexa en background."""
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

    background_tasks.add_task(rag_engine.indexar_documento, ruta_archivo, codigo, carpeta_limpia)

    stats = ruta_archivo.stat()
    fecha_iso = datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M")

    return {
        "status": "ok",
        "mensaje": f"Archivo '{nombre_limpio}' subido exitosamente. Indexación RAG en curso.",
        "archivo": {
            "nombre": nombre_limpio,
            "carpeta": carpeta_limpia,
            "tamano_bytes": stats.st_size,
            "tamano_legible": formatear_tamano(stats.st_size),
            "fecha_modificacion": fecha_iso,
            "indexado_rag": False,
            "estado_indexacion": "pendiente",
        },
    }


@app.delete("/api/ramos/{codigo_ramo}/archivos")
def eliminar_archivo_ramo(codigo_ramo: str, carpeta: str, nombre_archivo: str):
    """Elimina un archivo de la carpeta de un ramo y sus vectores asociados"""
    codigo = codigo_ramo.upper()
    ruta_archivo = BASE_DATA_DIR / codigo / "documentos" / carpeta / nombre_archivo
    if not ruta_archivo.exists():
        raise HTTPException(status_code=404, detail="El archivo no existe")

    ruta_archivo.unlink()
    rag_engine.eliminar_documento_vectorial(nombre_archivo, codigo, carpeta)
    return {"status": "ok", "mensaje": f"Archivo '{nombre_archivo}' eliminado correctamente."}


@app.delete("/api/ramos/{codigo_ramo}/carpetas")
def eliminar_carpeta_ramo(codigo_ramo: str, nombre_carpeta: str):
    """Elimina una carpeta, sus archivos y sus vectores asociados del ramo"""
    codigo = codigo_ramo.upper()
    nombre_limpio = nombre_carpeta.strip().replace("/", "_").replace("\\", "_")
    ruta_carpeta = BASE_DATA_DIR / codigo / "documentos" / nombre_limpio

    if not ruta_carpeta.exists() or not ruta_carpeta.is_dir():
        raise HTTPException(status_code=404, detail="La carpeta no existe")

    shutil.rmtree(ruta_carpeta)
    rag_engine.eliminar_carpeta_vectorial(codigo, nombre_limpio)
    return {
        "status": "ok",
        "mensaje": f"Carpeta '{nombre_limpio}' y sus archivos fueron eliminados correctamente.",
    }


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


def _sse(evento: Dict[str, Any]) -> str:
    return f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"


def _fragmentos_token(texto: str):
    palabras = texto.split(" ")
    for indice, palabra in enumerate(palabras):
        yield palabra if indice == 0 else f" {palabra}"


async def _respuesta_fija(
    texto: str, modo: str, con_contexto: bool, **extra: Any
) -> AsyncIterator[str]:
    """Emite una respuesta determinista por SSE, sin llamar al LLM."""
    yield _sse({
        "tipo": "inicio",
        "canal": "TUTOR_SOCRATICO",
        "modo": modo,
        "con_contexto": con_contexto,
        **extra,
    })
    for fragmento in _fragmentos_token(texto):
        yield _sse({"tipo": "token", "contenido": fragmento})
        await asyncio.sleep(0.02)
    yield _sse({"tipo": "fin", "canal": "TUTOR_SOCRATICO"})


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
    """Lista los temas del ramo a partir de los títulos de sus PDFs."""
    dir_documentos = BASE_DATA_DIR / codigo_ramo.upper() / "documentos"
    if not dir_documentos.exists():
        return []

    temas: List[str] = []
    for pdf in sorted(dir_documentos.rglob("*.pdf")):
        nombre = re.sub(
            r"^[A-Z]{2,}\d+\s*N\d+\s*-\s*",
            "",
            pdf.stem,
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
    reglas = datos_ramo.get("reglas_socraticas", "")
    temario = _obtener_temario(codigo_ramo)

    prompt = (
        f"Eres LuzAI, tutor socrático institucional de la Universidad Técnica Federico Santa María "
        f"para la asignatura {codigo_ramo} ({nombre}).\n\n"
        "PRINCIPIO GENERAL: ayuda a aprender, no a copiar. En ejercicios, laboratorios, cálculos "
        "y configuraciones, guía con preguntas y pistas progresivas sin entregar la solución "
        "completa. En consultas conceptuales, sí puedes explicar y resumir: una explicación breve "
        "no es una solución.\n"
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

        pdfs = sorted(dir_documentos.rglob("*.pdf"))
        if not pdfs:
            continue

        try:
            pendientes = []
            for pdf in pdfs:
                carpeta = pdf.parent.name if pdf.parent != dir_documentos else "General"
                if not rag_engine.esta_indexado(pdf.name, codigo, carpeta):
                    pendientes.append(pdf.name)

            if not pendientes:
                logger.info("RAG %s al día (%d PDFs).", codigo, len(pdfs))
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


async def _eventos_ollama(system_prompt: str, mensaje: str) -> AsyncIterator[Dict[str, Any]]:
    payload = {
        "model": OLLAMA_LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": mensaje},
        ],
        "stream": True,
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

    # 1. Jeff responde dudas administrativas sin tocar la GPU.
    jeff = router_jeff.resolver_consulta(consulta.mensaje, codigo)
    if jeff:
        async def generador_jeff():
            for fragmento in _fragmentos_token(jeff["respuesta"]):
                yield _sse({"tipo": "token", "contenido": fragmento})
                await asyncio.sleep(0.02)
            yield _sse({
                "tipo": "fin",
                "canal": "JEFF_ADMIN",
                "topico": jeff.get("topico"),
                "categoria": jeff.get("categoria"),
            })

        return StreamingResponse(generador_jeff(), media_type="text/event-stream")

    modo = router_modo.detectar_modo(consulta.mensaje)
    es_resumen = router_modo.es_solicitud_resumen(consulta.mensaje)

    # 2. RAG: recupera contexto de los apuntes (en hilo aparte para no bloquear el event loop).
    try:
        fragmentos = await asyncio.to_thread(
            rag_engine.buscar_fragmentos_relevantes, consulta.mensaje, codigo
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
        return StreamingResponse(
            _respuesta_fija(pista, modo, bool(contexto), pista_forzada=True),
            media_type="text/event-stream",
        )

    # 2c. Guard de alcance: evita que el tutor responda trivia fuera del ramo.
    temario = _obtener_temario(codigo)
    fuera_de_foco = (
        not router_modo.es_saludo(consulta.mensaje)
        and not router_modo.menciona_tema_del_ramo(consulta.mensaje, temario)
        and max_score < RAG_OFFTOPIC_SCORE
    )
    if fuera_de_foco:
        texto_fuera = (
            f"Esa consulta parece estar fuera del foco del ramo {codigo}. "
            "Este tutor está para ayudarte con los contenidos del curso. "
            "¿Quieres que repasemos algún tema del temario?"
        )
        logger.info(
            "Chat %s fuera de foco (modo=%s score=%.3f)", codigo, modo, max_score
        )
        return StreamingResponse(
            _respuesta_fija(texto_fuera, modo, bool(contexto), fuera_de_foco=True),
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
        yield _sse({
            "tipo": "inicio",
            "canal": "TUTOR_SOCRATICO",
            "modo": modo,
            "con_contexto": bool(contexto),
        })
        async for evento in _eventos_ollama(system_prompt, consulta.mensaje):
            yield _sse(evento)
        yield _sse({"tipo": "fin", "canal": "TUTOR_SOCRATICO"})

    return StreamingResponse(generador_ollama(), media_type="text/event-stream")
