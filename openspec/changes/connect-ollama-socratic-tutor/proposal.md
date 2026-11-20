# Proposal

## Why

Actualmente el endpoint `POST /api/chat` de [backend/app.py](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/backend/app.py) es un *placeholder* que devuelve un mensaje estático, y la pestaña **Reglas Socráticas** en la vista docente ([DocenteView.tsx](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/frontend/src/views/profesor/DocenteView.tsx)) aún no permite editar ni guardar reglas. Mientras el técnico avanza en el enrutador "Jeff" y el motor RAG, el líder del proyecto puede avanzar conectando el backend con el motor local **Ollama** (modelo `Qwen 3.8 8B`), aplicando las reglas socráticas configurables por el profesor y habilitando la experiencia de chat socrático multi-turno en la vista del alumno.

## What Changes

- Conectar `POST /api/chat` en [backend/app.py](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/backend/app.py) con la API de streaming de Ollama (`OLLAMA_HOST`, modelo configurable vía `OLLAMA_MODEL`) para generar respuestas socráticas token por token vía SSE.
- Incorporar un ensamblador de *System Prompt* socrático que combine las reglas institucionales base (andamiaje cognitivo, prohibición de entregar soluciones directas o código resuelto, resistencia a *prompt injection*) con las `reglas_socraticas` específicas del ramo leídas desde `backend/data/ramos/<CODIGO>/config.json`.
- Aceptar historial de conversación de la sesión (`historial`) en `POST /api/chat` para mantener coherencia socrática multi-turno, sin persistir identidad del estudiante.
- Dejar un punto de extensión desacoplado en `/api/chat` para integrar posteriormente los módulos externos `router_jeff` y `rag_engine` sin modificar el contrato con el frontend.
- Exponer `PUT /api/ramos/{codigo_ramo}/reglas-socraticas` en el backend para actualizar `reglas_socraticas` en `config.json`.
- Implementar el editor de reglas socráticas en la pestaña **Reglas Socráticas** de [DocenteView.tsx](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/frontend/src/views/profesor/DocenteView.tsx) y actualizar [ChatWindow.tsx](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/frontend/src/views/alumno/ChatWindow.tsx) para enviar historial de sesión y mostrar estado de espera/errores de Ollama.

## Capabilities

### New Capabilities

- `socratic-tutor`: Orquestación de tutoría socrática por streaming SSE contra Ollama local, combinando prompt institucional, reglas socráticas del ramo e historial efímero de sesión.
- `socratic-rules-config`: Consulta, edición y persistencia de las `reglas_socraticas` de cada asignatura desde la interfaz docente hacia `config.json`.

### Modified Capabilities

<!-- Ninguna capacidad existente cambia sus requerimientos a nivel de especificación. -->

## Impact

- **Backend**: [backend/app.py](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/backend/app.py) (cliente `httpx` asíncrono hacia Ollama, nuevos modelos Pydantic y endpoint `PUT /api/ramos/{codigo_ramo}/reglas-socraticas`), nuevo módulo opcional `backend/socratic_prompt.py` (o función dedicada), y variable `OLLAMA_MODEL` en [docker-compose.yml](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/docker-compose.yml).
- **Frontend**: [frontend/src/types.ts](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/frontend/src/types.ts), [frontend/src/services/api.ts](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/frontend/src/services/api.ts), [frontend/src/views/profesor/DocenteView.tsx](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/frontend/src/views/profesor/DocenteView.tsx) y [frontend/src/views/alumno/ChatWindow.tsx](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/frontend/src/views/alumno/ChatWindow.tsx).
- **Dependencias**: Requiere Ollama corriendo en el host (`OLLAMA_HOST=http://host.docker.internal:11434`) con el modelo Qwen descargado para pruebas en vivo.
