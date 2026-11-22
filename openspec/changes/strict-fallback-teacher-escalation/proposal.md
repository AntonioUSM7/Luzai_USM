# Proposal

## Why

Actualmente en `/api/chat` (`backend/app.py`), si una consulta no coincide con `faqs_jeff` y tampoco tiene contexto suficiente en el RAG (por ejemplo, dudas administrativas no registradas o preguntas académicas sin respaldo en apuntes), el sistema aún puede invocar a Ollama usando conocimiento general o devolver una respuesta genérica de fuera de foco sin ofrecer salida al estudiante. Esto consume GPU innecesariamente, expone al tutor socrático a alucinar fuera del material oficial y no deja registro de qué dudas reales quedaron sin respuesta para el profesor.

## What Changes

- Agregar configuración por ramo (`config_fallback` en `config.json`) para habilitar modo estricto de contención, mensaje de respaldo y escalamiento docente.
- Incorporar la capa `FALLBACK_DOCENTE` en `POST /api/chat` (`backend/app.py`): cuando Jeff no hace match y el RAG no alcanza contexto suficiente (o la consulta queda fuera de alcance sin ser saludo), responder de forma determinista a $0 GPU con `canal: "FALLBACK_DOCENTE"` y bandera `puede_escalar: true`.
- Agregar persistencia y endpoints de consultas escaladas por ramo (`backend/data/ramos/{CODIGO}/consultas_profesor.json`):
  - `POST /api/ramos/{codigo_ramo}/consultas` para registrar una duda confirmada por el estudiante.
  - `GET /api/ramos/{codigo_ramo}/consultas` para listar dudas en la vista docente.
  - `POST /api/ramos/{codigo_ramo}/consultas/{consulta_id}/responder` para que el profesor responda o descarte la consulta y opcionalmente la convierta en una nueva entrada de `faqs_jeff` en `config.json`.
- Actualizar el frontend del alumno (`frontend/src/views/alumno/ChatWindow.tsx` y `frontend/src/services/api.ts`) para leer metadatos SSE (`canal`, `puede_escalar`) y mostrar el botón de confirmación *"Enviar esta pregunta al profesor"*.
- Actualizar la vista docente (`frontend/src/views/profesor/DocenteView.tsx`) con un buzón de consultas pendientes donde el profesor pueda responder, descartar o guardar la respuesta como FAQ de Jeff.

## Capabilities

### New Capabilities
- `teacher-escalation`: Permite escalar consultas no resueltas por Jeff ni por el tutor socrático hacia un buzón docente por ramo previa confirmación del estudiante, y permite al profesor responderlas o convertirlas en FAQs de Jeff.

### Modified Capabilities
- `semantic-router`: Extiende el flujo de enrutamiento para aplicar fallback estricto a $0 GPU (`FALLBACK_DOCENTE`) cuando no hay coincidencia en Jeff ni contexto RAG suficiente, evitando invocar al LLM sin respaldo.

## Impact

- **Backend:** `backend/app.py`, `backend/router_jeff.py`, `backend/data/ramos/*/config.json`, nuevo almacenamiento por ramo `consultas_profesor.json`, y pruebas unitarias/integración en `backend/`.
- **Frontend:** `frontend/src/services/api.ts`, `frontend/src/types.ts`, `frontend/src/views/alumno/ChatWindow.tsx`, `frontend/src/views/profesor/DocenteView.tsx`.
- **APIs:** Nuevos endpoints `/api/ramos/{codigo_ramo}/consultas*` y metadatos adicionales en eventos SSE `inicio`/`fin` de `POST /api/chat` (retrocompatible con clientes que solo leen `tipo === "token"`).
