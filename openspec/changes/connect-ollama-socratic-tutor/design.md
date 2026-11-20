# Design

## Context

- Ver [proposal.md](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/openspec/changes/connect-ollama-socratic-tutor/proposal.md) para la motivación y alcance.
- Actualmente [backend/app.py](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/backend/app.py) ya tiene `httpx==0.27.2` en [backend/requirements.txt](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/backend/requirements.txt) y `OLLAMA_HOST=http://host.docker.internal:11434` en [docker-compose.yml](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/docker-compose.yml).
- El técnico del equipo está desarrollando por separado `router_jeff.py` (enrutamiento administrativo) y `rag_engine.py` (búsqueda vectorial). Este diseño debe permitir avanzar con Ollama + reglas socráticas + UI sin generar conflictos al integrar luego ambos módulos.

## Goals / Non-Goals

**Goals:**
- Conectar `POST /api/chat` con la API `/api/chat` de Ollama en modo streaming (`stream: true`) usando `httpx.AsyncClient` y reemitir tokens en el formato SSE existente (`data: {"tipo": "token", "contenido": ...}\n\n` y `{"tipo": "fin"}`).
- Centralizar el ensamblaje del *System Prompt* socrático (reglas institucionales + guardrails anti-prompt-injection + `reglas_socraticas` del ramo) en un módulo dedicado `backend/socratic_prompt.py`.
- Permitir configurar el modelo vía variable de entorno `OLLAMA_MODEL` (por defecto `qwen3:8b`, compatible con modelos livianos de prueba como `qwen2.5:3b`).
- Habilitar el flujo completo de edición de `reglas_socraticas` en [DocenteView.tsx](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/frontend/src/views/profesor/DocenteView.tsx) y diálogo multi-turno en [ChatWindow.tsx](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/frontend/src/views/alumno/ChatWindow.tsx).

**Non-Goals:**
- Implementar `router_jeff.py` ni `rag_engine.py` (responsabilidad del técnico).
- Implementar la pestaña de Analítica Anónima (`subTab === 'analitica'`) o la pestaña de Configuración de Jeff (`subTab === 'jeff'`).
- Persistir historiales de chat en base de datos o archivos (el historial vive únicamente en memoria de la sesión del navegador).

## Decisions

1. **Usar el endpoint `/api/chat` de Ollama en lugar de `/api/generate`**
   - *Razón*: `/api/chat` recibe nativamente una lista estructurada de mensajes con roles (`system`, `user`, `assistant`), lo que separa limpiamente el *System Prompt* socrático del historial conversacional del estudiante y reduce la superficie de *prompt injection*.
   - *Alternativa descartada*: `/api/generate` con un prompt concatenado manualmente, más propenso a ruptura de delimitadores.

2. **Configuración de modelo vía `OLLAMA_MODEL` (default `qwen3:8b`)**
   - *Razón*: Permite correr `qwen3:8b` (Qwen 3.8 8B) en la máquina host con RTX 5060 y cambiar fácilmente a `qwen2.5:3b` o `qwen2.5:7b` en equipos con menor VRAM sin tocar código.

3. **Punto de extensión desacoplado en `POST /api/chat`**
   - *Razón*: Mantener un comentario/hook claro antes de llamar a Ollama para que, al fusionar la rama del técnico, `router_jeff` intercepte primero y `rag_engine` aporte `contexto_rag: str` al constructor de `socratic_prompt.py`.

4. **Historial acotado en frontend (`ultimos 10 mensajes`)**
   - *Razón*: Evita desbordar la ventana de contexto del LLM y mantiene baja la latencia de inferencia, enviando `historial: Array<{ rol: 'user' | 'assistant', contenido: string }>` en el cuerpo de `POST /api/chat`.

5. **Endpoint dedicado `PUT /api/ramos/{codigo_ramo}/reglas-socraticas`**
   - *Razón*: Reutiliza la lectura de `config.json` existente en `backend/app.py`, realiza lectura-modificación-escritura atómica preservando `faqs_jeff`, `tareas` y metadatos, y evita exponer un endpoint genérico que pueda sobrescribir accidentalmente campos administrativos.

## Risks / Trade-offs

- **Ollama no iniciado o modelo no descargado en el host** → Capturar `httpx.ConnectError`, `httpx.TimeoutException` y respuestas HTTP de error de Ollama dentro del generador SSE, emitiendo un mensaje claro en español como token y cerrando con `{"tipo": "fin"}` para no colgar el estado `cargando` en el frontend.
- **Condición de carrera menor al editar `config.json`** → Suficiente para el MVP local con un único docente concurrente; se preserva el UTF-8 con `ensure_ascii=False, indent=2`.
- **Diferencia de nombre de tag en Ollama (`qwen3:8b` vs variante local)** → Configurable por variable de entorno `OLLAMA_MODEL` en `docker-compose.yml` sin reconstruir la imagen.
